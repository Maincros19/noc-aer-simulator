# Análisis Detallado de la Simulación Real N-MNIST

## Introducción

Este documento presenta un análisis en profundidad de los resultados obtenidos al simular una traza de eventos real generada por una Red Neuronal Espiking (SNN) sobre el dataset N-MNIST, utilizando tanto el simulador basado en ciclos (`cycle_sim.py`) como el simulador rápido (`fast_sim.py`). El objetivo es dilucidar las razones detrás de las diferencias observadas en las métricas de rendimiento, especialmente en la latencia y el jitter.

## Recapitulación de los Simuladores

El proyecto `noc-aer-simulator` ofrece dos enfoques complementarios para la simulación de Networks-on-Chip (NoC) para sistemas neuromórficos:

*   **`cycle_sim.py` (Simulador Basado en Ciclos):** Este simulador modela el comportamiento de la NoC ciclo a ciclo, emulando de cerca la operación de un hardware real. Considera el movimiento de los flits a través de los routers, la ocupación de buffers y la lógica de enrutamiento (XY routing) en cada paso de tiempo. Su precisión es alta, pero su coste computacional aumenta significativamente con el número de eventos y el tamaño de la red.

*   **`fast_sim.py` (Simulador Rápido/Analítico):** Este simulador adopta un enfoque analítico, calculando la latencia de los flits basándose en la distancia de Manhattan y aplicando una penalización por congestión. Está diseñado para procesar un gran volumen de eventos de forma muy eficiente, proporcionando estimaciones rápidas del rendimiento de la red, aunque con un nivel de detalle menor en la interacción ciclo a ciclo.

Para una comparativa más extensa de ambos simuladores, consulte [Comparación de Simuladores: `fast_sim.py` vs. `cycle_sim.py`](../../COMPARISON.md).

## Configuración de la Simulación Real N-MNIST

La simulación se realizó bajo las siguientes condiciones:

*   **Traza de Eventos:** `nmnist_trace.txt`, generada por una SNN (CSNN) entrenada durante 100 iteraciones sobre el dataset N-MNIST. La SNN alcanzó una precisión del **79.69%**, lo que garantiza que la traza representa una actividad neuronal funcional y realista. La traza contiene **411,420 eventos**.
*   **Topología de la NoC:** Malla de 4x4 (`mesh_4x4.config`).
*   **Mapeo:** Las capas de la SNN se mapearon a los nodos de la NoC según la configuración definida en el generador de trazas.

## Resultados Clave de la Simulación

Los resultados obtenidos de la ejecución de ambos simuladores con la traza real de N-MNIST son los siguientes:

| Métrica | `cycle_sim.py` (Ciclo) | `fast_sim.py` (Rápido) | Diferencia Clave |
| :------------------ | :-------------------- | :-------------------- | :--------------- |
| **Latencia Promedio** | **2.89 ciclos**       | **367.79 ciclos**     | `fast_sim.py` es ~127 veces mayor |
| **Jitter (StdDev)** | **1.05 ciclos**       | **276.71 ciclos**     | `fast_sim.py` es ~263 veces mayor |
| **Total Hops**      | **1,190,989**         | **1,190,989**         | Idéntico         |
| **Energía Estimada**| **1,396,699.00 unidades** | **1,396,699.00 unidades** | Idéntico         |

Los resultados se visualizan en el siguiente gráfico comparativo:

![Gráfico Comparativo N-MNIST](comparison_chart.png)

## Análisis Detallado de las Diferencias

La diferencia más llamativa reside en la **latencia promedio** y el **jitter**, donde `fast_sim.py` reporta valores significativamente más altos que `cycle_sim.py`. Esta divergencia se explica por los modelos de simulación subyacentes y cómo cada uno aborda la **congestión de la red**.

### Latencia y Jitter en `cycle_sim.py`

