"""
extract_pcap_delays_all_scenes.py

Same analysis as extract_pcap_delays.py, but it processes SEVERAL scenarios in a
single run (one after the other). For every scenario it computes the delay and
jitter of the audio and video streams of its 21 video calls, and the call
setup time, from the packet captures (.pcap) taken during the calls.

HOW TO USE
----------
1. Capture the traffic of the 5G network with tshark during each call, one
   file per call, named capture1.pcap ... capture21.pcap. The capture can be
   done in real time on the core interface, excluding the iperf traffic and the
   traffic of the machine that runs the capture (10.45.0.X is the IP of that
   machine), for example:

       tshark -i ogstun -f "not (tcp port 5201) and not (host 10.45.0.X)" -w capture1.pcap

2. Place the 21 files of each scenario in its own folder:

       <BASE_DIR>/scene_<SCENE>/

3. Set the variables in the CONFIGURATION section below. They are the only
   values that need to be edited; all the paths are built from them.

4. Run the script (tshark and scapy must be installed). The output folders are
   created automatically if they do not exist. A scenario whose folder is
   missing or has no usable captures is reported and skipped, and the script
   continues with the next one.

WHAT IT DOES
------------
- For every capture, it first creates a "fixed_" copy in which the IP address
  OLD_IP is replaced by NEW_IP, so that all the network nodes share the prefix
  NETWORK_PREFIX. Existing "fixed_" files are reused, not generated again.
- It detects the topology from the SIP traffic: the two terminals (A and B) and
  the SIP server. The server is the node with more SIP packets.
- The delay of each leg (terminal -> server and server -> terminal) is computed
  from the "frame.time_delta" field of tshark. The end-to-end delay of each
  direction is the sum of its two legs: A->B = (A->server) + (server->B), and
  B->A = (B->server) + (server->A).
- The jitter is the standard deviation of those per-packet values, taken from
  the first leg of each direction.
- Audio and video streams are told apart by the mean UDP packet length
  (audio below 300 bytes, video above 500 bytes).

OUTPUT
------
One file per scenario:

    <BASE_DIR>/done/delayscene_<SCENE>.csv

One row per call, separated by ";", with the columns: call_num,
call_setup_time_ms, and the audio/video delay and jitter (in ms) of each
direction (A_B and B_A).
"""

import subprocess
import statistics
import csv
import os
from collections import defaultdict
from scapy.all import *


# ============ CONFIGURATION ============
BASE_DIR = "delays"        # Folder that contains the scenario folders and the "done" folder
SCENES = range(11, 19)     # Scenarios to process: 11, 12, ..., 18 (the last number is excluded)

NETWORK_PREFIX = "10.45.0"
OLD_IP = "192.168.100.178"   # IP address to replace in the captures
NEW_IP = "10.45.0.1"         # IP address that replaces OLD_IP

# Paths of the scenario being processed (set automatically by main(), do not edit)
SCENE = None
SCENE_FOLDER = None
FIXED_FOLDER = None
OUTPUT_CSV = None

# ============ HELPER FUNCTIONS ============
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
        raise Exception(f"Not enough SIP nodes were detected in {pcap_file}")
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
    """Analyzes SRTP streams using the packet size"""
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
    """Analyzes one full direction (SIP + media)"""
    # SIP analysis
    sip_filter = f"(sip || tcp.port==5061 || tls) && ip.src=={src} && ip.dst=={dst}"
    sip_lines = run_tshark(pcap_file, ["frame.time_delta"], sip_filter)
    sip_delay = compute_delay(sip_lines)
    
    # Analyze media
    audio_delay, video_delay, audio_jitter, video_jitter = analyze_srtp_streams(pcap_file, src, dst)
    
    return {
        'sip_delay': sip_delay,
        'audio_delay': audio_delay,
        'video_delay': video_delay,
        'audio_jitter': audio_jitter,
        'video_jitter': video_jitter
    }

def fix_pcap(original_file, fixed_file):
    """Replaces the IP addresses in the pcap file"""
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
        print(f"  Error while fixing the file: {e}")
        return False

