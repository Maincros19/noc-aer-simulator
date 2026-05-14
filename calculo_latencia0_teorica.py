#!/usr/bin/env python3
import csv

def calcular_distancias_malla(dim):
    """
    Calcula la distancia máxima y media de Manhattan para una malla dim x dim.
    Se asume un patrón de tráfico uniforme all-to-all (excluyendo self-traffic).
    """
    distancia_max = 0
    suma_distancias = 0
    pares_totales = 0

    # Iteramos sobre todos los pares origen-destino posibles (x1,y1) -> (x2,y2)
    for y1 in range(dim):
        for x1 in range(dim):
            for y2 in range(dim):
                for x2 in range(dim):
                    if x1 == x2 and y1 == y2:
                        continue # Excluir envíos al propio nodo (self-traffic)

                    # Distancia de Manhattan
                    distancia = abs(x2 - x1) + abs(y2 - y1)

                    if distancia > distancia_max:
                        distancia_max = distancia

                    suma_distancias += distancia
                    pares_totales += 1

    distancia_media = suma_distancias / pares_totales
    return distancia_max, distancia_media

def main():
    csv_filename = "latencia_teorica_zero_load.csv"

    print("================================================================================")
    print(" 🧮 CÁLCULO TEÓRICO: LATENCIA 0 (ZERO-LOAD) EN TOPOLOGÍAS DE MALLA 2D")
    print("================================================================================")
    print(f"{'Malla':<10} | {'Max Hops':<10} | {'Lat. Max (Ciclos)':<18} | {'Avg Hops':<10} | {'Lat. Avg (Ciclos)'}")
    print("-" * 80)

    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Dimension_Malla", "Nodos_Totales", "Saltos_Max", "Latencia_Max_Ciclos", "Saltos_Avg", "Latencia_Avg_Ciclos"])

        for dim in range(2, 13):
            nodos = dim * dim
            max_hops, avg_hops = calcular_distancias_malla(dim)

            # Ecuación de hardware: L0 = (2 * H) + 1
            latencia_max = (2 * max_hops) + 1
            latencia_avg = (2 * avg_hops) + 1

            malla_str = f"{dim}x{dim}"
            print(f"{malla_str:<10} | {max_hops:<10} | {latencia_max:<18} | {avg_hops:<10.2f} | {latencia_avg:.2f}")

            writer.writerow([malla_str, nodos, max_hops, latencia_max, round(avg_hops, 4), round(latencia_avg, 4)])

    print("-" * 80)
    print(f"✅ Tabla de resultados exportada correctamente a: {csv_filename}")

if __name__ == "__main__":
    main()
