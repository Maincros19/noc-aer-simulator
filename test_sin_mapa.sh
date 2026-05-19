#!/bin/bash

# ==========================================
# CONFIGURACIÓN INICIAL
# ==========================================
TMP_FILE="temp_sim_output.txt"
DIR_RESULTADOS="resultados_validacion"

mkdir -p $DIR_RESULTADOS

CSV_F1="$DIR_RESULTADOS/fase1_regresion.csv"
CSV_F2="$DIR_RESULTADOS/fase2_congestion_estres.csv"
CSV_F3="$DIR_RESULTADOS/fase3_escalabilidad.csv"
CSV_F4="$DIR_RESULTADOS/fase4_impacto_datos.csv"
CSV_F5="$DIR_RESULTADOS/fase5_asimetria.csv"
CSV_F6="$DIR_RESULTADOS/fase6_perfil_ia.csv"

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE VALIDACIÓN AVANZADA NoC-AER"
echo "=========================================================="
echo "Los resultados se guardarán en: ./$DIR_RESULTADOS"
echo ""

# Cabecera actualizada con Buffer_Iny y Buffer_Red separados
STD_HEADER="Fase,Escenario,Dim_Malla,Buffer_Iny,Buffer_Red,Muestras,Spikes_Gen,Flits_Gen,Flits_Iny,Flits_Eyect,Flits_Proc,Lat_Total,Lat_RAM,Lat_Buf,Lat_Red,Jitter,Throughput,Energia_uJ,Eficiencia,Perf_Absoluto,Precision_IA,Tiempo_Test_s"

for file in "$CSV_F1" "$CSV_F2" "$CSV_F3" "$CSV_F4" "$CSV_F5" "$CSV_F6"; do
    echo "$STD_HEADER" > "$file"
done

# ==========================================
# FUNCIONES DE EXTRACCIÓN Y GUARDADO
# ==========================================

extraer_metrica() {
    grep "$1" "$TMP_FILE" | awk -v col="$2" '{print $col}' | tr -d ',' | tr -d '%'
}

extraer_rendimiento() {
    grep -E "Rendimiento:|Throughput Físico:|Tasa Absoluta:" "$TMP_FILE" | awk '{print $(NF-1)}' | tr -d ','
}



# Modifica la función guardar_metricas en run_tests.sh:
guardar_metricas() {
    local FASE=$1 ESCENARIO=$2 DIM=$3 BUF_INY=$4 BUF_RED=$5 MUESTRAS=$6 TIEMPO_TEST=$7 TARGET_CSV=$8

    SPK=$(extraer_metrica "Spikes Gen:" 4)
    FLITS_GEN=$(extraer_metrica "Flits Generados:" 4)
    FLITS_INY=$(extraer_metrica "Flits Inyectados:" 4)
    FLITS_EYE=$(extraer_metrica "Flits Eyectados:" 4)
    FLITS_PRO=$(extraer_metrica "Flits Procesados:" 4)

    LAT_TOT=$(extraer_metrica "Lat. Total:" 4)
    LAT_RAM=$(extraer_metrica "Cola RAM:" 4)      # Extrae la latencia de software
    LAT_BUF=$(extraer_metrica "Buffer Loc:" 4)    # Extrae la latencia de hardware
    LAT_RED=$(extraer_metrica "Red:" 4)

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
# FASE 1: REGRESIÓN (DETERMINISMO EN ZERO-LOAD)
# Default: dim=4, epochs=1, samples=1, freq=1200
# ==========================================
echo "▶ FASE 1: Comprobando Determinismo (1200 MHz)..."
for i in {1..3}; do
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --inj_buffer 4096 --net_buffer 4096 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)

    LAT=$(extraer_metrica "Lat. Total:" 4)
    echo "  Ejecución $i -> Latencia: $LAT"
    # Pasamos 4096 4096
    guardar_metricas "1_Regresion" "Determinismo_$i" 4 4096 4096 1 $((END_TIME - START_TIME)) "$CSV_F1"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 2: ESTRÉS Y CONGESTIÓN (RELOJ AHOGADO A 15 MHz)
