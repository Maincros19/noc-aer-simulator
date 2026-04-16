# Modelo de Energía Detallado (C++ DES Core)

Este documento describe el modelo de energía utilizado para estimar el consumo de potencia en el simulador de NoC AER basado en eventos discretos (DES).

## Componentes del Consumo de Energía

El consumo total de energía en un NoC se divide en dos categorías principales: **Energía Dinámica** y **Energía Estática (Leakage)**.

### 1. Energía Dinámica ($E_{dynamic}$)
Se consume solo cuando hay actividad en el NoC (conmutación de señales). En un simulador DES, esto se asocia directamente con los eventos procesados.

$$E_{dynamic} = E_{router} + E_{link}$$

- **$E_{router}$:** Energía consumida por el router al procesar un flit (arbitraje, ruteo y conmutación).
- **$E_{link}$:** Energía consumida al transmitir un flit a través de un enlace físico entre dos routers.

#### Parámetros de Referencia (Tecnología 45nm CMOS)
| Operación | Energía Estimada (pJ/flit) |
| :--- | :--- |
| **Arbitraje y Ruteo** | 0.15 pJ |
| **Conmutación (Crossbar)** | 0.45 pJ |
| **Escritura/Lectura de Buffer** | 0.80 pJ |
| **Transmisión en Enlace (1mm)** | 1.20 pJ |

### 2. Energía Estática ($P_{static}$)
Se consume de forma constante mientras el hardware está encendido, independientemente de la actividad.

$$E_{static} = P_{static} \times T_{total}$$

Donde $T_{total}$ es el tiempo total de simulación en ciclos de reloj.

## Cálculo en el Simulador DES

A diferencia de un simulador basado en ciclos, el simulador DES calcula la energía acumulando el costo de cada evento:

1.  **Evento `FLIT_ARRIVAL`:** Suma el costo de escritura en el buffer de entrada.
2.  **Evento `ROUTER_PROCESSING`:** Suma el costo de arbitraje, ruteo y conmutación en el crossbar.
3.  **Transmisión:** Al enviar un flit al siguiente router, se suma el costo del enlace.

### Ventaja del Enfoque DES
El simulador DES permite una estimación de energía mucho más precisa para el tráfico **AER (Address Event Representation)**, ya que el consumo dinámico es proporcional al número real de spikes procesados, capturando fielmente la naturaleza dispersa de las redes neuronales espikantes.

## Métricas de Eficiencia Energética

- **Energía por Spike (pJ/spike):** Energía total dividida por el número de spikes entregados con éxito.
- **Potencia Promedio (mW):** Energía total dividida por el tiempo de simulación.

---
*Nota: Los parámetros de energía son estimaciones basadas en literatura técnica de NoCs y pueden variar según la implementación física específica.*
