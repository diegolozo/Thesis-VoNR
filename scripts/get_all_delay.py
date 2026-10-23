import subprocess
import statistics
import csv
import os
from collections import defaultdict
from scapy.all import *


# tshark -i ogstun -f "not (tcp port 5201) and not (host 10.45.0.X)" -w captura1.pcap

# ============ CONFIGURACIÓN ============
SCENE = 17

SCENE_FOLDER = f"delays/scene_{SCENE}"      # Carpeta donde están los archivos originales
FIXED_FOLDER = f"delays/scene_{SCENE}"      # Carpeta donde se guardarán los archivos fixed
OUTPUT_CSV = f"delays/done/delayscene_{SCENE}.csv"  # Nombre del archivo de salida
 
NETWORK_PREFIX = "10.45.0"
OLD_IP = "192.168.100.178"
NEW_IP = "10.45.0.1"

# ============ FUNCIONES AUXILIARES ============
def run_tshark(pcap_file, fields, filter_exp):
    cmd = ["tshark", "-r", pcap_file, "-Y", filter_exp, "-T", "fields"]
    for f in fields:
        cmd += ["-e", f]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip().split("\n")

def compute_delay(lines):
    times = []
    for l in lines:
        if not l:
            continue
        try:
            delta = float(l.split("\t")[0])
            if 0 < delta < 1:
                times.append(delta * 1000)
        except:
            pass
    return statistics.mean(times) if times else 0

def get_first_timestamp(pcap_file, filter_exp):
    lines = run_tshark(pcap_file, ["frame.time_epoch"], filter_exp)
    for l in lines:
        try:
            return float(l)
        except:
            continue
    return None

def detect_topology(pcap_file):
    lines = run_tshark(pcap_file, ["ip.src", "ip.dst"], "sip")
    counts = defaultdict(int)
    for l in lines:
        parts = l.split("\t")
        if len(parts) != 2:
            continue
        src, dst = parts
        if src.startswith(NETWORK_PREFIX):
            counts[src] += 1
        if dst.startswith(NETWORK_PREFIX):
            counts[dst] += 1
    if len(counts) < 3:
        raise Exception(f"No se detectaron suficientes nodos SIP en {pcap_file}")
    server = max(counts, key=counts.get)
    ues = [ip for ip in counts if ip != server]
    return ues[0], ues[1], server

def compute_call_setup_time(pcap_file, caller, callee):
    invite_time = get_first_timestamp(pcap_file, f'sip.Method=="INVITE" && ip.dst=={callee}')
    ring_time = get_first_timestamp(pcap_file, f'sip.Status-Code==180 && ip.dst=={caller}')
    if invite_time is None or ring_time is None:
        return 0
    return (ring_time - invite_time) * 1000

