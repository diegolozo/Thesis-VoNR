import re
import csv

# Para obtener merged:

# cat part1.txt part2.txt part3.txt > merged.txt
# cat part*.txt > merged.txt

logfile = "baresip_log/scene_10/A/merged.txt"

audio_csv_path = "baresip_log/done/scene10A_audio.csv"
video_csv_path = "baresip_log/done/scene10A_video.csv"

with open(logfile) as f:
    lines = f.readlines()

# -------------------------
# 1️⃣ Limpiar prefijo
# -------------------------
clean_lines = []

for line in lines:
    cleaned = re.sub(
        r'^.*?Baresip\+\sLib:\s*',
        '',
        line
    )
    clean_lines.append(cleaned)

# -------------------------
# 2️⃣ Reparar bloques
# -------------------------
fixed_lines = []
i = 0

while i < len(clean_lines):

    line = clean_lines[i].rstrip()

    # ===== RECOMPONER "errors" PARTIDO =====
    if line.strip() == "err" and i+1 < len(clean_lines):

        next_line = clean_lines[i+1].strip()

        if next_line.startswith("ors"):

            # Extraer números si existen
            nums = re.findall(r'\d+', next_line)

            if len(nums) >= 2:
                line = f"errors: {nums[0]} {nums[1]}"
            else:
                line = "errors:"

            i += 1  # saltar "ors"

    # ===== UNIR JITTER =====
    elif "jitter:" in line and i+1 < len(clean_lines):

        next_line = clean_lines[i+1]

        if re.search(r'\d', next_line):
            line = line + " " + next_line.strip()
            i += 1

    # ===== UNIR errors normales =====
    elif line.strip().endswith("errors:") and i+1 < len(clean_lines):

        next_line = clean_lines[i+1]

        if re.match(r'^\s*\d+\s+\d+\s*$', next_line):
            line = line + " " + next_line.strip()
            i += 1

    fixed_lines.append(line + "\n")
    i += 1

data = "\n".join(fixed_lines)


# -------- AUDIO --------
audio_blocks = re.findall(
    r'audio(.*?)(?=\n\s*(audio|video|call closed)|$)',
    data,
    re.S
)

audio_blocks = [b[0] for b in audio_blocks if "packets:" in b[0]]


# -------- VIDEO --------
video_blocks = re.findall(
    r'video(.*?)(?=\n\s*(audio|video|call closed)|$)',
    data,
    re.S
)

video_blocks = [b[0] for b in video_blocks if "packets:" in b[0]]


# =========================
# ALMACENAR DATOS PARA CSV
# =========================
audio_csv_data = []
video_csv_data = []

# =========================
# PARSE AUDIO
# =========================
for i, block in enumerate(audio_blocks):

    print(f"\n=== AUDIO CALL {i+1} ===")

    packets = re.search(r'packets:\s+(\d+)\s+(\d+)', block)
    bitrate = re.search(r'bitrate:\s+([\d.]+)\s+([\d.]+)', block)
    errors = re.search(r'errors:\s+(\d+)\s+(\d+)', block)
    pkt_report = re.search(r'pkt\.report:\s+(\d+)\s+(\d+)', block)
    lost = re.search(r'lost:\s+(-?\d+)\s+(-?\d+)', block)
    jitter = re.search(
        r'jitter:\s+([\d.]+).*?([\d.]+)\s*\(ms\)',
        block,
        re.S
    )

    if packets:
        print("Packets TX/RX:", packets.groups())
    if bitrate:
        print("Bitrate TX/RX:", bitrate.groups())
    if errors:
        print("Errors TX/RX:", errors.groups())
    if pkt_report:
        print("Pkt Report TX/RX:", pkt_report.groups())
    if lost:
        print("Lost TX/RX:", lost.groups())
    if jitter:
        print("Jitter TX/RX:", jitter.groups())

    # Procesar lost con valor absoluto
    lost_tx_value = ''
    lost_rx_value = ''
    if lost:
        try:
            lost_tx_value = abs(int(lost.groups()[0]))
            lost_rx_value = abs(int(lost.groups()[1]))
        except:
            lost_tx_value = ''
            lost_rx_value = ''

    # Guardar TODAS las columnas
    audio_row = {
        'call_num': i+1,
        'packets_tx': packets.groups()[0] if packets else '',
        'packets_rx': packets.groups()[1] if packets else '',
        'bitrate_tx': bitrate.groups()[0] if bitrate else '',
        'bitrate_rx': bitrate.groups()[1] if bitrate else '',
        'errors_tx': errors.groups()[0] if errors else '',
        'errors_rx': errors.groups()[1] if errors else '',
        'pkt_report_tx': pkt_report.groups()[0] if pkt_report else '',
        'pkt_report_rx': pkt_report.groups()[1] if pkt_report else '',
        'lost_tx': lost_tx_value,
        'lost_rx': lost_rx_value,
        'jitter_tx': jitter.groups()[0] if jitter else '',
        'jitter_rx': jitter.groups()[1] if jitter else ''
    }
    audio_csv_data.append(audio_row)


