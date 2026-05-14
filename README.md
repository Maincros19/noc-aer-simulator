# 🧠 Simulador NoC-AER (Neuromorphic Network-on-Chip)

¡Bienvenido al simulador **NoC-AER**! Este proyecto es una herramienta de grado industrial diseñada para simular la comunicación de neuronas artificiales a través de una **Red en Chip (NoC)** utilizando el protocolo **AER (Address Event Representation)**.

Esta versión ha evolucionado hacia un motor **totalmente configurable**, permitiendo a investigadores y estudiantes de máster explorar cómo diferentes topologías y capacidades de hardware afectan el rendimiento de una red neuronal de impulsos (SNN). 🎯

## ⚡ Novedades: Configuración Dinámica y Visualización

A diferencia de versiones anteriores, el simulador ahora permite explorar arquitecturas de hardware variables sin necesidad de recompilar el núcleo, e incluye herramientas de monitorización avanzada:

- **Buffers Independientes (Inyección vs Red):** Ahora puedes simular cuellos de botella reales separando la capacidad del buffer local (DMA/Inyección) de los buffers de los enlaces de red (Norte, Sur, Este, Oeste).
- **Monitor de Topología y Ocupación:** Generación automática de video (mapas de calor) para visualizar la congestión de los buffers y los bloqueos (*stalls*) en los enlaces ciclo a ciclo.
- **Malla Escalable:** Configura dimensiones desde 2x2 hasta 16x16 mediante parámetros de ejecución.
- **Mapeo Automático de Capas:** El sistema distribuye automáticamente las capas (Input, SNN1, SNN2, Output) en grupos de nodos proporcionales al tamaño de la malla.
- **Pooling Local Inteligente:** Los flits se generan **después** del pooling en el nodo local, reduciendo drásticamente la congestión irreal y representando fielmente un chip neuromórfico optimizado. 📉

## ✨ Características de Alta Fidelidad

### 1. 🛡️ Control de Flujo Basado en Créditos (Credit-Based)

Implementamos el estándar de la industria. Los flits solo avanzan si el router vecino confirma espacio disponible, modelando con precisión la saturación de buffers y el estancamiento de paquetes en enlaces individuales. 🛑➡️✅

### 2. ⏱️ Restricción de Hardware Real

Cada router procesa exactamente **1 flit por ciclo**, respetando el límite físico del crossbar. Esto permite obtener métricas de **Throughput** (flits/ciclo/nodo) que coinciden con implementaciones en silicio.

### 3. 🔄 Inyección Optimizada Post-Pooling

El tráfico en la NoC refleja el flujo de datos real: solo los impulsos que "sobreviven" al pooling espacial son encapsulados en paquetes AER. Esto optimiza el consumo energético y la latencia del sistema simulado.

### 4. 📊 Dashboard TUI Evolucionado

La interfaz `nmnist_tui_sim.py` soporta la visualización de parámetros variables en tiempo real:
- **Estado SNN:** Épocas, iteraciones y precisión.
- **Hardware Metrics:** Latencia media, Jitter, Energía total (uJ) y Throughput por nodo.

## 🏗️ Arquitectura del Sistema

- **Frontend (Python 🐍):** Gestión del dataset N-MNIST y entrenamiento con `snntorch`.
- **Backend (C++ ⚙️):** Motor de alto rendimiento con gestión de eventos ciclo-a-ciclo y colas de prioridad.
- **Puente (PyBind11 🔗):** Inyección de eventos y extracción de estadísticas hardware.

## 🚀 Guía de Inicio y Ejecución

### 📋 Requisitos Previos

Antes de empezar, asegúrate de tener instalado:
- **C++:** GCC 11+ o Clang equivalente.
- **CMake:** Versión 3.10 o superior.
- **Python:** Versión 3.11 o superior.
- **Dataset:** Acceso a internet (la primera ejecución descargará N-MNIST automáticamente).

### 🛠️ Configuración del Entorno y Compilación

1. **Clonar el repositorio y crear entorno virtual:**
   ```bash
   git clone <url-del-repositorio>
   cd noc-aer-simulator
   python3 -m venv venv
   source venv/bin/activate
   ```
2. **Instalar dependencias de Python:**
   ```bash
   pip install --upgrade pip
   pip install torch snntorch tonic pybind11 networkx
   # Nota: Tonic requiere numpy < 2.0.0, y OpenCV < 4.9 es compatible con numpy 1.x
   pip install "numpy<2.0.0" "opencv-python<4.9" matplotlib seaborn
   ```
3. **Compilar el motor de simulación (C++):**
   ```bash
   cd cpp_simulator
   mkdir build && cd build
   cmake .. -Dpybind11_DIR=$(python3 -m pybind11 --cmakedir)
   make -j$(nproc)
   cd ../..
   ```

### 💻 Ejecución con Parámetros Dinámicos

Una vez compilado, puedes lanzar experimentos directamente desde la terminal. El simulador mapeará automáticamente las capas de la SNN sobre la topología elegida.

| Parámetro    | Descripción                                        | Valor por defecto |
| :----------- | :------------------------------------------------- | :---------------- |
| `--dim`      | Dimensión de la malla (N x N)                      | 4                 |
| `--inj_buffer` | Tamaño del buffer de inyección (LOCAL)             | 1024              |
| `--net_buffer` | Tamaño del buffer de red (N, S, E, W)              | 32                |
| `--epochs`   | Número de épocas de entrenamiento                  | 1                 |
| `--iters`    | Iteraciones por cada época                         | 20                |
| `--samples`  | Muestras a simular en la NoC                       | 1                 |
| `--lr`       | Tasa de aprendizaje (Learning Rate)                | 0.002             |
| `--video_name` | Nombre del archivo de video de salida              | `noc_traffic`     |

**Ejemplos de investigación:**

*   **Simulación estándar (Malla 4x4 con buffers asimétricos):**
    ```bash
    python3 nmnist_tui_sim.py
    ```
*   **Evaluar contrapresión extrema (Buffers reducidos):**
    ```bash
    python3 nmnist_tui_sim.py --inj_buffer 256 --net_buffer 8
    ```
*   **Explorar escalabilidad (Malla 8x8) reduciendo congestión:**
    ```bash
    python3 nmnist_tui_sim.py --dim 8 --video_name trafico_8x8
    ```
*   **Entrenamiento intensivo y mayor volumen de datos:**
    ```bash
    python3 nmnist_tui_sim.py --epochs 5 --iters 100 --samples 10
    ```

(Nota: La generación del video de mapas de calor consume recursos. Si deseas acelerar la simulación pura para extraer métricas, puedes comentar el bloque de renderizado en `nmnist_tui_sim.py` y usar `network.runSimulation()`).

## 📜 Documentación Técnica

Para un análisis profundo, consulta los informes en la carpeta `./documentacion`:

- 📄 **Análisis del Fan-out AER:** Impacto de la divergencia de flits.
- ⚙️ **Arquitectura de Ruteo:** Detalles del ruteo XY y arbitraje.
- ⚡ **Modelo de Energía:** Cálculos basados en tecnología 22nm FD-SOI.
- ⏱️ **Latencia Base (Zero-Load):** Cálculo teórico del límite físico de la red y el cauce hardware.

## 📜 Licencia y Contacto

Este proyecto es ideal para investigación avanzada en Arquitectura de Computadores, Sistemas Neuromórficos y diseño de Redes en Chip. 🎓

Si este simulador te ayuda en tu investigación, TFM o tesis, ¡no olvides darle una ⭐️ en el repositorio! 🌟

