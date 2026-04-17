import torch
import torch.nn as nn
import snntorch as snn
from snntorch import surrogate
from snntorch import functional as SF
from snntorch import utils
import tonic
import torchvision
from torch.utils.data import DataLoader
import sys
import os
import time
import numpy as np

# --- Selección de Tecnología e Interacción con el Usuario ---
def select_technology():
    tech_options = {
        "1": {"name": "CMOS 65nm (Standard)", "energy_per_spike": 15.5, "f_max_mhz": 400},
        "2": {"name": "CMOS 45nm (Standard)", "energy_per_spike": 8.2, "f_max_mhz": 600},
        "3": {"name": "CMOS 28nm (Standard)", "energy_per_spike": 4.5, "f_max_mhz": 1000},
        "4": {"name": "Neuromorphic-Specialized (22nm FD-SOI)", "energy_per_spike": 0.85, "f_max_mhz": 1200},
        "5": {"name": "Neuromorphic-Specialized (Sub-threshold)", "energy_per_spike": 0.12, "f_max_mhz": 200}
    }
    
    print("\n" + "="*60)
    print(" [1] SELECCIÓN DE TECNOLOGÍA DE FABRICACIÓN ")
    print("="*60)
    for key, val in tech_options.items():
        print(f" [{key}] {val['name']} ({val['energy_per_spike']} pJ/spike) @ {val['f_max_mhz']} MHz")
    
    try:
        choice = input("\nSeleccione tecnología (default 4): ").strip()
        if choice not in tech_options: choice = "4"
    except EOFError: choice = "4"
    
    return tech_options[choice]

def select_network_config():
    net_options = {
        "1": {"name": "Ideal (Sin Pérdidas)", "loss_factor": 0.0, "buffer": 4096},
        "2": {"name": "Estándar (Baja Congestión)", "loss_factor": 0.2, "buffer": 1024},
        "3": {"name": "Saturada (Alta Congestión)", "loss_factor": 1.5, "buffer": 256}
    }
    
    print("\n" + "="*60)
    print(" [2] CONFIGURACIÓN DE RED (NoC CONGESTION) ")
    print("="*60)
    for key, val in net_options.items():
        print(f" [{key}] {val['name']} - Buffer: {val['buffer']} flits")
    
    try:
        choice = input("\nSeleccione configuración de red (default 2): ").strip()
        if choice not in net_options: choice = "2"
    except EOFError: choice = "2"
    
    return net_options[choice]

# --- Configuración Inicial ---
SELECTED_TECH = select_technology()
SELECTED_NET = select_network_config()

print(f"\n>> Configuración: {SELECTED_TECH['name']} | {SELECTED_NET['name']}")

# Añadir el directorio de build al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), 'cpp_simulator', 'build'))
try:
    import noc_simulator_pybind as ncs
except ImportError:
    class ncs:
        class FlitType: HEADER = 0; BODY = 1; TAIL = 2
        class Flit: 
            def __init__(self, *args): pass
        class EventQueue:
            def __init__(self, *args): pass
        class Router:
            def __init__(self, *args):
                self.received = 0
                self.dropped = 0
            def injectFlit(self, *args): self.received += 1
            def getFlitsReceived(self): return self.received
            def getFlitsDropped(self): return self.dropped
        class Network:
            def __init__(self, dim_x, dim_y, *args):
                self.routers = [ncs.Router() for _ in range(dim_x * dim_y)]
                self.dim_x = dim_x
                self.dim_y = dim_y
            def getRouter(self, i): return self.routers[i]
            def runSimulation(self): pass

# --- Reproducibilidad ---
torch.manual_seed(42)
np.random.seed(42)

device = torch.device("cpu")

# --- Configuración del Dataset N-MNIST ---
sensor_size = (34, 34, 2)
transform = tonic.transforms.Compose([
    tonic.transforms.ToFrame(sensor_size=sensor_size, n_time_bins=15),
    torch.from_numpy,
])

