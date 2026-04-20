# Análisis Técnico Exhaustivo: NoC-AER Simulator 🧠⚙️

Este documento proporciona un desglose profundo de cada componente del simulador **NoC-AER**, analizando su lógica algorítmica, implementación de hardware y flujo de datos desde el nivel de software (SNN) hasta el nivel de hardware (NoC).

---

## 1. Frontend: Inteligencia Artificial y Generación de Eventos

El frontend, implementado en Python, es responsable de la carga de trabajo del simulador. Utiliza una arquitectura de red neuronal convolucional de impulsos (**CSNN**) para procesar datos neuromórficos.

### 1.1. Modelo de Red Neuronal (CSNN)
La red está construida sobre `snntorch` y consta de:
- **Capas Convolucionales:** Extraen características espaciales de los eventos N-MNIST.
- **Neuronas LIF (Leaky Integrate-and-Fire):** Implementan la dinámica temporal. Cada neurona mantiene un estado interno (potencial de membrana) que decae con el tiempo y se incrementa con los estímulos de entrada.
- **Surrogate Gradients:** Durante el entrenamiento, se utiliza la función `atan` como aproximación de la derivada del impulso, permitiendo el uso de optimizadores como Adam.

### 1.2. Mapeo AER y Fan-out
Una característica crítica es cómo se traduce un "spike" lógico en tráfico de red físico:
- **Estrategia de Mapeo:** Para evitar cuellos de botella, las capas se distribuyen en filas:
  - Fila 0 (Nodos 0-3): Sensores de entrada.
  - Fila 1 (Nodos 4-7): Capa SNN1.
  - Fila 2 (Nodos 8-11): Capa SNN2.
  - Fila 3 (Nodos 12-15): Capa de salida (Totalmente conectada).
- **Emulación de Fan-out:** En el script `nmnist_train_sim.py`, un solo impulso en una capa genera múltiples inyecciones en el NoC. Por ejemplo, un spike en SNN1 se traduce en 32 flits dirigidos a diferentes nodos de SNN2, modelando la conectividad sináptica real.

---

## 2. Motor de Simulación: Ciclo-a-Ciclo en C++

El núcleo de simulación está diseñado para ser determinista y de alta fidelidad, utilizando un motor de **Simulación por Eventos Discretos (DES)**.

### 2.1. Gestión de Eventos (EventQueue)
La simulación no avanza por tiempo real, sino procesando una cola de prioridad de eventos.
- **Tipos de Eventos y Prioridades:**
  1. `CREDIT_ARRIVAL`: Máxima prioridad para liberar recursos bloqueados.
  2. `ROUTER_PROCESSING`: Lógica interna del router.
  3. `FLIT_ARRIVAL`: Llegada de datos desde un vecino.
  4. `SOURCE_INJECTION`: Inyección local desde el procesador/neurona.
- **Determinismo:** Si dos eventos ocurren en el mismo ciclo, la prioridad del tipo de evento decide el orden, evitando condiciones de carrera lógicas.

### 2.2. Arquitectura del Router NoC
Cada router es un objeto complejo que implementa las siguientes funciones:

#### A. Control de Flujo Basado en Créditos
Es el mecanismo que garantiza **pérdida cero de paquetes**. 
- Cada puerto de salida mantiene un contador de "créditos" que representa el espacio disponible en el buffer de entrada del vecino.
- Si el contador llega a cero, el router hace un **Stall** (pausa) y reprograma el procesamiento del flit para el siguiente ciclo.
- Cuando un router procesa un flit y libera espacio en su buffer, envía un evento `CREDIT_ARRIVAL` hacia atrás para notificar al vecino.

#### B. Arbitraje Round-Robin
Para gestionar la contención (cuando varios puertos quieren enviar al mismo tiempo), el router utiliza un árbitro circular. Esto garantiza que ningún puerto sufra de inanición (starvation) y que el ancho de banda se distribuya equitativamente.

#### C. Algoritmo de Ruteo XY
Utiliza un enfoque determinista y libre de ciclos:
1. Se compara la coordenada X actual con la de destino. Se mueve al Este o Oeste.
2. Una vez alcanzada la coordenada X, se mueve al Norte o Sur (Y).
3. Si ambas coinciden, el flit se entrega al puerto `LOCAL`.

---

## 3. Modelo de Energía y Tecnología

El simulador integra un modelo de potencia basado en la actividad real del hardware.

### 3.1. Consumo Dinámico
Se calcula multiplicando el número total de flits reenviados (`flits_forwarded`) por la energía por spike de la tecnología seleccionada.
- **Ejemplo 22nm FD-SOI:** Solo 0.85 pJ por spike/flit.
- **Ejemplo 65nm:** 15.5 pJ por spike/flit.

### 3.2. Consumo Estático
Depende del tiempo total de simulación y de la potencia de fuga (leakage) de la tecnología. Esto penaliza las simulaciones que tardan muchos ciclos debido a la congestión.

---

## 4. Visualización y Resultados (TUI)

El componente `nmnist_tui_sim.py` proporciona una interfaz de terminal interactiva (`curses`) que muestra:
- **Métricas de IA:** Precisión del modelo en tiempo real.
- **Métricas de NoC:**
  - **Throughput:** Flits recibidos por ciclo.
  - **Latencia Media:** Ciclos promedio de viaje.
  - **Jitter:** Desviación estándar de la latencia, crucial para SNNs donde el tiempo es información.
  - **Eficiencia Energética:** Medida en pJ/spike, permitiendo comparar diferentes arquitecturas de hardware.

---

## 5. Resumen del Flujo de Datos

| Paso | Acción | Componente | Resultado |
| :--- | :--- | :--- | :--- |
| 1 | Inferencia SNN | Python (PyTorch) | Generación de spikes lógicos. |
| 2 | Mapeo Físico | Python Script | Conversión de spikes a coordenadas NoC. |
| 3 | Inyección | PyBind11 -> C++ | Los flits entran en la cola de eventos. |
| 4 | Tránsito NoC | C++ (Router Logic) | Movimiento salto a salto con control de créditos. |
| 5 | Recepción | C++ (Network) | Contabilidad de latencia y jitter. |
| 6 | Reporte | Python (TUI/Logs) | Visualización de métricas de hardware y energía. |

Este diseño permite a un investigador cambiar un parámetro en la red neuronal (ej. el umbral de disparo) y ver inmediatamente cómo impacta en el consumo de energía y la latencia del hardware final.
