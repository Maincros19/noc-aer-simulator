#!/bin/bash

# ==============================================================================
# NoC-AER EXHAUSTIVE VALIDATION AND PERFORMANCE SUITE (UNICAST vs MULTICAST)
# ==============================================================================
# Autor: Marcos Hernández Sánchez
# Descripción: Automatiza la ejecución de pruebas exhaustivas para el simulador NoC-AER.
#              Compara cada escenario físico bajo modos de ruteo Unicast y Multicast.
#              Incluye la métrica de ciclos medios por inferencia en el reporte.
# Entorno Académico: Máster en Ingeniería de Computadores y Redes - UPV

# Directorio de salida para los reportes numéricos
DIR_RESULTADOS="resultados_validacion"
mkdir -p "$DIR_RESULTADOS"

# Archivos temporales de volcado de datos
TMP_RAW="$DIR_RESULTADOS/temp_raw_output.txt"
TMP_CLEAN="$DIR_RESULTADOS/temp_clean_output.txt"

# Definición de archivos CSV individuales por tipo de prueba
CSV_FREQ="$DIR_RESULTADOS/test1_frecuencia.csv"
CSV_DIM="$DIR_RESULTADOS/test2_escalabilidad.csv"
CSV_SAT="$DIR_RESULTADOS/test3_saturacion.csv"
CSV_ENE="$DIR_RESULTADOS/test4_energia.csv"

# Cabecera estándar de métricas incluyendo Modo de Ruteo y Ciclos Medios por Inferencia
STD_HEADER="Fase,Escenario,Modo_Ruteo,Dim_Malla,Buffer_Iny,Buffer_Red,Muestras,Frecuencia_MHz,Spikes_Gen,Flits_Gen,Flits_Iny,Flits_Eyect,Flits_Proc,Late_Flits,Lat_Total,Lat_Buf,Lat_Red,Jitter,Throughput,Energia_uJ,Eficiencia,Perf_Absoluto,Precision_IA,Ciclos_Medios_Inf,Tiempo_Test_s"

# Inicializar los archivos CSV con sus cabeceras correspondientes
echo "$STD_HEADER" > "$CSV_FREQ"
echo "$STD_HEADER" > "$CSV_DIM"
echo "$STD_HEADER" > "$CSV_SAT"
echo "$STD_HEADER" > "$CSV_ENE"

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE PRUEBAS COMPARATIVAS: UNICAST VS MULTICAST"
echo "=========================================================="

# ------------------------------------------------------------------------------
# FUNCIONES DE EXTRACCIÓN Y LIMPIEZA
# ------------------------------------------------------------------------------

# Elimina TODOS los códigos de escape ANSI de control de terminal
limpiar_ansi() {
    sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g' "$TMP_RAW" > "$TMP_CLEAN"
}

# Extrae el valor numérico (entero o decimal) asociado a una etiqueta
extraer_valor() {
    local etiqueta="$1"
    local linea=$(grep -a "$etiqueta" "$TMP_CLEAN" | tail -n 1)

    if [ -z "$linea" ]; then
        echo "0"
        return
    fi

    linea=$(echo "$linea" | tr -d ',')
    echo "$linea" | grep -oE '[0-9]+(\.[0-9]+)?' | head -n 1
}

# Procesa el archivo temporal y añade una fila de métricas al CSV especificado
guardar_metricas() {
    local FASE="$1"
    local ESCENARIO="$2"
    local ROUTING="$3"
    local DIM="$4"
    local BUF_INY="$5"
    local BUF_RED="$6"
    local MUESTRAS="$7"
    local FREQ="$8"
    local TIEMPO_TEST="$9"
    local TARGET_CSV="${10}"

    limpiar_ansi

    # Extracción exhaustiva de contadores físicos
    local SPK=$(extraer_valor "Spikes Gen:")
    local FLITS_GEN=$(extraer_valor "Flits Generados:")
    local FLITS_INY=$(extraer_valor "Flits Inyectados:")
    local FLITS_EYE=$(extraer_valor "Flits Eyectados:")
    local FLITS_PRO=$(extraer_valor "Flits Procesados:")
    local LATE=$(extraer_valor "ALERTA:")

    # Extracción de latencias distribuidas y fluctuaciones (Jitter)
    local LAT_TOT=$(extraer_valor "Lat. Total:")
    local LAT_BUF=$(extraer_valor "Buffer Loc:")
    local LAT_RED=$(extraer_valor "Red:")
    local JIT=$(extraer_valor "Jitter (AER):")

    # Extracción de rendimiento de red y eficiencia de silicio
    local THR=$(extraer_valor "Throughput:")
    local ENG=$(extraer_valor "Energia Total:")
    local EFI=$(extraer_valor "Eficiencia:")
    local RND=$(extraer_valor "Throughput Físico:")

    # Precisión de la Red Neuronal medida en el hardware integrado
    local ACC=$(extraer_valor "Hardware (In-Memory):")

    # NUEVO: Extracción de ciclos medios por inferencia
    local CICLOS_INF=$(extraer_valor "Ciclos Medios/Inf:")

    # Validación de integridad de la simulación
    if [ -z "$LAT_TOT" ] || [ "$LAT_TOT" == "0" ]; then
        echo "$FASE,$ESCENARIO,$ROUTING,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,$FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO_TEST" >> "$TARGET_CSV"
    else
        echo "$FASE,$ESCENARIO,$ROUTING,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,$FREQ,$SPK,$FLITS_GEN,$FLITS_INY,$FLITS_EYE,$FLITS_PRO,$LATE,$LAT_TOT,$LAT_BUF,$LAT_RED,$JIT,$THR,$ENG,$EFI,$RND,$ACC,$CICLOS_INF,$TIEMPO_TEST" >> "$TARGET_CSV"
    fi
}

