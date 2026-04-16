import matplotlib.pyplot as plt
import numpy as np

# Datos de la simulación de Integridad Total (N-MNIST, 411,420 flits)
simulators = ['Cycle Sim (High Fid)', 'Fast Sim (Analytic)']
latencies = [49288.80, 367.79]
jitter = [28709.98, 276.71]

x = np.arange(len(simulators))
width = 0.35

fig, ax1 = plt.subplots(figsize=(10, 6))

# Latencia y Jitter (Escala logarítmica para visualizar la diferencia extrema)
rects1 = ax1.bar(x - width/2, latencies, width, label='Latencia Promedio', color='#2c3e50')
rects2 = ax1.bar(x + width/2, jitter, width, label='Jitter (StdDev)', color='#e67e22')

ax1.set_ylabel('Ciclos (Escala Logarítmica)')
ax1.set_yscale('log')
ax1.set_title('Comparativa de Rendimiento: Integridad Total (411k flits)')
ax1.set_xticks(x)
ax1.set_xticklabels(simulators)
ax1.legend()

ax1.bar_label(rects1, padding=3, fmt='%.0f')
ax1.bar_label(rects2, padding=3, fmt='%.0f')

plt.suptitle('Análisis de Saturación: El impacto del Backpressure en NoC')
fig.tight_layout()
plt.savefig('real_nmnist_comparison_plot.png')
print("Gráfico actualizado: real_nmnist_comparison_plot.png")
