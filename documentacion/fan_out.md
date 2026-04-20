# 🧠 Fan-out en NoC-AER Simulator: Un Análisis Detallado 📡

El concepto de **Fan-out** es crucial en arquitecturas neuromórficas y redes en chip (NoC) que implementan el protocolo Address Event Representation (AER). Se refiere a la capacidad de una neurona (o un nodo de origen) para enviar su "spike" o evento a múltiples neuronas (o nodos de destino) simultáneamente. En el contexto del simulador NoC-AER, el fan-out modela la conectividad sináptica divergente de las redes neuronales de impulsos (SNN) y tiene un impacto directo en el tráfico de la red y, consecuentemente, en el rendimiento y consumo energético.

---

## 1. ¿Qué es el Fan-out en NoC-AER?

En una SNN, una única neurona presináptica puede estar conectada a un gran número de neuronas postsinápticas. Cuando la neurona presináptica dispara un impulso (spike), este evento debe ser transmitido a todas sus neuronas de destino. En una implementación de hardware neuromórfico sobre una NoC, cada uno de estos destinos requiere un **flit** (la unidad mínima de datos en la NoC) que transporte la información del spike.

El simulador NoC-AER modela este comportamiento de la siguiente manera:
- **Generación de Spikes (SNN):** La red neuronal en Python (`nmnist_train_sim.py`, `nmnist_tui_sim.py`) genera eventos de spike a nivel lógico.
- **Expansión a Flits (NoC):** Por cada spike lógico, el simulador crea `N` flits individuales, donde `N` es el factor de fan-out para esa capa o conexión. Cada uno de estos flits tiene el mismo origen pero un destino diferente dentro de la NoC.

Por ejemplo, si una neurona de la capa `SNN1` dispara y tiene un fan-out de 32 hacia la capa `SNN2`, se inyectarán 32 flits en la NoC, cada uno dirigido a un router diferente que representa una neurona en `SNN2`.

---

## 2. Impacto del Fan-out en la NoC

El fan-out es una fuente principal de carga de trabajo y congestión en la NoC. Su impacto se manifiesta en varios aspectos:

### 2.1. Tráfico de Red
Un alto fan-out multiplica el número de flits inyectados en la red. Esto incrementa la demanda de ancho de banda en los enlaces y la capacidad de procesamiento de los routers. En el simulador, esto se traduce en:
- **Mayor Número de Flits Inyectados:** Como se observa en las métricas, el número de flits en la NoC es significativamente mayor que el número de spikes lógicos generados por la SNN.
- **Mayor Ocupación de Buffers:** Los buffers de entrada de los routers se llenan más rápidamente, aumentando la probabilidad de stalls debido al control de flujo basado en créditos.

### 2.2. Latencia y Jitter
El aumento del tráfico y la congestión tienen un efecto directo en el rendimiento temporal:
- **Incremento de Latencia:** Los flits pasan más tiempo esperando en los buffers de los routers debido a la contención, lo que aumenta la latencia extremo a extremo.
- **Aumento del Jitter:** La variabilidad en los tiempos de espera puede llevar a un mayor jitter, lo cual es crítico para la coherencia temporal de las SNN, donde el tiempo de llegada de los spikes es información relevante.

### 2.3. Consumo Energético
Cada flit que se mueve a través de la NoC consume energía (energía dinámica). Un mayor fan-out implica:
- **Mayor Consumo Dinámico:** Más flits significa más conmutaciones en los routers y enlaces, lo que se traduce en un mayor consumo de energía dinámica. El simulador contabiliza cada `flits_forwarded` para calcular este consumo.
- **Impacto en la Eficiencia (pJ/spike):** Aunque el fan-out es inherente a la arquitectura SNN, un diseño ineficiente de la NoC o un mapeo subóptimo pueden disparar el consumo energético por spike, reduciendo la eficiencia global del sistema neuromórfico.

---

## 3. Mapeo Distribuido y Fan-out

El simulador NoC-AER utiliza un mapeo distribuido de las capas de la SNN sobre la malla 4x4 de la NoC. Esta estrategia es crucial para mitigar los efectos negativos del fan-out:
- **Evitar Puntos Calientes:** Al distribuir los nodos de origen y destino de los flits de fan-out a través de diferentes routers, se evita que un solo router o una pequeña región de la NoC se convierta en un cuello de botella.
- **Balanceo de Carga:** El mapeo intenta balancear la carga de tráfico, distribuyendo los flits generados por el fan-out de manera más uniforme por la red.

Sin un mapeo cuidadoso, incluso con un control de flujo robusto, un alto fan-out podría saturar rápidamente la NoC, llevando a latencias inaceptables y un consumo energético excesivo.

---

## 4. Conclusión

El fan-out es una característica intrínseca de las SNN que, cuando se implementa en hardware, se traduce en un aumento significativo del tráfico en la NoC. El simulador NoC-AER modela este fenómeno con alta fidelidad, permitiendo a los investigadores evaluar el impacto real del fan-out en métricas críticas como la latencia, el jitter y el consumo energético. La comprensión y optimización del fan-out son esenciales para el diseño de sistemas neuromórficos eficientes y escalables.