# =========================
# PARSE VIDEO
# =========================
for i, block in enumerate(video_blocks):

    print(f"\n=== VIDEO CALL {i+1} ===")

    packets = re.search(r'packets:\s+(\d+)\s+(\d+)', block)
    bitrate = re.search(r'bitrate:\s+([\d.]+)\s+([\d.]+)', block)
    errors = re.search(r'errors:\s+(\d+)\s+(\d+)', block)
    pkt_report = re.search(r'pkt\.report:\s+(\d+)\s+(\d+)', block)
    lost = re.search(r'lost:\s+(-?\d+)\s+(-?\d+)', block)
    jitter = re.search(
        r'jitter:\s+([\d.]+).*?([\d.]+)\s*\(ms\)',
        block,
        re.S
    )

    if packets:
        print("Packets TX/RX:", packets.groups())
    if bitrate:
        tx, rx = map(float, bitrate.groups())
        print(f"Bitrate TX/RX: {tx}/{rx}")
    if errors:
        print("Errors TX/RX:", errors.groups())
    if pkt_report:
        print("Pkt Report TX/RX:", pkt_report.groups())
    if lost:
        print("Lost TX/RX:", lost.groups())
    if jitter:
        print("Jitter TX/RX:", jitter.groups())

    # Procesar lost con valor absoluto
    lost_tx_value = ''
    lost_rx_value = ''
    if lost:
        try:
            lost_tx_value = abs(int(lost.groups()[0]))
            lost_rx_value = abs(int(lost.groups()[1]))
        except:
            lost_tx_value = ''
            lost_rx_value = ''

    # Guardar TODAS las columnas
    video_row = {
        'call_num': i+1,
        'packets_tx': packets.groups()[0] if packets else '',
        'packets_rx': packets.groups()[1] if packets else '',
        'bitrate_tx': bitrate.groups()[0] if bitrate else '',
        'bitrate_rx': bitrate.groups()[1] if bitrate else '',
        'errors_tx': errors.groups()[0] if errors else '',
        'errors_rx': errors.groups()[1] if errors else '',
        'pkt_report_tx': pkt_report.groups()[0] if pkt_report else '',
        'pkt_report_rx': pkt_report.groups()[1] if pkt_report else '',
        'lost_tx': lost_tx_value,
        'lost_rx': lost_rx_value,
        'jitter_tx': jitter.groups()[0] if jitter else '',
        'jitter_rx': jitter.groups()[1] if jitter else ''
    }
    video_csv_data.append(video_row)


# =========================
# GUARDAR CSVs
# =========================

# CSV de AUDIO
with open(audio_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = [
        'call_num', 
        'packets_tx', 'packets_rx',
        'bitrate_tx', 'bitrate_rx',
        'errors_tx', 'errors_rx',
        'pkt_report_tx', 'pkt_report_rx',
        'lost_tx', 'lost_rx',
        'jitter_tx', 'jitter_rx'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerows(audio_csv_data)

print(f"\n✅ Archivo CSV de AUDIO guardado: {audio_csv_path}")
print(f"   Columnas: call_num | packets_tx | packets_rx | bitrate_tx | bitrate_rx | errors_tx | errors_rx | pkt_report_tx | pkt_report_rx | lost_tx | lost_rx | jitter_tx | jitter_rx")

# CSV de VIDEO
with open(video_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = [
        'call_num', 
        'packets_tx', 'packets_rx',
        'bitrate_tx', 'bitrate_rx',
        'errors_tx', 'errors_rx',
        'pkt_report_tx', 'pkt_report_rx',
        'lost_tx', 'lost_rx',
        'jitter_tx', 'jitter_rx'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerows(video_csv_data)

print(f"✅ Archivo CSV de VIDEO guardado: {video_csv_path}")
print(f"   Columnas: call_num | packets_tx | packets_rx | bitrate_tx | bitrate_rx | errors_tx | errors_rx | pkt_report_tx | pkt_report_rx | lost_tx | lost_rx | jitter_tx | jitter_rx")

# Mostrar preview
print("\n📊 PREVIEW resultados_audio.csv (primeras 3 filas):")
print("-" * 80)
for row in audio_csv_data[:3]:
    print(f"Call {row['call_num']}: packets({row['packets_tx']}/{row['packets_rx']}) | bitrate({row['bitrate_tx']}/{row['bitrate_rx']}) | lost({row['lost_tx']}/{row['lost_rx']}) | jitter({row['jitter_tx']}/{row['jitter_rx']})")

print("\n📊 PREVIEW resultados_video.csv (primeras 3 filas):")
print("-" * 80)
for row in video_csv_data[:3]:
    print(f"Call {row['call_num']}: packets({row['packets_tx']}/{row['packets_rx']}) | bitrate({row['bitrate_tx']}/{row['bitrate_rx']}) | lost({row['lost_tx']}/{row['lost_rx']}) | jitter({row['jitter_tx']}/{row['jitter_rx']})")