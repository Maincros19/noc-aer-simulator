#!/bin/bash

# ==============================================================================
# NoC-AER EXHAUSTIVE VALIDATION AND PERFORMANCE SUITE
# ==============================================================================
# Autor: Marcos Hernández Sánchez
# Descripción: Automatiza la ejecución de pruebas exhaustivas para el simulador NoC-AER.
#              Modifica un parámetro de forma aislada manteniendo el resto en sus
#              valores por defecto para un análisis científico riguroso.
#              Corrige los errores de extracción ANSI y manejo de comas en miles.
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

# Cabecera estándar de métricas de hardware y precisión de IA
STD_HEADER="Fase,Escenario,Dim_Malla,Buffer_Iny,Buffer_Red,Muestras,Frecuencia_MHz,Spikes_Gen,Flits_Gen,Flits_Iny,Flits_Eyect,Flits_Proc,Late_Flits,Lat_Total,Lat_Buf,Lat_Red,Jitter,Throughput,Energia_uJ,Eficiencia,Perf_Absoluto,Precision_IA,Tiempo_Test_s"

# Inicializar los archivos CSV con sus cabeceras correspondientes
echo "$STD_HEADER" > "$CSV_FREQ"
echo "$STD_HEADER" > "$CSV_DIM"
echo "$STD_HEADER" > "$CSV_SAT"
echo "$STD_HEADER" > "$CSV_ENE"

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE PRUEBAS EXHAUSTIVAS: NoC-AER"
echo "=========================================================="

# ------------------------------------------------------------------------------
# FUNCIONES DE EXTRACCIÓN Y LIMPIEZA
# ------------------------------------------------------------------------------

# Elimina TODOS los códigos de escape ANSI de control de terminal
limpiar_ansi() {
    # El patrón \x1B\[[0-9;]*[A-Za-z] elimina de forma limpia toda secuencia de escape ANSI
    sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g' "$TMP_RAW" > "$TMP_CLEAN"
}

# Extrae el valor numérico (entero o decimal) asociado a una etiqueta
extraer_valor() {
    local etiqueta="$1"

    # 1. Buscamos la línea correspondiente (tomamos la última ocurrencia, que es el panel de cierre)
    local linea=$(grep -a "$etiqueta" "$TMP_CLEAN" | tail -n 1)

    # Si la etiqueta no existe en el texto, devolvemos 0 por defecto
    if [ -z "$linea" ]; then
        echo "0"
        return
    fi

    # 2. Eliminamos las comas de formato de miles para evitar corromper las columnas del CSV
    linea=$(echo "$linea" | tr -d ',')

    # 3. Extraemos el primer número entero o decimal que siga a la etiqueta
    echo "$linea" | grep -oE '[0-9]+(\.[0-9]+)?' | head -n 1
}

# Procesa el archivo temporal y añade una fila de métricas al CSV especificado
guardar_metricas() {
    local FASE="$1"
    local ESCENARIO="$2"
    local DIM="$3"
    local BUF_INY="$4"
    local BUF_RED="$5"
    local MUESTRAS="$6"
    local FREQ="$7"
    local TIEMPO_TEST="$8"
    local TARGET_CSV="$9"

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

    # Validación de integridad de la simulación
    if [ -z "$LAT_TOT" ] || [ "$LAT_TOT" == "0" ]; then
        # En caso de fallo catastrófico o timeout, registrar fila vacía con NaNs
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,$FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO_TEST" >> "$TARGET_CSV"
    else
        # Escritura limpia en el CSV destino
        echo "$FASE,$ESCENARIO,$DIM,$BUF_INY,$BUF_RED,$MUESTRAS,$FREQ,$SPK,$FLITS_GEN,$FLITS_INY,$FLITS_EYE,$FLITS_PRO,$LATE,$LAT_TOT,$LAT_BUF,$LAT_RED,$JIT,$THR,$ENG,$EFI,$RND,$ACC,$TIEMPO_TEST" >> "$TARGET_CSV"
    fi
}

# Valores por defecto del simulador (acorde a nmnist_tui_sim.py)
DEF_DIM=4
DEF_INJ=1024
DEF_NET=32
DEF_FREQ=1200
DEF_SAMPLES=2

# ------------------------------------------------------------------------------
# TEST 1: ESPECTRO DE FRECUENCIA DE RELOJ (ESTRÉS TEMPORAL)
# ------------------------------------------------------------------------------
FRECUENCIAS=(0.1 1 10 100 1200 1600)
echo -e "\n▶ TEST 1: Impacto de la Frecuencia de Reloj..."

for FREQ in "${FRECUENCIAS[@]}"; do
    echo -n "  -> Simulando a ${FREQ} MHz (Resto por defecto)... "
    START_TIME=$(date +%s)

    # Ejecución controlada con timeout de seguridad
    timeout 300s python3 nmnist_tui_sim.py \
        --dim $DEF_DIM --inj_buffer $DEF_INJ --net_buffer $DEF_NET \
        --freq $FREQ --samples $DEF_SAMPLES > "$TMP_RAW" 2>&1

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    if [ $EXIT_CODE -eq 0 ]; then
        guardar_metricas "1_Frecuencia" "Freq_${FREQ}MHz" $DEF_DIM $DEF_INJ $DEF_NET $DEF_SAMPLES $FREQ $TIEMPO "$CSV_FREQ"
        echo "OK! (Lat: $(extraer_valor "Lat. Total:") ciclos | Acc: $(extraer_valor "Hardware (In-Memory):")% | Late: $(extraer_valor "ALERTA:"))"
    else
        echo "ERROR o TIMEOUT (Código $EXIT_CODE)"
        echo "1_Frecuencia,Freq_${FREQ}MHz,$DEF_DIM,$DEF_INJ,$DEF_NET,$DEF_SAMPLES,$FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_FREQ"
    fi
