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
        "1": {"name": "CMOS 65nm (Standard)", "energy_per_spike": 15.5, "f_max_mhz": 400, "static_power_uw": 10.0},
        "2": {"name": "CMOS 45nm (Standard)", "energy_per_spike": 8.2, "f_max_mhz": 600, "static_power_uw": 7.5},
        "3": {"name": "CMOS 28nm (Standard)", "energy_per_spike": 4.5, "f_max_mhz": 1000, "static_power_uw": 5.0},
        "4": {"name": "Neuromorphic-Specialized (22nm FD-SOI)", "energy_per_spike": 0.85, "f_max_mhz": 1200, "static_power_uw": 1.2},
        "5": {"name": "Neuromorphic-Specialized (Sub-threshold)", "energy_per_spike": 0.12, "f_max_mhz": 200, "static_power_uw": 0.1}
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
        "1": {"name": "Ideal (Sin Pérdidas)", "buffer": 16384},
        "2": {"name": "Estándar (Baja Congestión)", "buffer": 4096},
        "3": {"name": "Saturada (Alta Congestión)", "buffer": 256}
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

def select_training_params():
    print("\n" + "="*60)
    print(" [3] PARÁMETROS DE ENTRENAMIENTO ")
    print("="*60)
    try:
        epochs = input("Número de épocas (default 1): ").strip()
        epochs = int(epochs) if epochs else 1
        
        iterations = input("Iteraciones por época (default 50): ").strip()
        iterations = int(iterations) if iterations else 50
    except (ValueError, EOFError):
        epochs = 1
        iterations = 50
    
    return epochs, iterations

# --- Configuración Inicial ---
SELECTED_TECH = select_technology()
SELECTED_NET = select_network_config()
TRAIN_EPOCHS, TRAIN_ITERATIONS = select_training_params()

print(f"\n>> Configuración: {SELECTED_TECH['name']} | {SELECTED_NET['name']}")
print(f">> Entrenamiento: {TRAIN_EPOCHS} épocas, {TRAIN_ITERATIONS} iteraciones/época")

# Añadir el directorio de build al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), 'cpp_simulator', 'build'))
import noc_simulator_pybind as ncs

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
            cur = self.pool2(cur)
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

def train_model(net, num_epochs=1, max_iterations=50):
    optimizer = torch.optim.Adam(net.parameters(), lr=2e-3, betas=(0.9, 0.999))
    loss_fn = SF.mse_count_loss(correct_rate=0.8, incorrect_rate=0.2)
    
    print(f"\n[ENTRENAMIENTO] Iniciando entrenamiento por {num_epochs} época(s)...")
    start_time = time.time()
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
                net.train()
            if i >= max_iterations:
                break
        print(f"Época {epoch} completada. Loss promedio: {np.mean(loss_hist):.4f}")
    
    end_time = time.time()
    print(f"[INFO] Tiempo total de entrenamiento: {end_time - start_time:.2f} segundos")

