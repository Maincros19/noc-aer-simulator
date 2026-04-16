# NoC AER Simulator

Este proyecto es un simulador de **Network-on-Chip (NoC)** optimizado para el protocolo **Address Event Representation (AER)**, diseñado específicamente para sistemas neuromórficos (SNN). Ofrece dos enfoques de simulación principales: un **simulador analítico rápido (`fast_sim.py`)** para evaluaciones de alto rendimiento y un **simulador basado en ciclos (`cycle_sim.py`)** para un modelado detallado a nivel de hardware.

## Tipos de Simuladores

| Simulador | Enfoque Principal | Características Clave | Casos de Uso |
| :-------- | :---------------- | :-------------------- | :----------- |
| `fast_sim.py` | **Analítico y Rápido** | Calcula latencias y congestión mediante fórmulas. Ideal para millones de eventos. | Prototipado rápido, exploración de diseños, análisis de tendencias. |
| `cycle_sim.py` | **Basado en Ciclos** | Modela routers y paquetes ciclo a ciclo. Preciso para detalles de hardware. | Validación de lógica de control de flujo, diseño de buffers, algoritmos de enrutamiento. |

Para una comparación más detallada, consulta [Comparación de Simuladores: `fast_sim.py` vs. `main.py`](COMPARISON.md).

## Estructura del Proyecto

- `traffic_generator/`: Generador de trazas basado en **snntorch** y **tonic**.
- `python_simulator/`: Simulador de NoC optimizado en Python.
  - `src/`: Contiene los scripts de simulación (`fast_sim.py`, `main.py`, `network.py`, `router.py`, etc.).
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
- **Energía Estimada:** Basada en saltos (hops) y eventos procesados. Consulta el [Modelo de Energía Detallado](python_simulator/docs/modelo_energia_detallado.md) para más información.

## Notas de Diseño
El simulador utiliza un modelo de **latencia analítica con penalización por congestión**, lo que permite procesar millones de eventos en segundos, manteniendo la precisión necesaria para el análisis de rendimiento en hardware neuromórfico.
