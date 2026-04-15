import sys
import math
import collections
import time

def load_config(config_file):
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()
    return config

def get_dist(src, dst, dim_x):
    src_x, src_y = src % dim_x, src // dim_x
    dst_x, dst_y = dst % dim_x, dst // dim_x
    return abs(src_x - dst_x) + abs(src_y - dst_y)

def run_fast_sim(trace_file, config):
    dim_x = int(config.get('MESH_DIM_X', 4))
    dim_y = int(config.get('MESH_DIM_Y', 4))
    
    events = []
    with open(trace_file, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 4:
                events.append({
                    'ts': int(parts[0]),
                    'src': int(parts[1]),
                    'dst': int(parts[2]),
                    'type': parts[4] if len(parts) > 4 else 'unknown'
                })
    
    print(f"--- Iniciando Simulador Rápido NoC AER ---")
    print(f"Eventos cargados: {len(events)}")
    
    start_time = time.time()
    
    # Métricas
    delivered_count = 0
    total_latency = 0
    latencies = []
    link_usage = collections.defaultdict(int)
    total_hops = 0
    
    # Modelo de congestión simple: contador de flits por nodo por ventana de tiempo
    node_load = collections.defaultdict(int)
    
    for ev in events:
        src, dst = ev['src'], ev['dst']
        hops = get_dist(src, dst, dim_x)
        
        # Latencia base = hops * ciclos_por_hop (ej. 2 ciclos por router)
        # Penalización por congestión basada en la carga del nodo origen
        congestion_delay = node_load[src] // 100 
        latency = (hops * 2) + 1 + congestion_delay
        
        arrival_ts = ev['ts'] + latency
        latencies.append(latency)
        total_latency += latency
        total_hops += hops
        delivered_count += 1
        
        # Registrar actividad de enlaces (simplificado: origen -> destino)
        link_usage[src] += 1
        
        # Actualizar carga del nodo (se "limpia" cada 100 ciclos de simulación)
        node_load[src] += 1
        if ev['ts'] % 100 == 0:
            for n in node_load: node_load[n] = max(0, node_load[n] - 10)

    end_time = time.time()
    
    print(f"\n--- Resultados de la Simulación (Modo Rápido) ---")
    print(f"Tiempo de ejecución: {end_time - start_time:.2f} segundos")
    print(f"Flits procesados: {delivered_count}")
    
    if delivered_count > 0:
        avg_lat = total_latency / delivered_count
        print(f"Latencia promedio: {avg_lat:.2f} ciclos")
        
        variance = sum((l - avg_lat) ** 2 for l in latencies) / delivered_count
        print(f"Jitter (StdDev): {math.sqrt(variance):.2f} ciclos")
    
    print(f"Total Hops: {total_hops}")
    print(f"Energía Estimada: {total_hops * 1.0 + delivered_count * 0.5:.2f} unidades")
    
    print("\n--- Top 5 Nodos más Activos ---")
    sorted_links = sorted(link_usage.items(), key=lambda x: x[1], reverse=True)
    for node, count in sorted_links[:5]:
        print(f"Nodo {node}: {count} eventos inyectados")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 fast_sim.py <trace> <config>")
    else:
        cfg = load_config(sys.argv[2])
        run_fast_sim(sys.argv[1], cfg)
