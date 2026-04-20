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
TECH = {"name": "Neuromorphic-Specialized (22nm FD-SOI)", "energy_per_spike": 0.85, "f_max_mhz": 1200, "static_power_uw": 1.2}
NET_CONFIG = {"name": "Estándar (Baja Congestión)", "buffer": 4096}
TRAIN_EPOCHS = 1
TRAIN_ITERATIONS = 20 # Aumentamos para ver el proceso
NUM_SAMPLES = 1

device = torch.device("cpu")
sensor_size = (34, 34, 2)
transform = tonic.transforms.Compose([
    tonic.transforms.ToFrame(sensor_size=sensor_size, n_time_bins=15),
    torch.from_numpy,
])

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
        spk1_rec, spk2_rec, spk_out_rec = [], [], []
        for step in range(x.size(0)):
            cur = self.conv1(x[step])
            spk1, mem1 = self.snn1(cur, mem1)
            cur = self.pool1(spk1)
            cur = self.conv2(cur)
            spk2, mem2 = self.snn2(cur, mem2)
            cur = self.pool2(cur)
            cur = self.flatten(cur)
            cur = self.fc1(cur)
            spk_out, mem3 = self.snn3(cur, mem3)
            spk1_rec.append(spk1); spk2_rec.append(spk2); spk_out_rec.append(spk_out)
        return torch.stack(spk_out_rec), torch.stack(spk1_rec), torch.stack(spk2_rec)

def draw_dashboard_compat(phase, progress, metrics=None, train_info=None):
    # Limpiar pantalla de forma compatible
    os.system('clear' if os.name == 'posix' else 'cls')
    
    width = 70
    print("\n" + " [ NoC-AER SIMULATOR: DASHBOARD EN TIEMPO REAL ] ".center(width, "="))
    print(f"\n FASE ACTUAL: {phase}")
    
    bar_width = 40
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f" PROGRESO:    [{bar}] {progress*100:.1f}%")
    
    if train_info:
        print("\n +-- ESTADO DEL ENTRENAMIENTO SNN ----------------------------")
        print(f" | Epoca:      {train_info.get('epoch', 0)}")
        print(f" | Iteracion:  {train_info.get('iter', 0)} / {TRAIN_ITERATIONS}")
        print(f" | Loss:       {train_info.get('loss', 0):.4f}")
        print(f" | Accuracy:   {train_info.get('acc', 0):.2f}%")
        print(" +------------------------------------------------------------")

    print("\n +-- CONFIGURACION NoC ---------------------------------------")
    print(f" | Tecnologia: {TECH['name']}")
    print(f" | Frecuencia: {TECH['f_max_mhz']} MHz")
    print(f" | Red:        {NET_CONFIG['name']} (Buffer: {NET_CONFIG['buffer']})")
    print(" +------------------------------------------------------------")
    
    if metrics:
        print("\n +-- METRICAS DE HARDWARE (RESULTADO FINAL) ------------------")
        print(f" | Spikes Gen:    {metrics.get('spikes', 0):,}")
        print(f" | Flits NoC:     {metrics.get('flits', 0):,}")
        print(f" | Latencia Med:  {metrics.get('latency', 0):.2f} ciclos")
        print(f" | Jitter (AER):  {metrics.get('jitter', 0):.2f} ciclos")
        print(f" | Throughput:    {metrics.get('throughput', 0):.4f} flits/ciclo/nodo")
        print(f" | Energia Total: {metrics.get('energy', 0):.6f} uJ")
        print(" +------------------------------------------------------------")
        print(f"\n PRECISION IA FINAL:  {metrics.get('accuracy', 0):.2f}%")
    
    print(f"\n NoC-AER Engine v2.1 (Industrial Edition) | COMPAT_MODE")
    print("=" * width)

