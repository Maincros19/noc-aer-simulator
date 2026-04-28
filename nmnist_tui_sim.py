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
    parser = argparse.ArgumentParser(description="NoC-AER Simulator Industrial Edition")
    parser.add_argument("--dim", type=int, default=4, help="Dimensión de la malla NoC (ej. 4 para 4x4)")
    parser.add_argument("--buffer", type=int, default=4096, help="Tamaño del buffer de los routers")
    parser.add_argument("--epochs", type=int, default=1, help="Épocas de entrenamiento")
    parser.add_argument("--iters", type=int, default=20, help="Iteraciones por época")
    parser.add_argument("--samples", type=int, default=1, help="Muestras para simulación NoC")
    parser.add_argument("--lr", type=float, default=2e-3, help="Tasa de aprendizaje")
    return parser.parse_args()



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
        print(f" | Latencia Med:  {metrics.get('latency', 0):.2f} ciclos")
        print(f" | Jitter (AER):  {metrics.get('jitter', 0):.2f} ciclos")
        print(f" | Throughput:    {metrics.get('throughput', 0):.6f} flits/ciclo/nodo")
        print(f" | Energia Total: {metrics.get('energy', 0):.6f} uJ")
        print(" +------------------------------------------------------------")
        print(f"\n PRECISION IA FINAL:  {metrics.get('accuracy', 0):.2f}%")

def main_compat():
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
    train_loader = DataLoader(trainset, batch_size=32, collate_fn=tonic.collation.PadTensors(batch_first=False), shuffle=True)
    test_loader = DataLoader(testset, batch_size=32, collate_fn=tonic.collation.PadTensors(batch_first=False), shuffle=False)

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
    draw_dashboard_compat("Inyectando Tráfico en NoC...", 0.6, args)
    event_queue = ncs.EventQueue()
    network = ncs.Network(args.dim, args.dim, event_queue)
    for r in range(args.dim * args.dim):
        network.getRouter(r).setMaxBufferSize(args.buffer)

    flit_id, total_spikes = 0, 0
    net.eval()
    with torch.no_grad():
        for i in range(args.samples):
            data, _ = testset[i]
            data = data.to(device).unsqueeze(1)
            spk_out, spk1_p, spk2_p = net(data.float())

            for step in range(data.size(0)):
                t_base = step * 100 + (i * 2000)

                # Función para inyectar flits entre capas
                def inject_layer(tensor, src_grp, dst_grp, fan, offset):
                    nonlocal flit_id, total_spikes
                    idxs = (tensor > 0).nonzero(as_tuple=False)
                    total_spikes += len(idxs)
                    for idx, _ in enumerate(idxs):
                        src = src_grp[idx % len(src_grp)]
                        dsts = [dst_grp[j % len(dst_grp)] for j in range(fan)]
                        for d in dsts:
                            t_sim = t_base + offset + (idx % 10)
                            flit = ncs.Flit(flit_id, 0, ncs.FlitType.BODY, src, d, src, t_sim)
                            network.getRouter(src).injectFlit(flit, t_sim)
                            flit_id += 1

                inject_layer(data[step], nodes['input'], nodes['snn1'], 12, 0)
                inject_layer(spk1_p[step], nodes['snn1'], nodes['snn2'], 32, 20)
                inject_layer(spk2_p[step], nodes['snn2'], nodes['output'], 10, 40)

    draw_dashboard_compat("Ejecutando Simulación Ciclo-a-Ciclo...", 0.85, args)
    network.runSimulation()

    # Métricas Finales
    sim_t = network.getSimulationTime()
    period_ns = 1000.0 / TECH['f_max_mhz']
    metrics = {
        "spikes": total_spikes, "flits": flit_id, "latency": network.getAvgLatency(),
        "jitter": network.getAvgJitter(),
        "throughput": (network.getTotalFlitsReceived() / sim_t) / (args.dim**2) if sim_t > 0 else 0,
        "energy": (network.getTotalForwarded() * TECH['energy_per_spike']) / 1e6 + (TECH['static_power_uw'] * (sim_t * period_ns)) / 1e6,
        "accuracy": acc
    }

    draw_dashboard_compat("Simulación Completada ✅", 1.0, args, metrics=metrics)

if __name__ == "__main__":
    main_compat()
