# 🧠 Simulador NoC-AER (Neuromorphic Network-on-Chip)

¡Bienvenido al simulador **NoC-AER**! Este proyecto es una herramienta de grado industrial diseñada para simular la ejecución y comunicación de Redes Neuronales de Impulsos (SNNs) a través de una **Red en Chip (NoC)** utilizando el protocolo **AER (Address Event Representation)**.

El simulador implementa una arquitectura de **In-Memory Computing pura**, permitiendo explorar cómo las limitaciones físicas del silicio (topologías, buffers, contención por fan-out, lógicas de ruteo y frecuencia de reloj) afectan el rendimiento y la precisión de una inteligencia artificial neuromórfica. Ideal para el desarrollo académico avanzado y la validación arquitectónica en ingeniería de computadores. 🎯

## ⚡ Novedades: Inferencia en Silicio y Ruteo Multicast

A diferencia de simuladores que dependen de un software anfitrión (CPU) para calcular la red neuronal, esta versión emula un chip ASIC con capacidades avanzadas de ruteo en hardware:

* **In-Memory Computing Pura:** Las neuronas Leaky Integrate-and-Fire (LIF) residen físicamente en los routers de C++. El cálculo del potencial de membrana ($V_{mem}$) y la generación de *spikes* ocurre directamente en el silicio.
* **Flasheo de Pesos (Mapping):** Python actúa exclusivamente como compilador offline. Entrena la SNN con `snnTorch`, desenrolla las matrices (Conv2D/Linear) y mapea las sinapsis directamente en la memoria estática de los núcleos.
* **Ruteo Multicast Path-Based (XY):** El hardware ahora soporta nativamente la coexistencia de modos Unicast y Multicast. En modo Multicast, el router origen inyecta un único flit que viaja por el eje X y se replica dinámicamente al divergir en el eje Y. Esto elimina por completo el embudo de inyección, reduciendo el tráfico global de la red en más de un 40% y disminuyendo drásticamente el *jitter* temporal.
* **Cierre Lógico y Precisión Física:** El voltaje de los flits se integra en las neuronas destino. La precisión de la IA se evalúa leyendo los contadores de *spikes* alojados en el hardware.

## ✨ Características de Alta Fidelidad

### 1. 🛡️ Control de Flujo Basado en Créditos (Credit-Based)
Implementamos el estándar de la industria. Los flits solo avanzan si el router vecino confirma espacio disponible, modelando con precisión la saturación de buffers y el estancamiento de paquetes (*stalls*) en enlaces individuales. 🛑➡️✅

### 2. 💥 Gestión de la Explosión del Fan-Out
El simulador permite contrastar dos paradigmas arquitectónicos para gestionar la explosión de tráfico sináptico:
* **Modo Unicast:** El hardware genera físicamente un flit independiente por cada sinapsis conectada, modelando el "colapso de inyección" donde los flits se atascan en el buffer `LOCAL`.
* **Modo Multicast:** Emulando la eficiencia de chips como SpiNNaker o Loihi, el hardware agrupa los destinos, resolviendo la congestión y multiplicando el *throughput* efectivo al evitar copias redundantes en el nodo de origen.

### 3. ⏱️ Precisión Cycle-Accurate y Jitter
Traducción automática de la ventana temporal biológica a ciclos de reloj. El simulador rastrea la latencia exacta de cada paquete, permitiendo observar cómo el *Jitter* (deformación temporal) altera la información asíncrona de la SNN.

### 4. 📊 Dashboard TUI Evolucionado
Muestra en tiempo real las métricas de la simulación física:
* **Métricas de Congestión:** Latencia media desglosada (Espera en Buffer Local vs. Vuelo en Red NoC) y Jitter.
* **Rendimiento y Energía:** Energía total consumida (uJ), Eficiencia (flits/uJ) y Throughput Físico (flits/s).
* **Precisión de IA In-Memory:** Tasa de acierto evaluada puramente desde los contadores de la memoria del chip.

## 🏗️ Arquitectura del Sistema

* **Frontend (Python 🐍):** Entrenamiento del modelo SNN, desenrollado matemático de tensores espaciales (mapeo a 1D) e inyección de eventos sensoriales crudos (N-MNIST).
* **Backend (C++ ⚙️):** Motor de inferencia in-memory. Gestiona eventos discretos, física de integración neuronal (Leaky Integrate) y lógica de ruteo XY y replicación Multicast *cycle-accurate*.
* **Puente (PyBind11 🔗):** Integración API que permite flashear la configuración estructural (sinapsis y umbrales) y los modos de operación de red desde PyTorch al simulador en C++.

## 🚀 Guía de Inicio y Ejecución

### 📋 Requisitos Previos

Antes de empezar, asegúrate de tener instalado:

* **C++:** GCC 11+ o Clang equivalente.
* **CMake:** Versión 3.10 o superior.
* **Python:** Versión 3.11 o superior.
* **Dataset:** Acceso a internet (la primera ejecución descargará N-MNIST automáticamente).

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
| `--routing`   | Modo de ruteo NoC (`unicast` o `multicast`)             | `unicast`         |
| `--inj_buffer`| Tamaño del buffer de inyección (LOCAL)                  | 1024              |
| `--net_buffer`| Tamaño del buffer de red (N, S, E, W)                   | 32                |
| `--epochs`    | Número de épocas de entrenamiento                       | 1                 |
| `--iters`     | Iteraciones por cada época                              | 20                |
| `--samples`   | Muestras a simular en la NoC                            | 1                 |
| `--lr`        | Tasa de aprendizaje (Learning Rate)                     | 0.002             |

**Ejemplos de investigación:**

* **Optimización de Tráfico Multicast:** Evaluar la eficiencia de red y la caída de latencia utilizando replicación hardware para 10 muestras:
    ```bash
    python3 nmnist_tui_sim.py --samples 10 --routing multicast
    ```
* **Estudio del Cuello de Botella Unicast:** Forzar la saturación del router de origen y observar el aumento del jitter temporal:
    ```bash
    python3 nmnist_tui_sim.py --samples 10 --routing unicast
    ```
* **Estrés de memoria:** Provocar congestión reduciendo agresivamente la SRAM del núcleo:
    ```bash
    python3 nmnist_tui_sim.py --inj_buffer 64 --net_buffer 4 --routing multicast
    ```

## 📜 Documentación Técnica

Para un análisis profundo, consulta los informes en la carpeta `./documentacion`:

* 📄 **Mapeo Sináptico In-Memory:** Técnicas para desplegar operaciones Conv2D en arquitecturas 1D.
* ⚙️ **Multicast vs Unicast en Sistemas AER:** Efectos físicos de la inyección simultánea de múltiples *spikes* en buffers locales y el impacto de la replicación en malla.
* ⚡ **Modelo de Energía y Throughput:** Rendimiento basado en litografía de 22nm FD-SOI a 1.2 GHz.

## 📜 Licencia y Contacto

Este proyecto está diseñado para satisfacer los más altos estándares en validación académica y es una plataforma ideal para investigación avanzada en Arquitectura de Computadores, Sistemas Neuromórficos y Redes en Chip. 🎓

Si este simulador te ayuda en tu investigación o en tus desarrollos, ¡no olvides darle una ⭐️ en el repositorio! 🌟
