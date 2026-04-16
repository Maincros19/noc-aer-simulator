import sys
import os
import math
import collections
import simpy

# --- INTEGRACIÓN DE MÓDULOS DE APOYO ---
# Importamos las clases de los archivos de apoyo
from packet import Packet, Flit
from router import Router, NORTH, EAST, SOUTH, WEST, LOCAL
from network import Network

# Nota: Para que esto funcione sin errores de importación relativa, 
# se asume que estamos ejecutando desde el directorio src.

class ModularNoCSimulator:
    """
    Versión modular de AdvancedNoCSimulator que utiliza los módulos de apoyo.
    """
    def __init__(self, config):
        self.env = simpy.Environment()
        self.config = config
        
        # En lugar de crear routers manualmente, usamos la clase Network
        # que ya encapsula la creación de routers y enlaces.
        self.network = Network(self.env, self.config)
        
        self.total_events = 0
        self.injected_count = 0

    def run(self, trace):
        """
        Ejecuta la simulación utilizando el motor de SimPy.
        """
        self.total_events = len(trace)
        
        print(f"Inyectando {self.total_events} eventos en la red...")
        for event in trace:
            p = Packet(
                packet_id=self.injected_count,
                source_node=event['source'],
                destination_nodes=[event['destination']],
                timestamp_injection=event['timestamp'],
                packet_type_str="AER_EVENT"
            )
            self.network.inject_packet(p)
            self.injected_count += 1

        self.env.process(self.network.run_network_cycle())
        
        print(f"--- Iniciando Simulación Modular (SimPy + Módulos de Apoyo) ---")
        # Monitoreo de progreso
        def monitor():
            while True:
                yield self.env.timeout(1000)
                if len(self.network.completed_packets) % 1000 == 0:
                    print(f"Ciclo {self.env.now} | Entregados: {len(self.network.completed_packets)}/{self.injected_count}")
                if len(self.network.completed_packets) >= self.injected_count:
                    break
        
        self.env.process(monitor())
        self.env.run(until=self.env.process(monitor()))

    def print_results(self):
        """
        Muestra resultados utilizando las métricas recolectadas por Network.
        """
        completed = len(self.network.completed_packets)
        print(f"\n--- Resultados de la Simulación Modular ---")
        print(f"Eventos inyectados: {self.injected_count}")
        print(f"Eventos entregados: {completed}")
        
        if completed > 0:
            total_lat = sum(p.delivery_times[list(p.destination_nodes)[0]] - p.timestamp_injection 
                            for p in self.network.completed_packets)
            print(f"Latencia promedio: {total_lat / completed:.2f} ciclos")
        print(f"Total Hops (acumulados en Network): {self.network.total_flit_hops}")

def load_config(config_file):
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            key, value = line.split('=', 1)
            config[key.strip()] = int(value) if value.strip().isdigit() else value.strip()
    
    # Asegurar campos mínimos para Network.py
    if 'NUM_NODES' not in config:
        config['NUM_NODES'] = int(config.get('MESH_DIM_X', 4)) * int(config.get('MESH_DIM_Y', 4))
    if 'BUFFER_SIZE' not in config:
        config['BUFFER_SIZE'] = 16
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
        print("Uso: python3 cycle_sim_modular.py <trace_file> <config_file>")
        sys.exit(1)

    config = load_config(sys.argv[2])
    trace = load_trace(sys.argv[1])
    # Para el modular, si la traza es muy grande, tomamos una muestra representativa
    # para evitar tiempos de ejecución excesivos en el entorno de sandbox
    if len(trace) > 20000:
        print(f"Traza grande detectada ({len(trace)}). Usando primeros 20000 eventos para validación modular.")
        trace = trace[:20000]
    
    sim = ModularNoCSimulator(config)
    sim.run(trace)
    sim.print_results()