# Default: dim=4
# ==========================================
BUFFERS=(1024 256 64 16)
echo "▶ FASE 2: Prueba de Contrapresión (Estrés a 15 MHz)..."
for BUF in "${BUFFERS[@]}"; do
    echo -n "  Simulando Buffers a $BUF... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --samples 2 --inj_buffer $BUF --net_buffer $BUF --freq 15 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)

    echo "OK! (Lat: $(extraer_metrica "Lat. Total:" 4))"
    # Pasamos $BUF $BUF
    guardar_metricas "2_Congestion" "Stress_Buf_$BUF" 4 $BUF $BUF 2 $((END_TIME - START_TIME)) "$CSV_F2"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 3: ESCALABILIDAD TOPOLÓGICA (1200 MHz)
# Default: freq=1200
# ==========================================
DIMS=(2 4 6)
echo "▶ FASE 3: Escalabilidad (Aumentando Malla)..."
for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM}... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim $DIM --samples 2 --inj_buffer 512 --net_buffer 512 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)

    echo "OK! (Lat: $(extraer_metrica "Lat. Total:" 4))"
    # Pasamos 512 512
    guardar_metricas "3_Escalabilidad" "Malla_${DIM}x${DIM}" $DIM 512 512 2 $((END_TIME - START_TIME)) "$CSV_F3"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 4: IMPACTO DEL VOLUMEN DE DATOS (1200 MHz)
# Default: dim=4, epochs=1, freq=1200, inj_buffer=1024
# ==========================================
SAMPLES_ARRAY=(1 5 10)
echo "▶ FASE 4: Impacto del Volumen de Muestras..."
for S in "${SAMPLES_ARRAY[@]}"; do
    echo -n "  Inyectando $S muestras... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --iters 10 --samples $S --net_buffer 1024 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)

    echo "OK! (Flits Procesados: $(extraer_metrica "Flits Procesados:" 4))"
    # Pasamos 1024 1024 (ya que inj_buffer es 1024 por defecto)
    guardar_metricas "4_Impacto_Datos" "Muestras_$S" 4 1024 1024 $S $((END_TIME - START_TIME)) "$CSV_F4"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 5: ASIMETRÍA DE BUFFERS (ESTRÉS A 15 MHz)
# Default: dim=4
# ==========================================
echo "▶ FASE 5: Asimetría de Buffers (Inyección vs Red)..."
CONFIGS_ASIM=("4096:16" "16:4096" "256:32" "32:256")
for CONF in "${CONFIGS_ASIM[@]}"; do
    INJ="${CONF%%:*}"
    NET="${CONF##*:}"
    echo -n "  Simulando Inj=$INJ / Net=$NET... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --samples 2 --inj_buffer $INJ --net_buffer $NET --freq 15 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)

    echo "OK! (Lat: $(extraer_metrica "Lat. Total:" 4))"
    # Pasamos $INJ $NET
    guardar_metricas "5_Asimetria" "Stress_Inj${INJ}_Net${NET}" 4 $INJ $NET 2 $((END_TIME - START_TIME)) "$CSV_F5"
done
echo "----------------------------------------------------------"

# ==========================================
# FASE 6: IMPACTO DEL ENTRENAMIENTO IA (1200 MHz)
# Default: dim=4, epochs=1, freq=1200, inj_buffer=1024
# ==========================================
ITERS_ARRAY=(5 20 50)
echo "▶ FASE 6: Perfil de Tráfico por Madurez SNN..."
for ITER in "${ITERS_ARRAY[@]}"; do
    echo -n "  Entrenando $ITER iteraciones... "
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --iters $ITER --samples 2 --net_buffer 1024 > "$TMP_FILE" 2>&1
    END_TIME=$(date +%s)

    echo "OK! (Acc: $(extraer_metrica "PRECISION IA FINAL:" 4)%)"
    # Pasamos 1024 1024 (ya que inj_buffer es 1024 por defecto)
    guardar_metricas "6_Perfil_IA" "Iters_$ITER" 4 1024 1024 2 $((END_TIME - START_TIME)) "$CSV_F6"
done
echo "----------------------------------------------------------"

rm -f "$TMP_FILE"
echo "🎉 ¡VALIDACIÓN INTEGRAL COMPLETADA! 🎉"
