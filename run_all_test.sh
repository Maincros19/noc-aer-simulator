#!/bin/bash

# ==========================================
# CONFIGURACIÓN INICIAL
# ==========================================
TMP_FILE="temp_sim_output.txt"
DIR_RESULTADOS="resultados_validacion"

# Crear carpeta de resultados si no existe
mkdir -p $DIR_RESULTADOS

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE VALIDACIÓN AVANZADA NoC-AER"
echo "=========================================================="
echo "Los resultados y videos se guardarán en: ./$DIR_RESULTADOS/"
echo "Nota: La generación de videos aumenta considerablemente el tiempo."
echo ""

# Función auxiliar para extraer un dato individual
extraer_metrica() {
    local metrica=$1
    local columna=$2
    grep "$metrica" $TMP_FILE | awk -v col="$columna" '{print $col}' | tr -d ',' | tr -d '%'
}

# Función para extraer TODAS las métricas en formato CSV
extraer_todas_las_metricas() {
    SPK=$(extraer_metrica "Spikes Gen:" 4)
    FLITS=$(extraer_metrica "Flits NoC:" 4)
    LAT=$(extraer_metrica "Latencia Med:" 4)
    JIT=$(extraer_metrica "Jitter (AER):" 4)
    THR=$(extraer_metrica "Throughput:" 3)
    ENG=$(extraer_metrica "Energia Total:" 4)
    EFI=$(extraer_metrica "Eficiencia:" 3)
    RND=$(extraer_metrica "Rendimiento:" 3)
    ACC=$(extraer_metrica "PRECISION IA FINAL:" 4)

    if [ -z "$LAT" ]; then
        echo "NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN"
    else
        echo "$SPK,$FLITS,$LAT,$JIT,$THR,$ENG,$EFI,$RND,$ACC"
    fi
}

# Cabecera estándar para todos los CSV
STD_HEADER="Spikes_Gen,Flits_NoC,Latencia_Media,Jitter,Throughput,Energia_Total_uJ,Eficiencia_flits_uJ,Rendimiento_flits_s,Precision_IA"

# ==========================================
# FASE 1: REGRESIÓN (DETERMINISMO)
# ==========================================
echo "▶ FASE 1: Comprobando Determinismo (3 ejecuciones)..."
for i in {1..3}; do
    # Guardamos un video para verificar que el tráfico es idéntico visualmente
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --samples 1 --buffer 4096 --video_name "$DIR_RESULTADOS/v1_determinismo_$i" > $TMP_FILE 2>&1
    LAT=$(extraer_metrica "Latencia Med:" 4)
    SPIKES=$(extraer_metrica "Spikes Gen:" 4)
    echo "  Ejecución $i -> Spikes: $SPIKES | Latencia: $LAT"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 2: ESTRÉS Y CONGESTIÓN (BÚFER)
# ==========================================
CSV_BUFFER="$DIR_RESULTADOS/test_2_congestion_buffer.csv"
echo "Buffer,$STD_HEADER" > $CSV_BUFFER
BUFFERS=(1024 256 64 16) # Reducido para no eternizar la validación

echo "▶ FASE 2: Prueba de Contrapresión (Reduciendo Buffer)..."
for BUF in "${BUFFERS[@]}"; do
    echo -n "  Simulando Buffer $BUF... "
    python3 nmnist_tui_sim.py --dim 4 --samples 2 --buffer $BUF --video_name "$DIR_RESULTADOS/v2_buffer_$BUF" > $TMP_FILE 2>&1

    ALL_METRICS=$(extraer_todas_las_metricas)
    LAT=$(echo "$ALL_METRICS" | cut -d',' -f3)
    echo "OK! (Lat: $LAT)"
    echo "$BUF,$ALL_METRICS" >> $CSV_BUFFER
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 3: ESCALABILIDAD (TAMAÑOS DE MALLA)
# ==========================================
CSV_DIM="$DIR_RESULTADOS/test_3_escalabilidad_dim.csv"
echo "Dimension,Nodos_Totales,$STD_HEADER" > $CSV_DIM
DIMS=(2 4 6)

echo "▶ FASE 3: Escalabilidad Topológica (Aumentando Malla)..."
for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM}... "
    python3 nmnist_tui_sim.py --dim $DIM --samples 2 --buffer 512 --video_name "$DIR_RESULTADOS/v3_malla_${DIM}x${DIM}" > $TMP_FILE 2>&1

    NODOS=$((DIM * DIM))
    ALL_METRICS=$(extraer_todas_las_metricas)
    LAT=$(echo "$ALL_METRICS" | cut -d',' -f3)
    echo "OK! (Lat: $LAT)"
    echo "$DIM,$NODOS,$ALL_METRICS" >> $CSV_DIM
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 4: IMPACTO DEL VOLUMEN DE MUESTRAS
# ==========================================
CSV_SAMPLES="$DIR_RESULTADOS/test_4_impacto_muestras.csv"
echo "Muestras,Tiempo_Ejecucion_s,$STD_HEADER" > $CSV_SAMPLES
SAMPLES_ARRAY=(1 5 10)

echo "▶ FASE 4: Impacto del Volumen de Datos..."
for S in "${SAMPLES_ARRAY[@]}"; do
    echo -n "  Inyectando $S muestras... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --iters 10 --samples $S --buffer 1024 --video_name "$DIR_RESULTADOS/v4_muestras_$S" > $TMP_FILE 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    ALL_METRICS=$(extraer_todas_las_metricas)
    FLITS=$(echo "$ALL_METRICS" | cut -d',' -f2)
    echo "OK! (Flits: $FLITS)"
    echo "$S,$TIEMPO,$ALL_METRICS" >> $CSV_SAMPLES
done
echo "----------------------------------------------------------"

# Limpieza final de archivos temporales de texto
rm -f $TMP_FILE

echo "🎉 ¡VALIDACIÓN INTEGRAL COMPLETADA! 🎉"
echo "Resultados disponibles en ./$DIR_RESULTADOS/:"
ls -lh $DIR_RESULTADOS/*.csv
ls -lh $DIR_RESULTADOS/*.mp4