def main_compat():
    # --- Phase 0: Dataset ---
    draw_dashboard_compat("Preparando Dataset N-MNIST...", 0.05)
    trainset = tonic.datasets.NMNIST(save_to='./data', train=True, transform=transform)
    testset = tonic.datasets.NMNIST(save_to='./data', train=False, transform=transform)
    train_loader = DataLoader(trainset, batch_size=32, collate_fn=tonic.collation.PadTensors(batch_first=False), shuffle=True)
    test_loader = DataLoader(testset, batch_size=32, collate_fn=tonic.collation.PadTensors(batch_first=False), shuffle=False)

    # --- Phase 1: Real Training ---
    net = CSNN(beta, spike_grad).to(device)
    optimizer = torch.optim.Adam(net.parameters(), lr=2e-3, betas=(0.9, 0.999))
    loss_fn = SF.mse_count_loss(correct_rate=0.8, incorrect_rate=0.2)
    
    acc = 0.0
    for epoch in range(TRAIN_EPOCHS):
        for i, (data, targets) in enumerate(train_loader):
            if i >= TRAIN_ITERATIONS: break
            
            net.train()
            data, targets = data.to(device), targets.to(device)
            spk_out, _, _ = net(data.float())
            loss_val = loss_fn(spk_out, targets)
            
            optimizer.zero_grad()
            loss_val.backward()
            optimizer.step()
            
            # Update Dashboard with real training metrics
            if i % 2 == 0:
                with torch.no_grad():
                    net.eval()
                    # Quick accuracy check on a small batch
                    test_data, test_targets = next(iter(test_loader))
                    spk_out_test, _, _ = net(test_data.float())
                    _, predicted = spk_out_test.sum(dim=0).max(1)
                    acc = (predicted == test_targets).sum().item() / test_targets.size(0) * 100
                
                draw_dashboard_compat("Entrenando Modelo SNN (PROCESO REAL)", 0.1 + (i/TRAIN_ITERATIONS)*0.4, 
                                     train_info={'epoch': epoch, 'iter': i, 'loss': loss_val.item(), 'acc': acc})
    
    # --- Phase 2: NoC Simulation ---
    draw_dashboard_compat("Inyectando Eventos AER en NoC...", 0.6)
    event_queue = ncs.EventQueue()
    network = ncs.Network(4, 4, event_queue)
    for i in range(16): network.getRouter(i).setMaxBufferSize(NET_CONFIG['buffer'])
    
    flit_id_counter = 0
    total_spikes = 0
    input_nodes = list(range(0, 4)); snn1_nodes = list(range(4, 8)); snn2_nodes = list(range(8, 12)); output_nodes = list(range(12, 16))
    FAN_OUT_CONV1 = 12; FAN_OUT_CONV2 = 32; FAN_OUT_FC = 10
    
    net.eval()
    with torch.no_grad():
        for i in range(NUM_SAMPLES):
            data, label = testset[i]
            data = data.to(device).unsqueeze(1)
            spk_out, spk1, spk2 = net(data.float())
            for step in range(data.size(0)):
                sim_time_base = step * 100 + (i * 2000)
                input_spikes = (data[step] > 0).nonzero(as_tuple=False)
                total_spikes += len(input_spikes)
                for idx, spike in enumerate(input_spikes):
                    pixel_idx = spike[2].item() * 34 + spike[3].item()
                    src_node = input_nodes[pixel_idx % len(input_nodes)]
                    dest_nodes = [snn1_nodes[j % len(snn1_nodes)] for j in range(FAN_OUT_CONV1)]
                    for dst_node in dest_nodes:
                        sim_time = sim_time_base + (idx % 10)
                        flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src_node, dst_node, src_node, sim_time)
                        network.getRouter(src_node).injectFlit(flit, sim_time)
                        flit_id_counter += 1
                
                spikes1 = (spk1[step] > 0).nonzero(as_tuple=False)
                total_spikes += len(spikes1)
                for idx, s in enumerate(spikes1):
                    src_node = snn1_nodes[idx % len(snn1_nodes)]
                    dest_nodes = [snn2_nodes[j % len(snn2_nodes)] for j in range(FAN_OUT_CONV2)]
                    for dst_node in dest_nodes:
                        sim_time = sim_time_base + 20 + (idx % 10)
                        flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src_node, dst_node, src_node, sim_time)
                        network.getRouter(src_node).injectFlit(flit, sim_time)
                        flit_id_counter += 1
                
                spikes2 = (spk2[step] > 0).nonzero(as_tuple=False)
                total_spikes += len(spikes2)
                for idx, s in enumerate(spikes2):
                    src_node = snn2_nodes[idx % len(snn2_nodes)]
                    dest_nodes = [output_nodes[j % len(output_nodes)] for j in range(FAN_OUT_FC)]
                    for dst_node in dest_nodes:
                        sim_time = sim_time_base + 40 + (idx % 10)
                        flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src_node, dst_node, src_node, sim_time)
                        network.getRouter(src_node).injectFlit(flit, sim_time)
                        flit_id_counter += 1
    
    draw_dashboard_compat("Ejecutando Simulacion Ciclo-a-Ciclo...", 0.8)
    network.runSimulation()
    
    sim_time_cycles = network.getSimulationTime()
    total_forwarded = network.getTotalForwarded()
    period_ns = 1000.0 / TECH['f_max_mhz']
    metrics = {
        "spikes": total_spikes, "flits": flit_id_counter, "latency": network.getAvgLatency(),
        "jitter": network.getAvgJitter(), "throughput": (network.getTotalFlitsReceived() / sim_time_cycles) / 16 if sim_time_cycles > 0 else 0,
        "energy": (total_forwarded * TECH['energy_per_spike']) / 1e6 + (TECH['static_power_uw'] * (sim_time_cycles * period_ns)) / 1e6,
        "accuracy": acc
    }
    
    draw_dashboard_compat("Simulacion Completada ✅", 1.0, metrics)
    print("\nEjecución finalizada con éxito.")

if __name__ == "__main__":
    main_compat()
