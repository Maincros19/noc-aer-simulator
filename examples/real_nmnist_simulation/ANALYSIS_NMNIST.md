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

## Análisis de Régimen de Operación: Baja Carga

Para comprender mejor el comportamiento de la red en condiciones no saturadas, se realizó una simulación con una traza de **baja carga** (los primeros 1,000 eventos de N-MNIST).

### Resultados de Baja Carga (1,000 flits)

| Métrica | `cycle_sim.py` (Alta Fidelidad) | `fast_sim.py` (Analítico) |
| :------------------ | :-------------------- | :-------------------- |
| **Flits Procesados** | **1,000**             | **1,000**             |
| **Latencia Promedio** | **211.25 ciclos**     | **8.87 ciclos**       |
| **Jitter (StdDev)** | **171.39 ciclos**     | **2.92 ciclos**       |
| **Total Hops**      | **3,032**             | **3,032**             |

### Comparativa Baja Carga vs. Alta Carga

| Escenario | `cycle_sim.py` (Latencia Promedio) | `fast_sim.py` (Latencia Promedio) |
| :---------------- | :--------------------------------- | :-------------------------------- |
| **Baja Carga (1k)** | **211.25 ciclos**                  | **8.87 ciclos**                   |
| **Alta Carga (411k)** | **49,288.80 ciclos**               | **367.79 ciclos**                 |

![Comparativa de Carga](load_comparison.png)

### Interpretación de los Resultados de Baja Carga

1.  **Diferencia Persistente:** Incluso con baja carga, `cycle_sim.py` sigue reportando una latencia significativamente mayor que `fast_sim.py`. Esto se debe a que, aunque no hay saturación global, los mecanismos de arbitraje y la gestión de buffers introducen una latencia base por cada salto y por las micro-contenciones locales que `fast_sim.py` no modela con la misma granularidad. `fast_sim.py` sigue siendo más optimista en su estimación de latencia.
2.  **Escalabilidad de la Congestión:** La latencia de `cycle_sim.py` escala drásticamente de 211 ciclos (baja carga) a casi 50,000 ciclos (alta carga), lo que confirma que el *backpressure* es el factor dominante en la saturación de la red. En contraste, `fast_sim.py` muestra un aumento de latencia de 8.87 a 367.79 ciclos, un incremento considerable pero mucho menos abrupto, ya que su modelo analítico suaviza los picos de congestión.

## Conclusión General

La combinación de simulaciones de baja y alta carga, junto con la evolución del modelo de `cycle_sim.py`, proporciona una visión completa del comportamiento de la NoC:

*   **`fast_sim.py`:** Es ideal para la exploración rápida del espacio de diseño y para obtener estimaciones de latencia en escenarios de baja a media carga, donde la congestión no es el factor dominante.
*   **`cycle_sim.py` (Alta Fidelidad):** Es indispensable para la validación detallada del hardware, la identificación de cuellos de botella por *backpressure* y la caracterización del rendimiento en escenarios de saturación crítica. Revela las limitaciones reales de la arquitectura bajo cargas intensas.

Ambos simuladores son herramientas complementarias que, utilizadas en conjunto, permiten un diseño robusto y optimizado de NoCs para sistemas neuromórficos.
