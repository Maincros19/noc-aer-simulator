#!/bin/bash

# ==========================================
# CONFIGURACIÓN INICIAL (IN-MEMORY COMPUTING)
# ==========================================
TMP_FILE="temp_sim_output.txt"
DIR_RESULTADOS="resultados_validacion"

mkdir -p $DIR_RESULTADOS

CSV_FREQ="$DIR_RESULTADOS/test1_frecuencia.csv"
CSV_DIM="$DIR_RESULTADOS/test2_escalabilidad.csv"

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE VALIDACIÓN EXTENSA NoC-AER"
echo "🧠 Arquitectura: In-Memory Computing (ASIC Emulation)"
echo "=========================================================="
echo "Los resultados se guardarán en: ./$DIR_RESULTADOS"
echo ""

# Cabecera actualizada: Se elimina Lat_RAM (al ser In-Memory es 0/inexistente)
STD_HEADER="Fase,Escenario,Dim_Malla,Buffer_Iny,Buffer_Red,Muestras,Spikes_Gen,Flits_Gen,Flits_Iny,Flits_Eyect,Flits_Proc,Lat_Total,Lat_Buf,Lat_Red,Jitter,Throughput,Energia_uJ,Eficiencia,Perf_Absoluto,Precision_IA,Tiempo_Test_s"

echo "$STD_HEADER" > "$CSV_FREQ"
echo "$STD_HEADER" > "$CSV_DIM"

# ==========================================
# FUNCIONES DE EXTRACCIÓN Y GUARDADO
# ==========================================

extraer_metrica() {
    # Busca la etiqueta, selecciona la columna indicada, y limpia comas y porcentajes
    grep "$1" "$TMP_FILE" | awk -v col="$2" '{print $col}' | tr -d ',' | tr -d '%'
}

extraer_rendimiento() {
    # Extracción específica robusta para el formato "Throughput Físico:XXXX flits/s"
    grep "Throughput Físico:" "$TMP_FILE" | awk -F':' '{print $2}' | awk '{print $1}' | tr -d ','
}

guardar_metricas() {
    local FASE=$1 ESCENARIO=$2 DIM=$3 BUF_INY=$4 BUF_RED=$5 MUESTRAS=$6 TIEMPO_TEST=$7 TARGET_CSV=$8

    SPK=$(extraer_metrica "Spikes Gen:" 4)
    FLITS_GEN=$(extraer_metrica "Flits Generados:" 4)
    FLITS_INY=$(extraer_metrica "Flits Inyectados:" 4)
    FLITS_EYE=$(extraer_metrica "Flits Eyectados:" 4)
    FLITS_PRO=$(extraer_metrica "Flits Procesados:" 4)

    LAT_TOT=$(extraer_metrica "Lat. Total:" 4)
    LAT_BUF=$(extraer_metrica "├─ Buffer Loc:" 5)   # Latencia de hardware por contención Fan-Out
    LAT_RED=$(extraer_metrica "└─ Red:" 4)         # Latencia de vuelo en los enlaces NoC

    JIT=$(extraer_metrica "Jitter (AER):" 4)
    THR=$(extraer_metrica "Throughput:" 3)
    ENG=$(extraer_metrica "Energia Total:" 4)
    EFI=$(extraer_metrica "Eficiencia:" 3)
    RND=$(extraer_rendimiento)
    ACC=$(extraer_metrica "PRECISION IA FINAL:" 4) # Precisión calculada en silicio

    if [ -z "$LAT_TOT" ]; then
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO_TEST" >> "$TARGET_CSV"
    else
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,$SPK,$FLITS_GEN,$FLITS_INY,$FLITS_EYE,$FLITS_PRO,$LAT_TOT,$LAT_BUF,$LAT_RED,$JIT,$THR,$ENG,$EFI,$RND,$ACC,$TIEMPO_TEST" >> "$TARGET_CSV"
    fi
}

# ==========================================
# TEST 1: IMPACTO DE LA FRECUENCIA DEL RELOJ
# ==========================================
# Bajamos a frecuencias sub-MHz para obligar a que la ventana de tiempo
# sea MENOR a los ciclos que necesita la red (ej. 0.01 MHz = solo 10 ciclos por ms)
FRECUENCIAS=(0.01 0.05 0.1 0.5 1 5 10 50)
echo "▶ TEST 1: Espectro de Frecuencia de Reloj (Stress Temporal)..."

for FREQ in "${FRECUENCIAS[@]}"; do
    echo -n "  Simulando a ${FREQ} MHz... "
    START_TIME=$(date +%s)
    # 5 muestras para dar solidez estadística a la precisión de la IA
    python3 nmnist_tui_sim.py --samples 5 --inj_buffer 64 --net_buffer 64 --freq $FREQ > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT_TOT=$(extraer_metrica "Lat. Total:" 4)
    ACC_IA=$(extraer_metrica "PRECISION IA FINAL:" 4)
    echo "OK! (Lat Total: $LAT_TOT ciclos | Precisión IA: $ACC_IA%)"

    guardar_metricas "1_Frecuencia" "Freq_${FREQ}MHz" 4 64 64 5 $TIEMPO "$CSV_FREQ"
done
echo "----------------------------------------------------------"

# ==========================================
# TEST 2: ESCALABILIDAD TOPOLÓGICA (ALIVIO DEL FAN-OUT)
# Fijamos: Freq=1200MHz, Muestras=5, Buffers=512
# Objetivo: Ver cómo esparcir el mapeo reduce el colapso del Buffer Loc
# ==========================================
DIMS=(2 4 6 8 10)
echo "▶ TEST 2: Escalabilidad Física (Variación de la Malla)..."

for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM} (${DIM}x${DIM} routers)... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim $DIM --samples 5 --inj_buffer 512 --net_buffer 512 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT_BUF=$(extraer_metrica "├─ Buffer Loc:" 5)
    LAT_RED=$(extraer_metrica "└─ Red:" 4)
    echo "OK! (Lat Buffer: $LAT_BUF | Lat Red: $LAT_RED)"

    guardar_metricas "2_Escalabilidad" "Malla_${DIM}x${DIM}" $DIM 512 512 5 $TIEMPO "$CSV_DIM"
done
echo "----------------------------------------------------------"

# Limpieza final
rm -f "$TMP_FILE"

echo "🎉 ¡PRUEBAS EXTENSAS COMPLETADAS! 🎉"
echo "Archivos generados:"
echo " 1. ./$CSV_FREQ"
echo " 2. ./$CSV_DIM"
