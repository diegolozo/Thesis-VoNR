"""
extract_baresip_metrics.py

Extracts the raw call metrics (packets, bitrate, errors, packet report,
lost packets and jitter, for TX and RX) from the log files of the Baresip+
application and saves them as one CSV file for audio and one for video.

HOW TO USE
----------
1. Save the log of the terminal after every 7 calls, to avoid losing data by
   overwriting. This produces several .txt files per scenario and flow.

2. Merge the .txt files of the scenario and flow into a single file named
   "merged.txt" (Linux `cat` command), for example:

       cat part1.txt part2.txt part3.txt > merged.txt
       cat part*.txt > merged.txt

3. Place "merged.txt" in the folder:

       <BASE_DIR>/scene_<SCENE>/<FLOW>/merged.txt

4. Set the three variables in the CONFIGURATION section below
   (BASE_DIR, SCENE and FLOW). They are the only values that need to be
   edited; all the paths are built from them.

5. Run the script. The output folder "<BASE_DIR>/done/" is created
   automatically if it does not exist, and the script prints where the
   results were saved when it finishes.

OUTPUT
------
    <BASE_DIR>/done/scene<SCENE><FLOW>_audio.csv
    <BASE_DIR>/done/scene<SCENE><FLOW>_video.csv

Both files use ";" as delimiter and have one row per call, with the columns:
call_num, packets_tx, packets_rx, bitrate_tx, bitrate_rx, errors_tx, errors_rx,
pkt_report_tx, pkt_report_rx, lost_tx, lost_rx, jitter_tx, jitter_rx
"""

import os
import re
import csv

# =========================
# CONFIGURATION
# =========================
BASE_DIR = "baresip_log"  # Folder that contains the logs and the "done" output folder
SCENE = "10"              # Scenario number
FLOW = "A"                # Flow identifier ("A" or "B")

# Paths (built from the variables above, do not edit)
logfile = f"{BASE_DIR}/scene_{SCENE}/{FLOW}/merged.txt"
output_dir = f"{BASE_DIR}/done"
audio_csv_path = f"{output_dir}/scene{SCENE}{FLOW}_audio.csv"
video_csv_path = f"{output_dir}/scene{SCENE}{FLOW}_video.csv"

# =========================
# CHECK INPUT AND OUTPUT FOLDERS
# =========================
if not os.path.isfile(logfile):
    raise FileNotFoundError(
        f"Input file not found: {logfile}\n"
        f"Check BASE_DIR, SCENE and FLOW, and make sure the merged log is saved "
        f"as 'merged.txt' in that folder."
    )

# Create the output folder if it does not exist
os.makedirs(output_dir, exist_ok=True)

with open(logfile) as f:
    lines = f.readlines()

# -------------------------
# Remove prefix
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
# Repair broken blocks
# -------------------------
fixed_lines = []
i = 0

while i < len(clean_lines):

    line = clean_lines[i].rstrip()

    # ===== REBUILD SPLIT "errors" LINE =====
    if line.strip() == "err" and i+1 < len(clean_lines):

        next_line = clean_lines[i+1].strip()

        if next_line.startswith("ors"):

            # Extract the numbers, if any
            nums = re.findall(r'\d+', next_line)

            if len(nums) >= 2:
                line = f"errors: {nums[0]} {nums[1]}"
            else:
                line = "errors:"

            i += 1  # skip "ors"

    # ===== JOIN JITTER LINES =====
    elif "jitter:" in line and i+1 < len(clean_lines):

        next_line = clean_lines[i+1]

        if re.search(r'\d', next_line):
            line = line + " " + next_line.strip()
            i += 1

    # ===== JOIN REGULAR errors LINES =====
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
# STORE DATA FOR THE CSV FILES
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

    # Process lost packets using the absolute value
    lost_tx_value = ''
    lost_rx_value = ''
    if lost:
        try:
            lost_tx_value = abs(int(lost.groups()[0]))
            lost_rx_value = abs(int(lost.groups()[1]))
        except:
            lost_tx_value = ''
            lost_rx_value = ''

    # Store ALL the columns
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

    # Process lost packets using the absolute value
    lost_tx_value = ''
    lost_rx_value = ''
    if lost:
        try:
            lost_tx_value = abs(int(lost.groups()[0]))
            lost_rx_value = abs(int(lost.groups()[1]))
        except:
            lost_tx_value = ''
            lost_rx_value = ''

    # Store ALL the columns
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
# SAVE CSV FILES
# =========================

# AUDIO CSV
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

print(f"\n✅ AUDIO CSV file saved: {audio_csv_path}")
print(f"   Columns: call_num | packets_tx | packets_rx | bitrate_tx | bitrate_rx | errors_tx | errors_rx | pkt_report_tx | pkt_report_rx | lost_tx | lost_rx | jitter_tx | jitter_rx")

# VIDEO CSV
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

print(f"VIDEO CSV file saved: {video_csv_path}")
print(f"   Columns: call_num | packets_tx | packets_rx | bitrate_tx | bitrate_rx | errors_tx | errors_rx | pkt_report_tx | pkt_report_rx | lost_tx | lost_rx | jitter_tx | jitter_rx")

# Show preview
print(f"\nPREVIEW {audio_csv_path} (first 3 rows):")
print("-" * 80)
for row in audio_csv_data[:3]:
    print(f"Call {row['call_num']}: packets({row['packets_tx']}/{row['packets_rx']}) | bitrate({row['bitrate_tx']}/{row['bitrate_rx']}) | lost({row['lost_tx']}/{row['lost_rx']}) | jitter({row['jitter_tx']}/{row['jitter_rx']})")

print(f"\n📊REVIEW {video_csv_path} (first 3 rows):")
print("-" * 80)
for row in video_csv_data[:3]:
    print(f"Call {row['call_num']}: packets({row['packets_tx']}/{row['packets_rx']}) | bitrate({row['bitrate_tx']}/{row['bitrate_rx']}) | lost({row['lost_tx']}/{row['lost_rx']}) | jitter({row['jitter_tx']}/{row['jitter_rx']})")

# =========================
# SUMMARY
# =========================
print("\n" + "=" * 80)
print(f"DONE: scene {SCENE}, flow {FLOW}")
print(f"  Audio calls processed: {len(audio_csv_data)}")
print(f"  Video calls processed: {len(video_csv_data)}")
print(f"  Results saved in the folder: {os.path.abspath(output_dir)}")
print(f"    - {os.path.basename(audio_csv_path)}")
print(f"    - {os.path.basename(video_csv_path)}")
print("=" * 80)