import sys
import os
import math
import collections

# Definiciones de puertos
NORTH, EAST, SOUTH, WEST, LOCAL = 0, 1, 2, 3, 4
PORT_NAMES = {NORTH: "NORTH", EAST: "EAST", SOUTH: "SOUTH", WEST: "WEST", LOCAL: "LOCAL"}

class Flit:
    __slots__ = ['packet_id', 'source', 'destination', 'timestamp_injection', 'current_node', 'hops', 'timestamp_arrival']
    def __init__(self, packet_id, source, destination, timestamp_injection):
        self.packet_id = packet_id
        self.source = source
        self.destination = destination
        self.timestamp_injection = timestamp_injection
        self.current_node = source
        self.hops = 0
        self.timestamp_arrival = -1

class Router:
    __slots__ = ['node_id', 'input_buffers', 'next_input_to_serve']
    def __init__(self, node_id, buffer_size):
        self.node_id = node_id
        # Buffers de entrada para cada puerto (FIFO)
        self.input_buffers = [collections.deque(maxlen=buffer_size) for _ in range(5)]
        # Estado del árbitro para cada puerto de salida (Round Robin)
        self.next_input_to_serve = [0] * 5

class HighFidelityCycleSimulator:
    def __init__(self, config):
        self.dim_x = config['MESH_DIM_X']
        self.dim_y = config['MESH_DIM_Y']
        self.num_nodes = config['NUM_NODES']
        self.buffer_size = config['BUFFER_SIZE']
        
        self.current_cycle = 0
        self.routers = [Router(i, self.buffer_size) for i in range(self.num_nodes)]
        self.completed_count = 0
        self.total_latency = 0
        self.latency_sq_sum = 0
        self.link_activity = collections.defaultdict(lambda: collections.defaultdict(int))
        self.total_hops = 0
        self.injected_count = 0
        
        # Buffer de espera para inyección si el puerto LOCAL está lleno
        self.injection_queues = [collections.deque() for _ in range(self.num_nodes)]

    def get_coordinates(self, node_id):
        return node_id % self.dim_x, node_id // self.dim_x

    def get_next_port(self, current_node, dest_node):
        curr_x, curr_y = current_node % self.dim_x, current_node // self.dim_x
        dest_x, dest_y = dest_node % self.dim_x, dest_node // self.dim_x
        
        if curr_x < dest_x: return EAST
        if curr_x > dest_x: return WEST
        if curr_y < dest_y: return SOUTH
        if curr_y > dest_y: return NORTH
        return LOCAL

    def get_neighbor_id(self, node_id, port):
        x, y = node_id % self.dim_x, node_id // self.dim_x
        if port == NORTH and y > 0: return node_id - self.dim_x
        if port == SOUTH and y < self.dim_y - 1: return node_id + self.dim_x
        if port == EAST and x < self.dim_x - 1: return node_id + 1
        if port == WEST and x > 0: return node_id - 1
        return -1

    def step(self, new_events):
        # 1. Añadir nuevos eventos a la cola de inyección del nodo correspondiente
        for event in new_events:
            flit = Flit(self.injected_count, event['source'], event['destination'], event['timestamp'])
            self.injection_queues[flit.source].append(flit)
            self.injected_count += 1

        # 2. Intentar inyectar flits de la cola al puerto LOCAL del router (si hay espacio)
        for i in range(self.num_nodes):
            router = self.routers[i]
            queue = self.injection_queues[i]
            while queue and len(router.input_buffers[LOCAL]) < self.buffer_size:
                router.input_buffers[LOCAL].append(queue.popleft())

        # 3. Movimiento entre Routers (Switch Traversal & Link Traversal)
        transfers = [] # (dest_router_idx, dest_port, flit)

        for router_id in range(self.num_nodes):
            router = self.routers[router_id]
            for out_port in range(5):
                start_in = router.next_input_to_serve[out_port]
                for i in range(5):
                    in_port = (start_in + i) % 5
                    buffer = router.input_buffers[in_port]
                    if buffer:
                        flit = buffer[0]
                        if self.get_next_port(router_id, flit.destination) == out_port:
                            if out_port == LOCAL:
                                # Entrega final
                                buffer.popleft()
                                lat = self.current_cycle + 1 - flit.timestamp_injection
                                self.total_latency += lat
                                self.latency_sq_sum += lat * lat
                                self.completed_count += 1
                                router.next_input_to_serve[out_port] = (in_port + 1) % 5
                                break
                            else:
                                # Movimiento a vecino
                                neighbor_id = self.get_neighbor_id(router_id, out_port)
                                if neighbor_id != -1:
                                    neighbor = self.routers[neighbor_id]
                                    # Puerto opuesto en el vecino
                                    in_port_neighbor = [SOUTH, WEST, NORTH, EAST, -1][out_port]
                                    if len(neighbor.input_buffers[in_port_neighbor]) < self.buffer_size:
                                        buffer.popleft()
                                        flit.current_node = neighbor_id
                                        flit.hops += 1
                                        transfers.append((neighbor_id, in_port_neighbor, flit))
                                        self.link_activity[router_id][out_port] += 1
                                        self.total_hops += 1
                                        router.next_input_to_serve[out_port] = (in_port + 1) % 5
                                        break

        # 4. Aplicar transferencias al final del ciclo
        for d_idx, d_port, flit in transfers:
            self.routers[d_idx].input_buffers[d_port].append(flit)

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
                events.append({'timestamp': int(parts[0]), 'source': int(parts[1]), 'destination': int(parts[2])})
    return events

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 cycle_sim.py <trace_file> <config_file>")
        sys.exit(1)

    config = load_config(sys.argv[2])
    trace = load_trace(sys.argv[1])
    trace.sort(key=lambda x: x['timestamp'])

    sim = HighFidelityCycleSimulator(config)
    event_idx = 0
    
    print(f"--- Iniciando Simulador de Ciclos de Alta Fidelidad (Integridad Total) ---")
    print(f"Traza cargada: {len(trace)} eventos.")
    
    # Simular mientras queden eventos en la traza, en las colas de inyección o en los buffers de los routers
    def is_simulation_active(sim, trace_idx, trace_len):
        if trace_idx < trace_len: return True
        if any(q for q in sim.injection_queues): return True
        if any(any(b for b in r.input_buffers) for r in sim.routers): return True
        return False

    while is_simulation_active(sim, event_idx, len(trace)):
        current_events = []
        while event_idx < len(trace) and trace[event_idx]['timestamp'] <= sim.current_cycle:
            current_events.append(trace[event_idx])
            event_idx += 1
        
        sim.step(current_events)
        
        if sim.current_cycle % 10000 == 0 and sim.current_cycle > 0:
            print(f"Ciclo {sim.current_cycle} | Entregados: {sim.completed_count}/{len(trace)} | En red: {sim.injected_count - sim.completed_count}")

        if sim.current_cycle > 10000000: # Límite de seguridad extendido para alta congestión
            print("AVISO: Límite de ciclos alcanzado.")
            break

    print(f"\n--- Resultados de la Simulación (Alta Fidelidad) ---")
    print(f"Ciclos totales: {sim.current_cycle}")
    print(f"Flits inyectados: {sim.injected_count}")
    print(f"Flits entregados: {sim.completed_count}")
    
    if sim.completed_count > 0:
        avg_lat = sim.total_latency / sim.completed_count
        var = (sim.latency_sq_sum / sim.completed_count) - (avg_lat * avg_lat)
        print(f"Latencia promedio: {avg_lat:.2f} ciclos")
        print(f"Jitter (StdDev): {math.sqrt(max(0, var)):.2f} ciclos")
    
    print(f"Total Hops: {sim.total_hops}")
    print(f"Energía Estimada: {sim.total_hops * 1.0 + sim.completed_count * 0.5:.2f} unidades")
