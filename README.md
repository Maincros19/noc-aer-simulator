# NoC AER Simulator (C++ DES Core & SNN Training)

Este repositorio contiene un simulador de **Red en Chip (NoC)** de alto rendimiento diseñado para el tráfico de **Redes Neuronales Espiking (SNN)** utilizando el protocolo **AER (Address Event Representation)**. 

El sistema integra un flujo completo: desde el **entrenamiento real** de una SNN con el dataset N-MNIST hasta la **simulación de hardware** con métricas de rendimiento detalladas, configurables y en tiempo real.

---

## 🚀 Características Principales

- **Entrenamiento Real de SNN:** Implementación de una **Convolutional SNN (CSNN)** utilizando `snntorch`. El modelo se entrena realmente con el dataset N-MNIST antes de la simulación.
- **Selección de Tecnología con Frecuencia Real:** El usuario puede elegir entre diferentes nodos tecnológicos, cada uno con su propia **Frecuencia de Operación (MHz)** y consumo energético.
- **Conversión a Tiempo Real:** El simulador traduce automáticamente los ciclos de reloj a **nanosegundos (ns)** basándose en la tecnología seleccionada.
- **Configuración de Red Personalizable:** Menú interactivo para definir el estado de la NoC (Ideal, Estándar, Saturada) y el tamaño de los buffers de los routers.
- **Métricas de Hardware Dinámicas:** Cálculo en tiempo real de Latencia Media (ciclos/ns), Jitter, Throughput y Tasa de Entrega.
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

## 🔋 Modelos de Tecnología y Tiempo

| Tecnología | Frecuencia (MHz) | Periodo (ns) | Energía (pJ/spike) |
| :--- | :---: | :---: | :---: |
| **CMOS 65nm** | 400 | 2.50 | 15.5 |
| **CMOS 45nm** | 600 | 1.67 | 8.2 |
| **CMOS 28nm** | 1000 | 1.00 | 4.5 |
| **22nm FD-SOI** | 1200 | 0.83 | 0.85 |
| **Sub-threshold** | 200 | 5.00 | 0.12 |

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