# Valores por defecto del simulador (acorde a nmnist_tui_sim.py)
DEF_DIM=4
DEF_INJ=1024
DEF_NET=32
DEF_FREQ=1200
DEF_SAMPLES=2
MODOS_RUTEO=("unicast" "multicast")

# ------------------------------------------------------------------------------
# TEST 1: ESPECTRO DE FRECUENCIA DE RELOJ (ESTRÉS TEMPORAL)
# ------------------------------------------------------------------------------
FRECUENCIAS=(0.1 1 10 100 1200 1600)
echo -e "\n▶ TEST 1: Impacto de la Frecuencia de Reloj (Unicast vs Multicast)..."

for FREQ in "${FRECUENCIAS[@]}"; do
    for ROUTING in "${MODOS_RUTEO[@]}"; do
        echo -n "  -> [${ROUTING^^}] Simulando a ${FREQ} MHz... "
        START_TIME=$(date +%s)

        timeout 300s python3 nmnist_tui_sim.py \
            --routing $ROUTING \
            --dim $DEF_DIM --inj_buffer $DEF_INJ --net_buffer $DEF_NET \
            --freq $FREQ --samples $DEF_SAMPLES \
            --video_name "noc_traffic_freq_${FREQ}_${ROUTING}" > "$TMP_RAW" 2>&1

        EXIT_CODE=$?
        END_TIME=$(date +%s)
        TIEMPO=$((END_TIME - START_TIME))

        if [ $EXIT_CODE -eq 0 ]; then
            guardar_metricas "1_Frecuencia" "Freq_${FREQ}MHz" $ROUTING $DEF_DIM $DEF_INJ $DEF_NET $DEF_SAMPLES $FREQ $TIEMPO "$CSV_FREQ"
            echo "OK! (Ciclos/Inf: $(extraer_valor "Ciclos Medios/Inf:") | Lat: $(extraer_valor "Lat. Total:") ciclos)"
        else
            echo "ERROR o TIMEOUT"
            echo "1_Frecuencia,Freq_${FREQ}MHz,$ROUTING,$DEF_DIM,$DEF_INJ,$DEF_NET,$DEF_SAMPLES,$FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_FREQ"
        fi
    done
done

# ------------------------------------------------------------------------------
# TEST 2: ESCALABILIDAD TOPOLÓGICA (ALIVIO DE FAN-OUT)
# ------------------------------------------------------------------------------
DIMS=(2 4 6 8)
echo -e "\n▶ TEST 2: Escalabilidad de la Malla NoC (Unicast vs Multicast)..."

for DIM in "${DIMS[@]}"; do
    for ROUTING in "${MODOS_RUTEO[@]}"; do
        echo -n "  -> [${ROUTING^^}] Simulando Malla ${DIM}x${DIM}... "
        START_TIME=$(date +%s)

        timeout 400s python3 nmnist_tui_sim.py \
            --routing $ROUTING \
            --dim $DIM --inj_buffer $DEF_INJ --net_buffer $DEF_NET \
            --freq $DEF_FREQ --samples $DEF_SAMPLES \
            --video_name "noc_traffic_dim_${DIM}_${ROUTING}" > "$TMP_RAW" 2>&1

        EXIT_CODE=$?
        END_TIME=$(date +%s)
        TIEMPO=$((END_TIME - START_TIME))

        if [ $EXIT_CODE -eq 0 ]; then
            guardar_metricas "2_Escalabilidad" "Malla_${DIM}x${DIM}" $ROUTING $DIM $DEF_INJ $DEF_NET $DEF_SAMPLES $DEF_FREQ $TIEMPO "$CSV_DIM"
            echo "OK! (Ciclos/Inf: $(extraer_valor "Ciclos Medios/Inf:") | Throughput: $(extraer_valor "Throughput:") flits/ciclo/nodo)"
        else
            echo "ERROR"
            echo "2_Escalabilidad,Malla_${DIM}x${DIM},$ROUTING,$DIM,$DEF_INJ,$DEF_NET,$DEF_SAMPLES,$DEF_FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_DIM"
        fi
    done
