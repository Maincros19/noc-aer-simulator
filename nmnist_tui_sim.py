import torch
import torch.nn as nn
import snntorch as snn
from snntorch import surrogate
from snntorch import functional as SF
import tonic
from torch.utils.data import DataLoader
import sys
import os
import time
import numpy as np
import argparse
import random
import matplotlib
matplotlib.use('Agg') # Fuerza renderizado en memoria sin ventana gráfica
import matplotlib.pyplot as plt
import seaborn as sns
import cv2
import glob
import shutil
import networkx as nx

# Intentamos importar curses, pero permitimos que falle
try:
    import curses
    import locale
    locale.setlocale(locale.LC_ALL, "")
    HAS_CURSES = True
except (ImportError, Exception):
    HAS_CURSES = False

# Add build directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'cpp_simulator', 'build'))
import noc_simulator_pybind as ncs

# --- Configuration ---
TECH = {
    "name": "Neuromorphic-Specialized (22nm FD-SOI)",
    "energy_per_spike": 0.85,
    "f_max_mhz": 1200,
    "static_power_uw": 1.2
}
def parse_args():
    parser = argparse.ArgumentParser(description="NoC-AER Simulator")
    parser.add_argument("--dim", type=int, default=4, help="Dimensión de la malla NoC (ej. 4 para 4x4)")
    parser.add_argument("--inj_buffer", type=int, default=1024, help="Tamaño del buffer de inyección (LOCAL)")
    parser.add_argument("--net_buffer", type=int, default=32, help="Tamaño del buffer de red (N, S, E, W)")
    parser.add_argument("--epochs", type=int, default=1, help="Épocas de entrenamiento")
    parser.add_argument("--iters", type=int, default=20, help="Iteraciones por época")
    parser.add_argument("--samples", type=int, default=1, help="Muestras para simulación NoC")
    parser.add_argument("--lr", type=float, default=2e-3, help="Tasa de aprendizaje")
    parser.add_argument("--video_name", type=str, default="noc_traffic", help="Nombre del archivo de video de salida")
    return parser.parse_args()

