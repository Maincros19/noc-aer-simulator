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
echo "Los resultados se guardarán en: ./$DIR_RESULTADOS/"
echo "Nota: Este proceso es exhaustivo. Puede tardar bastante. ☕"
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

    # Si hay un error y no hay datos, rellenamos con NaN
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
echo "▶ FASE 1: Comprobando Determinismo (3 ejecuciones idénticas)..."
for i in {1..3}; do
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --samples 2 --buffer 4096 > $TMP_FILE 2>&1

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
BUFFERS=(4096 1024 256 64 16 8 4)

echo "▶ FASE 2: Prueba de Contrapresión (Reduciendo Buffer)..."
for BUF in "${BUFFERS[@]}"; do
    echo -n "  Simulando Buffer $BUF... "
    python3 nmnist_tui_sim.py --dim 4 --samples 5 --buffer $BUF > $TMP_FILE 2>&1

    ALL_METRICS=$(extraer_todas_las_metricas)
    LAT=$(echo "$ALL_METRICS" | cut -d',' -f3) # Extraer solo latencia para el echo

    if [ "$LAT" == "NaN" ]; then echo "ERROR"; else echo "OK! (Lat: $LAT)"; fi
    echo "$BUF,$ALL_METRICS" >> $CSV_BUFFER
done
echo "----------------------------------------------------------"


# ==========================================
# FASE 3: ESCALABILIDAD (MÁS TAMAÑOS DE MALLA)
# ==========================================
CSV_DIM="$DIR_RESULTADOS/test_3_escalabilidad_dim.csv"
echo "Dimension,Nodos_Totales,$STD_HEADER" > $CSV_DIM
DIMS=(2 3 4 5 6 8)

echo "▶ FASE 3: Escalabilidad Topológica (Aumentando Malla)..."
for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM}... "
    python3 nmnist_tui_sim.py --dim $DIM --samples 3 --buffer 1024 > $TMP_FILE 2>&1

    NODOS=$((DIM * DIM))
    ALL_METRICS=$(extraer_todas_las_metricas)
    LAT=$(echo "$ALL_METRICS" | cut -d',' -f3)

    if [ "$LAT" == "NaN" ]; then echo "ERROR"; else echo "OK! (Lat: $LAT)"; fi
    echo "$DIM,$NODOS,$ALL_METRICS" >> $CSV_DIM
done
echo "----------------------------------------------------------"


# ==========================================
# FASE 4: IMPACTO DEL VOLUMEN DE MUESTRAS
# ==========================================
CSV_SAMPLES="$DIR_RESULTADOS/test_4_impacto_muestras.csv"
echo "Muestras,Tiempo_Ejecucion_s,$STD_HEADER" > $CSV_SAMPLES
SAMPLES_ARRAY=(1 2 5 10 20)

echo "▶ FASE 4: Impacto del Volumen de Datos (Inferencia Fija)..."
for S in "${SAMPLES_ARRAY[@]}"; do
    echo -n "  Inyectando $S muestras consecutivas... "

    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --iters 10 --samples $S --buffer 1024 > $TMP_FILE 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    ALL_METRICS=$(extraer_todas_las_metricas)
    FLITS=$(echo "$ALL_METRICS" | cut -d',' -f2)

    if [ "$FLITS" == "NaN" ]; then echo "ERROR"; else echo "OK! (Flits: $FLITS)"; fi
    echo "$S,$TIEMPO,$ALL_METRICS" >> $CSV_SAMPLES
done
echo "----------------------------------------------------------"


# ==========================================
# FASE 5: PRECISIÓN DE IA Y ESPARSIDAD
# ==========================================
CSV_IA="$DIR_RESULTADOS/test_5_precision_ia.csv"
echo "Epocas,Iteraciones,Tiempo_Entrenamiento_s,$STD_HEADER" > $CSV_IA

# Arrays emparejados (Epocas, Iters)
EPOCAS=(1 1 2 3 5)
ITERS=(5 20 40 50 100)

echo "▶ FASE 5: Convergencia IA y Esparsidad (Muestras Fijas=5)..."
for i in "${!EPOCAS[@]}"; do
    E=${EPOCAS[$i]}
    IT=${ITERS[$i]}

    echo -n "  Entrenando IA (Epocas:$E, Iters:$IT)... "

    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --epochs $E --iters $IT --samples 5 --buffer 1024 > $TMP_FILE 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    ALL_METRICS=$(extraer_todas_las_metricas)
    ACC=$(echo "$ALL_METRICS" | cut -d',' -f9)

    if [ "$ACC" == "NaN" ]; then echo "ERROR"; else echo "OK! (Precisión: $ACC%)"; fi
    echo "$E,$IT,$TIEMPO,$ALL_METRICS" >> $CSV_IA
done
echo "----------------------------------------------------------"

# Limpieza final
rm -f $TMP_FILE

echo "🎉 ¡VALIDACIÓN INTEGRAL COMPLETADA! 🎉"
echo "Tus 4 archivos CSV ahora contienen todas las métricas de hardware e IA y están listos en ./$DIR_RESULTADOS/"
