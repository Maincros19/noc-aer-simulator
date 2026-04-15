# NoC AER Simulator (Python Fast-Sim Edition)

Este proyecto es un simulador de **Network-on-Chip (NoC)** optimizado para el protocolo **Address Event Representation (AER)**, diseñado específicamente para sistemas neuromórficos (SNN).

## Estructura del Proyecto

- `traffic_generator/`: Generador de trazas basado en **snntorch** y **tonic**.
- `python_simulator/`: Simulador de NoC optimizado en Python.
  - `src/fast_sim.py`: Núcleo del simulador de alto rendimiento.
  - `config/`: Archivos de configuración de la topología (ej. `mesh_4x4.config`).

## Requisitos del Sistema

### Generador de Trazas (Python)
- Python 3.8+
- PyTorch
- snntorch
- tonic
- pandas, numpy, matplotlib, seaborn

### Simulador de NoC (Python)
- Python 3.8+
- No requiere librerías externas adicionales.

## Instrucciones de Uso

### 1. Generar la Traza
Navega a la carpeta del generador y ejecuta el script:
```bash
cd traffic_generator
python3 network_trace_generator_v2.py
```
Esto generará el archivo `generic_trace.txt`.

### 2. Ejecutar la Simulación
Navega a la carpeta del simulador y ejecuta el script rápido:
```bash
cd python_simulator/src
python3 fast_sim.py ../../traffic_generator/generic_trace.txt ../config/mesh_4x4.config
```

## Métricas Calculadas
- **Latencia Promedio:** Tiempo de tránsito de los spikes en ciclos de reloj.
- **Jitter:** Variabilidad temporal de la latencia (crítico para SNN).
- **Actividad de Nodos:** Identificación de hotspots y cuellos de botella.
- **Energía Estimada:** Basada en saltos (hops) y eventos procesados.

## Notas de Diseño
El simulador utiliza un modelo de **latencia analítica con penalización por congestión**, lo que permite procesar millones de eventos en segundos, manteniendo la precisión necesaria para el análisis de rendimiento en hardware neuromórfico.
