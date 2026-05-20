#!/bin/bash

# ==========================================
# CONFIGURACIÓN INICIAL
# ==========================================
TMP_FILE="temp_sim_output.txt"
DIR_RESULTADOS="resultados_validacion"

mkdir -p $DIR_RESULTADOS

CSV_FREQ="$DIR_RESULTADOS/test1_frecuencia.csv"
CSV_DIM="$DIR_RESULTADOS/test2_escalabilidad.csv"

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE VALIDACIÓN EXTENSA NoC-AER"
echo "=========================================================="
echo "Los resultados se guardarán en: ./$DIR_RESULTADOS"
echo ""

# Cabecera completa con Buffer_Iny y Buffer_Red separados
STD_HEADER="Fase,Escenario,Dim_Malla,Buffer_Iny,Buffer_Red,Muestras,Spikes_Gen,Flits_Gen,Flits_Iny,Flits_Eyect,Flits_Proc,Lat_Total,Lat_RAM,Lat_Buf,Lat_Red,Jitter,Throughput,Energia_uJ,Eficiencia,Perf_Absoluto,Precision_IA,Tiempo_Test_s"

echo "$STD_HEADER" > "$CSV_FREQ"
echo "$STD_HEADER" > "$CSV_DIM"

# ==========================================
# FUNCIONES DE EXTRACCIÓN Y GUARDADO
# ==========================================

extraer_metrica() {
    grep "$1" "$TMP_FILE" | awk -v col="$2" '{print $col}' | tr -d ',' | tr -d '%'
}

extraer_rendimiento() {
    grep -E "Rendimiento:|Throughput Físico:|Tasa Absoluta:" "$TMP_FILE" | awk '{print $(NF-1)}' | tr -d ','
}

guardar_metricas() {
    local FASE=$1 ESCENARIO=$2 DIM=$3 BUF_INY=$4 BUF_RED=$5 MUESTRAS=$6 TIEMPO_TEST=$7 TARGET_CSV=$8

    SPK=$(extraer_metrica "Spikes Gen:" 4)
    FLITS_GEN=$(extraer_metrica "Flits Generados:" 4)
    FLITS_INY=$(extraer_metrica "Flits Inyectados:" 4)
    FLITS_EYE=$(extraer_metrica "Flits Eyectados:" 4)
    FLITS_PRO=$(extraer_metrica "Flits Procesados:" 4)

    LAT_TOT=$(extraer_metrica "Lat. Total:" 4)
    LAT_RAM=$(extraer_metrica "Cola RAM:" 5)      # Extrae la latencia de software
    LAT_BUF=$(extraer_metrica "Buffer Loc:" 5)    # Extrae la latencia de hardware
    LAT_RED=$(extraer_metrica "Red:" 4)           # Extrae la latencia de vuelo

    JIT=$(extraer_metrica "Jitter (AER):" 4)
    THR=$(extraer_metrica "Throughput:" 3)
    ENG=$(extraer_metrica "Energia Total:" 4)
    EFI=$(extraer_metrica "Eficiencia:" 3)
    RND=$(extraer_rendimiento)
    ACC=$(extraer_metrica "PRECISION IA FINAL:" 4)

    if [ -z "$LAT_TOT" ]; then
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO_TEST" >> "$TARGET_CSV"
    else
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,$SPK,$FLITS_GEN,$FLITS_INY,$FLITS_EYE,$FLITS_PRO,$LAT_TOT,$LAT_RAM,$LAT_BUF,$LAT_RED,$JIT,$THR,$ENG,$EFI,$RND,$ACC,$TIEMPO_TEST" >> "$TARGET_CSV"
    fi
}

# ==========================================
# TEST 1: IMPACTO DE LA FRECUENCIA DEL RELOJ
# Fijamos: Dim=4, Muestras=2, Buffers=64 (para evidenciar saturación)
# ==========================================
FRECUENCIAS=(10 15 25 50 100 250 500 800 1200)
echo "▶ TEST 1: Espectro de Frecuencia de Reloj (Contrapresión Dinámica)..."

for FREQ in "${FRECUENCIAS[@]}"; do
    echo -n "  Simulando a ${FREQ} MHz... "
    START_TIME=$(date +%s)
    # Buffers a 64 obligan al DMA y a la Red a mostrar sus límites bajo distintas velocidades de reloj
    python3 nmnist_tui_sim.py --samples 2 --inj_buffer 64 --net_buffer 64 --freq $FREQ > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT_TOT=$(extraer_metrica "Lat. Total:" 4)
    LAT_RAM=$(extraer_metrica "Cola RAM:" 5)
    echo "OK! (Lat Total: $LAT_TOT | Lat RAM: $LAT_RAM)"

    guardar_metricas "1_Frecuencia" "Freq_${FREQ}MHz" 4 64 64 2 $TIEMPO "$CSV_FREQ"
done
echo "----------------------------------------------------------"

# ==========================================
# TEST 2: ESCALABILIDAD TOPOLÓGICA (TAMAÑO DE LA MALLA)
# Fijamos: Freq=1200MHz, Muestras=2, Buffers=512 (para aislar el coste del Hop Count)
# ==========================================
DIMS=(2 4 6 8 10)
echo "▶ TEST 2: Escalabilidad Física (Variación de la Malla)..."

for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM} (${DIM}x${DIM} routers)... "
    START_TIME=$(date +%s)
    # Almacenamiento holgado (512) para que el atasco no ensucie la latencia de vuelo puro
    python3 nmnist_tui_sim.py --dim $DIM --samples 2 --inj_buffer 512 --net_buffer 512 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT_RED=$(extraer_metrica "Red:" 4)
    echo "OK! (Lat Red/Vuelo: $LAT_RED)"

    guardar_metricas "2_Escalabilidad" "Malla_${DIM}x${DIM}" $DIM 512 512 2 $TIEMPO "$CSV_DIM"
done
echo "----------------------------------------------------------"

# Limpieza final
rm -f "$TMP_FILE"

echo "🎉 ¡PRUEBAS EXTENSAS COMPLETADAS! 🎉"
echo "Archivos generados:"
echo " 1. ./$CSV_FREQ"
echo " 2. ./$CSV_DIM"