def analyze_srtp_streams(pcap_file, src, dst):
    """Analiza SRTP usando tamaño de paquete"""
    udp_filter = f"udp && ip.src=={src} && ip.dst=={dst} && !sip"
    
    cmd = ["tshark", "-r", pcap_file, "-Y", udp_filter, "-T", "fields",
           "-e", "udp.dstport", "-e", "frame.time_delta", "-e", "udp.length"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")
    
    if not lines or (len(lines) == 1 and not lines[0]):
        return 0, 0, 0, 0
    
    streams_by_port = defaultdict(lambda: {'delays': [], 'lengths': []})
    
    for line in lines:
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            port = parts[0]
            try:
                delta = float(parts[1]) * 1000
                if 0 < delta < 1000:
                    streams_by_port[port]['delays'].append(delta)
                if len(parts) >= 3:
                    try:
                        length = int(parts[2])
                        streams_by_port[port]['lengths'].append(length)
                    except:
                        pass
            except:
                pass
    
    audio_delays = []
    video_delays = []
    audio_jitter = 0
    video_jitter = 0
    
    for port, data in streams_by_port.items():
        avg_length = statistics.mean(data['lengths']) if data['lengths'] else 0
        mean_delay = statistics.mean(data['delays']) if data['delays'] else 0
        jitter = statistics.stdev(data['delays']) if len(data['delays']) > 1 else 0
        
        if avg_length < 300:  # Audio
            audio_delays.append(mean_delay)
            audio_jitter = jitter
        elif avg_length > 500:  # Video
            video_delays.append(mean_delay)
            video_jitter = jitter
    
    audio_delay = statistics.mean(audio_delays) if audio_delays else 0
    video_delay = statistics.mean(video_delays) if video_delays else 0
    
    return audio_delay, video_delay, audio_jitter, video_jitter

def analyze_direction(pcap_file, src, dst):
    """Analiza una dirección completa (SIP + medios)"""
    # Análisis SIP
    sip_filter = f"(sip || tcp.port==5061 || tls) && ip.src=={src} && ip.dst=={dst}"
    sip_lines = run_tshark(pcap_file, ["frame.time_delta"], sip_filter)
    sip_delay = compute_delay(sip_lines)
    
    # Analizar medios
    audio_delay, video_delay, audio_jitter, video_jitter = analyze_srtp_streams(pcap_file, src, dst)
    
    return {
        'sip_delay': sip_delay,
        'audio_delay': audio_delay,
        'video_delay': video_delay,
        'audio_jitter': audio_jitter,
        'video_jitter': video_jitter
    }

def fix_pcap(original_file, fixed_file):
    """Fija las IPs en el archivo pcap"""
    try:
        packets = rdpcap(original_file)
        for p in packets:
            if IP in p:
                if p[IP].src == OLD_IP:
                    p[IP].src = NEW_IP
                if p[IP].dst == OLD_IP:
                    p[IP].dst = NEW_IP
                del p[IP].chksum
        wrpcap(fixed_file, packets)
        return True
    except Exception as e:
        print(f"  Error al fijar el archivo: {e}")
        return False

def process_pcap(pcap_num):
    """Procesa un solo archivo pcap y retorna las métricas"""
    original_name = f"capture{pcap_num}.pcap"
    original_path = os.path.join(SCENE_FOLDER, original_name)
    fixed_name = f"fixed_{original_name}"
    fixed_path = os.path.join(FIXED_FOLDER, fixed_name)
    
    print(f"\n[INFO] Procesando iteración {pcap_num}/21: {original_name}")
    
    # Verificar si existe el archivo original
    if not os.path.exists(original_path):
        print(f"  [WARNING] No existe {original_path}, saltando...")
        return None
    
    # Fijar el archivo (si no existe el fixed o forzar regeneración)
    if not os.path.exists(fixed_path):
        print(f"  [INFO] Generando archivo fixed...")
        if not fix_pcap(original_path, fixed_path):
            print(f"  [ERROR] No se pudo fijar {original_name}")
            return None
    
    try:
        # Detectar topología
        A, B, SERVER = detect_topology(fixed_path)
        
        # Calcular Call Setup Time
        call_setup_time = compute_call_setup_time(fixed_path, A, B)
        
        # Analizar flujos
        a_to_server = analyze_direction(fixed_path, A, SERVER)
        server_to_b = analyze_direction(fixed_path, SERVER, B)
        b_to_server = analyze_direction(fixed_path, B, SERVER)
        server_to_a = analyze_direction(fixed_path, SERVER, A)
        
        # Calcular totales
        ab_audio = a_to_server['audio_delay'] + server_to_b['audio_delay']
        ab_video = a_to_server['video_delay'] + server_to_b['video_delay']
        ba_audio = b_to_server['audio_delay'] + server_to_a['audio_delay']
        ba_video = b_to_server['video_delay'] + server_to_a['video_delay']
        
        # Jitter (usamos el del primer tramo, que es donde se genera)
        ab_audio_jitter = a_to_server['audio_jitter']
        ab_video_jitter = a_to_server['video_jitter']
        ba_audio_jitter = b_to_server['audio_jitter']
        ba_video_jitter = b_to_server['video_jitter']
        
        # Mostrar resultados
        print(f"  [OK] Call Setup Time: {call_setup_time:.2f}ms")
        print(f"  [OK] A→B: Audio={ab_audio:.2f}ms, Video={ab_video:.2f}ms")
        print(f"  [OK] B→A: Audio={ba_audio:.2f}ms, Video={ba_video:.2f}ms")
        
        return {
            'num_sim': pcap_num,
            'call_setup_time_ms': call_setup_time,
            'ab_audio_delay': ab_audio,
            'ab_audio_jitter': ab_audio_jitter,
            'ab_video_delay': ab_video,
            'ab_video_jitter': ab_video_jitter,
            'ba_audio_delay': ba_audio,
            'ba_audio_jitter': ba_audio_jitter,
            'ba_video_delay': ba_video,
            'ba_video_jitter': ba_video_jitter
        }
        
    except Exception as e:
        print(f"  [ERROR] Falló el procesamiento: {e}")
        return None

def main():
    # Crear carpeta fixed si no existe
    os.makedirs(FIXED_FOLDER, exist_ok=True)
    
    # Procesar los 21 archivos
    resultados = []
    for i in range(1, 22):  # 1 a 21
        resultado = process_pcap(i)
        if resultado:
            resultados.append(resultado)
    
    # Guardar resultados en CSV
    if resultados:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'call_num',
                'call_setup_time_ms',
                'audio_delay_A_B_ms',
                'audio_jitter_A_B_ms',
                'video_delay_A_B_ms',
                'video_jitter_A_B_ms',
                'audio_delay_B_A_ms',
                'audio_jitter_B_A_ms',
                'video_delay_B_A_ms',
                'video_jitter_B_A_ms'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            
            for r in resultados:
                writer.writerow({
                    'call_num': r['num_sim'],
                    'call_setup_time_ms': round(r['call_setup_time_ms'], 3),
                    'audio_delay_A_B_ms': round(r['ab_audio_delay'], 3),
                    'audio_jitter_A_B_ms': round(r['ab_audio_jitter'], 3),
                    'video_delay_A_B_ms': round(r['ab_video_delay'], 3),
                    'video_jitter_A_B_ms': round(r['ab_video_jitter'], 3),
                    'audio_delay_B_A_ms': round(r['ba_audio_delay'], 3),
                    'audio_jitter_B_A_ms': round(r['ba_audio_jitter'], 3),
                    'video_delay_B_A_ms': round(r['ba_video_delay'], 3),
                    'video_jitter_B_A_ms': round(r['ba_video_jitter'], 3)
                })
        
        print("\n" + "="*60)
        print(f"✅ PROCESAMIENTO COMPLETADO")
        print(f"   Archivos procesados: {len(resultados)}/21")
        print(f"   Resultados guardados en: {OUTPUT_CSV}")
        print("="*60)
        
        # Mostrar primeras 5 filas como preview
        print("\n📊 PREVIEW de los primeros resultados:")
        print("-"*60)
        for i, r in enumerate(resultados[:5]):
            print(f"Sim {r['num_sim']}: Setup={r['call_setup_time_ms']:.1f}ms | A→B (A:{r['ab_audio_delay']:.1f}ms V:{r['ab_video_delay']:.1f}ms) | B→A (A:{r['ba_audio_delay']:.1f}ms V:{r['ba_video_delay']:.1f}ms)")
        
        # Calcular estadísticas básicas
        print("\n📊 ESTADÍSTICAS BÁSICAS (sobre 21 muestras):")
        print("-"*60)
        setup_vals = [r['call_setup_time_ms'] for r in resultados]
        ab_audio_vals = [r['ab_audio_delay'] for r in resultados]
        ab_video_vals = [r['ab_video_delay'] for r in resultados]
        print(f"Call Setup Time: media={statistics.mean(setup_vals):.2f}ms, std={statistics.stdev(setup_vals):.2f}ms")
        print(f"Audio A→B: media={statistics.mean(ab_audio_vals):.2f}ms, std={statistics.stdev(ab_audio_vals):.2f}ms")
        print(f"Video A→B: media={statistics.mean(ab_video_vals):.2f}ms, std={statistics.stdev(ab_video_vals):.2f}ms")
        
    else:
        print("\n❌ No se pudo procesar ningún archivo")
        print("   Verifica que los archivos captura1.pcap a captura21.pcap existan en la carpeta:", SCENE_FOLDER)

if __name__ == "__main__":
    main()