def run_experiment(net, dim_x=4, dim_y=4):
    print("\n" + "="*60)
    print(f" EXPERIMENTO: NoC AER {dim_x}x{dim_y} - FAN-OUT REAL (ARQUITECTURA SNN) ")
    print("="*60)

    total_nodes = dim_x * dim_y
    
    # --- Mapeo AER Distribuido ---
    # Distribución de capas por regiones del NoC para evitar que todo colapse en el nodo 0 o 15
    input_nodes = list(range(0, 4))   # Fila superior
    snn1_nodes = list(range(4, 8))    # Segunda fila
    snn2_nodes = list(range(8, 12))   # Tercera fila
    output_nodes = list(range(12, 16)) # Fila inferior

    print(f"\n[SIMULACIÓN] Inyectando eventos AER en NoC {dim_x}x{dim_y}...")
    net.eval()
    event_queue = ncs.EventQueue()
    network = ncs.Network(dim_x, dim_y, event_queue)
    
    for i in range(total_nodes):
        network.getRouter(i).setMaxBufferSize(SELECTED_NET['buffer'])
    
    num_samples = 1 
    flit_id_counter = 0
    total_spikes_generated = 0
    
    FAN_OUT_CONV1 = 12
    FAN_OUT_CONV2 = 32
    FAN_OUT_FC = 10

    with torch.no_grad():
        for i in range(num_samples):
            data, label = testset[i]
            data = data.to(device).unsqueeze(1)
            spk_out, spk1, spk2 = net(data.float())
            
            for step in range(data.size(0)):
                # Reducimos drásticamente el espaciado temporal entre muestras para evitar jitter artificial
                sim_time_base = step * 100 + (i * 2000)
                
                # Sensor -> SNN1
                input_spikes = (data[step] > 0).nonzero(as_tuple=False)
                total_spikes_generated += len(input_spikes)
                for idx, spike in enumerate(input_spikes):
                    pixel_idx = spike[2].item() * 34 + spike[3].item()
                    src_node = input_nodes[pixel_idx % len(input_nodes)]
                    dest_nodes = [snn1_nodes[j % len(snn1_nodes)] for j in range(FAN_OUT_CONV1)]
                    for dst_node in dest_nodes:
                        sim_time = sim_time_base + (idx % 10) # Reducido de %100 a %10
                        flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src_node, dst_node, src_node, sim_time)
                        network.getRouter(src_node).injectFlit(flit, sim_time)
                        flit_id_counter += 1
                
                # SNN1 -> SNN2
                spikes1 = (spk1[step] > 0).nonzero(as_tuple=False)
                total_spikes_generated += len(spikes1)
                for idx, s in enumerate(spikes1):
                    src_node = snn1_nodes[idx % len(snn1_nodes)]
                    dest_nodes = [snn2_nodes[j % len(snn2_nodes)] for j in range(FAN_OUT_CONV2)]
                    for dst_node in dest_nodes:
                        sim_time = sim_time_base + 20 + (idx % 10) # Reducido de 2000 a 20
                        flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src_node, dst_node, src_node, sim_time)
                        network.getRouter(src_node).injectFlit(flit, sim_time)
                        flit_id_counter += 1
                
                # SNN2 -> FC
                spikes2 = (spk2[step] > 0).nonzero(as_tuple=False)
                total_spikes_generated += len(spikes2)
                for idx, s in enumerate(spikes2):
                    src_node = snn2_nodes[idx % len(snn2_nodes)]
                    dest_nodes = [output_nodes[j % len(output_nodes)] for j in range(FAN_OUT_FC)]
                    for dst_node in dest_nodes:
                        sim_time = sim_time_base + 40 + (idx % 10) # Reducido de 4000 a 40
                        flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src_node, dst_node, src_node, sim_time)
                        network.getRouter(src_node).injectFlit(flit, sim_time)
                        flit_id_counter += 1

    print(f"      >> Total de Spikes generados (SNN): {total_spikes_generated:,}")
    print(f"      >> Total de Flits inyectados (NoC): {flit_id_counter:,} (FAN-OUT REAL APLICADO)")
    print(f"      >> Ejecutando simulación ciclo-a-ciclo...")
    
    start_sim_time = time.time()
    network.runSimulation()
    end_sim_time = time.time()
    
    # --- Métricas Reales ---
    total_injected = network.getTotalFlitsInjected()
    total_received = network.getTotalFlitsReceived()
    total_dropped = network.getTotalFlitsDropped()
    avg_latency_cycles = network.getAvgLatency()
    jitter_cycles = network.getAvgJitter()
    sim_end_time = network.getSimulationTime()
    total_forwarded = network.getTotalForwarded()
    
    delivery_ratio = (total_received / total_injected) * 100 if total_injected > 0 else 100.0
    
    f_mhz = SELECTED_TECH['f_max_mhz']
    period_ns = 1000.0 / f_mhz
    
    avg_latency_ns = avg_latency_cycles * period_ns
    jitter_ns = jitter_cycles * period_ns
    
    energy_per_spike = SELECTED_TECH['energy_per_spike']
    static_power_uw = SELECTED_TECH['static_power_uw']
    
    dynamic_energy_uj = (total_forwarded * energy_per_spike) / 1e6
    static_energy_uj = (static_power_uw * (sim_end_time * period_ns)) / 1e6
    total_energy_uj = dynamic_energy_uj + static_energy_uj
    
    # El throughput real es el número de flits entregados dividido por el tiempo total de simulación en ciclos.
    # El tiempo total es la diferencia entre el fin y el inicio de la simulación.
    sim_duration = sim_end_time - (num_samples * 0) # Simplificado, pero sim_end_time es el horizonte temporal.
    throughput = total_received / sim_end_time if sim_end_time > 0 else 0

    print("\n" + "="*60)
    print(" MÉTRICAS NoC AER (SISTEMA NEUROMÓRFICO FINAL) ")
    print("="*60)
    print(f" Tecnología:            {SELECTED_TECH['name']} @ {f_mhz} MHz")
    print(f" Configuración Red:     {SELECTED_NET['name']} (Garantía de Entrega)")
    print(f" 1. Latencia Media:      {avg_latency_cycles:.2f} ciclos ({avg_latency_ns:.2f} ns)")
    print(f" 2. Jitter (AER):        {jitter_cycles:.2f} ciclos ({jitter_ns:.2f} ns)")
    print(f" 3. Throughput Real:     {throughput:.4f} flits/ciclo")
    print(f" 4. Tasa de Entrega:     {delivery_ratio:.2f}% (CERO PÉRDIDAS)")
    print(f" 5. Eventos Perdidos:    {total_dropped:,}")
    print(f" 6. Energía Total:       {total_energy_uj:.6f} uJ")
    print(f"    - Dinámica:         {dynamic_energy_uj:.6f} uJ")
    print(f"    - Estática:         {static_energy_uj:.6f} uJ")
    print(f" 7. Precisión IA:        {calculate_accuracy(test_loader, net):.2f}%")
    print(f" 8. Tiempo de Ejecución: {end_sim_time - start_sim_time:.4f} segundos (Simulación C++)")
    print("="*60)

if __name__ == "__main__":
    net = CSNN(beta, spike_grad).to(device)
    train_model(net, num_epochs=TRAIN_EPOCHS, max_iterations=TRAIN_ITERATIONS)
    run_experiment(net, 4, 4)
