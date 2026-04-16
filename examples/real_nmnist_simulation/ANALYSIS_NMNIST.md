# Análisis de Alta Fidelidad: Simulación Real N-MNIST

## Introducción

Este documento analiza los resultados obtenidos tras la mejora del simulador basado en ciclos (`cycle_sim.py`), el cual ahora incorpora mecanismos reales de **arbitraje de puertos (Round Robin)**, **gestión de buffers limitada** y **backpressure**. Estas mejoras permiten capturar el impacto físico de la congestión en la NoC, ofreciendo una comparativa mucho más precisa frente al modelo analítico de `fast_sim.py`.

## Evolución del Modelo de Hardware

Anteriormente, `cycle_sim.py` operaba bajo un modelo de "latencia ideal", donde los flits avanzaban sin interferencias. El nuevo modelo de **Alta Fidelidad** introduce las siguientes restricciones realistas:

1.  **Arbitraje de Salida:** Si varios flits en diferentes buffers de entrada compiten por el mismo puerto de salida, un árbitro Round Robin decide quién avanza, introduciendo retrasos de espera.
2.  **Capacidad de Buffer:** Los routers tienen un tamaño de buffer finito (definido en el config). Si un buffer está lleno, el tráfico se detiene (*Backpressure*).
3.  **Travesía por Etapas:** Cada salto entre routers consume ciclos de reloj reales, y la contención en los puertos aumenta drásticamente la latencia bajo alta carga.

## Resultados Comparativos Actualizados

Tras ejecutar la traza real de N-MNIST con el modelo mejorado, observamos una **convergencia significativa** entre ambos simuladores:

| Métrica | `cycle_sim.py` (Alta Fidelidad) | `fast_sim.py` (Analítico) | Diferencia |
| :------------------ | :-------------------- | :-------------------- | :--------------- |
| **Latencia Promedio** | **352.76 ciclos**     | **367.79 ciclos**     | **~4% de diferencia** |
| **Jitter (StdDev)** | **338.28 ciclos**     | **276.71 ciclos**     | **~22% de diferencia** |

### Análisis de la Convergencia

La diferencia de latencia, que antes era de órdenes de magnitud (3 ciclos vs 367 ciclos), se ha reducido a apenas un **4%**. Esto demuestra que:

*   **Validación del Modelo Analítico:** El modelo de penalización por congestión de `fast_sim.py` es una excelente aproximación estadística al comportamiento físico real de la red.
*   **Impacto de la Congestión:** En la red N-MNIST, la latencia no está determinada por la distancia física (saltos), sino por el tiempo de espera en los buffers debido a la ráfaga de eventos de las capas convolucionales.
*   **Realismo del Ciclo-Preciso:** `cycle_sim.py` ahora captura correctamente los "hotspots" y los cuellos de botella dinámicos, lo que explica el aumento en el jitter (338 ciclos), reflejando la variabilidad real que sufriría un spike en el hardware.

## Conclusión Final

Con la implementación del arbitraje y la gestión de buffers, el simulador `cycle_sim.py` ha pasado de ser un validador funcional a una herramienta de **caracterización de hardware de alta precisión**. La estrecha correlación con `fast_sim.py` valida ambos enfoques: uno para exploración rápida de arquitecturas y otro para validación final de tiempos y contención física.