def process_pcap(pcap_num):
    """Processes a single pcap file and returns its metrics"""
    original_name = f"capture{pcap_num}.pcap"
    original_path = os.path.join(SCENE_FOLDER, original_name)
    fixed_name = f"fixed_{original_name}"
    fixed_path = os.path.join(FIXED_FOLDER, fixed_name)
    
    print(f"\n[INFO] Processing iteration {pcap_num}/21: {original_name}")
    
    # Check that the original file exists
    if not os.path.exists(original_path):
        print(f"  [WARNING] {original_path} does not exist, skipping...")
        return None
    
    # Fix the file (if the fixed file does not exist; delete it to force regeneration)
    if not os.path.exists(fixed_path):
        print(f"  [INFO] Generating fixed file...")
        if not fix_pcap(original_path, fixed_path):
            print(f"  [ERROR] Could not fix {original_name}")
            return None
    
    try:
        # Detect topology
        A, B, SERVER = detect_topology(fixed_path)
        
        # Compute Call Setup Time
        call_setup_time = compute_call_setup_time(fixed_path, A, B)
        
        # Analyze flows
        a_to_server = analyze_direction(fixed_path, A, SERVER)
        server_to_b = analyze_direction(fixed_path, SERVER, B)
        b_to_server = analyze_direction(fixed_path, B, SERVER)
        server_to_a = analyze_direction(fixed_path, SERVER, A)
        
        # Compute totals
        ab_audio = a_to_server['audio_delay'] + server_to_b['audio_delay']
        ab_video = a_to_server['video_delay'] + server_to_b['video_delay']
        ba_audio = b_to_server['audio_delay'] + server_to_a['audio_delay']
        ba_video = b_to_server['video_delay'] + server_to_a['video_delay']
        
        # Jitter (the first leg is used, since that is where it is generated)
        ab_audio_jitter = a_to_server['audio_jitter']
        ab_video_jitter = a_to_server['video_jitter']
        ba_audio_jitter = b_to_server['audio_jitter']
        ba_video_jitter = b_to_server['video_jitter']
        
        # Show results
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
        print(f"  [ERROR] Processing failed: {e}")
        return None

def main(scene):

    global SCENE
    global SCENE_FOLDER
    global FIXED_FOLDER
    global OUTPUT_CSV

    SCENE = scene
    SCENE_FOLDER = f"{BASE_DIR}/scene_{SCENE}"                # Folder with the original captures
    FIXED_FOLDER = SCENE_FOLDER                               # Folder where the "fixed_" captures are saved
    OUTPUT_CSV = f"{BASE_DIR}/done/delayscene_{SCENE}.csv"    # Output file

    print(f"\n🚀 Processing SCENE {SCENE}")

    # Check the input folder and create the output folders if they do not exist
    if not os.path.isdir(SCENE_FOLDER):
        print(f"\n❌ Input folder not found: {SCENE_FOLDER}")
        print("   Check BASE_DIR and the scenario number, and make sure the captures "
              "(capture1.pcap ... capture21.pcap) are inside that folder.")
        return False
    os.makedirs(FIXED_FOLDER, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    # Process the 21 files
    results = []

    for i in range(1, 22):
        result = process_pcap(i)
        if result:
            results.append(result)

    # Save results to CSV
    if results:
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

            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=';'
            )

            writer.writeheader()

            for r in results:
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

        print(f"\n✅ SCENE {SCENE} completed ({len(results)}/21 files processed)")
        print(f"CSV: {os.path.abspath(OUTPUT_CSV)}")
        return True

    else:
        print(f"\n❌ SCENE {SCENE} could not be processed")
        print("   Check that the files capture1.pcap to capture21.pcap exist in the folder:", SCENE_FOLDER)
        return False

if __name__ == "__main__":
    completed = []
    failed = []

    for scene in SCENES:
        if main(scene):
            completed.append(scene)
        else:
            failed.append(scene)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Scenarios completed: {completed if completed else 'none'}")
    if failed:
        print(f"Scenarios NOT processed: {failed}")
    if completed:
        print(f"Results saved in: {os.path.abspath(os.path.join(BASE_DIR, 'done'))}")