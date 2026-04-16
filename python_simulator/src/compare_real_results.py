import matplotlib.pyplot as plt
import numpy as np

# Datos de la simulación real (N-MNIST, 411,420 eventos)
simulators = ['Cycle Sim', 'Fast Sim']
latencies = [2.89, 367.79]
jitter = [1.05, 276.71]
hops = [1190989, 1190989]
energy = [1396699.00, 1396699.00]

x = np.arange(len(simulators))
width = 0.35

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Subplot 1: Latencia (Escala Logarítmica debido a la gran diferencia)
rects1 = ax1.bar(x - width/2, latencies, width, label='Latencia Promedio', color='#3498db')
rects2 = ax1.bar(x + width/2, jitter, width, label='Jitter (StdDev)', color='#e74c3c')

ax1.set_ylabel('Ciclos (Escala Logarítmica)')
ax1.set_yscale('log')
ax1.set_title('Latencia y Jitter (N-MNIST Real)')
ax1.set_xticks(x)
ax1.set_xticklabels(simulators)
ax1.legend()
ax1.bar_label(rects1, padding=3, fmt='%.2f')
ax1.bar_label(rects2, padding=3, fmt='%.2f')

# Subplot 2: Hops y Energía
rects3 = ax2.bar(x, energy, width, label='Energía Estimada', color='#2ecc71')
ax2.set_ylabel('Unidades / Hops')
ax2.set_title('Energía y Saltos Totales')
ax2.set_xticks(x)
ax2.set_xticklabels(simulators)
ax2.legend()
ax2.bar_label(rects3, padding=3, fmt='%.0f')

plt.suptitle('Comparativa: Red Neuronal N-MNIST en Malla 4x4 (411k eventos)')
fig.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig('real_nmnist_comparison_plot.png')
print("Gráfico generado: real_nmnist_comparison_plot.png")
