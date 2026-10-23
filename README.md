# Design and Implementation of a Methodology for Video Call Evaluation in Open-Source Private 5G SA Networks

## Description

This repository contains the material developed for evaluating over-the-top (OTT) video calls over a private 5G Standalone (SA) network built entirely with open-source software and low-cost hardware.

The main contribution is the evaluation methodology together with a standardized multimedia database. As a direct application, the methodology is used to compare two open-source radio access network (RAN) implementations, srsRAN and OpenAirInterface (OAI), under different congestion and traffic prioritization conditions.

## Key Contributions

- **Evaluation methodology.** A step-by-step procedure for deploying the network, running video call sessions and collecting per-flow network metrics (delay, jitter, packet loss and bitrate) in both directions.
- **Multimedia database.** A set of 21 standardized audio and video stimuli, built from [ITU-T P.501](https://www.itu.int/myworkspace/t-signals/vectors?val=17) speech material and the [LIVE-Qualcomm](https://live.ece.utexas.edu/research/incaptureDatabase/index.html) video dataset, so that experiments are reproducible across setups. See the [Multimedia Folder](multimedia/).
- **Quality of experience estimation.** Computation of speech, video and multimedia quality ($S_q$, $V_q$ and $MM_q$) following [ITU-T G.1070](https://www.itu.int/rec/T-REC-G.1070-201806-I/es), from the metrics captured during each call for both flows.
- **Application to RAN comparison.** An experimental comparison of srsRAN and OAI in 18 scenarios, covering no congestion, congestion with default QoS, and congestion with a prioritized QoS flow (5QI 1).

## System Architecture

The testbed is a private 5G Standalone network deployed with open-source software and a software-defined radio. Two commercial smartphones act as the video call endpoints (A and B), and a third device generates background traffic to create congestion.

<!-- Replace with the path of your architecture diagram -->
![System architecture](docs/figures/architecture.png)

| Component | Software / Hardware | Version |
|---|---|---|
| 5G core | Open5GS | 2.7.6 |
| gNB (RAN) | srsRAN Project | 24.10.1 |
| gNB (RAN) | OpenAirInterface (OAI) | 2.4.0 |
| Radio front end | USRP B210 | - |
| SIP server | Kamailio | 6.0.1 |
| Media relay | RTPEngine | 11.5.1.15 |
| SIP client | baresip+ | 62.1.0 |
| Traffic generator | iPerf3 | 3.9 |
| User equipment | Samsung Galaxy S21 (A) and S23 Ultra (B) | - |

Radio configuration: band n78, 3410.1 MHz (ARFCN 627340), 40 MHz bandwidth, TDD, PLMN 999-70.

## Experimental Design

Each experiment combines one RAN implementation with one of three network conditions:

| Condition | Description | srsRAN | OAI |
|---|---|---|---|
| C1 | No congestion, default QoS (5QI 9) | E1-E3 | E10-E12 |
| C2 | Congestion, default QoS (5QI 9) | E4-E6 | E13-E15 |
| C3 | Congestion, prioritized QoS (5QI 1) | E7-E9 | E16-E18 |

- Congestion is generated with iPerf3 background traffic from a third UE.
- Media encryption (SRTP/SDES and ZRTP) is tested within each condition. Since it operates at the application layer, results are averaged across encryption modes.
- Each scenario is repeated **21 times**, for a total of **378 video call sessions**.
- Audio uses AMR-WB codec and video uses H.265 codec.

## Repository Structure

```text
.
├── configs/          # Configuration files (Open5GS, srsRAN, OAI, Kamailio, RTPEngine, baresip+)
├── multimedia/       # Audio and video stimuli and the scripts used to build them
├── scripts/          # Scripts for running experiments and capturing data
├── analysis/         # Scripts for metric extraction, QoE computation and plots
├── docs/
   ├── figures/                # Figures used in the documentation
   ├── baresip-plus-setup.md   # Configuration of the baresip+ client
   ├── network-setup.md        # 5G core, gNB, SIM cards and UE registration
   ├── sip-server.md           # Kamailio and RTPEngine configuration
   ├── data-processing.md      # How to run the analysis scripts
   └── troubleshooting.md      # Common problems and solutions
├── LICENSE
└── README.md
```

## Documentation

Detailed guides for each part of the setup are in the `docs/` folder:

| Guide | Description |
|---|---|
| [Network setup](docs/network-setup.md) | 5G core, gNB, SIM cards and UE registration |
| [SIP server](docs/sip-server.md) | Kamailio and RTPEngine configuration |
| [baresip+ setup](docs/baresip-plus-setup.md) | Configuration of the SIP client on the terminals |
| [Data processing](docs/data-processing.md) | Running the analysis scripts and understanding their output |
| [Troubleshooting](docs/troubleshooting.md) | Common problems and solutions |

## Getting Started

### Requirements

- A host machine for the 5G core and one for the gNB (or a single machine running both)
- Ettus USRP B210 and compatible cables and antennas
- Two 5G SA-capable smartphones, plus a third device to generate background traffic
- Programmable SIM cards (recommended)
- Software at the versions listed in the [System Architecture](#system-architecture) section

### Reproducing the Experiments

The methodology is organized in eight steps, from deploying the network to computing the quality metrics.

#### Step 1: Deploy the network infrastructure

1. Install and configure the 5G core. This work uses Open5GS, but any compatible core can be used.
2. Install the RAN platform to evaluate (srsRAN, OAI, or both). It must be compatible with the chosen core and with the radio unit (here, the USRP B210), and the right antennas must be connected.
3. Register the user equipment (UE) in the core, using the SIM card parameters (authentication keys and identifiers). Programmable SIM cards are recommended, since they make it easier to debug and customize these parameters.

See the [network setup guide](docs/network-setup.md) for details.

#### Step 2: Configure the SIP server

1. Install Kamailio as the SIP server and RTPEngine as the media relay, following their documentation. The configuration files used in this work are in `configs/`.
2. Start from a minimal Kamailio configuration, enough to place calls.
3. Create the users and passwords authorized to register. Each SIP URI can be freely defined, either as a phone number following ITU-T E.164 or as another value.
4. If E.164 numbers are used, keep the same country code for all users and enable the roaming option in the mobile network settings of each device, since calls between different country codes may behave differently.

See the [SIP server guide](docs/sip-server.md) for details.

#### Step 3: Configure the terminals

1. Connect the UE to the network using the configured SIM cards and install the baresip+ application.
2. Register each UE in the SIP server with its IP address, user and password.
3. Select the audio and video codecs (AMR-WB and H.265 in this work). To force a single codec, disable all the others. Set the video resolution and frame rate (1080p and 30 fps in this work).
4. Set the media encryption mode to accept. To force a specific one, select the same mode in both terminals.
5. Define which UE starts and ends the calls, and register the number of the UE that receives them.
6. Install iPerf3 on the machine running the RAN (server side) and on a third UE, outside the video call, in client mode. This device generates the background traffic in the scenarios with congestion. Configure both uplink and downlink traffic, so that the load resembles a regular user and competes for radio resources.

See the [baresip+ setup guide](docs/baresip-plus-setup.md) for the exact settings, since some of them are not intuitive.

#### Step 4: Prepare the multimedia material

There are two options:

1. **Use the 21 audiovisual stimuli provided in this repository** (`multimedia/`), which include the audio-video correspondence and the sequence tuples used.
2. **Build new stimuli.** Select audio from Annexes C and D of ITU-T P.501 and video from the LIVE-Qualcomm database. Then generate the tuples ($i$, $j$, $Δ1$, $Δ2$), different from the provided ones if new stimuli are desired, always keeping the balance between gender and language (male and female speakers from Annex C, and Annex D). The scripts used to convert and combine the material are in `multimedia/`.

Keep the correspondence between stimuli and iterations fixed for each scenario.

#### Step 5: Design the experimental scenarios

Define the scenarios by combining the independent variables to evaluate. In this work: RAN platform, media encryption mechanism, 5QI level and presence of external traffic. Start from a well-defined base case and change one variable at a time, keeping the rest constant, to isolate its effect.

#### Step 6: Set up the test bench

1. Place each UE together with the device that plays its stimulus on a tripod or equivalent support. The screen of the playback device must face the UE camera, which must capture the whole screen, at a distance where the UE microphone also captures the audio.
2. Make sure all UE receive similar signal levels, to avoid variability caused by signal differences.
3. Keep lighting and ambient noise constant throughout all experiments.

In this work, three terminals were placed in a coverage area of about 6 meters.

#### Step 7: Run the experiments

For each scenario, run the 21 iterations (or the number you define):

1. Check connectivity between the UE.
2. Start the capture with `tshark` before the call.
3. Play the corresponding stimulus and start iPerf3 if the scenario requires congestion.
4. Start the one-minute video call and, when it ends, save the generated `.pcapng` file.
5. Retrieve the baresip+ logs from each terminal every 7 calls, to avoid data loss by overwriting. This produces 3 log files per scenario.

#### Step 8: Process the data and compute the metrics

1. Process the `.pcapng` files and the baresip+ logs with the Python scripts in `analysis/`, to extract the network metrics per user and flow: delay, jitter, packet loss and bitrate, for both audio and video.
2. Compute the quality metrics $S_q$, $V_q$ and $MM_q$ following ITU-T G.1070, using the equations and constants of the recommendation and the delay approximation described below.
3. Group the results by operating condition (for example, averaging across encryption modes) and compute the mean and the standard error of the mean (SEM) of each metric, propagating the uncertainty when scenarios are averaged:

$$
\bar{\mu} = \frac{1}{n}\sum_{i=1}^{n} \mu_i, \qquad
\overline{\text{SEM}} = \frac{1}{n}\sqrt{\sum_{i=1}^{n} \text{SEM}_i^2}
$$

See the [data processing guide](docs/data-processing.md) for how to run each script.

**Delay approximation.** The jitter buffer of the client is not observable, so the delay used in the quality model is the one-way network delay plus the jitter. This is a lower bound of the real delay, and therefore the $S_q$, $V_q$ and $MM_q$ values are an upper bound of the real quality.

If something does not work as expected, check the [troubleshooting guide](docs/troubleshooting.md).

## Multimedia Database

To make the experiments reproducible, the video calls do not use live speech or scenes. Instead, a database of **21 standardized audiovisual stimuli** is played in front of each terminal's microphone and camera.

- **Audio.** Speech material from Annexes C and D of ITU-T P.501 (super-wideband, 48 kHz), combined into sequences of ($i$, $j$, $Δ1$, $Δ2$) tuples that balance gender and language between male speakers, female speakers and the second language set.
- **Video.** Sequences from the LIVE-Qualcomm database, covering its three distortion categories: Sharpness, Stabilization and Artifacts. The original YUV files are converted to MP4 with `ffmpeg`.
- **Playback.** Each stimulus is played from a separate device placed in front of the terminal, so the full capture and encoding chain of the phone is exercised.

The audio-video correspondence, the sequence tuples and the conversion scripts are in `multimedia/`.

> **Note on licenses:** the original ITU-T P.501 and LIVE-Qualcomm material belongs to their authors and is subject to their own terms. Check them before redistributing any file.

## Metrics and QoE Computation

For each call, the following per-flow metrics are extracted for audio (S) and video (V), in each direction:

| Metric | Symbol |
|---|---|
| One-way delay | $d_S$, $d_V$ |
| Jitter | $j_S$, $j_V$ |
| Packet loss | $P_{pl_S}$, $P_{pl_V}$ |
| Bitrate | $Br_S$, $Br_V$ |

From these, the speech, video and multimedia quality scores (**$S_q$**, **$V_q$** and **$MM_q$**) are computed with the ITU-T G.1070 model, on a scale from 1 to 5. The client jitter buffer is not observable, so the transmission delay is approximated as $T \approx d + j$, which is a lower bound of the real delay. Consequently, the reported scores are an upper bound of the real quality.

Bitrate is mainly determined by the encoder (for example, AMR-WB is constant bitrate), so it is reported but not used to compare RAN platforms.

The scripts that compute all metrics are in `analysis/`.

## Main Results

The 18 scenarios were grouped into three conditions per platform (results averaged over 21 repetitions and over the encryption modes). The table shows the $MM_q$ score in each direction (A→B / B→A):

| Condition | srsRAN | OAI |
|---|---|---|
| C1: no congestion, 5QI 9 | 3.257 / 2.928 | 3.381 / 3.195 |
| C2: congestion, 5QI 9 | 2.922 / 2.508 | 3.067 / 2.793 |
| C3: congestion, 5QI 1 | 3.239 / 3.128 | 3.316 / 3.059 |

Main findings:

- **Congestion degrades quality** on both platforms, and the effect is stronger in the B→A direction, which is attributed to the hardware of the terminals.
- **OAI is more robust under congestion** when no traffic prioritization is applied.
- **srsRAN reacts more strongly to prioritization** with 5QI 1; for example, the B→A speech quality of srsRAN rises from 2.331 (C2) to 3.977 (C3).
- **Neither platform is globally superior**; the best choice depends on the metric and the network condition.
- **Speech quality is more sensitive** to the network conditions than video quality.

## Limitations

- Stimuli are played in front of the cameras and microphones of the terminals; they are not injected digitally, so capture conditions (lighting, noise, distance) must be controlled.
- The jitter buffer of the client is not observable, so the quality scores are an upper bound of the real quality.
- The results correspond to one hardware configuration (USRP B210, two specific smartphones) and may differ with other equipment.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Author

- **Diego Torreblanca**
- University of Chile, Department of Electrical Engineering
- Email: diego.torreblanca@ug.uchile.cl