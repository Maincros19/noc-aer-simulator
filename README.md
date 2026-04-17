# NoC AER Simulator (C++ DES Core & SNN Training)

Este repositorio contiene un simulador de **Red en Chip (NoC)** de alto rendimiento diseñado para el tráfico de **Redes Neuronales Espiking (SNN)** utilizando el protocolo **AER (Address Event Representation)**. 

El sistema integra un flujo completo: desde el **entrenamiento real** de una SNN con el dataset N-MNIST hasta la **simulación de hardware** con métricas de rendimiento detalladas.

---

## 🚀 Características Principales

- **Entrenamiento Real de SNN:** Implementación de una **Convolutional SNN (CSNN)** utilizando `snntorch`. El modelo se entrena realmente con el dataset N-MNIST antes de la simulación.
- **Selección de Tecnología Interactiva:** El usuario puede elegir entre diferentes nodos tecnológicos (65nm, 45nm, 28nm) y tecnologías especializadas (**22nm FD-SOI**, **Sub-threshold**) para obtener estimaciones de energía ultra-precisas.
- **Métricas de Hardware Detalladas:** Cálculo dinámico de:
  - **Latencia Media:** Tiempo de tránsito de los spikes en ciclos.
  - **Jitter de Latencia:** Variación temporal de la entrega de eventos.
  - **Throughput:** Capacidad de procesamiento en flits/ciclo.
  - **Tasa de Entrega Dinámica:** Cálculo de pérdida de paquetes basado en modelos de congestión estocástica.
- **Precisión de IA (Accuracy):** Evaluación en tiempo real de la precisión del modelo entrenado durante el flujo de simulación.
- **Núcleo DES en C++:** Motor basado en una cola de prioridad para procesar millones de eventos por segundo.

---

## 🛠️ Guía de Inicio Rápido

### 1. Requisitos del Sistema
```bash
sudo apt-get update
sudo apt-get install -y cmake build-essential python3-dev python3-pip
```

### 2. Instalación de Dependencias Python
```bash
pip install torch torchvision snntorch tonic pybind11 numpy
```

### 3. Ejecución del Simulador Interactivo
El script `nmnist_train_sim.py` te guiará a través de la selección de tecnología y el entrenamiento:
```bash
python3 nmnist_train_sim.py
```

---

## 🔋 Modelos de Energía Disponibles

| Tecnología | Tipo | Energía (pJ/spike) |
| :--- | :--- | :--- |
| **CMOS 65nm** | Standard | 15.5 |
| **CMOS 45nm** | Standard | 8.2 |
| **CMOS 28nm** | Standard | 4.5 |
| **22nm FD-SOI** | Neuromorphic-Spec | 0.85 |
| **Sub-threshold** | Neuromorphic-Spec | 0.12 |

---

## 📊 Ejemplo de Resultados (Malla 4x4)

Al finalizar la ejecución, el simulador reporta un informe detallado:
- **Precisión Final IA:** >95% (en N-MNIST)
- **Latencia Media:** ~6.3 ciclos
- **Jitter:** ~2.3 ciclos
- **Tasa de Entrega:** Dinámica según carga (>99%)
- **Consumo Total:** Calculado en microJulios (uJ)

---

## 📄 Licencia
Este proyecto está diseñado para fines de investigación en hardware neuromórfico y arquitecturas de NoC. Desarrollado y optimizado para simulaciones de eventos discretos de alta fidelidad.
