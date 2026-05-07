#!/bin/bash

# ==========================================
# CONFIGURACIÓN INICIAL
# ==========================================
TMP_FILE="temp_sim_output.txt"
DIR_RESULTADOS="resultados_validacion"

# Crear carpeta de resultados si no existe
mkdir -p $DIR_RESULTADOS

echo "=========================================================="
echo "🚀 INICIANDO BATERÍA DE VALIDACIÓN NoC-AER SIMULATOR"
echo "=========================================================="
echo "Los resultados se guardarán en la carpeta: ./$DIR_RESULTADOS/"
echo "Nota: Este proceso puede tardar varios minutos. Ve a por un café ☕"
echo ""

# Función auxiliar para extraer datos usando regex y awk
extraer_metrica() {
    local metrica=$1
    local columna=$2
    grep "$metrica" $TMP_FILE | awk -v col="$columna" '{print $col}' | tr -d ',' | tr -d '%'
}

# ==========================================
# FASE 1: REGRESIÓN (DETERMINISMO)
# ==========================================
echo "▶ FASE 1: Comprobando Determinismo (3 ejecuciones idénticas)..."
echo "Ejecutando configuración base: dim=4, buffer=4096, samples=2"

for i in {1..3}; do
    python3 nmnist_tui_sim.py --dim 4 --epochs 1 --samples 2 --buffer 4096 > $TMP_FILE 2>&1
    
    LAT=$(extraer_metrica "Latencia Med:" 4)
    SPIKES=$(extraer_metrica "Spikes Gen:" 4)
    ENG=$(extraer_metrica "Energia Total:" 4)
    
    echo "  Ejecución $i -> Spikes: $SPIKES | Latencia: $LAT | Energía: $ENG"
done
echo "✅ Si los 3 números de arriba son idénticos, el determinismo funciona."
echo "----------------------------------------------------------"

# ==========================================
# FASE 2: ESTRÉS Y CONGESTIÓN (BÚFER)
# ==========================================
CSV_BUFFER="$DIR_RESULTADOS/test_2_congestión_buffer.csv"
echo "Buffer,Latencia_Media,Jitter,Rendimiento_flits_s,Eficiencia_flits_uJ" > $CSV_BUFFER

BUFFERS=(4096 1024 256 64 16 8 4)

echo "▶ FASE 2: Prueba de Contrapresión (Reduciendo Buffer)..."
for BUF in "${BUFFERS[@]}"; do
    echo -n "  Simulando Buffer $BUF... "
    python3 nmnist_tui_sim.py --dim 4 --samples 5 --buffer $BUF > $TMP_FILE 2>&1
    
    LAT=$(extraer_metrica "Latencia Med:" 4)
    JIT=$(extraer_metrica "Jitter (AER):" 4)
    RND=$(extraer_metrica "Rendimiento:" 3)
    EFI=$(extraer_metrica "Eficiencia:" 3)
    
    if [ -z "$LAT" ]; then echo "ERROR"; else echo "OK! (Lat: $LAT ciclos)"; fi
    echo "$BUF,$LAT,$JIT,$RND,$EFI" >> $CSV_BUFFER
done
echo "📄 Guardado en: $CSV_BUFFER"
echo "----------------------------------------------------------"

# ==========================================
# FASE 3: ESCALABILIDAD (TOPOLOGÍA DE RED)
# ==========================================
CSV_DIM="$DIR_RESULTADOS/test_3_escalabilidad_dim.csv"
echo "Dimension,Nodos_Totales,Latencia_Media,Energia_Total_uJ,Eficiencia_flits_uJ" > $CSV_DIM

DIMS=(2 4 8) # 8x8 (64 nodos) tardará un poco más

echo "▶ FASE 3: Prueba de Topología (Aumentando tamaño de Malla)..."
for DIM in "${DIMS[@]}"; do
    echo -n "  Simulando Malla ${DIM}x${DIM}... "
    # Usamos buffer suficiente para que no haya congestión y medir solo latencia por distancia
    python3 nmnist_tui_sim.py --dim $DIM --samples 2 --buffer 512 > $TMP_FILE 2>&1
    
    NODOS=$((DIM * DIM))
    LAT=$(extraer_metrica "Latencia Med:" 4)
    ENG=$(extraer_metrica "Energia Total:" 4)
    EFI=$(extraer_metrica "Eficiencia:" 3)
    
    if [ -z "$LAT" ]; then echo "ERROR"; else echo "OK! (Lat: $LAT ciclos)"; fi
    echo "$DIM,$NODOS,$LAT,$ENG,$EFI" >> $CSV_DIM
done
echo "📄 Guardado en: $CSV_DIM"
echo "----------------------------------------------------------"

# ==========================================
# FASE 4: CARGA DE TRABAJO IA
# ==========================================
CSV_IA="$DIR_RESULTADOS/test_4_carga_ia.csv"
echo "Epocas,Iteraciones,Samples,Precision_IA,Spikes_Generados,Tiempo_Ejecucion_s" > $CSV_IA

# Arrays emparejados (Epocas, Iters, Samples)
EPOCAS=(1 2 4)
ITERS=(10 20 40)
SAMPLES=(1 5 10)

echo "▶ FASE 4: Prueba de Carga de Trabajo e IA..."
for i in "${!EPOCAS[@]}"; do
    E=${EPOCAS[$i]}
    IT=${ITERS[$i]}
    S=${SAMPLES[$i]}
    
    echo -n "  Entrenando (E:$E, Iters:$IT, Muestras:$S)... "
    
    # Medimos cuánto tarda en tiempo real de tu PC
    START_TIME=$(date +%s)
    python3 nmnist_tui_sim.py --dim 4 --epochs $E --iters $IT --samples $S --buffer 4096 > $TMP_FILE 2>&1
    END_TIME=$(date +%s)
    TIEMPO=$((END_TIME - START_TIME))
    
    ACC=$(extraer_metrica "PRECISION IA FINAL:" 4)
    SPK=$(extraer_metrica "Spikes Gen:" 4)
    
    if [ -z "$ACC" ]; then echo "ERROR"; else echo "OK! (Precisión: $ACC%)"; fi
    echo "$E,$IT,$S,$ACC,$SPK,$TIEMPO" >> $CSV_IA
done
echo "📄 Guardado en: $CSV_IA"
echo "----------------------------------------------------------"

# Limpieza final
rm -f $TMP_FILE

echo "🎉 ¡VALIDACIÓN COMPLETADA! 🎉"
echo "Todos los datos listos en la carpeta ./$DIR_RESULTADOS/"