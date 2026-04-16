# Ejemplos de Ejecución

Esta carpeta contiene ejemplos prácticos de cómo utilizar los simuladores del proyecto y las comparativas de rendimiento obtenidas.

## Contenido

### 1. [Simulación Compleja (10,000 flits)](complex_simulation/)
Una prueba de estrés diseñada para evaluar el comportamiento de la red bajo una carga significativa.
- **Traza:** `complex_trace.txt` (10,000 eventos aleatorios).
- **Resultados:** Comparativa detallada entre `cycle_sim.py` y `fast_sim.py`.
- **Gráficos:** Visualización de latencia, jitter y energía.

### 2. [Simulación Simple](simple_simulation/)
Una ejecución básica con pocos eventos para validar la lógica de enrutamiento y el funcionamiento inicial.
- **Traza:** `synthetic_trace.txt`.
- **Resultados:** Reportes de ejecución rápida.

## Cómo ejecutar estos ejemplos

Para replicar los resultados de la simulación compleja, puedes ejecutar:

```bash
# Para el simulador de ciclos
python3 python_simulator/src/cycle_sim.py examples/complex_simulation/complex_trace.txt python_simulator/config/mesh_4x4.config

# Para el simulador rápido
python3 python_simulator/src/fast_sim.py examples/complex_simulation/complex_trace.txt python_simulator/config/mesh_4x4.config
```
