#!/bin/bash

# ==========================================================
# NoC-AER VALIDATION SUITE (IMPROVED)
# ==========================================================
# Este script automatiza la validación física y de IA del NoC-AER.
# Mejoras: Limpieza de códigos ANSI, extracción robusta por Regex,
# métrica de Late Flits y mejor reporte de errores.

TMP_RAW="temp_raw_output.txt"
TMP_CLEAN="temp_clean_output.txt"
DIR_RESULTADOS="resultados_validacion"

mkdir -p "$DIR_RESULTADOS"

CSV_FREQ="$DIR_RESULTADOS/test1_frecuencia.csv"
CSV_DIM="$DIR_RESULTADOS/test2_escalabilidad.csv"

# Cabecera: Añadimos Late_Flits y corregimos nombres
STD_HEADER="Fase,Escenario,Dim_Malla,Buffer_Iny,Buffer_Red,Muestras,Spikes_Gen,Flits_Gen,Flits_Iny,Flits_Eyect,Flits_Proc,Late_Flits,Lat_Total,Lat_Buf,Lat_Red,Jitter,Throughput,Energia_uJ,Eficiencia,Perf_Absoluto,Precision_IA,Tiempo_Test_s"

echo "$STD_HEADER" > "$CSV_FREQ"
echo "$STD_HEADER" > "$CSV_DIM"

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE VALIDACIÓN MEJORADA NoC-AER"
echo "🧠 Arquitectura: In-Memory Computing (ASIC Emulation)"
echo "=========================================================="

# ----------------------------------------------------------
# FUNCIONES DE APOYO
# ----------------------------------------------------------

# Limpia códigos de escape ANSI (colores, movimientos de cursor)
limpiar_ansi() {
    sed -r "s/\x1B\[([0-9]{1,3}(;[0-9]{1,2})?)?[mGK]//g" "$TMP_RAW" > "$TMP_CLEAN"
}

# Extrae un valor numérico siguiendo una etiqueta específica
# Uso: extraer_valor "Etiqueta"
extraer_valor() {
    local etiqueta="$1"
    # Busca la etiqueta, toma el resto de la línea, extrae el primer número (entero o decimal)
    grep -a "$etiqueta" "$TMP_CLEAN" | head -n 1 | grep -oE '[0-9]+(\.[0-9]+)?' | head -n 1
}

guardar_metricas() {
    local FASE=$1 ESCENARIO=$2 DIM=$3 BUF_INY=$4 BUF_RED=$5 MUESTRAS=$6 TIEMPO_TEST=$7 TARGET_CSV=$8

    limpiar_ansi

    # Extracción de contadores
    SPK=$(extraer_valor "Spikes Gen:")
    FLITS_GEN=$(extraer_valor "Flits Generados:")
    FLITS_INY=$(extraer_valor "Flits Inyectados:")
    FLITS_EYE=$(extraer_valor "Flits Eyectados:")
    FLITS_PRO=$(extraer_valor "Flits Procesados:")
    LATE=$(extraer_valor "ALERTA:.*flits descartados" || echo "0")

    # Extracción de latencias y física
    LAT_TOT=$(extraer_valor "Lat. Total:")
    LAT_BUF=$(extraer_valor "Buffer Loc:")
    LAT_RED=$(extraer_valor "Red:")
    JIT=$(extraer_valor "Jitter (AER):")

    # Métricas de rendimiento
    THR=$(extraer_valor "Throughput:")
    ENG=$(extraer_valor "Energia Total:")
    EFI=$(extraer_valor "Eficiencia:")
    RND=$(extraer_valor "Throughput Físico:")

    # Precisión (Buscamos la de Hardware)
    ACC=$(extraer_valor "Hardware (In-Memory):")

    # Validación de datos extraídos
    if [ -z "$LAT_TOT" ]; then
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO_TEST" >> "$TARGET_CSV"
    else
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,$SPK,$FLITS_GEN,$FLITS_INY,$FLITS_EYE,$FLITS_PRO,$LATE,$LAT_TOT,$LAT_BUF,$LAT_RED,$JIT,$THR,$ENG,$EFI,$RND,$ACC,$TIEMPO_TEST" >> "$TARGET_CSV"
    fi
}

# ----------------------------------------------------------
# TEST 1: IMPACTO DE LA FRECUENCIA (ESTRÉS TEMPORAL)
# ----------------------------------------------------------
FRECUENCIAS=(0.1 1 10 100 1200)
echo "▶ TEST 1: Espectro de Frecuencia de Reloj..."

for FREQ in "${FRECUENCIAS[@]}"; do
    echo -n "  Simulando a ${FREQ} MHz... "
    START_TIME=$(date +%s)

    # Ejecución con timeout de seguridad
    timeout 300s python3 nmnist_tui_sim.py --samples 3 --inj_buffer 128 --net_buffer 32 --freq $FREQ > "$TMP_RAW" 2>&1

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    if [ $EXIT_CODE -eq 0 ]; then
        limpiar_ansi
        LAT=$(extraer_valor "Lat. Total:")
        ACC=$(extraer_valor "Hardware (In-Memory):")
        LATE=$(extraer_valor "ALERTA:.*flits descartados" || echo "0")
        echo "OK! (Lat: $LAT | Acc: $ACC% | Late: $LATE)"
        guardar_metricas "1_Frecuencia" "Freq_${FREQ}MHz" 4 128 32 3 $TIEMPO "$CSV_FREQ"
    else
        echo "ERROR (Código $EXIT_CODE)"
        echo "1_Frecuencia,Freq_${FREQ}MHz,4,128,32,3,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_FREQ"
    fi
done

echo "----------------------------------------------------------"

# ----------------------------------------------------------
# TEST 2: ESCALABILIDAD (ALIVIO DE FAN-OUT)
# ----------------------------------------------------------
DIMS=(2 4 8)
echo "▶ TEST 2: Escalabilidad Topológica..."

for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM}... "
    START_TIME=$(date +%s)

    timeout 600s python3 nmnist_tui_sim.py --dim $DIM --samples 3 --inj_buffer 256 --net_buffer 64 > "$TMP_RAW" 2>&1

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    if [ $EXIT_CODE -eq 0 ]; then
        limpiar_ansi
        LAT_B=$(extraer_valor "Buffer Loc:")
        ACC=$(extraer_valor "Hardware (In-Memory):")
        echo "OK! (Lat_Buf: $LAT_B | Acc: $ACC%)"
        guardar_metricas "2_Escalabilidad" "Malla_${DIM}x${DIM}" $DIM 256 64 3 $TIEMPO "$CSV_DIM"
    else
        echo "ERROR"
        echo "2_Escalabilidad,Malla_${DIM}x${DIM},$DIM,256,64,3,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_DIM"
    fi
done

# Limpieza
rm -f "$TMP_RAW" "$TMP_CLEAN"

echo ""
echo "🎉 ¡VALIDACIÓN COMPLETADA! 🎉"
echo "Resultados en: $DIR_RESULTADOS"
