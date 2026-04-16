import sys
import os
import math
import collections

# Definiciones de puertos
NORTH, EAST, SOUTH, WEST, LOCAL = 0, 1, 2, 3, 4
PORT_NAMES = {NORTH: "NORTH", EAST: "EAST", SOUTH: "SOUTH", WEST: "WEST", LOCAL: "LOCAL"}

class Flit:
    def __init__(self, packet_id, source, destination, timestamp_injection):
        self.packet_id = packet_id
        self.source = source
        self.destination = destination
        self.timestamp_injection = timestamp_injection
        self.current_node = source
        self.hops = 0

class CycleSimulator:
    def __init__(self, config):
        self.dim_x = config['MESH_DIM_X']
        self.dim_y = config['MESH_DIM_Y']
        self.num_nodes = config['NUM_NODES']
        self.buffer_size = config['BUFFER_SIZE']
        
        self.current_cycle = 0
        self.pending_flits = [] # Flits actualmente en tránsito
        self.completed_flits = []
        self.link_activity = collections.defaultdict(lambda: collections.defaultdict(int))
        self.total_hops = 0

    def get_coordinates(self, node_id):
        return node_id % self.dim_x, node_id // self.dim_x

    def get_next_port(self, current_node, dest_node):
        curr_x, curr_y = self.get_coordinates(current_node)
        dest_x, dest_y = self.get_coordinates(dest_node)
        
        if curr_x < dest_x: return EAST
        if curr_x > dest_x: return WEST
        if curr_y < dest_y: return SOUTH
        if curr_y > dest_y: return NORTH
        return LOCAL

    def step(self, new_events):
        # 1. Inyectar nuevos eventos
        for event in new_events:
            flit = Flit(len(self.completed_flits) + len(self.pending_flits), 
                        event['source'], event['destination'], self.current_cycle)
            self.pending_flits.append(flit)

        # 2. Mover flits en tránsito (Simulación de un ciclo)
        still_pending = []
        for flit in self.pending_flits:
            port = self.get_next_port(flit.current_node, flit.destination)
            
            if port == LOCAL:
                flit.timestamp_arrival = self.current_cycle
                self.completed_flits.append(flit)
            else:
                # Mover al siguiente nodo
                self.link_activity[flit.current_node][port] += 1
                self.total_hops += 1
                flit.hops += 1
                
                if port == EAST: flit.current_node += 1
                elif port == WEST: flit.current_node -= 1
                elif port == SOUTH: flit.current_node += self.dim_x
                elif port == NORTH: flit.current_node -= self.dim_x
                
                still_pending.append(flit)
        
        self.pending_flits = still_pending
        self.current_cycle += 1

def load_config(config_file):
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            key, value = line.split('=', 1)
            config[key.strip()] = int(value) if value.strip().isdigit() else value.strip()
    return config

def load_trace(trace_file):
    events = []
    with open(trace_file, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                events.append({
                    'timestamp': int(parts[0]),
                    'source': int(parts[1]),
                    'destination': int(parts[2])
                })
    return events

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 cycle_sim.py <trace_file> <config_file>")
        sys.exit(1)

    config = load_config(sys.argv[2])
    trace = load_trace(sys.argv[1])
    trace.sort(key=lambda x: x['timestamp'])

    sim = CycleSimulator(config)
    
    event_idx = 0
    while event_idx < len(trace) or sim.pending_flits:
        current_events = []
        while event_idx < len(trace) and trace[event_idx]['timestamp'] <= sim.current_cycle:
            current_events.append(trace[event_idx])
            event_idx += 1
        
        sim.step(current_events)
        
        if sim.current_cycle > 10000: # Safety break
            print("AVISO: Límite de ciclos alcanzado.")
            break

    # Resultados
    print(f"\n--- Resultados de la Simulación (Modo Ciclo Simplificado) ---")
    print(f"Ciclos totales: {sim.current_cycle}")
    print(f"Flits inyectados: {len(sim.completed_flits)}")
    
    latencies = [f.timestamp_arrival - f.timestamp_injection for f in sim.completed_flits]
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        jitter = math.sqrt(sum((l - avg_lat)**2 for l in latencies) / len(latencies))
        print(f"Latencia promedio: {avg_lat:.2f} ciclos")
        print(f"Jitter (StdDev): {jitter:.2f} ciclos")
    
    print(f"Total Hops: {sim.total_hops}")
    energy = sim.total_hops * 1.0 + len(sim.completed_flits) * 0.5
    print(f"Energía Estimada: {energy:.2f} unidades")
    
    print("\n--- Top 5 Enlaces más Activos ---")
    activity = []
    for node, ports in sim.link_activity.items():
        for port, count in ports.items():
            activity.append((node, port, count))
    activity.sort(key=lambda x: x[2], reverse=True)
    for i in range(min(5, len(activity))):
        node, port, count = activity[i]
        print(f"Nodo {node} [{PORT_NAMES[port]}]: {count} flits")