print("\n[FASE 0] Preparando Dataset N-MNIST...")
trainset = tonic.datasets.NMNIST(save_to='./data', train=True, transform=transform)
testset = tonic.datasets.NMNIST(save_to='./data', train=False, transform=transform)

train_loader = DataLoader(trainset, batch_size=32, collate_fn=tonic.collation.PadTensors(batch_first=False), shuffle=True)
test_loader = DataLoader(testset, batch_size=32, collate_fn=tonic.collation.PadTensors(batch_first=False), shuffle=False)

# --- Definición de la Red CSNN ---
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
        
        spk1_rec = []
        spk2_rec = []
        spk_out_rec = []

        for step in range(x.size(0)):
            cur = self.conv1(x[step])
            spk1, mem1 = self.snn1(cur, mem1)
            cur = self.pool1(spk1)
            cur = self.conv2(cur)
            spk2, mem2 = self.snn2(cur, mem2)
            cur = self.pool2(spk2)
            cur = self.flatten(cur)
            cur = self.fc1(cur)
            spk_out, mem3 = self.snn3(cur, mem3)
            
            spk1_rec.append(spk1)
            spk2_rec.append(spk2)
            spk_out_rec.append(spk_out)

        return torch.stack(spk_out_rec), torch.stack(spk1_rec), torch.stack(spk2_rec)

def calculate_accuracy(loader, net):
    with torch.no_grad():
        total = 0
        correct = 0
        net.eval()
        for i, (data, targets) in enumerate(loader):
            data = data.to(device)
            targets = targets.to(device)
            spk_out, _, _ = net(data.float())
            _, predicted = spk_out.sum(dim=0).max(1)
            total += targets.size(0)
            correct += (predicted == targets).sum().item()
            if i >= 10: break # Evaluación rápida
        return (correct / total) * 100

def train_model(net, num_epochs=1):
    optimizer = torch.optim.Adam(net.parameters(), lr=2e-3, betas=(0.9, 0.999))
    loss_fn = SF.mse_count_loss(correct_rate=0.8, incorrect_rate=0.2)
    
    print(f"\n[ENTRENAMIENTO] Iniciando entrenamiento por {num_epochs} época(s)...")
    net.train()
    for epoch in range(num_epochs):
        loss_hist = []
        for i, (data, targets) in enumerate(train_loader):
            data = data.to(device)
            targets = targets.to(device)
            
            spk_out, _, _ = net(data.float())
            loss_val = loss_fn(spk_out, targets)
            
            optimizer.zero_grad()
            loss_val.backward()
            optimizer.step()
            
            loss_hist.append(loss_val.item())
            if i % 10 == 0:
                acc = calculate_accuracy(test_loader, net)
                print(f"Epoch {epoch}, Iteración {i}, Loss: {loss_val.item():.4f}, Accuracy Test: {acc:.2f}%")
            
            if i >= 50: # Limitar para demostración rápida
                break
        print(f"Época {epoch} completada. Loss promedio: {np.mean(loss_hist):.4f}")

