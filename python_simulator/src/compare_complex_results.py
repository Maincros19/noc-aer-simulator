import matplotlib.pyplot as plt
import numpy as np

# Datos obtenidos de las ejecuciones complejas (10,000 flits)
simulators = ['Cycle Sim', 'Fast Sim']
latencies = [2.66, 6.31]
jitter = [1.23, 2.46]
hops = [26561, 26561]
energy = [31561.00, 31561.00]

x = np.arange(len(simulators))
width = 0.35

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Subplot 1: Latencia y Jitter
rects1 = ax1.bar(x - width/2, latencies, width, label='Latencia Promedio', color='#3498db')
rects2 = ax1.bar(x + width/2, jitter, width, label='Jitter (StdDev)', color='#e74c3c')

ax1.set_ylabel('Ciclos')
ax1.set_title('Latencia y Jitter (10,000 flits)')
ax1.set_xticks(x)
ax1.set_xticklabels(simulators)
ax1.legend()
ax1.bar_label(rects1, padding=3)
ax1.bar_label(rects2, padding=3)

# Subplot 2: Hops y Energía
rects3 = ax2.bar(x, energy, width, label='Energía Estimada', color='#2ecc71')
ax2.set_ylabel('Unidades / Hops')
ax2.set_title('Energía y Saltos Totales')
ax2.set_xticks(x)
ax2.set_xticklabels(simulators)
ax2.legend()
ax2.bar_label(rects3, padding=3)

plt.suptitle('Comparativa de Rendimiento a Gran Escala (Malla 4x4)')
fig.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig('complex_comparison_plot.png')
print("Gráfico generado: complex_comparison_plot.png")
