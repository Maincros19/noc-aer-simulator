# Ejemplos de Ejecución

Esta carpeta contiene ejemplos prácticos de cómo utilizar los simuladores del proyecto con datos reales de una Red Neuronal Espiking (SNN).

## Contenido

### 1. [Simulación Real N-MNIST](real_nmnist_simulation/)
Una ejecución completa utilizando una traza generada a partir de una inferencia real sobre el dataset N-MNIST.
- **Red Neuronal:** CSNN entrenada durante 100 iteraciones (Precisión final ~80%).
- **Traza:** `nmnist_trace.txt` (411,420 eventos).
- **Resultados:** Comparativa de rendimiento entre `cycle_sim.py` y `fast_sim.py`.
- **Gráficos:** Visualización de latencia, jitter y energía.

## Cómo ejecutar este ejemplo

Para replicar los resultados de la simulación real, puedes ejecutar:

```bash
# Para el simulador de ciclos
python3 python_simulator/src/cycle_sim.py examples/real_nmnist_simulation/nmnist_trace.txt python_simulator/config/mesh_4x4.config

# Para el simulador rápido
python3 python_simulator/src/fast_sim.py examples/real_nmnist_simulation/nmnist_trace.txt python_simulator/config/mesh_4x4.config
```

## Análisis de Resultados Reales

En esta simulación de alta densidad, se observa cómo el simulador rápido (`fast_sim.py`) aplica una penalización por congestión significativa debido al gran volumen de tráfico simultáneo generado por las capas convolucionales de la SNN, mientras que el simulador de ciclos (`cycle_sim.py`) ofrece una visión de la latencia base en un hardware idealmente sincronizado.
