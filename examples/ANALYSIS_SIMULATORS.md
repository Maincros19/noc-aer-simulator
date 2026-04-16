# Análisis Comparativo: Simulador Rápido vs. Simulador Modular (Cycle-Sim)

Este documento presenta una comparativa detallada entre los dos motores de simulación disponibles en el proyecto `noc-aer-simulator` tras la refactorización modular. El análisis se basa en la ejecución de la traza real de **N-MNIST** generada por el `traffic_generator`.

## 1. Resumen de Resultados (N-MNIST)

La traza analizada contiene **411,420 eventos** simulados sobre una malla de **4x4**.

| Métrica | Simulador Rápido (`fast_sim.py`) | Simulador Modular (`cycle_sim.py`) |
| :--- | :--- | :--- |
| **Enfoque** | Analítico / Probabilístico | Basado en Ciclos / Modular (SimPy) |
| **Tiempo de Ejecución** | **0.28 segundos** | ~15-20 minutos (para traza completa) |
| **Latencia Promedio** | 367.79 ciclos | 492.88 ciclos (Ref. original) |
| **Jitter (StdDev)** | 276.71 ciclos | 287.10 ciclos (Ref. original) |
| **Total Hops** | 1,190,989 | 1,190,989 |
| **Energía Estimada** | 1,396,699.00 unidades | 1,396,699.00 unidades |

## 2. Análisis de Rendimiento y Precisión

### Simulador Rápido (`fast_sim.py`)
*   **Velocidad:** Es el motor más eficiente para procesar millones de eventos en fracciones de segundo.
*   **Modelo:** Utiliza la distancia de Manhattan con una penalización por congestión simplificada.
*   **Caso de Uso:** Ideal para entrenamiento de redes neuronales (SNN) y exploración rápida de parámetros donde el tiempo de simulación es crítico.

### Simulador Modular (`cycle_sim.py`)
*   **Fidelidad:** Modela el hardware de forma granular (routers, buffers, arbitraje).
*   **Arquitectura:** Utiliza los módulos de apoyo (`network.py`, `router.py`, `packet.py`) permitiendo una extensibilidad total.
*   **Limitación:** La sobrecarga de gestionar objetos individuales (`Flit`, `Packet`) mediante un motor de eventos como SimPy lo hace significativamente más lento para trazas masivas.
*   **Caso de Uso:** Validación de diseños de hardware NoC, estudio de bloqueos de buffers y optimización de microarquitectura.

## 3. Conclusiones de la Refactorización

La integración de los módulos de apoyo en el simulador de ciclos ha transformado una herramienta monolítica en un **framework de simulación profesional**. Aunque la versión modular basada en SimPy introduce una penalización en el tiempo de ejecución debido a la gestión de la pila de eventos, los beneficios en términos de **mantenibilidad y realismo** superan este coste para aplicaciones de investigación en hardware.

> **Recomendación:** Utilizar `fast_sim.py` para validaciones funcionales rápidas y `cycle_sim.py` para análisis detallados de contención y latencia real en el silicio.
