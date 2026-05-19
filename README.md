# 🧠 Simulador NoC-AER (Neuromorphic Network-on-Chip)

¡Bienvenido al simulador **NoC-AER**! Este proyecto es una herramienta de grado industrial diseñada para simular la comunicación de neuronas artificiales a través de una **Red en Chip (NoC)** utilizando el protocolo **AER (Address Event Representation)**.

Esta versión ha evolucionado hacia un motor **totalmente configurable y temporalmente preciso**, permitiendo a investigadores y estudiantes de máster explorar cómo diferentes topologías, capacidades de hardware y frecuencias de reloj afectan el rendimiento de una red neuronal de impulsos (SNN). 🎯

## ⚡ Novedades: Co-Simulación Temporal y Configuración Dinámica

A diferencia de versiones anteriores de inyección en bloque, el simulador ahora ejecuta una **co-simulación paso a paso** entre el software (snnTorch) y el hardware (C++), garantizando un mapeo temporal 1:1 entre los milisegundos biológicos y los ciclos de reloj del chip:

*   **Co-Simulación SNN-NoC Entrelazada:** El hardware avanza a la par que la red neuronal procesa cada *timestep*, permitiendo modelar latencias realistas y contrapresión (backpressure) en caliente.
*   **Mapeo Biológico-Físico Realista:** Traducción automática de ventanas temporales SNN a ciclos de hardware basados en la frecuencia del chip (ej. 1 ms = 1,200,000 ciclos a 1200 MHz).
*   **Controlador DMA Virtual:** Implementación de acceso directo a memoria que restringe la inyección desde la RAM al silicio a exactamente 1 paquete por ciclo de reloj, evitando cuellos de botella artificiales.
*   **Buffers Independientes (Inyección vs Red):** Ahora puedes simular congestiones reales separando la capacidad del buffer local (DMA/Inyección) de los buffers de los enlaces de red (Norte, Sur, Este, Oeste).
*   **Malla Escalable y Mapeo Automático:** Configura dimensiones desde 2x2 hasta 16x16. El sistema distribuye automáticamente las capas (Input, SNN1, SNN2, Output) en grupos de nodos proporcionales.

## ✨ Características de Alta Fidelidad

### 1. 🛡️ Control de Flujo Basado en Créditos (Credit-Based)

Implementamos el estándar de la industria. Los flits solo avanzan si el router vecino confirma espacio disponible, modelando con precisión la saturación de buffers y el estancamiento de paquetes (*stalls*) en enlaces individuales. 🛑➡️✅

### 2. ⏱️ Restricción de Hardware y Pipeline DMA

Cada router procesa rigurosamente **1 flit por ciclo**, respetando los límites físicos del crossbar y del puerto `LOCAL`. Los flits generados se almacenan en una cola infinita de RAM simulada y el DMA transfiere los datos al silicio respetando el ancho de banda disponible y la ocupación de los buffers.

### 3. 🔄 Inyección Optimizada Post-Pooling

El tráfico en la NoC refleja el flujo de datos real: solo los impulsos que "sobreviven" al pooling espacial son encapsulados en paquetes AER. Además, los *spikes* de un mismo timestep se distribuyen linealmente a lo largo de la ventana de ciclos disponible para imitar el comportamiento asíncrono de un chip neuromórfico.

### 4. 📊 Dashboard TUI Evolucionado

La interfaz `nmnist_tui_sim.py` soporta la visualización de parámetros variables en tiempo real:

*   **Estado SNN:** Épocas, iteraciones y precisión.
*   **Hardware Metrics:** Latencia media (desglosada en Inyección y Red), Jitter, Energía total (uJ), Eficiencia y Throughput Físico.

## 🏗️ Arquitectura del Sistema

*   **Frontend (Python 🐍):** Gestión del dataset N-MNIST y modelado del comportamiento neuronal con `snntorch`.
*   **Backend (C++ ⚙️):** Motor de alto rendimiento con gestión de eventos discretos, colas de prioridad y lógica de ruteo hardware cycle-accurate.
*   **Puente (PyBind11 🔗):** Integración transparente para el control temporal y la extracción de estadísticas de hardware en tiempo de ejecución.

