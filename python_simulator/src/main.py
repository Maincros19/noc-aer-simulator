import simpy
import collections
import sys
import os
import math
import json

from .network import Network
from .packet import Packet, Flit

# Definiciones de puertos (igual que en C++)
NORTH, EAST, SOUTH, WEST, LOCAL = 0, 1, 2, 3, 4
NUM_PORTS = 5

class AERTraceEvent:
    def __init__(self, timestamp, source, destination, packet_size, packet_type):
        self.timestamp = int(timestamp)
        self.source = int(source)
        self.destination = int(destination)
        self.packet_size = int(packet_size)
        self.packet_type = packet_type

def load_config(config_file):
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            if key == 'MESH_DIM_X' or key == 'MESH_DIM_Y' or key == 'NUM_NODES' or key == 'BUFFER_SIZE':
                config[key] = int(value)
            elif key == 'MULTICAST_SUPPORT':
                config[key] = (value.upper() == 'TRUE')
            else:
                config[key] = value
    return config

def load_trace(trace_file):
    trace_events = []
    with open(trace_file, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) == 5:
                trace_events.append(AERTraceEvent(*parts))
    return trace_events

def simulate(env, network, trace_events, config):
    next_packet_id = 0
    all_injected_packets = {}

    # Ordenar eventos por timestamp
    trace_events.sort(key=lambda x: x.timestamp)

    # Proceso de inyección de tráfico
    def traffic_injector():
        nonlocal next_packet_id
        for event in trace_events:
            yield env.timeout(event.timestamp - env.now) # Esperar hasta el timestamp del evento
            
            # Crear un nuevo paquete
            packet = Packet(next_packet_id, event.source, {event.destination}, event.timestamp, event.packet_type)
            all_injected_packets[next_packet_id] = packet
            network.inject_packet(packet)
            next_packet_id += 1

    env.process(traffic_injector())
    env.process(network.run_network_cycle())

    # Bucle principal de simulación: Continúa hasta que no queden eventos por inyectar y todos los paquetes inyectados hayan sido entregados.
    # O hasta que se alcance un límite de ciclos, o se detecte estancamiento.
    MAX_SIM_CYCLES = trace_events[-1].timestamp + 5000 if trace_events else 5000 # Límite de ciclos
    STAGNATION_THRESHOLD = 2000 # Si no hay actividad en 2000 ciclos, asumir estancamiento
    cycles_without_activity = 0
    last_total_flit_hops = 0

    while env.now < MAX_SIM_CYCLES and (len(trace_events) > 0 or len(network.injected_packets) > 0 or cycles_without_activity < STAGNATION_THRESHOLD):
        yield env.timeout(1) # Avanzar un ciclo

        # Comprobar estancamiento
        if network.total_flit_hops == last_total_flit_hops and len(network.injected_packets) > 0:
            cycles_without_activity += 1
        else:
            cycles_without_activity = 0
            last_total_flit_hops = network.total_flit_hops
        
        if env.now % 1000 == 0:
            print(f"Simulando ciclo: {env.now}, Flits entregados: {len(network.completed_packets)}")

        # Si todos los eventos de la traza han sido inyectados, y no quedan paquetes en la red, terminar
        if len(trace_events) == 0 and len(network.injected_packets) == 0:
            break

    print(f"\n--- Resultados de la Simulación ---")
    print(f"Ciclos totales simulados: {env.now}")
    print(f"Flits inyectados: {next_packet_id}")
    print(f"Flits entregados: {len(network.completed_packets)}")

    # Cálculo de métricas finales
    all_latencies_for_metrics = []
    for packet in network.completed_packets:
        for dest_time in packet.delivery_times.values():
            latency = dest_time - packet.timestamp_injection
            all_latencies_for_metrics.append(latency)

    if all_latencies_for_metrics:
        avg_latency = sum(all_latencies_for_metrics) / len(all_latencies_for_metrics)
        print(f"Latencia promedio (ciclos): {avg_latency:.2f}")

        sum_sq_diff = sum([(lat - avg_latency) ** 2 for lat in all_latencies_for_metrics])
        jitter = math.sqrt(sum_sq_diff / len(all_latencies_for_metrics))
        print(f"Jitter (desviación estándar de latencia): {jitter:.2f}")
    else:
        print("No se pudieron calcular las métricas de latencia (ningún paquete completado).")

    # Mostrar actividad de enlaces (Top 5 enlaces más activos)
    print(f"\n--- Actividad de Enlaces (Top 5) ---")
    activity_list = []
    for r_id, ports in network.link_activity.items():
        for p, count in ports.items():
            activity_list.append({"router_id": r_id, "port": p, "count": count})
    
    activity_list.sort(key=lambda x: x["count"], reverse=True)

    port_names = {NORTH: "NORTH", EAST: "EAST", SOUTH: "SOUTH", WEST: "WEST", LOCAL: "LOCAL"}
    for i in range(min(5, len(activity_list))):
        link = activity_list[i]
        print(f"Router {link['router_id']} [{port_names[link['port']]}]: {link['count']} flits")

    # Estimación básica de energía
    ENERGY_PER_FLIT_HOP = 1.0 # Unidades de energía por hop de flit
    ENERGY_PER_SWITCH_TRAVERSAL = 0.5 # Unidades de energía por travesía de switch

    estimated_energy = (network.total_flit_hops * ENERGY_PER_FLIT_HOP) + \
                       (network.total_switch_traversals * ENERGY_PER_SWITCH_TRAVERSAL)
    print(f"Estimación de Energía Total: {estimated_energy:.2f} unidades")
    print(f"Flit Hops Totales: {network.total_flit_hops}")
    print(f"Switch Traversals Totales: {network.total_switch_traversals}")

    print("Simulación completada.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 main.py <trace_file> <config_file>")
        sys.exit(1)

    trace_file = sys.argv[1]
    config_file = sys.argv[2]

    config = load_config(config_file)
    trace_events = load_trace(trace_file)

    print(f"--- Configuración de NoC ---")
    for key, value in config.items():
        print(f"{key}: {value}")
    print(f"---------------------------")

    print(f"--- Iniciando Simulador de NoC AER ---")
    print(f"Leyendo traza: {trace_file}")
    print(f"Total de eventos de traza cargados: {len(trace_events)}")
    print(f"Simulando hasta el ciclo: {trace_events[-1].timestamp if trace_events else 0}...")

    env = simpy.Environment()
    network = Network(env, config)
    simulate(env, network, trace_events, config)
    env.run()
