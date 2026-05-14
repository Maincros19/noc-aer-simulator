# Análisis Teórico de Latencia Base (Zero-Load Latency) en Arquitecturas NoC-AER

## 1. Introducción al Concepto de Latencia Cero
En el diseño y evaluación de Redes en Chip (NoC), la **latencia cero** ($L_0$), también conocida como *Zero-Load Latency* o latencia base, representa el tiempo mínimo absoluto que tarda un flit en atravesar la red desde el nodo de inyección hasta el nodo de destino bajo un escenario ideal de tráfico nulo.

Conocer este límite físico es fundamental. Permite desacoplar el retardo inherente a la topología y al cauce (*pipeline*) del hardware, del retardo dinámico introducido por la contención de los recursos (saturación de buffers y arbitraje) cuando la red está bajo carga.

## 2. Modelo de Hardware y Cauce del Router
El simulador NoC-AER modela un hardware síncrono de precisión de ciclo, diseñado para el transporte de eventos (Spikes) encapsulados en paquetes de un único flit (*flit-level granularity*).

Analizando la implementación en C++ del router, el ciclo de vida de un flit en tránsito se divide en etapas deterministas:

* **Procesamiento de Router (Routing & Arbitration):** Cuando un flit avanza a la cabeza del buffer de entrada, el router calcula el puerto de salida (ruteo XY) y evalúa la disponibilidad de créditos. Esta operación consume exactamente **1 ciclo de reloj**.
* **Tránsito por el Enlace (Link Traversal):** Una vez que el flit abandona el router origen, su propagación a través del canal físico (crossbar y enlace entre routers) hasta el buffer del router vecino consume **1 ciclo de reloj**.

Por lo tanto, la penalización temporal ($P$) por cada salto (*hop*) entre routers se define como:
$$P_{salto} = T_{router} + T_{enlace} = 1 + 1 = 2 \text{ ciclos/salto}$$

* **Eyección Local:** Al alcanzar el router de destino, el flit debe ser derivado hacia el puerto `LOCAL`. Este último paso de conmutación consume **1 ciclo de reloj** adicional antes de que el evento sea registrado y entregado a la capa neuronal.

## 3. Modelo de Distancia Topológica
La arquitectura emplea una topología de malla 2D bidimensional. Debido a las restricciones físicas de enrutamiento determinista ortogonal (ruteo XY), la distancia que recorre un paquete no es euclidiana, sino que obedece a la métrica de distancia de Manhattan.

Para un flit inyectado en un nodo origen con coordenadas cartesianas $(X_{src}, Y_{src})$ y destinado a un nodo $(X_{dst}, Y_{dst})$, el número total de saltos físicos ($H$) se calcula como:

$$H = |X_{dst} - X_{src}| + |Y_{dst} - Y_{src}|$$

## 4. Ecuación General de Latencia Base
Integrando el modelo de distancia topológica con el modelo de penalización del cauce hardware, podemos formalizar la ecuación analítica para la latencia base de cualquier envío punto a punto en la malla:

$$L_0 = (2 \times H) + 1$$

Donde:
* $L_0$ es la latencia de red teórica sin carga (medida en ciclos).
* $H$ es el número de saltos físicos calculados mediante la distancia de Manhattan.
* El factor $2$ corresponde a los ciclos consumidos por salto (procesamiento + enlace).
* El factor $+ 1$ representa el ciclo final de eyección hacia la interfaz de red local.

### 4.1. Ejemplo de Trazabilidad
Supongamos una malla de 4x4. Se inyecta un impulso sináptico desde la neurona conectada al Router 0, situado en $(0,0)$, destinado a la neurona conectada al Router 10, situado en $(2,2)$.

1. **Cálculo de saltos:** $H = |2 - 0| + |2 - 0| = 4 \text{ saltos}$.
2. **Cálculo de latencia base:** $L_0 = (2 \times 4) + 1 = 9 \text{ ciclos}$.

Cualquier latencia medida empíricamente en simulación para esta misma ruta que supere los 9 ciclos, será estrictamente atribuible a latencia de contención (tiempos de espera en buffers por congestión o falta de créditos).

## 5. Aplicación en la Evaluación de Rendimiento
Durante las baterías de validación, la métrica global **Latencia Media de Red** obtenida mediante simulación empírica ($\bar{L}_{sim}$) debe ser comparada directamente contra el promedio teórico global de la malla ($\bar{L}_0$).

La diferencia entre ambas magnitudes define la **Latencia de Contención Media** ($L_c$):

$$L_c = \bar{L}_{sim} - \bar{L}_0$$

Monitorizar el crecimiento de $L_c$ a medida que se aumenta la tasa de inyección de las capas convolucionales de la red neuronal (SNN) es el indicador principal para justificar el dimensionamiento asimétrico de las colas FIFO (Buffers de Inyección vs. Buffers de Red) en el diseño final del chip.
