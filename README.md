# 🧠 NoC-AER Simulator: Simulación Neuromórfica de Alta Precisión 🚀

¡Bienvenido al simulador **NoC-AER**! Este proyecto es una herramienta avanzada diseñada para simular cómo se comunican las neuronas artificiales a través de una **Red en Chip (NoC)** utilizando el protocolo **AER (Address Event Representation)**. 

Hemos transformado este simulador de un modelo matemático simple a un motor de simulación **ciclo-a-ciclo** ultra preciso en C++, garantizando que **no se pierda ni un solo evento (spike)**. 🎯

---

## ✨ Características Estrella

### 1. ⏱️ Simulación Ciclo-a-Ciclo (C++ Core)
¡Nada de aproximaciones! Cada movimiento de un dato (flit) se calcula ciclo por ciclo de reloj. Esto nos da métricas reales de:
- **Latencia:** Cuánto tarda un spike en llegar a su destino. ⏳
- **Jitter:** La variabilidad en el tiempo de llegada (crucial en sistemas AER). 📉
- **Energía:** Consumo detallado (dinámico y estático) según la tecnología (desde 65nm hasta 22nm). ⚡

### 2. 🔄 Conectividad "Fan-out" Real
A diferencia de otros simuladores, aquí la conectividad es **biológicamente fiel** a la red neuronal:
- **Entrada → Conv1:** 1 spike se convierte en 12 eventos en la red. 🌊
- **Conv1 → Conv2:** 1 spike se propaga a 32 destinos. 🌊🌊
- **Conv2 → Salida:** 1 spike llega a las 10 neuronas de clasificación. 🎯
- **Resultado:** ¡Simulamos ráfagas masivas de más de **750,000 eventos** con total precisión! 💥

### 3. 🛡️ Garantía de Cero Pérdidas
En los sistemas neuromórficos, perder un spike es perder información. Nuestro simulador implementa un sistema de **control de flujo (backpressure)** que asegura una **tasa de entrega del 100%**. 🛑➡️✅

### 4. 🗺️ Mapeo Inteligente
Distribuimos las neuronas por toda la "malla" (mesh) de la NoC para evitar atascos y que el tráfico fluya como la seda. 🕸️

---

## 🏗️ Arquitectura del Sistema

- **Frontend (Python 🐍):** Entrena la red neuronal (SNN) con el dataset N-MNIST y genera los spikes.
- **Backend (C++ ⚙️):** El motor de alto rendimiento que simula la física de la red.
- **Puente (PyBind11 🔗):** Conecta ambos mundos para una ejecución rápida y fluida.

---

## 🚀 Guía de Inicio Rápido

### 📋 Requisitos Previos
Necesitarás tener instalado:
- Python 3.11+
- CMake y un compilador de C++ (G++)
- Librerías: `torch`, `snntorch`, `tonic`, `pybind11`

### 🛠️ Instalación en 2 pasos

1. **Compila el motor C++:**
   ```bash
   cd cpp_simulator && mkdir build && cd build
   cmake ..
   make
   ```

2. **¡Lanza la simulación!:**
   ```bash
   python3 nmnist_train_sim.py
   ```

---

## 📊 ¿Qué verás en los resultados?

Al final de cada experimento, el simulador te mostrará un panel detallado con:
- **Precisión de la IA:** ¿Qué tan bien está clasificando los números? 🤖
- **Eventos en la NoC:** El volumen total de tráfico gestionado. 📈
- **Latencia y Jitter:** El rendimiento temporal de tu hardware. ⏱️
- **Consumo de Energía:** ¡Ideal para optimizar diseños de bajo consumo! 🔋
- **Tiempo de Ejecución:** Cuánto ha tardado el PC en procesar todo. 💻

---

## 🧪 Experimentos Recientes (Fan-out Real)

| Métrica | 1 Época | 2 Épocas | 3 Épocas |
| :--- | :---: | :---: | :---: |
| **Precisión IA** | 96.88% | 97.16% | 96.88% |
| **Eventos (Flits)** | ~700k | ~710k | ~760k |
| **Latencia Media** | 5.97 ciclos | 5.98 ciclos | 5.99 ciclos |
| **Energía Total** | 3.00 uJ | 3.05 uJ | 3.19 uJ |

---

## 📜 Licencia y Contacto
Este proyecto es ideal para investigadores y entusiastas de la **arquitectura de computadores** y la **IA neuromórfica**. 🎓

¡Si te gusta el proyecto, no dudes en darle una ⭐️ en GitHub! 🌟
