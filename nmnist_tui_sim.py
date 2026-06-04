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
    parser.add_argument("--freq", type=int, default=1200, help="Frecuencia NoC en MHz (Para Test de Estrés)")
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

def save_heatmap(network, dim, current_time, frames_dir, net_buffer_size):
    plt.style.use('dark_background')
    
    # Obtener mapeo de nodos para identificar capas
    node_mapping = get_node_mapping(dim)
    layer_colors = {
        "input": "#2ecc71",  # Verde
        "snn1": "#3498db",   # Azul
        "snn2": "#9b59b6",   # Púrpura
        "output": "#e74c3c"  # Rojo
    }

    # Matriz expandida para intercalar enlaces entre los routers
    grid_size = dim * 2 - 1
    grid = np.full((grid_size, grid_size), np.nan)
    labels = np.full((grid_size, grid_size), "", dtype=object)

    for y in range(dim):
        for x in range(dim):
            r_id = y * dim + x
            router = network.getRouter(r_id)
            activity = router.getLinkActivity()

            # 1. Posición del Router
            grid[y*2, x*2] = np.nan
            labels[y*2, x*2] = f"R{r_id}"

            # 2. Enlace HORIZONTAL
            if x < dim - 1:
                r_east = network.getRouter(y * dim + x + 1)
                east_bound = activity[3]
                west_bound = r_east.getLinkActivity()[4]
                link_load = east_bound + west_bound
                grid[y*2, x*2 + 1] = link_load
                labels[y*2, x*2 + 1] = str(link_load) if link_load > 0 else ""

            # 3. Enlace VERTICAL
            if y < dim - 1:
                r_south = network.getRouter((y + 1) * dim + x)
                south_bound = activity[2]
                north_bound = r_south.getLinkActivity()[1]
                link_load = south_bound + north_bound
                grid[y*2 + 1, x*2] = link_load
                labels[y*2 + 1, x*2] = str(link_load) if link_load > 0 else ""

    # Resetear contadores de actividad
    for r in range(dim * dim):
        network.getRouter(r).resetLinkActivity()

    fig, ax = plt.subplots(figsize=(12, 10))
    cmap = plt.cm.magma.copy()
    cmap.set_bad(color='#1a1a1a')
    
    vmax_limit = max(10, np.nanmax(grid) if np.any(~np.isnan(grid)) else 10)

    # Dibujar el heatmap de enlaces
    sns.heatmap(grid, cmap=cmap, annot=labels, fmt="",
                linewidths=1, linecolor='#333333',
                vmin=0, vmax=vmax_limit,
                cbar_kws={'label': 'Flits en tránsito', 'shrink': 0.8}, ax=ax)

    # Superponer los Routers con colores de capa
    for y in range(dim):
        for x in range(dim):
            r_id = y * dim + x
            # Determinar a qué capa pertenece el router
            layer_name = "unknown"
            for name, ids in node_mapping.items():
                if r_id in ids:
                    layer_name = name
                    break
            
            color = layer_colors.get(layer_name, "#555555")
            # Dibujar un rectángulo sobre la celda del router
            rect = plt.Rectangle((x*2, y*2), 1, 1, fill=True, color=color, alpha=0.8, transform=ax.transData)
            ax.add_patch(rect)
            # Añadir el texto del router
            ax.text(x*2 + 0.5, y*2 + 0.5, f"R{r_id}\n({layer_name.upper()})", 
                    color='white', ha='center', va='center', fontweight='bold', fontsize=8)

    # Añadir etiquetas de capa en los laterales
    for i, (layer_name, color) in enumerate(layer_colors.items()):
        plt.text(grid_size + 0.5, i * (grid_size/4) + 1, f"■ {layer_name.upper()}", 
                 color=color, fontweight='bold', fontsize=12)

    ax.set_title(f"Visualización Arquitectónica NoC-AER\nCiclo: {current_time:,} | Tráfico de Impulsos SNN", 
                 pad=30, fontsize=18, fontweight='bold', color='white')
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Añadir un marco elegante
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#444444')
        spine.set_linewidth(2)

    plt.tight_layout()
    filename = os.path.join(frames_dir, f"frame_{current_time:015d}.png")
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    plt.style.use('default')

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
        out.append(f" |  ├─ Buffer Loc:   {metrics.get('buf_latency', 0):.2f} ciclos (Bloqueo hardware)")
        out.append(f" |  └─ Red:          {metrics.get('net_latency', 0):.2f} ciclos (Vuelo y saltos)")
        out.append(f" | Jitter (AER):     {metrics.get('jitter', 0):.2f} ciclos")
        out.append(f" | Throughput:       {metrics.get('throughput', 0):.6f} flits/ciclo/nodo")
        out.append(f" | Energia Total:    {metrics.get('energy', 0):.6f} uJ")
        out.append(f" | Eficiencia:       {metrics.get('energy_eff', 0):,.2f} flits/uJ")
        out.append(f" | Throughput Físico:{metrics.get('temporal_perf', 0):,.0f} flits/s")
        out.append(f" | Ciclos Medios/Inf:{metrics.get('ciclos_medios', 0):,.0f} ciclos")
        out.append(f" | Ciclos Simulador: {metrics.get('ciclos_simulacion', 0):,.0f} ciclos")
        late = metrics.get('late_flits', 0)
        if late > 0:
            out.append(f" | ⚠️ ALERTA: {late:,} flits descartados por latencia (Violación temporal)")
        out.append(" +------------------------------------------------------------")
        out.append(f" PRECISION IA:")
        out.append(f"  └─ Software (Baseline): {metrics.get('baseline_accuracy', 0):.2f}%")
        out.append(f"  └─ Hardware (In-Memory): {metrics.get('accuracy', 0):.2f}%")

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
    TECH["f_max_mhz"] = args.freq
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

    final_baseline_acc = 0.0
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
            final_baseline_acc = acc


