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

# Variable global para saber cuántas líneas tenemos que retroceder el cursor
lineas_impresas = 0

def draw_dashboard_compat(phase, progress, args, metrics=None, train_info=None):
    global lineas_impresas

    out = []
    width = 75
    out.append(f" [ NoC-AER SIMULATOR: Malla {args.dim}x{args.dim} ] ".center(width, "="))
    out.append("") # Línea en blanco en lugar de \n
    out.append(f" FASE: {phase}")

    bar_w = 40
    filled = int(bar_w * progress)
    bar = "█" * filled + "░" * (bar_w - filled)
    out.append(f" PROGRESO: [{bar}] {progress*100:.1f}%")

    if train_info:
        out.append("")
        out.append(" +-- ENTRENAMIENTO -------------------------------------------")
        out.append(f" | Epoca: {train_info.get('epoch')} | Iter: {train_info.get('iter')}/{args.iters}")
        out.append(f" | Loss: {train_info.get('loss', 0):.4f} | Acc: {train_info.get('acc', 0):.2f}%")
        out.append(" +------------------------------------------------------------")

    if metrics:
        out.append("")
        out.append(" +-- RESULTADOS HARDWARE -------------------------------------")
        out.append(f" | Spikes Gen:       {metrics.get('spikes', 0):,}")
        out.append(f" | Flits Generados:  {metrics.get('flits_generados', 0):,} (Producidos por SNN)")
        out.append(f" | Flits Inyectados: {metrics.get('flits_inyectados', 0):,} (Enviados al nodo origen)")
        out.append(f" | Flits Eyectados:  {metrics.get('flits_eyectados', 0):,} (Recibidos en destino)")
        out.append(f" | Flits Procesados: {metrics.get('flits_procesados', 0):,} (Total de saltos/ruteos)")
        out.append(f" | Lat. Total:       {metrics.get('latency', 0):.2f} ciclos (End-to-End)")
        out.append(f" |  ├─ Inyección:    {metrics.get('inj_latency', 0):.2f} ciclos (Cola origen)")
        out.append(f" |  └─ Red:          {metrics.get('net_latency', 0):.2f} ciclos (Vuelo y saltos)")
        out.append(f" | Jitter (AER):     {metrics.get('jitter', 0):.2f} ciclos")
        out.append(f" | Throughput:       {metrics.get('throughput', 0):.6f} flits/ciclo/nodo")
        out.append(f" | Energia Total:    {metrics.get('energy', 0):.6f} uJ")
        out.append(f" | Eficiencia:       {metrics.get('energy_eff', 0):,.2f} flits/uJ")
        out.append(f" | Throughput Físico:{metrics.get('temporal_perf', 0):,.0f} flits/s")
        out.append(" +------------------------------------------------------------")
        out.append("")
        out.append(f" PRECISION IA FINAL:  {metrics.get('accuracy', 0):.2f}%")

    texto_final = "\n".join(out)

    # Si ya hemos impreso algo antes, subimos el cursor y borramos hacia abajo
    if lineas_impresas > 0:
        # \033[{n}A mueve el cursor arriba. \033[J limpia hasta el final
        sys.stdout.write(f"\033[{lineas_impresas}A\033[J")

    sys.stdout.write(texto_final + "\n")
    sys.stdout.flush()

    # Ahora la cantidad de líneas generadas coincide perfectamente
    lineas_impresas = len(out)

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
# Fase 2: Co-Simulación NoC Paso a Paso (Intercalada SNN-NoC)
    draw_dashboard_compat("Iniciando Fase 2: Co-Simulación Temporal...", 0.6, args)

    # --- 1. INICIALIZACIÓN DE LA RED ---
    event_queue = ncs.EventQueue()
    network = ncs.Network(args.dim, args.dim, event_queue)
    for r in range(args.dim * args.dim):
        network.getRouter(r).setBufferSizes(args.inj_buffer, args.net_buffer)

    flit_id, total_spikes = 0, 0
    net.eval()

    # Correspondencia Temporal Física: 1 ms SNN = 1,200,000 ciclos NoC (a 1200 MHz)
    CYCLES_PER_SNN_STEP = int((TECH["f_max_mhz"] * 1e6) * 1e-3)

    with torch.no_grad():
        for i in range(args.samples):
            data, _ = testset[i]
            data = data.to(device).unsqueeze(1) # Matriz de la muestra corriente

            # Inicializamos los estados de membrana de snnTorch al inicio de la muestra
            mem1 = net.snn1.init_leaky()
            mem2 = net.snn2.init_leaky()
            mem3 = net.snn3.init_leaky()

            total_steps = data.size(0)

            for step in range(total_steps):
                # --- A. GENERACIÓN INMEDIATA (1 SOLO TIMESTEP SNN) ---
                # Replicamos el pipeline convolucional-SNN paso a paso de la clase CSNN
                cur = net.conv1(data[step].float())
                spk1, mem1 = net.snn1(cur, mem1)
                cur_p1 = net.pool1(spk1)

                cur = net.conv2(cur_p1)
                spk2, mem2 = net.snn2(cur, mem2)
                cur_p2 = net.pool2(spk2)

                cur = net.flatten(cur_p2)
                cur = net.fc1(cur)
                spk_out, mem3 = net.snn3(cur, mem3)

                # Base de tiempo absoluta para este paso temporal concreto
                t_base = step * CYCLES_PER_SNN_STEP + (i * total_steps * CYCLES_PER_SNN_STEP)

                # Definimos la función de inyección local adaptada al paso actual
                def inject_layer_step(tensor, src_grp, dst_grp, fan, offset_cycles):
                    nonlocal flit_id, total_spikes
                    idxs = (tensor > 0).nonzero(as_tuple=False)
                    num_spikes = len(idxs)

                    if num_spikes == 0:
                        return

                    total_spikes += num_spikes
                    cycles_between_spikes = CYCLES_PER_SNN_STEP // (num_spikes + 1)

                    for idx_num, _ in enumerate(idxs):
                        src = src_grp[idx_num % len(src_grp)]
                        dsts = [dst_grp[k % len(dst_grp)] for k in range(fan)]

                        for j, d in enumerate(dsts):
                            # El tiempo del flit se calcula de manera proporcional dentro del paso actual
                            t_sim = t_base + offset_cycles + (idx_num * cycles_between_spikes) + j
                            flit = ncs.Flit(flit_id, 0, ncs.FlitType.BODY, src, d, src, int(t_sim))
                            network.getRouter(src).injectFlit(flit, int(t_sim))
                            flit_id += 1

                # --- B. INYECCIÓN INMEDIATA DEL TIMESTEP ---
                inject_layer_step(data[step], nodes['input'], nodes['snn1'], 12, offset_cycles=0)
                inject_layer_step(cur_p1, nodes['snn1'], nodes['snn2'], 32, offset_cycles=50000)
                inject_layer_step(cur_p2, nodes['snn2'], nodes['output'], 10, offset_cycles=100000)

                # --- C. SIMULACIÓN INMEDIATA (El Hardware alcanza a la SNN) ---
                # Definimos la barrera temporal: el hardware no puede pasarse del tiempo de este step
                tiempo_limite = t_base + CYCLES_PER_SNN_STEP

                # Consumimos la cola de eventos en C++ poco a poco hasta llegar al límite de tiempo
                while not event_queue.isEmpty() and event_queue.getCurrentTime() < tiempo_limite:
                    network.stepSimulation(1) # Avanza procesando exactamente un evento por ciclo

                # Actualización en vivo del Dashboard
                global_step = i * total_steps + step
                max_global_steps = args.samples * total_steps
                progreso_sim = 0.60 + (global_step / max_global_steps) * 0.35
                if step % 2 == 0:
                    draw_dashboard_compat("Co-Simulando SNN y NoC paso a paso...", progreso_sim, args)

    # --- 3. LIMPIEZA DE EVENTOS RESIDUALES ---
    # Procesamos cualquier flit en vuelo o créditos remanentes que queden tras el último step
    draw_dashboard_compat("Procesando tráfico residual en la NoC...", 0.95, args)
    while not event_queue.isEmpty():
        network.stepSimulation(25000)

    # --- 4. MÉTRICAS FINALES ---
    sim_t = network.getSimulationTime()
    period_ns = 1000.0 / TECH['f_max_mhz']
    total_energy_uj = (network.getTotalForwarded() * TECH['energy_per_spike']) / 1e6 + (TECH['static_power_uw'] * (sim_t * period_ns)) / 1e6
    energy_eff = flit_id / total_energy_uj if total_energy_uj > 0 else 0
    total_time_seconds = sim_t * period_ns * 1e-9
    temporal_perf = flit_id / total_time_seconds if total_time_seconds > 0 else 0

    metrics = {
        "spikes": total_spikes,
        "flits_generados": flit_id,
        "flits_inyectados": network.getTotalFlitsInjected(),
        "flits_eyectados": network.getTotalFlitsReceived(),
        "flits_procesados": network.getTotalForwarded(),
        "latency": network.getAvgLatency(),
        "inj_latency": network.getAvgInjectionLatency(),
        "net_latency": network.getAvgNetworkLatency(),
        "jitter": network.getAvgJitter(),
        "energy": total_energy_uj,
        "accuracy": acc,
        "energy_eff": energy_eff,
        "temporal_perf": temporal_perf,
        "throughput": (network.getTotalFlitsReceived() / sim_t) / (args.dim**2) if sim_t > 0 else 0,
    }

    draw_dashboard_compat("Simulación Completada ✅", 1.0, args, metrics=metrics)

if __name__ == "__main__":
    main_compat()
