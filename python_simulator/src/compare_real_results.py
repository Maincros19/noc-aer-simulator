import matplotlib.pyplot as plt
import numpy as np

# Datos de los escenarios (N-MNIST, 411,420 flits)
simulators = ['Fast Sim (Analytic)', 'Cycle Sim (Baseline)', 'Cycle Sim (Advanced VCs)']
latencies = [367.79, 49288.80, 49934.45]
jitter = [276.71, 28709.98, 28768.50]

x = np.arange(len(simulators))
width = 0.35

fig, ax = plt.subplots(figsize=(12, 7))

# Latencia y Jitter (Escala logarítmica)
rects1 = ax.bar(x - width/2, latencies, width, label='Latencia Promedio', color='#2c3e50')
rects2 = ax.bar(x + width/2, jitter, width, label='Jitter (StdDev)', color='#e67e22')

ax.set_ylabel('Ciclos (Escala Log)')
ax.set_yscale('log')
ax.set_title('Comparativa de Arquitecturas NoC: Impacto de VCs y Créditos')
ax.set_xticks(x)
ax.set_xticklabels(simulators)
ax.legend()

# Etiquetas
ax.bar_label(rects1, padding=3, fmt='%.0f')
ax.bar_label(rects2, padding=3, fmt='%.0f')

plt.suptitle('Análisis de Control de Flujo Avanzado en Sistemas Neuromórficos')
fig.tight_layout()
plt.savefig('advanced_architecture_comparison.png')
print("Gráfico generado: advanced_architecture_comparison.png")
