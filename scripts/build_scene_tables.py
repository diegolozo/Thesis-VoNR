"""
build_scene_tables.py

Merges, for ONE scenario, the metrics obtained from the baresip+ logs and the
delays obtained from the tshark captures, and generates the final tables
(one CSV per media type and direction) used by the analysis notebook to make
the plots.

HOW TO USE
----------
1. Run the previous extraction scripts first, so that the following 5 files
   exist for the scenario (SCENE_NUM):

   From extract_baresip_metrics.py (run once for flow A and once for flow B):
       <BARESIP_DIR>/scene<SCENE_NUM>A_audio.csv
       <BARESIP_DIR>/scene<SCENE_NUM>A_video.csv
       <BARESIP_DIR>/scene<SCENE_NUM>B_audio.csv
       <BARESIP_DIR>/scene<SCENE_NUM>B_video.csv

   From extract_pcap_delays.py:
       <DELAYS_DIR>/delayscene_<SCENE_NUM>.csv

2. Set the variables in the CONFIGURATION section below. They are the only
   values that need to be edited; all the paths are built from them.

3. Run the script. The output folder is created automatically if it does not
   exist. If any input file is missing, the script lists all the missing files
   and stops without generating anything.

WHAT IT DOES
------------
For each call (call_num) present in all the input files, and for each of the
4 cases (audio A->B, video A->B, audio B->A, video B->A), it takes:
- packets_sent, bitrate_kbps: from the transmitting side (TX) of the sender.
- packet_loss_%: lost_tx / packets_tx * 100, from the sender.
- jitter_ms: jitter measured by baresip+ at the receiver (jitter_rx).
- delay_network_ms, jitter_network_ms: from the tshark delays file.

OUTPUT
------
    <TABLES_DIR>/scene<SCENE_NUM>/audio_AB_scene<SCENE_NUM>.csv
    <TABLES_DIR>/scene<SCENE_NUM>/video_AB_scene<SCENE_NUM>.csv
    <TABLES_DIR>/scene<SCENE_NUM>/audio_BA_scene<SCENE_NUM>.csv
    <TABLES_DIR>/scene<SCENE_NUM>/video_BA_scene<SCENE_NUM>.csv

Columns (separated by ";"): call_num, packets_sent, packet_loss_%, jitter_ms,
bitrate_kbps, delay_network_ms, jitter_network_ms.
"""

import csv
import os

# ============ CONFIGURATION ============
SCENE_NUM = 18                      # Scenario to process (1, 2, 3, ...)

BARESIP_DIR = "baresip_log/done"    # Folder with the CSVs from extract_baresip_metrics.py
DELAYS_DIR = "delays/done"          # Folder with the CSVs from extract_pcap_delays.py
TABLES_DIR = "tables"               # Output folder (one subfolder per scenario)
# =======================================

# Output folder of the scenario (built from the variables above, do not edit)
OUTPUT_DIR = f"{TABLES_DIR}/scene{SCENE_NUM}"

def find_files(scene_num):
    """Finds the 5 input files for a given scenario number"""

    files = {
        'A_audio': f'{BARESIP_DIR}/scene{scene_num}A_audio.csv',
        'A_video': f'{BARESIP_DIR}/scene{scene_num}A_video.csv',
        'B_audio': f'{BARESIP_DIR}/scene{scene_num}B_audio.csv',
        'B_video': f'{BARESIP_DIR}/scene{scene_num}B_video.csv',
        'delays': f'{DELAYS_DIR}/delayscene_{scene_num}.csv'
    }
        
    # Check that all of them exist (list every missing file)
    missing = [path for path in files.values() if not os.path.exists(path)]
    for path in missing:
        print(f"File not found: {path}")
    if missing:
        return None
    return files