## 🚀 Guía de Inicio y Ejecución

### 📋 Requisitos Previos

Antes de empezar, asegúrate de tener instalado:

*   **C++:** GCC 11+ o Clang equivalente.
*   **CMake:** Versión 3.10 o superior.
*   **Python:** Versión 3.11 o superior.
*   **Dataset:** Acceso a internet (la primera ejecución descargará N-MNIST automáticamente).

### 🛠️ Configuración del Entorno y Compilación

1.  **Clonar el repositorio y crear entorno virtual:**

    ```bash
    git clone <url-del-repositorio>
    cd noc-aer-simulator
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Instalar dependencias de Python:**

    ```bash
    pip install --upgrade pip
    pip install torch snntorch tonic pybind11 networkx
    # Nota: Tonic requiere numpy < 2.0.0, y OpenCV < 4.9 es compatible con numpy 1.x
    pip install "numpy<2.0.0" "opencv-python<4.9" matplotlib seaborn
    ```

3.  **Compilar el motor de simulación (C++):**

    ```bash
    cd cpp_simulator
    mkdir build && cd build
    cmake .. -Dpybind11_DIR=$(python3 -m pybind11 --cmakedir)
    make -j$(nproc)
    cd ../..
    ```

### 💻 Ejecución con Parámetros Dinámicos

Una vez compilado, puedes lanzar experimentos directamente desde la terminal. El simulador orquestará la co-simulación inyectando tráfico progresivamente.

| Parámetro     | Descripción                                             | Valor por defecto |
| :------------ | :------------------------------------------------------ | :---------------- |
| `--dim`       | Dimensión de la malla (N x N)                           | 4                 |
| `--inj_buffer`| Tamaño del buffer de inyección (LOCAL)                  | 1024              |
| `--net_buffer`| Tamaño del buffer de red (N, S, E, W)                   | 32                |
| `--epochs`    | Número de épocas de entrenamiento                       | 1                 |
| `--iters`     | Iteraciones por cada época                              | 20                |
| `--samples`   | Muestras a simular en la NoC                            | 1                 |
| `--lr`        | Tasa de aprendizaje (Learning Rate)                     | 0.002             |

**Ejemplos de investigación:**

*   **Simulación estándar (Zero-Load / Malla 4x4):**

    ```bash
    python3 nmnist_tui_sim.py
    ```

*   **Forzar congestión de hardware (Buffers reducidos al extremo):**

    ```bash
    python3 nmnist_tui_sim.py --inj_buffer 16 --net_buffer 1
    ```

*   **Explorar escalabilidad (Malla 8x8) reduciendo congestión:**

    ```bash
    python3 nmnist_tui_sim.py --dim 8
    ```

*   **Entrenamiento intensivo y mayor volumen de datos:**

    ```bash
    python3 nmnist_tui_sim.py --epochs 5 --iters 100 --samples 10
    ```

## 📜 Documentación Técnica

Para un análisis profundo, consulta los informes en la carpeta `./documentacion`:

*   📄 Análisis del Fan-out AER: Impacto de la divergencia de flits.
*   ⚙️ Arquitectura de Ruteo y DMA: Detalles del ruteo XY, arbitraje y pipeline de inyección desde RAM.
*   ⚡ Modelo de Energía: Cálculos basados en tecnología 22nm FD-SOI.
*   ⏱️ Latencia Base (Zero-Load): Cálculo teórico del límite físico de la red y el cauce hardware frente a escenarios de saturación.

## 📜 Licencia y Contacto

Este proyecto es ideal para investigación avanzada en Arquitectura de Computadores, Sistemas Neuromórficos y diseño de Redes en Chip. 🎓

Si este simulador te ayuda en tu investigación, ¡no olvides darle una ⭐️ en el repositorio! 🌟

