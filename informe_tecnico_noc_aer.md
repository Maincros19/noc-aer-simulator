# Informe Técnico: NoC-AER Simulator 🧠🚀

El simulador **NoC-AER** es una plataforma de alta fidelidad diseñada para el estudio de sistemas neuromórficos, integrando el entrenamiento de redes neuronales de impulsos (**SNN**) con una simulación de hardware **ciclo-a-ciclo** precisa de una Red en Chip (**NoC**) utilizando el protocolo **AER** (Address Event Representation).

---

## 1. Arquitectura General del Sistema

El sistema se divide en tres capas principales que colaboran para transformar datos sensoriales en métricas de rendimiento de hardware:

| Capa | Componente | Función Principal |
| :--- | :--- | :--- |
| **Frontend** | Python (PyTorch + snnTorch) | Entrenamiento de la SNN, generación de eventos AER y mapeo lógico-físico. |
| **Bridge** | PyBind11 | Interfaz de baja latencia que comunica los objetos de Python con el motor de C++. |
| **Backend** | C++ Core | Motor de simulación discreta por eventos que modela routers, enlaces y control de flujo. |

---

## 2. Componentes del Simulador y su Funcionamiento

### 2.1. Red Neuronal de Impulsos (CSNN)
El proceso comienza en el script `nmnist_train_sim.py`, donde se define una red neuronal convolucional neuromórfica (**CSNN**):
- **Dataset N-MNIST:** Utiliza eventos asíncronos (spikes) capturados por sensores de visión dinámica.
- **Modelo Leaky Integrate-and-Fire (LIF):** Implementado mediante `snntorch`, modela el comportamiento de las neuronas biológicas que acumulan potencial de membrana y disparan al alcanzar un umbral.
- **Entrenamiento:** Se realiza mediante retropropagación a través del tiempo (BPTT) utilizando gradientes sustitutos para manejar la naturaleza no diferenciable de los impulsos.

### 2.2. Mapeo AER y Generación de Tráfico
Una vez entrenada la red, los impulsos neuronales deben viajar por el hardware:
- **Distribución en el NoC:** Las capas de la red se mapean en una malla 4x4. Por ejemplo, la capa de entrada ocupa la fila superior, mientras que la capa de salida ocupa la inferior.
- **Protocolo AER:** Cada impulso se encapsula en un **Flit** (unidad mínima de información) que contiene el ID del router de origen, el de destino y la marca de tiempo de inyección.
- **Fan-out Real:** El simulador modela la conectividad real; un solo impulso de una neurona presináptica puede generar múltiples flits en la red si se conecta a varias neuronas postsinápticas.

### 2.3. Motor de Simulación C++ (Ciclo-a-Ciclo)
Es el núcleo de alta fidelidad que garantiza que la simulación sea físicamente consistente:
- **EventQueue (Cola de Eventos):** Gestiona la línea de tiempo global. Procesa eventos de llegada de créditos, procesamiento de routers e inyección de flits de forma determinista.
- **Router NoC:**
    - **Control de Flujo Basado en Créditos:** Un router solo envía un flit si el vecino tiene espacio en su buffer, eliminando la pérdida de paquetes por desbordamiento y modelando con precisión la congestión.
    - **Arbitraje Round-Robin:** Garantiza equidad en el acceso a los recursos del router entre los diferentes puertos (Norte, Sur, Este, Oeste, Local).
    - **Ruteo XY:** Algoritmo determinista que minimiza la lógica de control y evita bloqueos (deadlocks).
    - **Restricción de Hardware:** Cada router procesa exactamente **1 flit por ciclo**, reflejando la limitación real de un crossbar físico.

---

## 3. Características Técnicas Destacadas

### 3.1. Modelo de Energía Detallado
El simulador permite seleccionar entre diversas tecnologías de fabricación, afectando directamente al consumo:
- **Tecnologías soportadas:** Desde CMOS 65nm hasta **22nm FD-SOI** especializado para neuromórfica.
- **Cálculo de Energía:** Se contabiliza la energía estática (fuga) y dinámica (conmutación por cada flit procesado/reenviado).

### 3.2. Métricas de Precisión
A diferencia de simuladores abstractos, NoC-AER proporciona:
- **Latencia Extremo a Extremo:** Tiempo exacto desde que una neurona dispara hasta que el flit llega a su destino, incluyendo esperas por congestión.
- **Jitter (AER):** Variabilidad en la entrega de impulsos, crítica para mantener la coherencia temporal en redes SNN.
- **Tasa de Entrega del 100%:** Gracias al control de flujo por créditos, no se pierden eventos por falta de memoria.

---

## 4. Flujo de Trabajo: Del Entrenamiento a los Resultados

1.  **Entrenamiento:** El usuario define épocas e iteraciones. La red aprende a clasificar dígitos del dataset N-MNIST.
2.  **Configuración de Hardware:** Se selecciona la tecnología (ej. 22nm) y el tamaño de los buffers del NoC.
3.  **Inyección de Tráfico:** Los impulsos generados por la inferencia se transforman en flits AER y se agendan en la cola de eventos.
4.  **Ejecución de Simulación:** El motor C++ procesa todos los eventos hasta que el último flit es entregado.
5.  **Visualización (TUI/Logs):** 
    - Se muestran resultados de **Precisión IA** (Accuracy).
    - Se presentan métricas de hardware: **Latencia Media**, **Throughput**, **Consumo Energético Total** y **Eficiencia (pJ/spike)**.
    - El componente `nmnist_tui_sim.py` permite ver este proceso en un tablero interactivo en tiempo real.

---

> **Conclusión:** El simulador NoC-AER cierra la brecha entre el diseño de algoritmos de IA y la implementación física en hardware, permitiendo a los investigadores evaluar cómo la arquitectura de red (NoC) afecta la precisión y eficiencia de una red neuronal de impulsos real.
