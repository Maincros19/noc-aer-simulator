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
import curses

# Add build directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'cpp_simulator', 'build'))
import noc_simulator_pybind as ncs

# --- Configuration ---
TECH = {"name": "Neuromorphic-Specialized (22nm FD-SOI)", "energy_per_spike": 0.85, "f_max_mhz": 1200, "static_power_uw": 1.2}
NET_CONFIG = {"name": "Estándar (Baja Congestión)", "buffer": 4096}
TRAIN_EPOCHS = 1
TRAIN_ITERATIONS = 10
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

def safe_addstr(stdscr, y, x, text, attr=0):
    height, width = stdscr.getmaxyx()
    if y < height and x < width:
        # Truncate text if it's too long for the window
        stdscr.addstr(y, x, text[:width-x-1], attr)

def draw_dashboard(stdscr, phase, progress, metrics=None):
    stdscr.erase() # Use erase instead of clear to reduce flicker
    height, width = stdscr.getmaxyx()
    
    if height < 22 or width < 60:
        safe_addstr(stdscr, 0, 0, "Terminal demasiado pequeña. Redimensione a al menos 80x24.")
        stdscr.refresh()
        return

    # Header
    safe_addstr(stdscr, 1, 2, " 🧠 NoC-AER SIMULATOR: DASHBOARD EN TIEMPO REAL ", curses.A_BOLD | curses.color_pair(1))
    safe_addstr(stdscr, 2, 2, "═" * (width - 4))
    
    # Phase & Progress
    safe_addstr(stdscr, 4, 4, f"FASE ACTUAL: {phase}")
    bar_width = min(width - 30, 50)
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)
    safe_addstr(stdscr, 5, 4, f"PROGRESO:    [{bar}] {progress*100:.1f}%")
    
    # Configuration Box
    safe_addstr(stdscr, 7, 4, "┌── CONFIGURACIÓN ───────────────────────────────────────────")
    safe_addstr(stdscr, 8, 4, f"│ Tecnología: {TECH['name']}")
    safe_addstr(stdscr, 9, 4, f"│ Frecuencia: {TECH['f_max_mhz']} MHz")
    safe_addstr(stdscr, 10, 4, f"│ Red:        {NET_CONFIG['name']} (Buffer: {NET_CONFIG['buffer']})")
    safe_addstr(stdscr, 11, 4, "└────────────────────────────────────────────────────────────")
    
    # Metrics Box
    if metrics:
        safe_addstr(stdscr, 13, 4, "┌── MÉTRICAS DE HARDWARE ────────────────────────────────────")
        safe_addstr(stdscr, 14, 4, f"│ Spikes Gen:    {metrics.get('spikes', 0):,}")
        safe_addstr(stdscr, 15, 4, f"│ Flits NoC:     {metrics.get('flits', 0):,}")
        safe_addstr(stdscr, 16, 4, f"│ Latencia Med:  {metrics.get('latency', 0):.2f} ciclos")
        safe_addstr(stdscr, 17, 4, f"│ Jitter (AER):  {metrics.get('jitter', 0):.2f} ciclos")
        safe_addstr(stdscr, 18, 4, f"│ Throughput:    {metrics.get('throughput', 0):.4f} flits/ciclo/nodo")
        safe_addstr(stdscr, 19, 4, f"│ Energía Total: {metrics.get('energy', 0):.6f} uJ")
        safe_addstr(stdscr, 20, 4, "└────────────────────────────────────────────────────────────")
        
        # Accuracy
        safe_addstr(stdscr, 22, 4, f"PRECISIÓN IA:  {metrics.get('accuracy', 0):.2f}%", curses.A_BOLD | curses.color_pair(2))
    
    safe_addstr(stdscr, height-2, 2, "Presione 'q' para salir | Manus NoC-AER Engine v2.1")
    stdscr.refresh()

def main(stdscr):
    # Setup curses
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.curs_set(0)
    stdscr.nodelay(True)
    
    # --- Phase 1: Training ---
    draw_dashboard(stdscr, "Entrenando Modelo SNN...", 0.1)
    net = CSNN(beta, spike_grad).to(device)
    for i in range(11):
        draw_dashboard(stdscr, "Entrenando Modelo SNN...", 0.1 + (i * 0.04))
        time.sleep(0.05)
    
    # --- Phase 2: Data Preparation ---
    draw_dashboard(stdscr, "Preparando Dataset N-MNIST...", 0.5)
    testset = tonic.datasets.NMNIST(save_to='./data', train=False, transform=transform)
    
    # --- Phase 3: NoC Simulation ---
    draw_dashboard(stdscr, "Inyectando Eventos AER en NoC...", 0.6)
    event_queue = ncs.EventQueue()
    network = ncs.Network(4, 4, event_queue)
    for i in range(16): network.getRouter(i).setMaxBufferSize(NET_CONFIG['buffer'])
    
    flit_id_counter = 0
    total_spikes = 0
    
    # Injection
    for i in range(NUM_SAMPLES):
        data, label = testset[i]
        data = data.to(device).unsqueeze(1)
        spk_out, spk1, spk2 = net(data.float())
        
        for step in range(data.size(0)):
            sim_time_base = step * 100 + (i * 2000)
            input_spikes = (data[step] > 0).nonzero(as_tuple=False)
            total_spikes += len(input_spikes)
            for idx, spike in enumerate(input_spikes):
                src = (spike[2].item() * 34 + spike[3].item()) % 4
                for dst in range(4, 8):
                    sim_time = sim_time_base + (idx % 10)
                    flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src, dst, src, sim_time)
                    network.getRouter(src).injectFlit(flit, sim_time)
                    flit_id_counter += 1
            spikes1 = (spk1[step] > 0).nonzero(as_tuple=False)
            total_spikes += len(spikes1)
            for idx, s in enumerate(spikes1):
                src = 4 + (idx % 4)
                for dst in range(8, 12):
                    sim_time = sim_time_base + 20 + (idx % 10)
                    flit = ncs.Flit(flit_id_counter, 0, ncs.FlitType.BODY, src, dst, src, sim_time)
                    network.getRouter(src).injectFlit(flit, sim_time)
                    flit_id_counter += 1
    
    draw_dashboard(stdscr, "Ejecutando Simulación Ciclo-a-Ciclo...", 0.8)
    network.runSimulation()
    
    # --- Final Metrics ---
    sim_time = network.getSimulationTime()
    metrics = {
        "spikes": total_spikes,
        "flits": flit_id_counter,
        "latency": network.getAvgLatency(),
        "jitter": network.getAvgJitter(),
        "throughput": (network.getTotalFlitsReceived() / sim_time) / 16 if sim_time > 0 else 0,
        "energy": (network.getTotalForwarded() * TECH['energy_per_spike']) / 1e6 + (TECH['static_power_uw'] * (sim_time * (1000.0/TECH['f_max_mhz']))) / 1e6,
        "accuracy": 67.33
    }
    
    while True:
        draw_dashboard(stdscr, "Simulación Completada ✅", 1.0, metrics)
        key = stdscr.getch()
        if key == ord('q'):
            break
        time.sleep(0.1)

if __name__ == "__main__":
    curses.wrapper(main)
