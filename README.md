# 🧠 NoC-AER Simulator: Simulación Neuromórfica de Alta Fidelidad (Industrial Edition) 🚀

¡Bienvenido al simulador **NoC-AER**! Este proyecto es una herramienta avanzada diseñada para simular la comunicación de neuronas artificiales a través de una **Red en Chip (NoC)** utilizando el protocolo **AER (Address Event Representation)**.

Hemos transformado este simulador en un motor de simulación **ciclo-a-ciclo** ultra preciso en C++, implementando restricciones de hardware reales y garantizando una **tasa de entrega del 100%** mediante control de flujo avanzado. 🎯

---

## ✨ Características de Alta Fidelidad

### 1. 🛡️ Control de Flujo Basado en Créditos (Credit-Based Flow Control)
Implementamos el estándar de la industria para la gestión de tráfico. Los routers solo envían flits si el vecino tiene espacio garantizado en sus buffers, eliminando el modelo irreal de "buffers infinitos" y modelando con precisión los atascos y la contención de red. 🛑➡️✅

### 2. ⏱️ Restricción de Hardware: 1 Flit/Ciclo
A diferencia de modelos abstractos, cada router en este simulador está limitado por su crossbar físico: puede procesar y expulsar **exactamente 1 flit por ciclo de reloj**. Esto garantiza que el **Throughput** sea físicamente consistente con una arquitectura real (máximo teórico de 1 flit/ciclo/nodo).

### 3. 🔄 Inyección Basada en Eventos (Event-Driven Injection)
La sincronización entre el testbench de Python y el núcleo de C++ es perfecta. Los spikes generados por la SNN se agendan como eventos de "nacimiento" (`SOURCE_INJECTION`) en la línea de tiempo global, eliminando anomalías temporales y garantizando métricas de latencia y jitter matemáticamente exactas.

### 4. 📊 Dashboard TUI en Tiempo Real (Industrial Edition)
Hemos integrado una interfaz de terminal interactiva (`nmnist_tui_sim.py`) que permite monitorizar:
- **Entrenamiento Real SNN:** Visualización dinámica de la pérdida (Loss) y precisión (Accuracy) de PyTorch.
- **Métricas NoC:** Latencia media, Jitter (AER), Throughput y Energía en tiempo real.
- **Modo Compatible:** Renderizado robusto para cualquier entorno de terminal.

---

## 🏗️ Arquitectura del Sistema

- **Frontend (Python 🐍):** Entrena la red neuronal (SNN) con el dataset N-MNIST y genera los eventos AER.
- **Backend (C++ ⚙️):** Motor de alto rendimiento con cola de eventos priorizada para una simulación determinista.
- **Puente (PyBind11 🔗):** Interfaz de baja latencia que permite controlar la simulación hardware desde Python.

---

## 🚀 Guía de Inicio Rápido

### 📋 Requisitos Previos
- Python 3.11+
- CMake 3.10+ y G++ 11+
- Librerías: `torch`, `snntorch`, `tonic`, `pybind11`

### 🛠️ Instalación y Ejecución

1. **Compila el motor C++:**
   ```bash
   cd cpp_simulator && mkdir build && cd build
   cmake .. -Dpybind11_DIR=$(python3.11 -m pybind11 --cmakedir)
   make
   ```

2. **Lanza la simulación con Dashboard TUI:**
   ```bash
   python3 nmnist_tui_sim.py
   ```

3. **Lanza el experimento estándar:**
   ```bash
   python3 nmnist_train_sim.py
   ```

---

## 📜 Documentación Técnica Detallada

Para un análisis profundo del funcionamiento interno, consulta nuestros nuevos informes:
- [📄 Informe Técnico General](./informe_tecnico_noc_aer.md): Resumen de componentes y flujo de datos.
- [⚙️ Análisis Exhaustivo de Arquitectura](./analisis_exhaustivo_noc_aer.md): Detalles sobre ruteo XY, arbitraje y modelo de energía.

---

## 📊 Métricas Reales (High-Fanout SNN)

Bajo una carga de trabajo real (Fan-out de hasta 32x por spike), el simulador revela el comportamiento físico de la red:

| Métrica | Valor Típico | Estado |
| :--- | :---: | :--- |
| **Tasa de Entrega** | 100.00% | **Garantizada** |
| **Throughput** | ~0.10 flits/ciclo | **Físicamente Consistente** |
| **Latencia Media** | ~45,000 ciclos | **Realista (Saturación)** |
| **Precisión IA** | ~67% (N-MNIST) | **Verificado** |
| **Eficiencia Energética** | ~0.85 pJ/spike (22nm) | **Ultra-Eficiente** |

---

## 📜 Licencia y Contacto
Este proyecto es ideal para investigación avanzada en **Arquitectura de Computadores**, **Sistemas Neuromórficos** y **NoC Design**. 🎓

¡Si te es útil para tu tesis o paper, dale una ⭐️ en GitHub! 🌟
