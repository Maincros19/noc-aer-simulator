import matplotlib.pyplot as plt
import numpy as np

# Datos obtenidos de las ejecuciones
simulators = ['Cycle Sim', 'Fast Sim']
latencies = [4.25, 9.50]
jitter = [1.56, 3.12]
hops = [34, 34]
energy = [38.00, 38.00]

x = np.arange(len(simulators))
width = 0.35

fig, ax1 = plt.subplots(figsize=(10, 6))

# Latencia y Jitter
rects1 = ax1.bar(x - width/2, latencies, width, label='Latencia Promedio', color='skyblue')
rects2 = ax1.bar(x + width/2, jitter, width, label='Jitter (StdDev)', color='salmon')

ax1.set_ylabel('Ciclos')
ax1.set_title('Comparativa de Resultados: Cycle Sim vs Fast Sim')
ax1.set_xticks(x)
ax1.set_xticklabels(simulators)
ax1.legend(loc='upper left')

# Añadir etiquetas de valor
ax1.bar_label(rects1, padding=3)
ax1.bar_label(rects2, padding=3)

# Hops y Energía (Eje secundario)
ax2 = ax1.twinx()
ax2.set_ylabel('Unidades / Hops')
ax2.plot(x, energy, color='green', marker='o', linestyle='dashed', linewidth=2, label='Energía/Hops')
ax2.set_ylim(0, 50)
ax2.legend(loc='upper right')

fig.tight_layout()
plt.savefig('comparison_plot.png')
print("Gráfico generado: comparison_plot.png")