done

# ------------------------------------------------------------------------------
# TEST 2: ESCALABILIDAD TOPOLÓGICA (ALIVIO DE FAN-OUT)
# ------------------------------------------------------------------------------
DIMS=(2 4 6 8)
echo -e "\n▶ TEST 2: Escalabilidad de la Malla NoC..."

for DIM in "${DIMS[@]}"; do
    echo -n "  -> Simulando Malla ${DIM}x${DIM} (Resto por defecto)... "
    START_TIME=$(date +%s)

    timeout 400s python3 nmnist_tui_sim.py \
        --dim $DIM --inj_buffer $DEF_INJ --net_buffer $DEF_NET \
        --freq $DEF_FREQ --samples $DEF_SAMPLES > "$TMP_RAW" 2>&1

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    if [ $EXIT_CODE -eq 0 ]; then
        guardar_metricas "2_Escalabilidad" "Malla_${DIM}x${DIM}" $DIM $DEF_INJ $DEF_NET $DEF_SAMPLES $DEF_FREQ $TIEMPO "$CSV_DIM"
        echo "OK! (Lat_Red: $(extraer_valor "Red:") ciclos | Throughput: $(extraer_valor "Throughput:") flits/ciclo/nodo)"
    else
        echo "ERROR"
        echo "2_Escalabilidad,Malla_${DIM}x${DIM},$DIM,$DEF_INJ,$DEF_NET,$DEF_SAMPLES,$DEF_FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_DIM"
    fi
done

# ------------------------------------------------------------------------------
# TEST 3: SATURACIÓN DEL BUFFER DE INYECCIÓN (BACKPRESSURE)
# ------------------------------------------------------------------------------
# Restringimos drásticamente la capacidad de la NoC para forzar cuellos de botella
TEST_INJ=64
TEST_NET=16
TEST_FREQ=800
VOLUMENES_SAMPLES=(1 3 5 10 20 40)

echo -e "\n▶ TEST 3: Saturación de Buffer y Fenómeno de Backpressure..."
echo "     [Configuración de Estrés: Inj_Buf=${TEST_INJ}, Net_Buf=${TEST_NET}, Freq=${TEST_FREQ}MHz]"

for VOL in "${VOLUMENES_SAMPLES[@]}"; do
    echo -n "  -> Procesando volumen de $VOL muestras... "
    START_TIME=$(date +%s)

    timeout 600s python3 nmnist_tui_sim.py \
        --dim $DEF_DIM --inj_buffer $TEST_INJ --net_buffer $TEST_NET \
        --freq $TEST_FREQ --samples $VOL > "$TMP_RAW" 2>&1

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    if [ $EXIT_CODE -eq 0 ]; then
        guardar_metricas "3_Saturacion" "Samples_${VOL}" $DEF_DIM $TEST_INJ $TEST_NET $VOL $TEST_FREQ $TIEMPO "$CSV_SAT"
        echo "OK! (Flits_Gen: $(extraer_valor "Flits Generados:") | Late_Flits: $(extraer_valor "ALERTA:"))"
    else
        echo "ERROR"
        echo "3_Saturacion,Samples_${VOL},$DEF_DIM,$TEST_INJ,$TEST_NET,$VOL,$TEST_FREQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_SAT"
    fi
done

# ------------------------------------------------------------------------------
# TEST 4: EFICIENCIA ENERGÉTICA BAJO CARGA VARIABLE (ESTÁTICA VS DINÁMICA)
# ------------------------------------------------------------------------------
echo -e "\n▶ TEST 4: Perfiles de Eficiencia Energética bajo Carga Variable..."

# Matriz: Nombre del Escenario | Muestras | Frecuencia
ESCENARIOS_ENERGIA=(
    "Baja_Carga 1 1600"
    "Media_Carga 5 1200"
    "Alta_Carga 15 600"
)

for ESC in "${ESCENARIOS_ENERGIA[@]}"; do
    read -r NAME SMP FRQ <<< "$ESC"
    echo -n "  -> Ejecutando perfil: $NAME ($SMP muestras @ $FRQ MHz)... "
    START_TIME=$(date +%s)

    timeout 500s python3 nmnist_tui_sim.py \
        --dim $DEF_DIM --inj_buffer $DEF_INJ --net_buffer $DEF_NET \
        --freq $FRQ --samples $SMP > "$TMP_RAW" 2>&1

    EXIT_CODE=$?
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))

    if [ $EXIT_CODE -eq 0 ]; then
        guardar_metricas "4_Energia" "$NAME" $DEF_DIM $DEF_INJ $DEF_NET $SMP $FRQ $TIEMPO "$CSV_ENE"
        echo "OK! (Energía: $(extraer_valor "Energia Total:") uJ | Eficiencia: $(extraer_valor "Eficiencia:") flits/uJ)"
    else
        echo "ERROR"
        echo "4_Energia,$NAME,$DEF_DIM,$DEF_INJ,$DEF_NET,$SMP,$FRQ,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,$TIEMPO" >> "$CSV_ENE"
    fi
done

# ------------------------------------------------------------------------------
# LIMPIEZA FINAL
# ------------------------------------------------------------------------------
rm -f "$TMP_RAW" "$TMP_CLEAN"

echo -e "\n=========================================================="
echo "🎉 ¡BATERÍA DE SIMULACIONES COMPLETADA CON ÉXITO! 🎉"
echo "Todos los CSVs han sido generados en: ./$DIR_RESULTADOS"
echo "=========================================================="