El simulador `cycle_sim.py` muestra una latencia promedio muy baja (2.89 ciclos) y un jitter reducido (1.05 ciclos). Esto se debe a que, en su implementación actual, modela el movimiento de los flits de forma idealizada. Aunque simula el paso del tiempo ciclo a ciclo y el enrutamiento XY, no incorpora explícitamente mecanismos complejos de arbitraje de puertos o gestión de buffers que introduzcan retrasos significativos bajo alta carga. Es decir, asume un escenario donde los flits pueden avanzar en cada ciclo si su camino está libre, sin considerar las micro-contenciones que ocurrirían en un hardware real. Por lo tanto, los resultados de `cycle_sim.py` representan una **latencia base o ideal** en una NoC perfectamente sincronizada y con recursos ilimitados para evitar bloqueos.

### Latencia y Jitter en `fast_sim.py`

Por otro lado, `fast_sim.py` arroja una latencia promedio de 367.79 ciclos y un jitter de 276.71 ciclos. Esta gran diferencia se debe a su **modelo analítico de congestión**. A pesar de no simular cada ciclo de reloj individualmente, `fast_sim.py` aplica una `congestion_penalty` que escala con la densidad de tráfico en la red. En una traza con **411,420 eventos**, la red experimenta una alta carga de tráfico. El modelo de `fast_sim.py` interpreta esta alta densidad como una congestión severa, lo que resulta en un aumento significativo de la latencia para cada flit. Este enfoque, aunque no es ciclo-preciso, proporciona una **estimación más realista del rendimiento bajo carga**, ya que captura el impacto de la congestión que inevitablemente ocurriría en un hardware real con recursos finitos (buffers, ancho de banda).

### Consistencia en Hops y Energía

Es importante destacar que ambos simuladores reportan valores idénticos para el **Total Hops** (1,190,989) y la **Energía Estimada** (1,396,699.00 unidades). Esto valida que la lógica de enrutamiento (XY routing) y el cálculo de la distancia (número de saltos) son consistentes en ambos. La energía estimada se basa principalmente en el número de saltos, por lo que, al ser esta métrica idéntica, la energía también lo es.

## Implicaciones para el Diseño y la Investigación

La existencia de estos dos simuladores complementarios es crucial para la investigación en arquitecturas neuromórficas:

*   **`cycle_sim.py`** es invaluable para la **validación funcional** y el **análisis de micro-arquitectura**. Permite a los diseñadores verificar la corrección de los algoritmos de enrutamiento, la lógica de control de flujo y el comportamiento de los buffers en un entorno controlado. Es ideal para entender los límites de rendimiento ideales.

*   **`fast_sim.py`** es esencial para la **exploración del espacio de diseño a gran escala** y la **evaluación de rendimiento bajo carga realista**. Permite a los investigadores comparar rápidamente diferentes mapeos de SNN a la NoC, evaluar el impacto de la escala de la red o la densidad de tráfico, y obtener una estimación del rendimiento esperado en escenarios de congestión, sin la necesidad de simulaciones extremadamente largas.

En resumen, mientras que `cycle_sim.py` ofrece una visión 
idealizada del rendimiento, `fast_sim.py` proporciona una perspectiva más pragmática y pesimista bajo condiciones de alta carga, lo cual es fundamental para identificar posibles cuellos de botella y limitaciones en el diseño de hardware neuromórfico.

## Conclusión

La comparativa entre `cycle_sim.py` y `fast_sim.py` con una traza real de N-MNIST subraya la importancia de utilizar herramientas de simulación adecuadas para cada fase del diseño. El simulador de ciclos ofrece una base para entender el comportamiento ideal y validar la funcionalidad, mientras que el simulador rápido, con su modelo de congestión analítico, es indispensable para predecir el rendimiento bajo cargas realistas y explorar eficientemente un amplio espacio de diseño. La combinación de ambos proporciona una visión completa y robusta del rendimiento de las NoC para aplicaciones neuromórficas.