done

# ------------------------------------------------------------------------------
# TEST 3: SATURACIÓN DEL BUFFER DE INYECCIÓN (BACKPRESSURE)
# ------------------------------------------------------------------------------
TEST_INJ=64
TEST_NET=16
TEST_FREQ=800
VOLUMENES_SAMPLES=(1 3 5 10 20 40)

echo -e "\n▶ TEST 3: Buffer Backpressure (Unicast vs Multicast)..."
echo "     [Configuración de Estrés: Inj_Buf=${TEST_INJ}, Net_Buf=${TEST_NET}, Freq=${TEST_FREQ}MHz]"

for VOL in "${VOLUMENES_SAMPLES[@]}"; do
    for ROUTING in "${MODOS_RUTEO[@]}"; do
        echo -n "  -> [${ROUTING^^}] Procesando volumen de $VOL muestras... "
        START_TIME=$(date +%s)

        timeout 600s python3 nmnist_tui_sim.py \
            --routing $ROUTING \
            --dim $DEF_DIM --inj_buffer $TEST_INJ --net_buffer $TEST_NET \
            --freq $TEST_FREQ --samples $VOL \
            --video_name "noc_traffic_sat_${VOL}_${ROUTING}" > "$TMP_RAW" 2>&1

        EXIT_CODE=$?
        END_TIME=$(date +%s)
        TIEMPO=$((END_TIME - START_TIME))

        if [ $EXIT_CODE -eq 0 ]; then
            guardar_metricas "3_Saturacion" "Samples_${VOL}" $ROUTING $DEF_DIM $TEST_INJ $TEST_NET $VOL $TEST_FREQ $TIEMPO "$CSV_SAT"
            echo "OK! (Ciclos/Inf: $(extraer_valor "Ciclos Medios/Inf:") | Late_Flits: $(extraer_valor "ALERTA:"))"
        else
            echo "ERROR"
            echo "3_Saturacion,Samples_${VOL},$ROUTING,$DEF_DIM,$TEST_INJ,$TEST_NET,$VOL,$TEST_FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_SAT"
        fi
    done
done

# ------------------------------------------------------------------------------
# TEST 4: EFICIENCIA ENERGÉTICA BAJO CARGA VARIABLE (ESTÁTICA VS DINÁMICA)
# ------------------------------------------------------------------------------
echo -e "\n▶ TEST 4: Perfiles de Eficiencia Energética (Unicast vs Multicast)..."

ESCENARIOS_ENERGIA=(
    "Baja_Carga 1 1600"
    "Media_Carga 5 1200"
    "Alta_Carga 15 600"
)

for ESC in "${ESCENARIOS_ENERGIA[@]}"; do
    read -r NAME SMP FRQ <<< "$ESC"
    for ROUTING in "${MODOS_RUTEO[@]}"; do
        echo -n "  -> [${ROUTING^^}] Perfil: $NAME ($SMP muestras @ $FRQ MHz)... "
        START_TIME=$(date +%s)

        timeout 500s python3 nmnist_tui_sim.py \
            --routing $ROUTING \
            --dim $DEF_DIM --inj_buffer $DEF_INJ --net_buffer $DEF_NET \
            --freq $FRQ --samples $SMP \
            --video_name "noc_traffic_energy_${NAME}_${ROUTING}" > "$TMP_RAW" 2>&1

        EXIT_CODE=$?
        END_TIME=$(date +%s)
        TIEMPO=$((END_TIME - START_TIME))

        if [ $EXIT_CODE -eq 0 ]; then
            guardar_metricas "4_Energia" "$NAME" $ROUTING $DEF_DIM $DEF_INJ $DEF_NET $SMP $FRQ $TIEMPO "$CSV_ENE"
            echo "OK! (Ciclos/Inf: $(extraer_valor "Ciclos Medios/Inf:") | Energía: $(extraer_valor "Energia Total:") uJ)"
        else
            echo "ERROR"
            echo "4_Energia,$NAME,$ROUTING,$DEF_DIM,$DEF_INJ,$DEF_NET,$SMP,$FRQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_ENE"
        fi
    done
done

# ------------------------------------------------------------------------------
# LIMPIEZA FINAL
# ------------------------------------------------------------------------------
rm -f "$TMP_RAW" "$TMP_CLEAN"

echo -e "\n=========================================================="
echo "🎉 ¡BATERÍA DE SIMULACIONES COMPARATIVAS COMPLETADA CON ÉXITO! 🎉"
echo "Todos los CSVs han sido generados con 'Ciclos_Medios_Inf' en: ./$DIR_RESULTADOS"
echo "=========================================================="
