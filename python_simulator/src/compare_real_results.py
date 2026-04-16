import matplotlib.pyplot as plt
import numpy as np

# Datos de la simulación de Alta Fidelidad (N-MNIST)
simulators = ['Cycle Sim (High Fid)', 'Fast Sim (Analytic)']
latencies = [352.76, 367.79]
jitter = [338.28, 276.71]

x = np.arange(len(simulators))
width = 0.35

fig, ax1 = plt.subplots(figsize=(10, 6))

# Latencia y Jitter
rects1 = ax1.bar(x - width/2, latencies, width, label='Latencia Promedio', color='#2c3e50')
rects2 = ax1.bar(x + width/2, jitter, width, label='Jitter (StdDev)', color='#e67e22')

ax1.set_ylabel('Ciclos')
ax1.set_title('Convergencia de Resultados: Alta Fidelidad vs Analítico')
ax1.set_xticks(x)
ax1.set_xticklabels(simulators)
ax1.legend()

ax1.bar_label(rects1, padding=3, fmt='%.2f')
ax1.bar_label(rects2, padding=3, fmt='%.2f')

plt.suptitle('Impacto del Arbitraje y Gestión de Buffers en la Latencia NoC')
fig.tight_layout()
plt.savefig('real_nmnist_comparison_plot.png')
print("Gráfico actualizado: real_nmnist_comparison_plot.png")