def set_determinism(seed=42):
    """Fija todas las semillas para garantizar la reproducibilidad."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    # Aunque usas CPU, es buena práctica por si en el futuro cambias a GPU
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    # Fuerza a PyTorch a usar algoritmos deterministas donde sea posible
    torch.use_deterministic_algorithms(True, warn_only=True)

    # Configurar variable de entorno para determinismo en ciertas operaciones CUDA/cuDNN
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'

def generate_simulation_video(frames_dir, output_name="noc_heatmap.mp4"):
    images = sorted(glob.glob(f"{frames_dir}/*.png"))
    if not images:
        return

    frame = cv2.imread(images[0])
    height, width, _ = frame.shape
    video = cv2.VideoWriter(output_name, cv2.VideoWriter_fourcc(*'mp4v'), 10, (width, height))

    for img_path in images:
        video.write(cv2.imread(img_path))

    video.release()
    print(f"\n✅ Video de tráfico generado: {output_name}")



# --- Configuración inicial (fuera del main o al principio de main_compat) ---
def setup_topology(dim):
    G = nx.grid_2d_graph(dim, dim)
    # Ajustamos posiciones para que R0 esté arriba a la izquierda
    pos = {node: (node[0], dim - 1 - node[1]) for node in G.nodes()}
    return G, pos

# Mapeo de puertos para claridad
PORT_NAMES = {0: 'LOCAL', 1: 'NORTH', 2: 'SOUTH', 3: 'EAST', 4: 'WEST'}


# --- Model Definition ---
spike_grad = surrogate.atan()
beta = 0.5

class CSNN(nn.Module):
    def __init__(self, beta, spike_grad):
        super().__init__()
        self.conv1 = nn.Conv2d(2, 12, 5)
        self.snn1 = snn.Leaky(beta=beta, spike_grad=spike_grad)
        self.pool1 = nn.MaxPool2d(2)
        self.conv2 = nn.Conv2d(12, 32, 5)
        self.snn2 = snn.Leaky(beta=beta, spike_grad=spike_grad)
        self.pool2 = nn.MaxPool2d(2)
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(32*5*5, 10)
        self.snn3 = snn.Leaky(beta=beta, spike_grad=spike_grad)

    def forward(self, x):
        mem1 = self.snn1.init_leaky()
        mem2 = self.snn2.init_leaky()
        mem3 = self.snn3.init_leaky()

        # Listas para guardar lo que enviaremos a la NoC (ya con pooling)
        spk1_pooled_rec = []
        spk2_pooled_rec = []
        spk_out_rec = []

        for step in range(x.size(0)):
            # Capa 1: Conv -> SNN
            cur = self.conv1(x[step])
            spk1, mem1 = self.snn1(cur, mem1)

            # Operación de Pooling local (lo que reduce los datos antes de la NoC)
            cur_p1 = self.pool1(spk1)
            spk1_pooled_rec.append(cur_p1)

            # Capa 2: Recibe la salida de pool1
            cur = self.conv2(cur_p1)
            spk2, mem2 = self.snn2(cur, mem2)

            # Segundo Pooling local
            cur_p2 = self.pool2(spk2)
            spk2_pooled_rec.append(cur_p2)

            # Capa de Salida
            cur = self.flatten(cur_p2)
            cur = self.fc1(cur)
            spk_out, mem3 = self.snn3(cur, mem3)
            spk_out_rec.append(spk_out)

        # Retornamos los stacks de los tensores ya procesados paso a paso
        return (torch.stack(spk_out_rec),
                torch.stack(spk1_pooled_rec),
                torch.stack(spk2_pooled_rec))

# --- Utilidades de Mapeo y Dashboard ---
def get_node_mapping(dim):
    total_nodes = dim * dim
    nodes_per_layer = total_nodes // 4
    return {
        "input":  list(range(0, nodes_per_layer)),
        "snn1":   list(range(nodes_per_layer, nodes_per_layer * 2)),
        "snn2":   list(range(nodes_per_layer * 2, nodes_per_layer * 3)),
        "output": list(range(nodes_per_layer * 3, total_nodes))
    }

def draw_dashboard_compat(phase, progress, args, metrics=None, train_info=None):
    os.system('clear' if os.name == 'posix' else 'cls')
    width = 75
    print("\n" + f" [ NoC-AER SIMULATOR: Malla {args.dim}x{args.dim} ] ".center(width, "="))
    print(f"\n FASE: {phase}")

    bar_w = 40
    filled = int(bar_w * progress)
    bar = "█" * filled + "░" * (bar_w - filled)
    print(f" PROGRESO: [{bar}] {progress*100:.1f}%")

    if train_info:
        print("\n +-- ENTRENAMIENTO -------------------------------------------")
        print(f" | Epoca: {train_info.get('epoch')} | Iter: {train_info.get('iter')}/{args.iters}")
        print(f" | Loss: {train_info.get('loss', 0):.4f} | Acc: {train_info.get('acc', 0):.2f}%")
        print(" +------------------------------------------------------------")

    if metrics:
        print("\n +-- RESULTADOS HARDWARE -------------------------------------")
        print(f" | Spikes Gen:    {metrics.get('spikes', 0):,}")
        print(f" | Flits NoC:     {metrics.get('flits', 0):,}")
        print(f" | Lat. Total:    {metrics.get('latency', 0):.2f} ciclos (End-to-End)")
        print(f" |  ├─ Inyección: {metrics.get('inj_latency', 0):.2f} ciclos (Cola origen)")
        print(f" |  └─ Red:       {metrics.get('net_latency', 0):.2f} ciclos (Vuelo y saltos)")
        print(f" | Jitter (AER):  {metrics.get('jitter', 0):.2f} ciclos")
        print(f" | Throughput:    {metrics.get('throughput', 0):.6f} flits/ciclo/nodo")
        print(f" | Energia Total: {metrics.get('energy', 0):.6f} uJ")
        print(f" | Eficiencia:    {metrics.get('energy_eff', 0):,.2f} flits/uJ")
        print(f" | Rendimiento:   {metrics.get('temporal_perf', 0):,.0f} flits/segundo")
        print(" +------------------------------------------------------------")
        print(f"\n PRECISION IA FINAL:  {metrics.get('accuracy', 0):.2f}%")

def main_compat():
    set_determinism(42)

    args = parse_args()
    device = torch.device("cpu")
    nodes = get_node_mapping(args.dim)

    # Dataset
    sensor_size = (34, 34, 2)
    transform = tonic.transforms.Compose([
        tonic.transforms.ToFrame(sensor_size=sensor_size, n_time_bins=15),
        torch.from_numpy,
    ])

    draw_dashboard_compat("Cargando Dataset N-MNIST...", 0.05, args)
    trainset = tonic.datasets.NMNIST(save_to='./data', train=True, transform=transform)
    testset = tonic.datasets.NMNIST(save_to='./data', train=False, transform=transform)

    # Creamos un generador determinista para el shuffle
    g = torch.Generator()
    g.manual_seed(42)

    train_loader = DataLoader(
        trainset,
        batch_size=32,
        collate_fn=tonic.collation.PadTensors(batch_first=False),
        shuffle=True,
        generator=g  # <--- Añadir el generador
    )

    test_loader = DataLoader(
        testset,
        batch_size=32,
        collate_fn=tonic.collation.PadTensors(batch_first=False),
        shuffle=False
    )

    # Fase 1: Entrenamiento Real
    net = CSNN(beta, spike_grad).to(device)
    optimizer = torch.optim.Adam(net.parameters(), lr=args.lr)
    loss_fn = SF.mse_count_loss(correct_rate=0.8, incorrect_rate=0.2)

    acc = 0.0
    for epoch in range(args.epochs):
        for i, (data, targets) in enumerate(train_loader):
            if i >= args.iters: break

            net.train()
            spk_out, _, _ = net(data.to(device).float())
            loss_val = loss_fn(spk_out, targets.to(device))

            optimizer.zero_grad()
            loss_val.backward()
            optimizer.step()

            if i % 2 == 0:
                with torch.no_grad():
                    net.eval()
                    test_data, test_targets = next(iter(test_loader))
                    spk_test, _, _ = net(test_data.float())
                    _, predicted = spk_test.sum(dim=0).max(1)
                    acc = (predicted == test_targets).sum().item() / test_targets.size(0) * 100

                draw_dashboard_compat("Entrenando Modelo SNN...", 0.1 + (i/args.iters)*0.4, args,
                                     train_info={'epoch': epoch+1, 'iter': i, 'loss': loss_val.item(), 'acc': acc})

    # Fase 2: Simulación NoC
   # Fase 2: Simulación NoC
    draw_dashboard_compat("Inyectando Tráfico en NoC...", 0.6, args)

    # --- 1. INICIALIZACIÓN (Esto faltaba en tu bucle) ---
    event_queue = ncs.EventQueue()
    network = ncs.Network(args.dim, args.dim, event_queue)
    for r in range(args.dim * args.dim):
        network.getRouter(r).setBufferSizes(args.inj_buffer, args.net_buffer)

    # --- 2. INYECCIÓN DE TRÁFICO (Basado en la inferencia de la SNN) ---
    flit_id, total_spikes = 0, 0
    net.eval()
    with torch.no_grad():
        for i in range(args.samples):
            data, _ = testset[i]
            data = data.to(device).unsqueeze(1)
            spk_out, spk1_p, spk2_p = net(data.float())

            for step in range(data.size(0)):
                t_base = step * 2000 + (i * 50000)

                def inject_layer(tensor, src_grp, dst_grp, fan, offset, spread):
                    nonlocal flit_id, total_spikes
                    idxs = (tensor > 0).nonzero(as_tuple=False)
                    total_spikes += len(idxs)
                    for idx, _ in enumerate(idxs):
                        src = src_grp[idx % len(src_grp)]
                        dsts = [dst_grp[k % len(dst_grp)] for k in range(fan)]
                        for j, d in enumerate(dsts):
                            t_sim = t_base + offset + (idx % spread) + (j % 5)
                            flit = ncs.Flit(flit_id, 0, ncs.FlitType.BODY, src, d, src, int(t_sim))
                            network.getRouter(src).injectFlit(flit, int(t_sim))
                            flit_id += 1

                inject_layer(data[step], nodes['input'], nodes['snn1'], 12, offset=0, spread=100)
                inject_layer(spk1_p[step], nodes['snn1'], nodes['snn2'], 32, offset=200, spread=800)
                inject_layer(spk2_p[step], nodes['snn2'], nodes['output'], 10, offset=1200, spread=100)


    # --- 3. MONITOR AVANZADO DE TOPOLOGÍA Y BUFFERS ---

    draw_dashboard_compat("Simulando trafico de la red", 0.85, args)
    """ GENERACION DE MAPA DE CALOR DESACTIVADO MOMENTANEAMENTE
    frames_dir = "sim_frames"
    if os.path.exists(frames_dir): shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    # Configuración de la Topología (Grafo de la malla)
    G = nx.grid_2d_graph(args.dim, args.dim)
    pos = {node: (node[0], args.dim - 1 - node[1]) for node in G.nodes()}

    frame_idx = 0
    events_per_frame = 15000 # Ajustado para un buen equilibrio entre detalle y velocidad

    while not event_queue.isEmpty():
        network.stepSimulation(events_per_frame)

        # Creamos una figura con una rejilla: Izquierda para el Grafo, Derecha para detalles
        fig = plt.figure(figsize=(18, 9), facecolor='#121212')
        gs = fig.add_gridspec(2, 3)

        # --- PANEL A: MONITOR DE TOPOLOGÍA Y BLOQUEOS (STALLS) ---
        ax_topo = fig.add_subplot(gs[:, :2])
        ax_topo.set_facecolor('#121212')

        # Dibujamos los enlaces base (físicos)
        nx.draw_networkx_edges(G, pos, ax=ax_topo, edge_color='#333333', width=1.5)

        # Dibujamos los "Stalls": Flechas rojas cuando un enlace está bloqueado por falta de créditos
        for r_id in range(args.dim * args.dim):
            router = network.getRouter(r_id)
            stalls = router.getLinkStallStatus()
            x_c, y_c = router.getX(), router.getY()

            # Mapeo visual de puertos: N(arriba), S(abajo), E(derecha), W(izquierda)
            offsets = {1: (0, 0.4), 2: (0, -0.4), 3: (0.4, 0), 4: (-0.4, 0)}

            for p_idx, is_stalled in enumerate(stalls):
                if is_stalled and p_idx in offsets:
                    dx, dy = offsets[p_idx]
                    ax_topo.arrow(x_c, args.dim-1-y_c, dx, dy,
                                 color='#ff4d4d', head_width=0.1, width=0.04, zorder=5)

        # Routers coloreados por ocupación TOTAL (visión general)
        total_occ = [network.getRouter(r).getBufferOccupancy() for r in range(args.dim**2)]
        nodes = nx.draw_networkx_nodes(G, pos, ax=ax_topo, node_size=800,
                                       node_color=total_occ, cmap=plt.cm.YlGnBu, vmin=0, vmax=50)
        nx.draw_networkx_labels(G, pos, ax=ax_topo, font_color='white', font_size=9, font_weight='bold')
        ax_topo.set_title(f"TOPOLOGÍA NoC | Rojo: Enlace Bloqueado | Ciclo: {network.getSimulationTime()}",
                          color='white', fontsize=14, pad=15)

        # --- PANEL B: DESGLOSE TÉCNICO (BUFFERS ESPECÍFICOS) ---
        # Extraemos datos por puerto: LOCAL (inyección) y NORTH (ejemplo de red)
        local_data = np.zeros((args.dim, args.dim))
        north_data = np.zeros((args.dim, args.dim))

        for r_id in range(args.dim**2):
            router = network.getRouter(r_id)
            occ = router.getDetailedOccupancy() # [LOCAL, NORTH, SOUTH, EAST, WEST]
            local_data[router.getY(), router.getX()] = occ[0]
            north_data[router.getY(), router.getX()] = occ[1]

        # Puerto LOCAL (Muestra si las neuronas están saturando la entrada)
        ax_l = fig.add_subplot(gs[0, 2])
        sns.heatmap(local_data, annot=True, fmt=".0f", cmap="Oranges", vmin=0, vmax=20, ax=ax_l, cbar=False)
        ax_l.set_title("Ocupación: Puerto LOCAL (Inyección)", color='white')

        # Puerto NORTH (Muestra el tráfico fluyendo hacia arriba)
        ax_n = fig.add_subplot(gs[1, 2])
        sns.heatmap(north_data, annot=True, fmt=".0f", cmap="Reds", vmin=0, vmax=20, ax=ax_n, cbar=False)
        ax_n.set_title("Ocupación: Puerto NORTH (Red)", color='white')

        plt.tight_layout()
        plt.savefig(f"{frames_dir}/f_{frame_idx:04d}.png", facecolor='#121212')
        plt.close()
        frame_idx += 1

    # Al final de main_compat, usa el nombre pasado por argumento
    generate_simulation_video(frames_dir, f"{args.video_name}.mp4")
    if os.path.exists(frames_dir):
        print(f"🧹 Limpiando frames temporales en '{frames_dir}'...")
        shutil.rmtree(frames_dir)
        print("✅ Carpeta de frames eliminada.")
    """

    # EJECUCION DE LA SIMULACION SIN GENERACION DE MAPA DE CALOR
    network.runSimulation()

    # --- Métricas Finales (Cálculos originales) ---
    sim_t = network.getSimulationTime()
    period_ns = 1000.0 / TECH['f_max_mhz']
    total_energy_uj = (network.getTotalForwarded() * TECH['energy_per_spike']) / 1e6 + (TECH['static_power_uw'] * (sim_t * period_ns)) / 1e6
    energy_eff = flit_id / total_energy_uj if total_energy_uj > 0 else 0
    total_time_seconds = sim_t * period_ns * 1e-9
    temporal_perf = flit_id / total_time_seconds if total_time_seconds > 0 else 0

    metrics = {
        "spikes": total_spikes, "flits": flit_id,
        "latency": network.getAvgLatency(),
        "inj_latency": network.getAvgInjectionLatency(), # NUEVO
        "net_latency": network.getAvgNetworkLatency(),   # NUEVO
        "jitter": network.getAvgJitter(), "energy": total_energy_uj, "accuracy": acc,
        "energy_eff": energy_eff, "temporal_perf": temporal_perf,
        "throughput": (network.getTotalFlitsReceived() / sim_t) / (args.dim**2) if sim_t > 0 else 0,
    }

    draw_dashboard_compat("Simulación Completada ✅", 1.0, args, metrics=metrics)

if __name__ == "__main__":
    main_compat()
