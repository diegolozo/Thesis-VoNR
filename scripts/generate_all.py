import csv
import os

# ============ CONFIGURACIÓN MANUAL ============
# CAMBIA ESTE NÚMERO SEGÚN EL ESCENARIO QUE QUIERAS PROCESAR
SCENE_NUM = 18  # <--- Cambia aquí el número (1, 2, 3, etc.)
# =============================================

def encontrar_archivos(scene_num):
    """Encuentra los 5 archivos para un número de escenario dado"""

    archivos = {
        'A_audio': f'baresip_log/done/scene{scene_num}A_audio.csv',
        'A_video': f'baresip_log/done/scene{scene_num}A_video.csv',
        'B_audio': f'baresip_log/done/scene{scene_num}B_audio.csv',
        'B_video': f'baresip_log/done/scene{scene_num}B_video.csv',
        'delays': f'delays/done/delayscene_{scene_num}.csv'
    }
        
    # Verificar que existan
    for key, path in archivos.items():
        if not os.path.exists(path):
            print(f"⚠️ No existe: {path}")
            return None
    return archivos

def leer_csv(nombre_archivo):
    """Lee un CSV y devuelve diccionario key=call_num, value=fila"""
    datos = {}
    with open(nombre_archivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            call_num = int(row['call_num'])
            datos[call_num] = row
    return datos

def calcular_packet_loss(lost_tx, packets_tx):
    """Calcula Packet Loss % = (lost_tx / packets_tx) * 100"""
    if not lost_tx or not packets_tx:
        return 0
    try:
        lost = int(lost_tx)
        packets = int(packets_tx)
        if packets > 0:
            return round((lost / packets) * 100, 3)
        return 0
    except:
        return 0

def guardar_csv(nombre_archivo, datos, columnas):
    """Guarda un CSV con los datos proporcionados"""
    with open(nombre_archivo, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columnas, delimiter=';')
        writer.writeheader()
        writer.writerows(datos)
    print(f"✅ Guardado: {nombre_archivo}")

def procesar_escenario(scene_num):
    """Procesa un escenario completo"""
    print(f"\n{'='*60}")
    print(f"📁 Procesando Escenario {scene_num}")
    print('='*60)
    
    # Encontrar archivos
    archivos = encontrar_archivos(scene_num)
    if not archivos:
        print(f"❌ No se encontraron archivos para escenario {scene_num}")
        return None
    
    # Cargar datos
    print("📂 Cargando archivos...")
    data_A_audio = leer_csv(archivos['A_audio'])
    data_A_video = leer_csv(archivos['A_video'])
    data_B_audio = leer_csv(archivos['B_audio'])
    data_B_video = leer_csv(archivos['B_video'])
    data_delays = leer_csv(archivos['delays'])
    
    print(f"  Audio A: {len(data_A_audio)} llamadas")
    print(f"  Video A: {len(data_A_video)} llamadas")
    print(f"  Audio B: {len(data_B_audio)} llamadas")
    print(f"  Video B: {len(data_B_video)} llamadas")
    print(f"  Delays: {len(data_delays)} llamadas")
    
    # =========================================================
    # 1. AUDIO A → B
    # =========================================================
    print("\n📊 Procesando Audio A → B...")
    audio_AB = []
    for call_num in sorted(data_A_audio.keys()):
        if call_num in data_B_audio and call_num in data_delays:
            row_A = data_A_audio[call_num]
            row_B = data_B_audio[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_A.get('packets_tx', '')
            lost_tx = row_A.get('lost_tx', '')
            packet_loss_pct = calcular_packet_loss(lost_tx, packets_tx)
            
            audio_AB.append({
                'call_num': call_num,
                'packets_sent': packets_tx,
                'packet_loss_%': packet_loss_pct,
                'jitter_ms': row_B.get('jitter_rx', ''),  # Jitter de Baresip (Rx)
                'bitrate_kbps': row_A.get('bitrate_tx', ''),
                'delay_network_ms': row_delay.get('audio_delay_A_B_ms', ''),
                'jitter_network_ms': row_delay.get('audio_jitter_A_B_ms', '')
            })
            print(f"  Call {call_num}: TX={packets_tx}, Loss%={packet_loss_pct}%, Jitter(Baresip)={row_B.get('jitter_rx', '')}ms, Bitrate={row_A.get('bitrate_tx', '')}kbps, Delay(Net)={row_delay.get('audio_delay_A_B_ms', '')}ms, Jitter(Net)={row_delay.get('audio_jitter_A_B_ms', '')}ms")
    
    print(f"  Total: {len(audio_AB)} llamadas")
    
    # =========================================================
    # 2. VIDEO A → B
    # =========================================================
    print("\n📊 Procesando Video A → B...")
    video_AB = []
    for call_num in sorted(data_A_video.keys()):
        if call_num in data_B_video and call_num in data_delays:
            row_A = data_A_video[call_num]
            row_B = data_B_video[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_A.get('packets_tx', '')
            lost_tx = row_A.get('lost_tx', '')
            packet_loss_pct = calcular_packet_loss(lost_tx, packets_tx)
            
            video_AB.append({
                'call_num': call_num,
                'packets_sent': packets_tx,
                'packet_loss_%': packet_loss_pct,
                'jitter_ms': row_B.get('jitter_rx', ''),
                'bitrate_kbps': row_A.get('bitrate_tx', ''),
                'delay_network_ms': row_delay.get('video_delay_A_B_ms', ''),
                'jitter_network_ms': row_delay.get('video_jitter_A_B_ms', '')
            })
            print(f"  Call {call_num}: TX={packets_tx}, Loss%={packet_loss_pct}%, Jitter(Baresip)={row_B.get('jitter_rx', '')}ms, Bitrate={row_A.get('bitrate_tx', '')}kbps, Delay(Net)={row_delay.get('video_delay_A_B_ms', '')}ms, Jitter(Net)={row_delay.get('video_jitter_A_B_ms', '')}ms")
    
    print(f"  Total: {len(video_AB)} llamadas")
    
    # =========================================================
    # 3. AUDIO B → A
    # =========================================================
    print("\n📊 Procesando Audio B → A...")
    audio_BA = []
    for call_num in sorted(data_B_audio.keys()):
        if call_num in data_A_audio and call_num in data_delays:
            row_B = data_B_audio[call_num]
            row_A = data_A_audio[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_B.get('packets_tx', '')
            lost_tx = row_B.get('lost_tx', '')
            packet_loss_pct = calcular_packet_loss(lost_tx, packets_tx)
            
            audio_BA.append({
                'call_num': call_num,
                'packets_sent': packets_tx,
                'packet_loss_%': packet_loss_pct,
                'jitter_ms': row_A.get('jitter_rx', ''),
                'bitrate_kbps': row_B.get('bitrate_tx', ''),
                'delay_network_ms': row_delay.get('audio_delay_B_A_ms', ''),
                'jitter_network_ms': row_delay.get('audio_jitter_B_A_ms', '')
            })
            print(f"  Call {call_num}: TX={packets_tx}, Loss%={packet_loss_pct}%, Jitter(Baresip)={row_A.get('jitter_rx', '')}ms, Bitrate={row_B.get('bitrate_tx', '')}kbps, Delay(Net)={row_delay.get('audio_delay_B_A_ms', '')}ms, Jitter(Net)={row_delay.get('audio_jitter_B_A_ms', '')}ms")
    
    print(f"  Total: {len(audio_BA)} llamadas")
    
    # =========================================================
    # 4. VIDEO B → A
    # =========================================================
    print("\n📊 Procesando Video B → A...")
    video_BA = []
    for call_num in sorted(data_B_video.keys()):
        if call_num in data_A_video and call_num in data_delays:
            row_B = data_B_video[call_num]
            row_A = data_A_video[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_B.get('packets_tx', '')
            lost_tx = row_B.get('lost_tx', '')
            packet_loss_pct = calcular_packet_loss(lost_tx, packets_tx)
            
            video_BA.append({
                'call_num': call_num,
                'packets_sent': packets_tx,
                'packet_loss_%': packet_loss_pct,
                'jitter_ms': row_A.get('jitter_rx', ''),
                'bitrate_kbps': row_B.get('bitrate_tx', ''),
                'delay_network_ms': row_delay.get('video_delay_B_A_ms', ''),
                'jitter_network_ms': row_delay.get('video_jitter_B_A_ms', '')
            })
            print(f"  Call {call_num}: TX={packets_tx}, Loss%={packet_loss_pct}%, Jitter(Baresip)={row_A.get('jitter_rx', '')}ms, Bitrate={row_B.get('bitrate_tx', '')}kbps, Delay(Net)={row_delay.get('video_delay_B_A_ms', '')}ms, Jitter(Net)={row_delay.get('video_jitter_B_A_ms', '')}ms")
    
    print(f"  Total: {len(video_BA)} llamadas")
    
    # =========================================================
    # GUARDAR CSVs
    # =========================================================
    print("\n💾 Guardando archivos...")
    
    columnas = ['call_num', 'packets_sent', 'packet_loss_%', 'jitter_ms', 'bitrate_kbps', 'delay_network_ms', 'jitter_network_ms']
    
    guardar_csv(f'tables/scene{scene_num}/audio_AB_scene{scene_num}.csv', audio_AB, columnas)
    guardar_csv(f'tables/scene{scene_num}/video_AB_scene{scene_num}.csv', video_AB, columnas)
    guardar_csv(f'tables/scene{scene_num}/audio_BA_scene{scene_num}.csv', audio_BA, columnas)
    guardar_csv(f'tables/scene{scene_num}/video_BA_scene{scene_num}.csv', video_BA, columnas)
    
    return {
        'audio_AB': audio_AB,
        'video_AB': video_AB,
        'audio_BA': audio_BA,
        'video_BA': video_BA
    }

# =========================================================
# MAIN
# =========================================================
def main():
    print(f"\n🔧 Escenario seleccionado: {SCENE_NUM}")
    print(f"📁 Buscando archivos scene{SCENE_NUM}A_audio.csv, scene{SCENE_NUM}B_audio.csv, etc.")
    
    resultados = procesar_escenario(SCENE_NUM)
    
    if resultados:
        print("\n" + "="*60)
        print("✅ PROCESAMIENTO COMPLETADO")
        print("="*60)
        print(f"\nArchivos generados para Scene {SCENE_NUM}:")
        print(f"  - tables/scene{SCENE_NUM}/audio_AB_scene{SCENE_NUM}.csv")
        print(f"  - tables/scene{SCENE_NUM}/video_AB_scene{SCENE_NUM}.csv")
        print(f"  - tables/scene{SCENE_NUM}/audio_BA_scene{SCENE_NUM}.csv")
        print(f"  - tables/scene{SCENE_NUM}/video_BA_scene{SCENE_NUM}.csv")
        print("\n📊 Columnas en cada archivo:")
        print("  • call_num")
        print("  • packets_sent")
        print("  • packet_loss_%")
        print("  • jitter_ms (Baresip)")
        print("  • bitrate_kbps")
        print("  • delay_network_ms (Wireshark)")
        print("  • jitter_network_ms (Wireshark)")
        print("="*60)
    else:
        print("\n❌ Error: No se pudieron procesar los archivos")
        print("   Verifica que los archivos existan y tengan el formato correcto.")

if __name__ == "__main__":
    main()