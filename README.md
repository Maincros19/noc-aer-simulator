# NoC AER Simulator (C++ DES Core)

Este repositorio contiene un simulador de **Red en Chip (NoC)** de alto rendimiento diseñado específicamente para el tráfico de **Redes Neuronales Espiking (SNN)** utilizando el protocolo **AER (Address Event Representation)**.

El núcleo del simulador ha sido migrado de Python a **C++** utilizando un motor de **Simulación de Eventos Discretos (DES)**, lo que permite procesar millones de eventos por segundo con una precisión de ciclo.

---

## 🚀 Características Principales

- **Núcleo DES en C++:** Motor basado en una cola de prioridad (`std::priority_queue`) que salta instantáneamente entre eventos, optimizando el tráfico disperso (sparse) típico de las SNN.
- **Integración con Python (pybind11):** Inyección directa de spikes de memoria a memoria desde Python al núcleo C++, eliminando el cuello de botella de I/O de disco.
- **Soporte N-MNIST (Tonic):** Integración nativa con el dataset N-MNIST para generar trazas de tráfico realistas.
- **Métricas Neuromórficas:** Extracción automática de latencia de spike, tasa de entrega (delivery ratio) y energía por evento (pJ/spike).
- **Gestión de Congestión:** Buffers de entrada configurables (1024 flits) y arbitraje Round-Robin.

---

## 🛠️ Guía de Configuración del Entorno

Sigue estos pasos para preparar tu entorno de desarrollo y ejecutar el simulador.

### 1. Requisitos del Sistema
Asegúrate de tener instaladas las herramientas de compilación y desarrollo:
```bash
sudo apt-get update
sudo apt-get install -y cmake build-essential python3-dev python3-pip
```

### 2. Configuración del Entorno Python
Se recomienda el uso de un entorno virtual para gestionar las dependencias:
```bash
python3 -m venv venv
source venv/bin/activate
```

Instala las librerías necesarias para el entrenamiento y procesamiento de datos neuromórficos:
```bash
pip install torch torchvision torchaudio
pip install snntorch tonic pybind11 numpy
```

### 3. Compilación del Núcleo C++ (DES Core)
El simulador utiliza CMake para generar el módulo de Python mediante pybind11:
```bash
mkdir -p cpp_simulator/build
cmake -S cpp_simulator -B cpp_simulator/build
cmake --build cpp_simulator/build
```
*Esto generará un archivo `.so` en `cpp_simulator/build/` que Python podrá importar directamente.*

---

## 📊 Ejecución del Experimento N-MNIST

El script `nmnist_train_sim.py` realiza el flujo completo:
1. Carga una muestra real de **N-MNIST** usando `tonic`.
2. Procesa los eventos a través de una **CSNN** (Convolutional SNN).
3. Inyecta los spikes resultantes en la **NoC 4x4**.
4. Ejecuta la simulación DES y reporta métricas.

```bash
python3 nmnist_train_sim.py
```

### Resultados Esperados (Carga Masiva ~500k spikes)
| Métrica | Valor Típico |
| :--- | :--- |
| **Tasa de Entrega** | >99.8% |
| **Latencia Promedio** | ~5.2 ciclos |
| **Rendimiento** | >12,000,000 eventos/seg |
| **Energía Estimada** | ~2.0 pJ/spike |

---

## 🔋 Modelo de Energía
El simulador utiliza un modelo basado en eventos donde cada transacción consume una cantidad fija de energía. Consulta `modelo_energia_detallado.md` para profundizar en el cálculo de consumo por spike.

## 📄 Licencia
Este proyecto está diseñado para fines de investigación en hardware neuromórfico y arquitecturas de NoC.