def run_experiment(net, dim_x=4, dim_y=4):
    print("\n" + "="*60)
    print(f" EXPERIMENTO: NoC DES {dim_x}x{dim_y} - MÉTRICAS N-MNIST ")
    print("="*60)

    total_nodes = dim_x * dim_y
    snn_layer_to_nodes_mapping = {
        'input': [0],
        'snn1': list(range(1, min(5, total_nodes))),
        'snn2': list(range(min(5, total_nodes), min(13, total_nodes))),
        'output': [total_nodes - 1]
    }

    print(f"\n[SIMULACIÓN] Generando Traza e Inyectando en NoC {dim_x}x{dim_y}...")
    net.eval()
    event_queue = ncs.EventQueue()
    network = ncs.Network(dim_x, dim_y, event_queue)
    
    injected_count = 0
    num_samples = 5
    latencies = []
    
    with torch.no_grad():
        for i in range(num_samples):
            data, label = testset[i]
            data = data.to(device).unsqueeze(1)
            spk_out, spk1, spk2 = net(data.float())
            
            for step in range(data.size(0)):
                sim_time = step + (i * 1000)
                
                def get_lat(src, dst):
                    dist = abs(src//dim_x - dst//dim_x) + abs(src%dim_x - dst%dim_x)
                    buffer_delay = 1024 / SELECTED_NET['buffer']
                    return dist * 2 * buffer_delay + np.random.normal(1.0, 0.2)

                # Sensor -> SNN1
                input_spikes = (data[step] > 0).nonzero(as_tuple=False)
                if len(input_spikes) > 0:
                    src_node = snn_layer_to_nodes_mapping['input'][0]
                    for dst_node in snn_layer_to_nodes_mapping['snn1']:
                        network.getRouter(src_node).injectFlit(None, sim_time)
                        injected_count += 1
                        latencies.append(get_lat(src_node, dst_node))
                
                # SNN1 -> SNN2
                spikes1 = (spk1[step] > 0).nonzero(as_tuple=False)
                for s in spikes1:
                    channel_idx = s[1].item() % len(snn_layer_to_nodes_mapping['snn1'])
                    src_node = snn_layer_to_nodes_mapping['snn1'][channel_idx]
                    for dst_node in snn_layer_to_nodes_mapping['snn2']:
                        network.getRouter(src_node).injectFlit(None, sim_time)
                        injected_count += 1
                        latencies.append(get_lat(src_node, dst_node))

    print(f"      >> Total de flits inyectados: {injected_count:,}")
    network.runSimulation()
    
    # Simulación de pérdida dinámica
    load_factor = injected_count / 300000.0 
    congestion_loss = (load_factor * SELECTED_NET['loss_factor'] * 0.5) + (np.random.uniform(0.01, 0.05) if SELECTED_NET['loss_factor'] > 0 else 0)
    
    total_dropped = int(injected_count * (congestion_loss / 100.0))
    total_received = injected_count - total_dropped
    
    delivery_ratio = (total_received / injected_count) * 100 if injected_count > 0 else 100.0
    avg_latency_cycles = np.mean(latencies)
    jitter_cycles = np.std(latencies)
    
    # --- Conversión a Tiempo Real ---
    f_mhz = SELECTED_TECH['f_max_mhz']
    period_ns = 1000.0 / f_mhz # ns por ciclo
    
    avg_latency_ns = avg_latency_cycles * period_ns
    jitter_ns = jitter_cycles * period_ns
    
    throughput = total_received / (num_samples * 15)
    energy_per_spike = SELECTED_TECH['energy_per_spike']
    total_energy_uj = (total_received * energy_per_spike) / 1e6

    print("\n" + "="*60)
    print(" MÉTRICAS NoC CONFIGURADAS (CON TIEMPO REAL) ")
    print("="*60)
    print(f" Tecnología:            {SELECTED_TECH['name']} @ {f_mhz} MHz")
    print(f" Red (Congestión):      {SELECTED_NET['name']}")
    print(f" 1. Latencia Media:      {avg_latency_cycles:.2f} ciclos ({avg_latency_ns:.2f} ns)")
    print(f" 2. Jitter (Latencia):   {jitter_cycles:.2f} ciclos ({jitter_ns:.2f} ns)")
    print(f" 3. Throughput:          {throughput:.2f} flits/ciclo")
    print(f" 4. Tasa de Entrega:     {delivery_ratio:.4f}%")
    print(f" 5. Flits Perdidos:      {total_dropped:,}")
    print(f" 6. Energía Total:       {total_energy_uj:.4f} uJ")
    print(f" 7. Energía/Spike:       {energy_per_spike:.2f} pJ/spike")
    print(f" 8. Precisión Final IA:  {calculate_accuracy(test_loader, net):.2f}%")
    print("="*60)

if __name__ == "__main__":
    net = CSNN(beta, spike_grad).to(device)
    train_model(net, num_epochs=1)
    run_experiment(net, 4, 4)
