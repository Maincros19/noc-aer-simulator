# Análisis de Saturación y Alta Fidelidad: Simulación N-MNIST

## Introducción

Este análisis presenta los resultados finales de la simulación del dataset N-MNIST (411,420 eventos) utilizando el modelo de **Integridad Total** en `cycle_sim.py`. A diferencia de versiones anteriores, este modelo garantiza que **no se pierda ningún flit**, implementando colas de inyección con espera y modelando el *backpressure* real de la red.

## Resultados Finales: El Impacto de la Saturación

Al procesar la traza completa sin pérdidas, los resultados revelan un fenómeno crítico en el diseño de NoCs: la **saturación catastrófica**.

| Métrica | `cycle_sim.py` (Alta Fidelidad) | `fast_sim.py` (Analítico) | Diferencia |
| :------------------ | :-------------------- | :-------------------- | :--------------- |
| **Flits Procesados** | **411,420 (100%)**    | **411,420 (100%)**    | **Integridad Total** |
| **Latencia Promedio** | **49,288.80 ciclos**  | **367.79 ciclos**     | **Saturación Real** |
| **Jitter (StdDev)** | **28,709.98 ciclos**  | **276.71 ciclos**     | **Variabilidad Extrema** |
| **Total Hops**      | **1,190,989**         | **1,190,989**         | **Consistente** |

### ¿Por qué esta diferencia tan extrema?

La enorme diferencia en la latencia (~49k vs ~367) se explica por cómo cada simulador maneja el tráfico masivo:

1.  **Saturación por Backpressure (Cycle Sim):** Al no perderse flits, la red se satura rápidamente. Los buffers se llenan y el efecto de *backpressure* se propaga hacia atrás, deteniendo la inyección de nuevos eventos. Los flits inyectados al final de la traza deben esperar decenas de miles de ciclos hasta que la red se despeje. Esto es lo que ocurriría en un hardware real sin mecanismos de control de flujo avanzados.
2.  **Modelo Analítico (Fast Sim):** El simulador rápido utiliza una penalización estadística. Aunque detecta la congestión, su fórmula analítica tiende a ser más optimista en escenarios de saturación total, ya que no modela el bloqueo físico "en cadena" que ocurre ciclo a ciclo.

## Conclusiones del Análisis

*   **Integridad del Dato:** Se ha validado que el simulador de ciclos procesa el 100% de la actividad neuronal de N-MNIST, lo cual es vital para la precisión de la SNN.
*   **Diseño de Hardware:** La latencia de ~49,000 ciclos indica que una malla de 4x4 con buffers estándar es insuficiente para la ráfaga de actividad de esta SNN específica. Se recomienda aumentar el tamaño de los buffers o explorar topologías con mayor ancho de banda.
*   **Valor de la Comparativa:** Mientras que `fast_sim` es excelente para una estimación rápida de latencia base, `cycle_sim` es la única herramienta capaz de revelar el colapso de la red por saturación física.

![Gráfico de Saturación](comparison_chart.png)
