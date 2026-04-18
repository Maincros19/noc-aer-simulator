# Comparativa de Experimentos: NoC-AER con Fan-out Real

Este documento presenta los resultados de los experimentos realizados con el simulador NoC-AER refactorizado, utilizando un **fan-out real** basado en la arquitectura de la Spiking Neural Network (SNN).

## Configuración de los Experimentos
*   **Tecnología:** Neuromorphic-Specialized (22nm FD-SOI) @ 1200 MHz
*   **Configuración de Red:** Ideal (Sin Pérdidas) - Buffer: 16384 flits
*   **Iteraciones por Época:** 100
*   **Fan-out:** Real (Conv1: 12, Conv2: 32, FC: 10)
*   **Muestras de Simulación:** 5

## Resultados Comparativos

| Métrica | Experimento 1 (1 Época) | Experimento 2 (2 Épocas) | Experimento 3 (3 Épocas) |
| :--- | :---: | :---: | :---: |
| **Precisión IA (Accuracy)** | 96.88% | 97.16% | 96.88% |
| **Spikes Generados (SNN)** | 29,921 | 30,663 | 32,576 |
| **Flits Inyectados (NoC)** | 695,132 | 708,448 | 758,356 |
| **Latencia Media (ciclos)** | 5.97 | 5.98 | 5.99 |
| **Jitter (ciclos)** | 9,711.24 | 10,411.70 | 6,978.05 |
| **Throughput (flits/ciclo)** | 0.7379 | 0.7505 | 0.8050 |
| **Energía Total (uJ)** | 3.001971 | 3.045759 | 3.194569 |
| **Tiempo Entrenamiento (s)** | 45.55 | 69.51 | 106.15 |
| **Tiempo Simulación C++ (s)** | 9.54 | 9.33 | 9.81 |

## Análisis de los Resultados

1.  **Escalabilidad del Tráfico:** Se observa que el número de flits inyectados es significativamente mayor que el de spikes generados, reflejando fielmente el **fan-out real** de la arquitectura. Con ~30,000 spikes se generan más de 700,000 eventos en la NoC, lo que representa una carga de trabajo masiva y realista.
2.  **Estabilidad de la Latencia:** A pesar del incremento masivo en el tráfico, la latencia media se mantiene extremadamente estable en torno a los 6 ciclos. Esto indica que el mapeo distribuido y el escalado temporal AER están gestionando eficazmente la congestión en una red ideal.
3.  **Consumo Energético:** La energía dinámica domina el consumo total debido al alto volumen de tráfico (más de 2 uJ de energía dinámica frente a ~0.94 uJ de estática). Esto demuestra la importancia de optimizar el fan-out y la conectividad en hardware neuromórfico.
4.  **Rendimiento de la IA:** La precisión se mantiene alta y estable (~97%), lo que confirma que la infraestructura de la NoC no está degradando la calidad de la computación neuromórfica, incluso bajo cargas de tráfico intensas.
5.  **Eficiencia del Simulador:** El backend en C++ demuestra una gran eficiencia, procesando cerca de 750,000 eventos en menos de 10 segundos, lo que valida la decisión de delegar la física de la red al simulador ciclo-a-ciclo.
