#!/bin/bash

# ==========================================
# CONFIGURACIÓN INICIAL
# ==========================================
TMP_FILE="temp_sim_output.txt"
DIR_RESULTADOS="resultados_validacion"

# Crear carpeta de resultados si no existe
mkdir -p $DIR_RESULTADOS

# Archivos CSV independientes por cada fase
CSV_F1="$DIR_RESULTADOS/fase1_regresion.csv"
CSV_F2="$DIR_RESULTADOS/fase2_congestion_estres.csv"
CSV_F3="$DIR_RESULTADOS/fase3_escalabilidad.csv"
CSV_F4="$DIR_RESULTADOS/fase4_impacto_datos.csv"
CSV_F5="$DIR_RESULTADOS/fase5_asimetria.csv"
CSV_F6="$DIR_RESULTADOS/fase6_perfil_ia.csv"

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE VALIDACIÓN AVANZADA NoC-AER"
echo "=========================================================="
echo "Los resultados se guardarán en archivos separados dentro de: ./$DIR_RESULTADOS"
echo ""

# Cabecera estándar para todos los archivos CSV
STD_HEADER="Fase,Escenario,Dim_Malla,Buffer,Muestras,Spikes_Gen,Flits_Gen,Flits_Iny,Flits_Eyect,Flits_Proc,Lat_Total,Lat_Iny,Lat_Red,Jitter,Throughput,Energia_uJ,Eficiencia,Perf_Absoluto,Precision_IA,Tiempo_Test_s"

# Inicializar los archivos con la cabecera
echo "$STD_HEADER" > "$CSV_F1"
echo "$STD_HEADER" > "$CSV_F2"
echo "$STD_HEADER" > "$CSV_F3"
echo "$STD_HEADER" > "$CSV_F4"
echo "$STD_HEADER" > "$CSV_F5"
echo "$STD_HEADER" > "$CSV_F6"

# ==========================================
# FUNCIONES DE EXTRACCIÓN Y GUARDADO
# ==========================================

extraer_metrica() {
    local metrica=$1
    local columna=$2
    grep "$metrica" "$TMP_FILE" | awk -v col="$columna" '{print $col}' | tr -d ',' | tr -d '%'
}

extraer_rendimiento() {
    grep -E "Rendimiento:|Throughput Físico:|Tasa Absoluta:" "$TMP_FILE" | awk '{print $(NF-1)}' | tr -d ','
}

guardar_metricas() {
    local FASE=$1
    local ESCENARIO=$2
    local DIM=$3
    local BUF=$4
    local MUESTRAS=$5
    local TIEMPO_TEST=$6
    local TARGET_CSV=$7

    SPK=$(extraer_metrica "Spikes Gen:" 4)
    FLITS_GEN=$(extraer_metrica "Flits Generados:" 4)
    FLITS_INY=$(extraer_metrica "Flits Inyectados:" 4)
    FLITS_EYE=$(extraer_metrica "Flits Eyectados:" 4)
    FLITS_PRO=$(extraer_metrica "Flits Procesados:" 4)

    LAT_TOT=$(extraer_metrica "Lat. Total:" 4)
    LAT_INY=$(extraer_metrica "Inyección:" 4)
    LAT_RED=$(extraer_metrica "Red:" 4)
    JIT=$(extraer_metrica "Jitter (AER):" 4)

    THR=$(extraer_metrica "Throughput:" 3)
    ENG=$(extraer_metrica "Energia Total:" 4)
    EFI=$(extraer_metrica "Eficiencia:" 3)

    RND=$(extraer_rendimiento)
    ACC=$(extraer_metrica "PRECISION IA FINAL:" 4)

    if [ -z "$LAT_TOT" ]; then
        echo "$FASE,$ESCENARIO,$DIM,$BUF,$MUESTRAS,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO_TEST" >> "$TARGET_CSV"
    else
        echo "$FASE,$ESCENARIO,$DIM,$BUF,$MUESTRAS,$SPK,$FLITS_GEN,$FLITS_INY,$FLITS_EYE,$FLITS_PRO,$LAT_TOT,$LAT_INY,$LAT_RED,$JIT,$THR,$ENG,$EFI,$RND,$ACC,$TIEMPO_TEST" >> "$TARGET_CSV"
    fi
}