def read_csv(file_name):
    """Reads a CSV and returns a dictionary with key=call_num, value=row"""
    data = {}
    with open(file_name, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            call_num = int(row['call_num'])
            data[call_num] = row
    return data

def compute_packet_loss(lost_tx, packets_tx):
    """Computes Packet Loss % = (lost_tx / packets_tx) * 100"""
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

def save_csv(file_name, data, columns):
    """Saves a CSV with the given data"""
    with open(file_name, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter=';')
        writer.writeheader()
        writer.writerows(data)
    print(f"Saved: {file_name}")

def process_scene(scene_num):
    """Processes a complete scenario"""
    print(f"\n{'='*60}")
    print(f"Processing Scene {scene_num}")
    print('='*60)
    
    # Find files
    files = find_files(scene_num)
    if not files:
        print(f"Input files not found for scene {scene_num}")
        return None
    
    # Load data
    print("Loading files...")
    data_A_audio = read_csv(files['A_audio'])
    data_A_video = read_csv(files['A_video'])
    data_B_audio = read_csv(files['B_audio'])
    data_B_video = read_csv(files['B_video'])
    data_delays = read_csv(files['delays'])
    
    print(f"  Audio A: {len(data_A_audio)} calls")
    print(f"  Video A: {len(data_A_video)} calls")
    print(f"  Audio B: {len(data_B_audio)} calls")
    print(f"  Video B: {len(data_B_video)} calls")
    print(f"  Delays: {len(data_delays)} calls")
    
    # =========================================================
    # 1. AUDIO A → B
    # =========================================================
    print("\nProcessing Audio A → B...")
    audio_AB = []
    for call_num in sorted(data_A_audio.keys()):
        if call_num in data_B_audio and call_num in data_delays:
            row_A = data_A_audio[call_num]
            row_B = data_B_audio[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_A.get('packets_tx', '')
            lost_tx = row_A.get('lost_tx', '')
            packet_loss_pct = compute_packet_loss(lost_tx, packets_tx)
            
            audio_AB.append({
                'call_num': call_num,
                'packets_sent': packets_tx,
                'packet_loss_%': packet_loss_pct,
                'jitter_ms': row_B.get('jitter_rx', ''),  # Jitter from baresip+ (Rx)
                'bitrate_kbps': row_A.get('bitrate_tx', ''),
                'delay_network_ms': row_delay.get('audio_delay_A_B_ms', ''),
                'jitter_network_ms': row_delay.get('audio_jitter_A_B_ms', '')
            })
            print(f"  Call {call_num}: TX={packets_tx}, Loss%={packet_loss_pct}%, Jitter(Baresip)={row_B.get('jitter_rx', '')}ms, Bitrate={row_A.get('bitrate_tx', '')}kbps, Delay(Net)={row_delay.get('audio_delay_A_B_ms', '')}ms, Jitter(Net)={row_delay.get('audio_jitter_A_B_ms', '')}ms")
    
    print(f"  Total: {len(audio_AB)} calls")
    
    # =========================================================
    # 2. VIDEO A → B
    # =========================================================
    print("\nProcessing Video A → B...")
    video_AB = []
    for call_num in sorted(data_A_video.keys()):
        if call_num in data_B_video and call_num in data_delays:
            row_A = data_A_video[call_num]
            row_B = data_B_video[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_A.get('packets_tx', '')
            lost_tx = row_A.get('lost_tx', '')
            packet_loss_pct = compute_packet_loss(lost_tx, packets_tx)
            
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
    
    print(f"  Total: {len(video_AB)} calls")
    
    # =========================================================
    # 3. AUDIO B → A
    # =========================================================
    print("\nProcessing Audio B → A...")
    audio_BA = []
    for call_num in sorted(data_B_audio.keys()):
        if call_num in data_A_audio and call_num in data_delays:
            row_B = data_B_audio[call_num]
            row_A = data_A_audio[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_B.get('packets_tx', '')
            lost_tx = row_B.get('lost_tx', '')
            packet_loss_pct = compute_packet_loss(lost_tx, packets_tx)
            
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
    
    print(f"  Total: {len(audio_BA)} calls")
    
    # =========================================================
    # 4. VIDEO B → A
    # =========================================================
    print("\nProcessing Video B → A...")
    video_BA = []
    for call_num in sorted(data_B_video.keys()):
        if call_num in data_A_video and call_num in data_delays:
            row_B = data_B_video[call_num]
            row_A = data_A_video[call_num]
            row_delay = data_delays[call_num]
            
            packets_tx = row_B.get('packets_tx', '')
            lost_tx = row_B.get('lost_tx', '')
            packet_loss_pct = compute_packet_loss(lost_tx, packets_tx)
            
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
    
    print(f"  Total: {len(video_BA)} calls")
    
    # =========================================================
    # SAVE CSVs
    # =========================================================
    print("\nSaving files...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    columns = ['call_num', 'packets_sent', 'packet_loss_%', 'jitter_ms', 'bitrate_kbps', 'delay_network_ms', 'jitter_network_ms']
    
    save_csv(f'{OUTPUT_DIR}/audio_AB_scene{scene_num}.csv', audio_AB, columns)
    save_csv(f'{OUTPUT_DIR}/video_AB_scene{scene_num}.csv', video_AB, columns)
    save_csv(f'{OUTPUT_DIR}/audio_BA_scene{scene_num}.csv', audio_BA, columns)
    save_csv(f'{OUTPUT_DIR}/video_BA_scene{scene_num}.csv', video_BA, columns)
    
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
    print(f"\nSelected scene: {SCENE_NUM}")
    print(f"Looking for files scene{SCENE_NUM}A_audio.csv, scene{SCENE_NUM}B_audio.csv, etc. in {BARESIP_DIR}")
    
    results = process_scene(SCENE_NUM)
    
    if results:
        print("\n" + "="*60)
        print("PROCESSING COMPLETED")
        print("="*60)
        print(f"\nFiles generated for Scene {SCENE_NUM}:")
        print(f"  - {OUTPUT_DIR}/audio_AB_scene{SCENE_NUM}.csv")
        print(f"  - {OUTPUT_DIR}/video_AB_scene{SCENE_NUM}.csv")
        print(f"  - {OUTPUT_DIR}/audio_BA_scene{SCENE_NUM}.csv")
        print(f"  - {OUTPUT_DIR}/video_BA_scene{SCENE_NUM}.csv")
        print("\nColumns in each file:")
        print("  • call_num")
        print("  • packets_sent")
        print("  • packet_loss_%")
        print("  • jitter_ms (Baresip)")
        print("  • bitrate_kbps")
        print("  • delay_network_ms (Wireshark)")
        print("  • jitter_network_ms (Wireshark)")
        print(f"\nResults saved in: {os.path.abspath(OUTPUT_DIR)}")
        print("="*60)
    else:
        print("\nError: The files could not be processed")
        print("   Check that the files exist and have the correct format.")

if __name__ == "__main__":
    main()