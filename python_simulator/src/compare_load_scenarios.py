import matplotlib.pyplot as plt
import numpy as np

# Datos de los escenarios
scenarios = ['Baja Carga (1k)', 'Alta Carga (411k)']
cycle_latencies = [211.25, 49288.80]
fast_latencies = [8.87, 367.79]

x = np.arange(len(scenarios))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))

# Barras para Cycle Sim y Fast Sim en ambos escenarios
rects1 = ax.bar(x - width/2, cycle_latencies, width, label='Cycle Sim (Fidelidad)', color='#2c3e50')
rects2 = ax.bar(x + width/2, fast_latencies, width, label='Fast Sim (Analítico)', color='#e67e22')

ax.set_ylabel('Latencia Promedio (Ciclos - Escala Log)')
ax.set_yscale('log')
ax.set_title('Impacto de la Carga: Baja Carga vs Saturación')
ax.set_xticks(x)
ax.set_xticklabels(scenarios)
ax.legend()

# Etiquetas
ax.bar_label(rects1, padding=3, fmt='%.1f')
ax.bar_label(rects2, padding=3, fmt='%.1f')

plt.suptitle('Régimen de Operación NoC: De Operación Normal a Colapso')
fig.tight_layout()
plt.savefig('load_comparison_plot.png')
print("Gráfico generado: load_comparison_plot.png")
