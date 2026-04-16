# NoC AER Simulator

Este proyecto es un simulador de **Network-on-Chip (NoC)** optimizado para el protocolo **Address Event Representation (AER)**, diseñado específicamente para sistemas neuromórficos (SNN). Ofrece dos enfoques de simulación principales: un **simulador analítico rápido (`fast_sim.py`)** para evaluaciones de alto rendimiento y un **simulador basado en ciclos (`cycle_sim.py`)** para un modelado detallado a nivel de hardware.

## Tipos de Simuladores

| Simulador | Enfoque Principal | Características Clave | Casos de Uso |
| :-------- | :---------------- | :-------------------- | :----------- |
| `fast_sim.py` | **Analítico y Rápido** | Calcula latencias y congestión mediante fórmulas. Ideal para millones de eventos. | Prototipado rápido, exploración de diseños, análisis de tendencias. |
| `cycle_sim.py` | **Arquitectura Avanzada** | Modela routers con **Canales Virtuales (VCs)** y **Control de Flujo por Créditos**. | Validación profesional de hardware, mitigación de HoL blocking, análisis de saturación real. |

Para una comparación más detallada, consulta [Comparación de Simuladores: `fast_sim.py` vs. `cycle_sim.py`](COMPARISON.md).

Puedes encontrar ejemplos de ejecución y resultados reales en la carpeta [examples/](examples/). Para un análisis detallado de la simulación real de N-MNIST, consulta [aquí](examples/real_nmnist_simulation/ANALYSIS_NMNIST.md).

## Estructura del Proyecto

- `traffic_generator/`: Generador de trazas basado en **snntorch** y **tonic**. Incluye entrenamiento de SNN sobre N-MNIST.
- `python_simulator/`: Simulador de NoC optimizado en Python.
  - `src/`: Contiene los scripts de simulación (`fast_sim.py`, `cycle_sim.py`, `network.py`, `router.py`, etc.).
  - `config/`: Archivos de configuración de la topología (ej. `mesh_4x4.config`).
- `examples/`: Carpeta con ejemplos de ejecución, trazas de prueba y resultados comparativos.

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

### 1. Generar la Traza Real (N-MNIST)
Navega a la carpeta del generador y ejecuta el script (entrenará la red durante 100 iteraciones):
```bash
cd traffic_generator
python3 network_trace_generator_v2.py
```
Esto generará el archivo `nmnist_trace.txt`.

### 2. Ejecutar la Simulación
Navega a la carpeta del simulador y ejecuta el script rápido:
```bash
cd python_simulator/src
python3 fast_sim.py ../../traffic_generator/nmnist_trace.txt ../config/mesh_4x4.config
```

## Métricas Calculadas
- **Latencia Promedio:** Tiempo de tránsito de los spikes en ciclos de reloj.
- **Jitter:** Variabilidad temporal de la latencia (crítico para SNN).
- **Actividad de Nodos:** Identificación de hotspots y cuellos de botella.
- **Energía Estimada:** Basada en saltos (hops) y eventos procesados. Consulta el [Modelo de Energía Detallado](python_simulator/docs/modelo_energia_detallado.md) para más información.

## Notas de Diseño
El simulador utiliza un modelo de **latencia analítica con penalización por congestión**, lo que permite procesar millones de eventos en segundos, manteniendo la precisión necesaria para el análisis de rendimiento en hardware neuromórfico.
