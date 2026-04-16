# Comparación de Simuladores: `fast_sim.py` vs. `main.py`

Este documento detalla las diferencias fundamentales entre los dos simuladores principales del proyecto `noc-aer-simulator`: `fast_sim.py` y `main.py`. Ambos scripts tienen como objetivo simular el comportamiento de una Network-on-Chip (NoC) para sistemas neuromórficos que utilizan el protocolo Address Event Representation (AER), pero difieren significativamente en su enfoque, precisión y casos de uso.

## 1. Modelo de Simulación

La distinción más crucial radica en el modelo de simulación empleado por cada script. Mientras que `main.py` adopta un enfoque de simulación basado en ciclos de reloj, `fast_sim.py` utiliza un modelo analítico y estadístico.

| Característica Principal | `main.py` (Simulador Basado en Ciclos) | `fast_sim.py` (Simulador Analítico Rápido) |
| :----------------------- | :------------------------------------- | :----------------------------------------- |
| **Enfoque**              | **Basado en ciclos de reloj.** Modela el paso del tiempo de manera discreta, paso a paso (ticks o ciclos). Cada evento y movimiento de paquete se sincroniza con un ciclo de reloj. | **Basado en eventos analíticos.** Calcula las latencias y el comportamiento de la red mediante fórmulas matemáticas y modelos estadísticos, sin simular cada ciclo de reloj individualmente. |
| **Modelado de Hardware** | Modela **routers reales** con componentes detallados como buffers de entrada/salida, colas, unidades de arbitraje y lógica de enrutamiento (ej. XY routing). Permite una representación fiel del hardware. | Modela la red como una **malla de nodos** interconectados. Se enfoca en la distancia de Manhattan y aplica penalizaciones por congestión de manera abstracta, sin modelar los componentes internos de los routers. |
| **Movimiento de Paquetes** | Los paquetes se mueven físicamente de un router a otro en cada ciclo de reloj, experimentando retrasos por arbitraje, colas y contención de recursos. | Los paquetes "saltan" directamente al destino. La latencia se calcula como la distancia de Manhattan más una penalización por congestión, sin simular el recorrido paso a paso. |

## 2. Gestión de la Congestión

La forma en que cada simulador maneja y representa la congestión en la red es otra diferencia clave que afecta su precisión y rendimiento.

*   **`main.py` (Congestión Dinámica y Realista):**
    *   La congestión se modela de forma **dinámica y realista**. Si un buffer de entrada o salida de un router se llena, el paquete no puede avanzar y se detiene, aplicando **contrapresión (backpressure)** al router anterior. Esto puede causar bloqueos y un aumento significativo de la latencia para los paquetes que intentan usar ese recurso.
    *   Este enfoque es **muy preciso** para evaluar el impacto de la congestión en el rendimiento del hardware, pero es **computacionalmente intensivo** y lento de simular, especialmente con un gran número de eventos.

*   **`fast_sim.py` (Congestión Probabilística/Analítica):**
    *   La congestión se maneja de forma **probabilística o analítica**. Utiliza un factor de penalización (`congestion_penalty`) que se añade a la latencia base de un paquete. Esta penalización aumenta en función de la cantidad de tráfico o la densidad de paquetes que atraviesan una región de la red en un momento dado.
    *   No modela el bloqueo físico de los enlaces o buffers. Esto permite una **simulación mucho más rápida**, ideal para estimaciones a gran escala, pero con una **precisión menor** en la representación de los efectos exactos de la congestión a nivel de hardware.

## 3. Arquitectura del Código y Complejidad

La estructura y complejidad del código reflejan los diferentes objetivos de diseño de cada simulador.

*   **`main.py` (Orientado a Objetos y Modular):**
    *   Presenta una arquitectura **orientada a objetos** robusta y modular, con clases bien definidas como `Network`, `Router`, `Packet`, `TrafficManager`, etc.
    *   Esta estructura es ideal para la **validación detallada del diseño de hardware**, permitiendo a los investigadores modificar y probar componentes específicos de la NoC (ej. algoritmos de arbitraje, tamaños de buffer, lógicas de enrutamiento) con gran granularidad.
    *   Es más complejo de entender y modificar debido a su interconexión de objetos y lógica de simulación paso a paso.

*   **`fast_sim.py` (Funcional y Scripting):**
    *   Es un script mucho más **ligero y funcional**. Procesa una lista de eventos de forma secuencial, calculando las latencias y otras métricas directamente.
    *   Está diseñado para ser **rápido y eficiente** en el procesamiento de grandes volúmenes de datos (millones de "spikes"). Su simplicidad lo hace más fácil de entender y ejecutar para obtener resultados rápidos.
    *   No permite la misma granularidad en la modificación de componentes de la NoC como `main.py`.

## 4. Casos de Uso Recomendados

La elección entre `fast_sim.py` y `main.py` depende del objetivo específico de la simulación y la fase de investigación.

*   **Usa `main.py` cuando:**
    *   Necesites **validar la lógica de control de flujo**, el impacto de los tamaños de los buffers, los algoritmos de arbitraje o el algoritmo de enrutamiento exacto (ej. XY routing) en el rendimiento de la NoC.
    *   Estés en una fase avanzada del diseño de hardware y requieras una **precisión alta** para asegurar que el diseño funcionará correctamente en un chip real.
    *   El número de eventos a simular es manejable y el tiempo de simulación no es una restricción crítica.

*   **Usa `fast_sim.py` cuando:**
    *   Estés en una **fase temprana de investigación** y necesites comparar rápidamente diferentes configuraciones de red, mapeos de neuronas a nodos de la NoC o tamaños de chip (ej. mallas de 4x4 vs. 16x16).
    *   Necesites obtener **estimaciones rápidas** de latencia, congestión y consumo energético para millones de "spikes" sin incurrir en largos tiempos de simulación.
    *   El objetivo principal es la **evaluación de tendencias** y la identificación de cuellos de botella a nivel macro, más que la validación micro-arquitectónica.

En resumen, `main.py` es el simulador "de verdad" para la validación precisa del hardware y el estudio de detalles micro-arquitectónicos, mientras que `fast_sim.py` es la herramienta de "prototipado rápido" para análisis de datos a gran escala y exploración de diseños a alto nivel.
