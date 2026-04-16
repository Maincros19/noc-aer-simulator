# Modelo de Energía Detallado - Simulador NoC AER

Este documento describe la metodología, fórmulas y equivalencias tecnológicas utilizadas por el simulador para estimar el consumo energético de la red. El modelo se basa en eventos discretos (spikes) y desglosa el consumo en dos componentes principales: la conmutación en los routers y el transporte a través de los enlaces.

## 1. Metodología de Cálculo

El simulador utiliza una métrica de **Unidades de Energía (UE)**. El consumo total se calcula sumando el coste de cada operación realizada por los flits (spikes) durante la simulación.

### Fórmula General
$$E_{total} = (N_{hops} \times C_{link}) + (N_{flits} \times C_{router})$$

Donde:
*   **$N_{hops}$**: Número total de saltos realizados por todos los flits (distancia recorrida).
*   **$C_{link}$**: Coste energético por salto (por defecto = **1.0 UE**).
*   **$N_{flits}$**: Número total de flits inyectados y procesados.
*   **$C_{router}$**: Coste energético de procesamiento interno en el router (por defecto = **0.5 UE**).

### Justificación de los Pesos
*   **Enlace (1.0 UE):** Representa la carga capacitiva de los cables globales que conectan los routers. En NoCs, el transporte de datos suele ser el componente más costoso debido a la longitud de las líneas metálicas.
*   **Router (0.5 UE):** Representa la energía consumida en la lectura/escritura de buffers, la lógica del árbitro y el paso por el *crossbar* interno. En arquitecturas optimizadas para AER, este coste es menor que el del enlace.

## 2. Tabla de Equivalencias Tecnológicas

Para convertir las **Unidades de Energía (UE)** a valores físicos reales (Picojulios o Nanojulios), se pueden utilizar las siguientes equivalencias basadas en nodos tecnológicos comunes de la industria (CMOS):

| Nodo Tecnológico | Energía por Bit/mm (aprox.) | Equivalencia Sugerida (1 UE) | Consumo Estimado (pJ/spike) |
| :--- | :--- | :--- | :--- |
| **65 nm** | 150 - 200 fJ/bit/mm | **~0.20 pJ** | ~0.30 pJ |
| **45 nm** | 100 - 150 fJ/bit/mm | **~0.12 pJ** | ~0.18 pJ |
| **28 nm** | 60 - 90 fJ/bit/mm | **~0.08 pJ** | ~0.12 pJ |
| **Tecnología Neuromórfica (ej. Loihi)** | < 50 fJ/bit/mm | **~0.04 pJ** | ~0.06 pJ |

*Nota: Los valores asumen un tamaño de flit estándar para AER (32-64 bits) y una distancia entre routers de aproximadamente 1mm.*

## 3. Ejemplo de Interpretación

Si el simulador reporta una **Energía Total de 1,410,657 UE**:

1.  **En 65nm (0.20 pJ/UE):**
    *   $1,410,657 \times 0.20 \text{ pJ} = 282,131 \text{ pJ} \approx \mathbf{0.28 \mu J}$
2.  **En 28nm (0.08 pJ/UE):**
    *   $1,410,657 \times 0.08 \text{ pJ} = 112,852 \text{ pJ} \approx \mathbf{0.11 \mu J}$

## 4. Factores que Afectan la Energía

*   **Mapeo de Neuronas:** Un mapeo que coloque neuronas comunicantes en nodos adyacentes reducirá $N_{hops}$, bajando drásticamente la energía.
*   **Multicast:** El soporte multicast reduce la inyección de flits redundantes, pero aumenta la actividad interna de los routers donde ocurre la ramificación.
*   **Congestión:** Aunque la congestión aumenta la latencia, el impacto directo en la energía dinámica es menor, ya que los flits realizan el mismo número de saltos, aunque pasen más tiempo en los buffers (energía estática/leakage, no contabilizada en este modelo dinámico).

---
*Documento técnico para el Proyecto NoC AER Simulator - 2026*