# Fase 2: Mapeo In-Memory y Simulación Física
    draw_dashboard_compat("Iniciando Fase 2: Mapeo y Simulación In-Memory...", 0.6, args)

    # --- 1. INICIALIZACIÓN DE LA RED ---
    event_queue = ncs.EventQueue()
    network = ncs.Network(args.dim, args.dim, event_queue)
    for r in range(args.dim * args.dim):
        network.getRouter(r).setBufferSizes(args.inj_buffer, args.net_buffer)

    flit_id, total_spikes = 0, 0
    net.eval()

    ## --- 2. FLASHEO DE PESOS (MAPEO PYTORCH -> C++) ---
    draw_dashboard_compat("Mapeando pesos sinápticos al silicio...", 0.65, args)
    synapse_map = {}
    # Funciones auxiliares para desenrollar las capas de PyTorch al silicio 1D
    def map_conv2d_to_noc(weight_matrix, in_shape, out_channels, k_size, src_routers, dst_routers, v_th, leak):
        in_ch, in_h, in_w = in_shape
        out_h = in_h - k_size + 1
        out_w = in_w - k_size + 1

        # Diccionario para agrupar las sinapsis por neurona de origen
        # {src_neuron_idx: [Synapse(dst, weight), ...]}
        src_synapses = {}


        for oc in range(out_channels):
            for oh in range(out_h):
                for ow in range(out_w):
                    # Índice 1D de la neurona de destino en la capa plana
                    dst_neuron_idx = oc * (out_h * out_w) + oh * out_w + ow
                    dst_router_id = dst_routers[dst_neuron_idx % len(dst_routers)]

                    for ic in range(in_ch):
                        for kh in range(k_size):
                            for kw in range(k_size):
                                w_val = weight_matrix[oc, ic, kh, kw]

                                # Optimización de silicio: No mapeamos pesos cero (ahorro de RAM y ancho de banda)
                                if abs(w_val) > 1e-5:
                                    src_h = oh + kh
                                    src_w = ow + kw
                                    # Índice 1D de la neurona de origen
                                    src_neuron_idx = ic * (in_h * in_w) + src_h * in_w + src_w

                                    if src_neuron_idx not in synapse_map:
                                        synapse_map[src_neuron_idx] = []
                                    if dst_router_id not in synapse_map[src_neuron_idx]:
                                        synapse_map[src_neuron_idx].append(dst_router_id)

                                    if src_neuron_idx not in src_synapses:
                                        src_synapses[src_neuron_idx] = []
                                    src_synapses[src_neuron_idx].append(ncs.Synapse(dst_router_id, dst_neuron_idx, float(w_val)))

        # Flasheamos a la SRAM de C++
        for src_idx, synapses in src_synapses.items():
            src_router_id = src_routers[src_idx % len(src_routers)]
            router = network.getRouter(src_router_id)
            router.mapNeuron(neuron_id=src_idx, v_th=v_th, leak=leak, synapses=synapses)

    def map_linear_to_noc(weight_matrix, src_routers, dst_routers, v_th, leak):
        out_features, in_features = weight_matrix.shape
        src_synapses = {i: [] for i in range(in_features)}

        for dst_idx in range(out_features):
            dst_router_id = dst_routers[dst_idx % len(dst_routers)]
            for src_idx in range(in_features):
                w_val = weight_matrix[dst_idx, src_idx]
                if abs(w_val) > 1e-5:
                    if src_idx not in synapse_map:
                        synapse_map[src_idx] = []
                    if dst_router_id not in synapse_map[src_idx]:
                        synapse_map[src_idx].append(dst_router_id)
                    src_synapses[src_idx].append(ncs.Synapse(dst_router_id, dst_idx, float(w_val)))

        for src_idx, synapses in src_synapses.items():
            src_router_id = src_routers[src_idx % len(src_routers)]
            router = network.getRouter(src_router_id)
            router.mapNeuron(neuron_id=src_idx, v_th=v_th, leak=leak, synapses=synapses)

    with torch.no_grad():
        # Extracción de matrices de pesos de la red entrenada
        w_conv1 = net.conv1.weight.cpu().numpy()
        w_conv2 = net.conv2.weight.cpu().numpy()
        w_fc1 = net.fc1.weight.cpu().numpy()

        # Nodos mapeados según tu función get_node_mapping
        r_in = nodes['input']
        r_snn1 = nodes['snn1']
        r_snn2 = nodes['snn2']
        r_out = nodes['output']



        # 1. Mapeo Conv1 (Input -> SNN1)
        # Input shape de N-MNIST: 2 canales, 34x34
        map_conv2d_to_noc(w_conv1, in_shape=(2, 34, 34), out_channels=12, k_size=5,
                          src_routers=r_in, dst_routers=r_snn1, v_th=1.0, leak=beta)

        # NOTA SOBRE POOLING: En hardware neuromórfico puro, el MaxPool es muy costoso lógicamente.
        # Para mantener la simulación física fiel, aquí estamos colapsando conceptualmente
        # la operación de Pooling de PyTorch ajustando la entrada de Conv2.
        # En una arquitectura real, Conv1 conectaría a un bloque dedicaco a submuestreo.

        # 2. Mapeo Conv2 (SNN1 -> SNN2)
        # Asumiendo que la salida de Conv1 (30x30) pasó por un Pool 2x2 en PyTorch,
        # la entrada a Conv2 teórica es de 12 canales, 15x15.
        map_conv2d_to_noc(w_conv2, in_shape=(12, 15, 15), out_channels=32, k_size=5,
                          src_routers=r_snn1, dst_routers=r_snn2, v_th=1.0, leak=beta)

        # 3. Mapeo Capa Lineal FC1 (SNN2 -> Output)
        map_linear_to_noc(w_fc1, src_routers=r_snn2, dst_routers=r_out, v_th=1.0, leak=beta)
        # --- NUEVO: 4. Instanciar físicamente las neuronas de salida ---
        # Estas neuronas no envían sinapsis a nadie, solo reciben flits y disparan
        for dst_idx in range(10):
            dst_router_id = r_out[dst_idx % len(r_out)]
            network.getRouter(dst_router_id).mapNeuron(neuron_id=dst_idx, v_th=1.0, leak=beta, synapses=[])
    # --- 3. INYECCIÓN SENSORIAL Y CO-SIMULACIÓN ---
    draw_dashboard_compat("Inyectando eventos N-MNIST y simulando malla...", 0.75, args)

    CYCLES_PER_SNN_STEP = int((TECH["f_max_mhz"] * 1e6) * 1e-3)

    hw_correct = 0
    ciclos_por_inferencia = []
    tiempo_acumulado_anterior = 0

    # --- NUEVO: Setup para Heatmaps ---
    frames_dir = "heatmap_frames"
    os.makedirs(frames_dir, exist_ok=True)
    for f in glob.glob(f"{frames_dir}/*.png"):
        os.remove(f)

    next_heatmap_time = CYCLES_PER_SNN_STEP
    # Guardamos el estado histórico de los flits reenviados por cada router
    prev_forwarded = {r: 0 for r in range(args.dim * args.dim)}
    # ----------------------------------

    with torch.no_grad():
        w_conv1_flat = net.conv1.weight.detach().cpu().numpy().flatten()
        for i in range(args.samples):
            data, target = testset[i]
            data = data.to(device).unsqueeze(1)
            total_steps = data.size(0)

            for step in range(total_steps):
                t_base = step * CYCLES_PER_SNN_STEP + (i * total_steps * CYCLES_PER_SNN_STEP)

                # --- A. INYECCIÓN DEL SENSOR SÓLO EN LA CAPA INPUT ---
                # Ya no pasamos los datos por PyTorch, solo cogemos el estímulo inicial
                sensor_data = data[step].flatten()
                idxs = (sensor_data > 0).nonzero(as_tuple=False)
                num_spikes = len(idxs)
                total_spikes += num_spikes

                for idx_num, idx_tensor in enumerate(idxs):
                    idx_original = idx_tensor.item()
                    weight_real = float(w_conv1_flat[idx_original % len(w_conv1_flat)])
                    src = nodes['input'][idx_num % len(nodes['input'])]

                    destinos = synapse_map.get(idx_original, []) # synapse_map debería ser el dict que guardaste al mapear

                    if destinos:
                        for dst in destinos:
                            flit = ncs.Flit(flit_id, 0, ncs.FlitType.BODY, src, dst, src, int(t_base), weight_real, idx_original)
                            network.getRouter(src).injectFlit(flit, int(t_base))
                            flit_id += 1 # Es importante incrementar el ID del flit para evitar colisiones

                # --- B. SIMULACIÓN FÍSICA IN-MEMORY ---
                tiempo_limite = t_base + CYCLES_PER_SNN_STEP
                last_eval_time = -1 # <--- Añade esto antes del bucle
                # --- AVISO: Sincronización de routers ---
                tiempo_limite = t_base + CYCLES_PER_SNN_STEP
                for r in range(args.dim * args.dim):
                    network.getRouter(r).tiempo_limite_actual = tiempo_limite

                # Bucle de ciclo de reloj
                while not event_queue.isEmpty() and event_queue.getCurrentTime() < tiempo_limite:
                    current_time = event_queue.getCurrentTime()

                    # --- NUEVO: Generar mapa de estado de enlaces en cada paso SNN ---
                    if current_time >= next_heatmap_time:
                        save_heatmap(network, args.dim, current_time, frames_dir, args.net_buffer)
                        next_heatmap_time += CYCLES_PER_SNN_STEP
                    # ----------------------------------------------------------------------

                    # Solo evaluamos si el reloj físico ha avanzado
                    if current_time > last_eval_time:
                        for r in range(args.dim * args.dim):
                            network.getRouter(r).evaluateNeurons(current_time, tiempo_limite)
                        last_eval_time = current_time # Actualizamos la marca de tiempo

                    # El hardware procesa ruteo y colisiones (1 evento)
                    network.stepSimulation(1)

                # Dashboard progress update
                global_step = i * total_steps + step
                max_global_steps = args.samples * total_steps
                progreso_sim = 0.75 + (global_step / max_global_steps) * 0.20
                if step % 2 == 0:
                    draw_dashboard_compat("Simulando red In-Memory paso a paso...", progreso_sim, args)

            # ======================================================================
            # --- NUEVO: CIERRE LÓGICO DE IA (Al terminar la imagen actual) ---
            # =====================================================================

            # 1. Calculo de ciclos de la inferencia
            tiempo_actual_acumulado = network.getSimulationTime()
            ciclos_esta_inferencia = tiempo_actual_acumulado - tiempo_acumulado_anterior
            ciclos_por_inferencia.append(ciclos_esta_inferencia)
            tiempo_acumulado_anterior = tiempo_actual_acumulado


            # 2. Limpiamos los flits residuales DESCARTÁNDOLOS (Restricción temporal estricta)
            # Si el hardware (frecuencia) fue demasiado lento, los flits no llegan a sumar su voltaje.
            while not event_queue.isEmpty():
                event_queue.getNextEvent() # Lo sacamos de la cola de C++ pero NO lo simulamos

            # 3. Leemos cuántos spikes generó cada neurona de salida (Clases 0 a 9)
            out_spikes = np.zeros(10)
            for class_idx in range(10):
                dst_router = nodes['output'][class_idx % len(nodes['output'])]
                out_spikes[class_idx] = network.getRouter(dst_router).getNeuronSpikeCount(class_idx)

            # 4. La clase con más disparos en la SRAM es la predicción del chip
            prediction = np.argmax(out_spikes)
            if prediction == target:
                hw_correct += 1

            # 5. RESET: Borramos voltajes y spikes para que la próxima imagen empiece limpia
            network.resetNeuronsState()



    sim_t = network.getSimulationTime()
    period_ns = 1000.0 / TECH['f_max_mhz']

    # Lectura real del hardware en C++
    real_total_flits = network.getTotalFlitsInjected()

    total_energy_uj = (network.getTotalForwarded() * TECH['energy_per_spike']) / 1e6 + (TECH['static_power_uw'] * (sim_t * period_ns)) / 1e6
    energy_eff = real_total_flits / total_energy_uj if total_energy_uj > 0 else 0
    total_time_seconds = sim_t * period_ns * 1e-9
    temporal_perf = real_total_flits / total_time_seconds if total_time_seconds > 0 else 0
    total_late_flits = 0
    for r in range(args.dim * args.dim):
        total_late_flits += network.getRouter(r).getLateFlits()

    ciclos_medios = sum(ciclos_por_inferencia) / len(ciclos_por_inferencia) if ciclos_por_inferencia else 0

    hw_accuracy = (hw_correct / args.samples) * 100.0

    metrics = {
        "spikes": total_spikes,
        "flits_generados": real_total_flits,
        "flits_inyectados": real_total_flits,
        "flits_eyectados": network.getTotalFlitsReceived(),
        "flits_procesados": network.getTotalForwarded(),
        "late_flits": total_late_flits,
        "latency": network.getAvgLatency(),
        "buf_latency": network.getAvgBufferLatency(),
        "net_latency": network.getAvgNetworkLatency(),
        "jitter": network.getAvgJitter(),
        "energy": total_energy_uj,
        "accuracy": hw_accuracy,           # La real del hardware
        "baseline_accuracy": final_baseline_acc,
        "energy_eff": energy_eff,
        "temporal_perf": temporal_perf,
        "throughput": (network.getTotalFlitsReceived() / sim_t) / (args.dim**2) if sim_t > 0 else 0,
        "ciclos_medios": ciclos_medios,
        "ciclos_simulacion": sim_t,
    }

    # Ensamblar los frames generados en un video
    generate_simulation_video(frames_dir, output_name=args.video_name + ".mp4")


    draw_dashboard_compat("Simulación Completada ✅", 1.0, args, metrics=metrics)

if __name__ == "__main__":
    main_compat()
