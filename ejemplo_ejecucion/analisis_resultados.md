# Informe de Análisis de Resultados - Simulación NoC AER (SNN Entrenada - 100 Iteraciones)

Este documento presenta un análisis detallado de una ejecución de ejemplo del simulador de NoC AER utilizando una traza generada a partir de una **red neuronal de impulsos (SNN) entrenada durante 100 iteraciones** procesando el dataset N-MNIST.

## 1. Configuración de la Simulación

| Parámetro | Valor |
| :--- | :--- |
| **Topología** | Malla (Mesh) 4x4 |
| **Número de Nodos** | 16 |
| **Algoritmo de Enrutamiento** | XY |
| **Dataset SNN** | N-MNIST |
| **Entrenamiento SNN** | 100 iteraciones (Epoch 0) |
| **Eventos de Traza** | 403,061 |

## 2. Métricas de Rendimiento Obtenidas

La simulación se completó en **0.32 segundos**, procesando una carga de trabajo realista generada por la SNN entrenada.

| Métrica | Resultado |
| :--- | :--- |
| **Flits Procesados** | 403,061 |
| **Latencia Promedio** | 331.24 ciclos |
| **Jitter (Desviación Estándar)** | 249.37 ciclos |
| **Total de Saltos (Hops)** | 1,209,127 |
| **Energía Estimada** | 1,410,657.50 unidades |

## 3. Análisis de Carga y Cuellos de Botella

El entrenamiento de la SNN ha generado una actividad de spikes mucho más intensa y estructurada, lo que permite identificar con mayor precisión los puntos de presión en la NoC.

### Top 5 Nodos más Activos (Inyección)
1. **Nodo 5:** 90,468 eventos (Capa `snn1`)
2. **Nodo 3:** 84,448 eventos (Capa `snn1`)
3. **Nodo 2:** 79,352 eventos (Capa `snn1`)
4. **Nodo 6:** 50,484 eventos (Capa `snn1`)
5. **Nodo 4:** 35,126 eventos (Capa `snn1`)

> **Diagnóstico:** Se han detectado cuellos de botella críticos en los **Nodos 5, 3 y 2**. Estos nodos, que albergan neuronas de la primera capa convolucional (`snn1`), están generando ráfagas de spikes que saturan los buffers locales y aumentan significativamente la latencia promedio de la red. La concentración de más del 60% del tráfico en solo 3 nodos es insostenible para una malla 4x4.

## 4. Conclusiones Técnicas

1. **Realismo de la Traza:** El entrenamiento completo de la SNN ha generado una traza masiva de más de 400k eventos, lo que representa una carga de trabajo mucho más realista para el análisis de hardware.
2. **Impacto en la Latencia:** La latencia promedio de **331.24 ciclos** y un jitter de **249.37 ciclos** indican una congestión severa. Los spikes pasan la mayor parte de su tiempo esperando en los buffers, lo que es crítico para la funcionalidad de las SNN que dependen de la precisión temporal.
3. **Recomendación de Diseño:** Para manejar los más de 400k eventos generados por una SNN entrenada, es **imperativo** escalar a una malla 8x8 o superior. Además, se debe implementar una estrategia de mapeo de neuronas que distribuya la carga de las capas más activas (como `snn1`) de forma más uniforme por toda la red, evitando la saturación de nodos centrales.

---
*Generado automáticamente por el Simulador NoC AER - Ejemplo de Ejecución con SNN Entrenada (100 Iteraciones)*