# ==========================================
# FASE 1: REGRESIÓN (DETERMINISMO EN ZERO-LOAD)
# ==========================================
echo "▶ FASE 1: Comprobando Determinismo (1200 MHz)..."
for i in {1..3}; do
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --samples 1 --inj_buffer 4096 --net_buffer 4096 --freq 1200 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT=$(extraer_metrica "Lat. Total:" 4)
    SPIKES=$(extraer_metrica "Spikes Gen:" 4)
    echo "  Ejecución $i -> Spikes: $SPIKES | Latencia: $LAT"

    guardar_metricas "1_Regresion" "Determinismo_$i" 4 4096 1 $TIEMPO "$CSV_F1"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 2: ESTRÉS Y CONGESTIÓN (RELOJ AHOGADO A 15 MHz)
# ==========================================
BUFFERS=(1024 256 64 16)
echo "▶ FASE 2: Prueba de Contrapresión (Estrés a 15 MHz)..."
for BUF in "${BUFFERS[@]}"; do
    echo -n "  Simulando Buffers a $BUF... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --samples 2 --inj_buffer $BUF --net_buffer $BUF --freq 15 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT_INY=$(extraer_metrica "Inyección:" 4)
    LAT_RED=$(extraer_metrica "Red:" 4)
    echo "OK! (Lat. Inyección: $LAT_INY | Lat. Red: $LAT_RED)"

    guardar_metricas "2_Congestion" "Stress_Buf_$BUF" 4 $BUF 2 $TIEMPO "$CSV_F2"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 3: ESCALABILIDAD TOPOLÓGICA (1200 MHz)
# ==========================================
DIMS=(2 4 6)
echo "▶ FASE 3: Escalabilidad (Aumentando Malla)..."
for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM}... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim $DIM --samples 2 --inj_buffer 512 --net_buffer 512 --freq 1200 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT=$(extraer_metrica "Lat. Total:" 4)
    echo "OK! (Lat: $LAT)"

    guardar_metricas "3_Escalabilidad" "Malla_${DIM}x${DIM}" $DIM 512 2 $TIEMPO "$CSV_F3"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 4: IMPACTO DEL VOLUMEN DE DATOS (1200 MHz)
# ==========================================
SAMPLES_ARRAY=(1 5 10)
echo "▶ FASE 4: Impacto del Volumen de Muestras..."
for S in "${SAMPLES_ARRAY[@]}"; do
    echo -n "  Inyectando $S muestras... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --iters 10 --samples $S --inj_buffer 1024 --net_buffer 1024 --freq 1200 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    FLITS=$(extraer_metrica "Flits Procesados:" 4)
    echo "OK! (Flits Procesados: $FLITS)"

    guardar_metricas "4_Impacto_Datos" "Muestras_$S" 4 1024 $S $TIEMPO "$CSV_F4"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 5: ASIMETRÍA DE BUFFERS (ESTRÉS A 15 MHz)
# ==========================================
echo "▶ FASE 5: Asimetría de Buffers (Inyección vs Red)..."
CONFIGS_ASIM=("4096:16" "16:4096" "256:32" "32:256")
for CONF in "${CONFIGS_ASIM[@]}"; do
    INJ="${CONF%%:*}"
    NET="${CONF##*:}"
    echo -n "  Simulando Inj=$INJ / Net=$NET... "

    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --samples 2 --inj_buffer $INJ --net_buffer $NET --freq 15 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    LAT=$(extraer_metrica "Lat. Total:" 4)
    echo "OK! (Lat: $LAT)"

    guardar_metricas "5_Asimetria" "Stress_Inj${INJ}_Net${NET}" 4 "${INJ}_${NET}" 2 $TIEMPO "$CSV_F5"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 6: IMPACTO DEL ENTRENAMIENTO IA (1200 MHz)
# ==========================================
ITERS_ARRAY=(5 20 50)
echo "▶ FASE 6: Perfil de Tráfico por Madurez SNN..."
for ITER in "${ITERS_ARRAY[@]}"; do
    echo -n "  Entrenando $ITER iteraciones... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --iters $ITER --samples 2 --inj_buffer 1024 --net_buffer 1024 --freq 1200 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    SPK=$(extraer_metrica "Spikes Gen:" 4)
    ACC=$(extraer_metrica "PRECISION IA FINAL:" 4)
    echo "OK! (Spikes: $SPK | Acc: $ACC%)"

    guardar_metricas "6_Perfil_IA" "Iters_$ITER" 4 1024 2 $TIEMPO "$CSV_F6"
done
echo "----------------------------------------------------------"

# Limpieza final
rm -f "$TMP_FILE"

echo "🎉 ¡VALIDACIÓN INTEGRAL COMPLETADA! 🎉"
echo "Todos los datos han sido clasificados y guardados en:"
echo "👉 ./$DIR_RESULTADOS/"
