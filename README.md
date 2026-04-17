# NoC AER Simulator (C++ DES Core & SNN Training)

Este repositorio contiene un simulador de **Red en Chip (NoC)** de alto rendimiento diseñado para el tráfico de **Redes Neuronales Espiking (SNN)** utilizando el protocolo **AER (Address Event Representation)**. 

El sistema integra un flujo completo: desde el **entrenamiento real** de una SNN con el dataset N-MNIST hasta la **simulación de hardware** con métricas de rendimiento detalladas y configurables.

---

## 🚀 Características Principales

- **Entrenamiento Real de SNN:** Implementación de una **Convolutional SNN (CSNN)** utilizando `snntorch`. El modelo se entrena realmente con el dataset N-MNIST antes de la simulación.
- **Selección de Tecnología Interactiva:** El usuario puede elegir entre diferentes nodos tecnológicos (65nm, 45nm, 28nm) y tecnologías especializadas (**22nm FD-SOI**, **Sub-threshold**) para obtener estimaciones de energía ultra-precisas.
- **Configuración de Red Personalizable:** Menú interactivo para definir el estado de la NoC:
  - **Red Ideal:** Sin pérdidas de paquetes y buffers amplios.
  - **Red Estándar:** Congestión moderada con buffers de 1024 flits.
  - **Red Saturada:** Alta tasa de pérdida y buffers reducidos (256 flits) para pruebas de estrés.
- **Métricas de Hardware Dinámicas:** Cálculo en tiempo real de:
  - **Latencia Media:** Afectada dinámicamente por el tamaño del buffer y la congestión.
  - **Jitter de Latencia:** Variación temporal de la entrega de eventos.
  - **Tasa de Entrega (Delivery Ratio):** Calculada según la carga de tráfico y configuración de red.
- **Precisión de IA (Accuracy):** Evaluación de la precisión del modelo entrenado durante el flujo de simulación.

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
El script `nmnist_train_sim.py` te guiará a través de la selección de tecnología y configuración de red:
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

## 📊 Configuración de Red y Congestión

| Modo de Red | Buffer (Flits) | Factor de Pérdida | Impacto en Latencia |
| :--- | :---: | :---: | :--- |
| **Ideal** | 4096 | 0% | Mínima |
| **Estándar** | 1024 | Bajo | Moderada |
| **Saturada** | 256 | Alto | Alta (por reintentos/cola) |

---

## 📄 Licencia
Este proyecto está diseñado para fines de investigación en hardware neuromórfico y arquitecturas de NoC. Desarrollado y optimizado para simulaciones de eventos discretos de alta fidelidad.
