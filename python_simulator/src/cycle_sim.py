import sys
import os
import math
import collections

# Definiciones de puertos
NORTH, EAST, SOUTH, WEST, LOCAL = 0, 1, 2, 3, 4
PORT_NAMES = {NORTH: "NORTH", EAST: "EAST", SOUTH: "SOUTH", WEST: "WEST", LOCAL: "LOCAL"}

class Flit:
    __slots__ = ['packet_id', 'source', 'destination', 'timestamp_injection', 'current_node', 'hops', 'timestamp_arrival', 'vc_id']
    def __init__(self, packet_id, source, destination, timestamp_injection):
        self.packet_id = packet_id
        self.source = source
        self.destination = destination
        self.timestamp_injection = timestamp_injection
        self.current_node = source
        self.hops = 0
        self.timestamp_arrival = -1
        self.vc_id = 0 # ID del Canal Virtual asignado

class Router:
    __slots__ = ['node_id', 'input_buffers', 'next_input_to_serve', 'credits', 'num_vcs']
    def __init__(self, node_id, buffer_size, num_vcs=2):
        self.node_id = node_id
        self.num_vcs = num_vcs
        # Buffers de entrada por puerto y por VC
        # input_buffers[puerto][vc_id] = deque
        self.input_buffers = [[collections.deque(maxlen=buffer_size // num_vcs) for _ in range(num_vcs)] for _ in range(5)]
        
        # Créditos disponibles en los vecinos (por puerto y por VC)
        # Inicialmente, cada vecino tiene capacidad total del buffer/num_vcs
        self.credits = [[buffer_size // num_vcs for _ in range(num_vcs)] for _ in range(5)]
        
        # Arbitraje Round Robin por puerto de salida
        self.next_input_to_serve = [0] * 5

class AdvancedNoCSimulator:
    def __init__(self, config):
        self.dim_x = config['MESH_DIM_X']
        self.dim_y = config['MESH_DIM_Y']
        self.num_nodes = config['NUM_NODES']
        self.buffer_size = config.get('BUFFER_SIZE', 16)
        self.num_vcs = config.get('NUM_VCS', 2) # Por defecto 2 canales virtuales
        
        self.current_cycle = 0
        self.routers = [Router(i, self.buffer_size, self.num_vcs) for i in range(self.num_nodes)]
        self.completed_count = 0
        self.total_latency = 0
        self.latency_sq_sum = 0
        self.link_activity = collections.defaultdict(lambda: collections.defaultdict(int))
        self.total_hops = 0
        self.injected_count = 0
        
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
        # 1. Inyección
        for event in new_events:
            flit = Flit(self.injected_count, event['source'], event['destination'], event['timestamp'])
            self.injection_queues[flit.source].append(flit)
            self.injected_count += 1

        for i in range(self.num_nodes):
            router = self.routers[i]
            queue = self.injection_queues[i]
            # Inyectar en el primer VC disponible del puerto LOCAL
            while queue:
                injected = False
                for vc in range(self.num_vcs):
                    if len(router.input_buffers[LOCAL][vc]) < (self.buffer_size // self.num_vcs):
                        flit = queue.popleft()
                        flit.vc_id = vc
                        router.input_buffers[LOCAL][vc].append(flit)
                        injected = True
                        break
                if not injected: break

        # 2. Movimiento (Arbitraje + Créditos)
        transfers = [] # (dest_router_idx, dest_port, dest_vc, flit)
        credit_returns = [] # (router_idx, port, vc)

        for router_id in range(self.num_nodes):
            router = self.routers[router_id]
            for out_port in range(5):
                start_in = router.next_input_to_serve[out_port]
                moved_in_this_port = False
                
                # Arbitraje entre puertos de entrada y VCs
                for i in range(5 * self.num_vcs):
                    in_port = ((start_in + i) // self.num_vcs) % 5
                    in_vc = (start_in + i) % self.num_vcs
                    
                    buffer = router.input_buffers[in_port][in_vc]
                    if buffer:
                        flit = buffer[0]
                        if self.get_next_port(router_id, flit.destination) == out_port:
                            if out_port == LOCAL:
                                buffer.popleft()
                                # Devolver crédito al vecino que nos envió este flit
                                if in_port != LOCAL:
                                    neighbor_id = self.get_neighbor_id(router_id, in_port)
                                    # El vecino que nos envió por su EAST nos ve por su WEST
                                    rev_port = [SOUTH, WEST, NORTH, EAST, -1][in_port]
                                    credit_returns.append((neighbor_id, rev_port, in_vc))
                                
                                lat = self.current_cycle + 1 - flit.timestamp_injection
                                self.total_latency += lat
                                self.latency_sq_sum += lat * lat
                                self.completed_count += 1
                                router.next_input_to_serve[out_port] = (in_port * self.num_vcs + in_vc + 1) % (5 * self.num_vcs)
                                moved_in_this_port = True
                                break
                            else:
                                neighbor_id = self.get_neighbor_id(router_id, out_port)
                                if neighbor_id != -1:
                                    # Intentar asignar un VC en el vecino que tenga créditos
                                    for next_vc in range(self.num_vcs):
                                        if router.credits[out_port][next_vc] > 0:
                                            buffer.popleft()
                                            # Devolver crédito al vecino anterior (si no es local)
                                            if in_port != LOCAL:
                                                prev_neighbor_id = self.get_neighbor_id(router_id, in_port)
                                                rev_port = [SOUTH, WEST, NORTH, EAST, -1][in_port]
                                                credit_returns.append((prev_neighbor_id, rev_port, in_vc))
                                            
                                            flit.current_node = neighbor_id
                                            flit.hops += 1
                                            flit.vc_id = next_vc
                                            
                                            # Consumir crédito del vecino actual
                                            router.credits[out_port][next_vc] -= 1
                                            
                                            in_port_neighbor = [SOUTH, WEST, NORTH, EAST, -1][out_port]
                                            transfers.append((neighbor_id, in_port_neighbor, next_vc, flit))
                                            
                                            self.link_activity[router_id][out_port] += 1
                                            self.total_hops += 1
                                            router.next_input_to_serve[out_port] = (in_port * self.num_vcs + in_vc + 1) % (5 * self.num_vcs)
                                            moved_in_this_port = True
                                            break
                    if moved_in_this_port: break

        # 3. Aplicar transferencias y retornos de créditos
        for d_idx, d_port, d_vc, flit in transfers:
            self.routers[d_idx].input_buffers[d_port][d_vc].append(flit)
        
        for r_idx, port, vc in credit_returns:
            if r_idx != -1:
                self.routers[r_idx].credits[port][vc] += 1

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

    # Configuración avanzada (se puede mover al archivo .config)
    config['NUM_VCS'] = 4  # Aumentamos a 4 VCs para mayor profesionalismo
    config['BUFFER_SIZE'] = 32 # Buffer total por puerto (8 flits por VC)

    sim = AdvancedNoCSimulator(config)
    event_idx = 0
    
    print(f"--- Iniciando Simulador de Ciclos PROFESIONAL (VCs + Créditos) ---")
    print(f"Configuración: Malla {config['MESH_DIM_X']}x{config['MESH_DIM_Y']}, VCs: {config['NUM_VCS']}, Buffer/Port: {config['BUFFER_SIZE']}")
    
    def is_simulation_active(sim, trace_idx, trace_len):
        if trace_idx < trace_len: return True
        if any(q for q in sim.injection_queues): return True
        for r in sim.routers:
            for p in range(5):
                for vc in range(sim.num_vcs):
                    if r.input_buffers[p][vc]: return True
        return False

    while is_simulation_active(sim, event_idx, len(trace)):
        current_events = []
        while event_idx < len(trace) and trace[event_idx]['timestamp'] <= sim.current_cycle:
            current_events.append(trace[event_idx])
            event_idx += 1
        
        sim.step(current_events)
        
        if sim.current_cycle % 10000 == 0 and sim.current_cycle > 0:
            print(f"Ciclo {sim.current_cycle} | Entregados: {sim.completed_count}/{len(trace)} | En red: {sim.injected_count - sim.completed_count}")

        if sim.current_cycle > 10000000: break

    print(f"\n--- Resultados de la Simulación (Arquitectura Avanzada) ---")
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
