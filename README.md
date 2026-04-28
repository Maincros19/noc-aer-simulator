¡Bienvenido al simulador **NoC-AER**! Este proyecto es una herramienta de grado industrial diseñada para simular la comunicación de neuronas artificiales a través de una **Red en Chip (NoC)** utilizando el protocolo **AER (Address Event Representation)**.

Esta versión ha evolucionado hacia un motor **totalmente configurable**, permitiendo a investigadores y estudiantes de máster explorar cómo diferentes topologías de hardware afectan el rendimiento de una red neuronal de impulsos (SNN). 🎯

---

## ⚡ Novedades: Configuración Dinámica
A diferencia de versiones anteriores, el simulador ahora permite explorar arquitecturas de hardware variables sin necesidad de recompilar el núcleo:

- **Malla Escalable:** Configura dimensiones desde 2x2 hasta 16x16 mediante parámetros de ejecución.
- **Mapeo Automático de Capas:** El sistema distribuye automáticamente las capas (Input, SNN1, SNN2, Output) en grupos de nodos proporcionales al tamaño de la malla.
- **Pooling Local Inteligente:** Los flits se generan **después** del pooling en el nodo local, reduciendo drásticamente la congestión irreal y representando fielmente un chip neuromórfico optimizado. 📉

---

## ✨ Características de Alta Fidelidad

### 1. 🛡️ Control de Flujo Basado en Créditos (Credit-Based)
Implementamos el estándar de la industria. Los flits solo avanzan si el router vecino confirma espacio disponible, modelando con precisión la saturación de buffers y el estancamiento de paquetes. 🛑➡️✅

### 2. ⏱️ Restricción de Hardware Real
Cada router procesa exactamente **1 flit por ciclo**, respetando el límite físico del crossbar. Esto permite obtener métricas de **Throughput** (flits/ciclo/nodo) que coinciden con implementaciones en silicio.

### 3. 🔄 Inyección Optimizada Post-Pooling
El tráfico en la NoC refleja el flujo de datos real: solo los impulsos que "sobreviven" al pooling espacial son encapsulados en paquetes AER. Esto optimiza el consumo energético y la latencia del sistema simulado.

### 4. 📊 Dashboard TUI Evolucionado
La interfaz `nmnist_tui_sim.py` ahora soporta la visualización de parámetros variables:
- **Estado SNN:** Épocas, iteraciones y precisión en tiempo real.
- **Hardware Metrics:** Latencia media, Jitter, Energía total (uJ) y Throughput por nodo.

---

## 🏗️ Arquitectura del Sistema

- **Frontend (Python 🐍):** Gestión del dataset N-MNIST y entrenamiento con `snntorch`.
- **Backend (C++ ⚙️):** Motor de alto rendimiento con gestión de eventos ciclo-a-ciclo.
- **Puente (PyBind11 🔗):** Inyección de eventos y extracción de estadísticas hardware.

---

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
   pip install torch snntorch tonic pybind11 numpy
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

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `--dim` | Dimensión de la malla (N x N) | 4 |
| `--epochs` | Número de épocas de entrenamiento | 1 |
| `--iters` | Iteraciones por cada época | 20 |
| `--buffer` | Tamaño del buffer por router (flits) | 4096 |
| `--samples` | Muestras a simular en la NoC | 1 |
| `--lr` | Tasa de aprendizaje (Learning Rate) | 0.002 |

Ejemplos de investigación:

1. **Simulación estándar (Malla 4x4):**
   ```bash
   python3 nmnist_tui_sim.py
   ```

2. **Explorar escalabilidad (Malla 8x8) para reducir congestión:**
   ```bash
   python3 nmnist_tui_sim.py --dim 8
   ```

3. **Entrenamiento intensivo y mayor volumen de datos:**
   ```bash
   python3 nmnist_tui_sim.py --epochs 5 --iters 100 --samples 10
   ```

## 📜 Documentación Técnica

Para un análisis profundo, consulta los informes en la carpeta `./documentacion`:

- 📄 Análisis del Fan-out AER: Impacto de la divergencia de flits.
- ⚙️ Arquitectura de Ruteo: Detalles del ruteo XY y arbitraje.
- ⚡ Modelo de Energía: Cálculos basados en tecnología 22nm FD-SOI.

## 📜 Licencia y Contacto

Este proyecto es ideal para investigación avanzada en Arquitectura de Computadores, Sistemas Neuromórficos y NoC Design. 🎓

Si este simulador te ayuda en tu investigación, TFM o tesis, ¡no olvides darle una ⭐️ en el repositorio! 🌟

