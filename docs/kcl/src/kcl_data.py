"""Boaty Key Component List (BOATY-KCL-001) as data.

A "key component" is one whose characteristics feed the software, the
ArduPilot parameter set, the simulator's physics or an interface definition.
Foam, glands and fasteners are not key components.

Every key value carries a source class (SOURCES) so a reviewer can see how
much to trust it. check() validates references against the SRS, SSS, ADD and
FMEA data, recomputes the cost reconciliation and the supply-sag analysis,
and fails on anything inconsistent.
"""
import math
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DOCS / "sss" / "src"))
sys.path.insert(0, str(DOCS / "fmea" / "src"))
import fmea_data as F  # noqa: E402
import sss_data as SD  # noqa: E402

A = SD.A

# Upstream revisions the archived sources were taken from.
AP_COMMIT = "dbe792162d06cab66c3475fd5556bf7a120f119e"     # ArduPilot/ardupilot
WIKI_COMMIT = "5365bb696d91a16e6ffb5db2523f0bee0d13c94d"   # ArduPilot/ardupilot_wiki
AM32_COMMIT = "2738df3240baa5bd4295b460cf0c5cfe0bd49d97"   # am32-firmware/AM32

SOURCES = {
    "AP": ("ArduPilot source", "Read from ArduPilot's board definition, "
           "driver or parameter source at the commit below, and archived in "
           "docs/kcl/sources/. The firmware we flash is built from these "
           "files, so for the helm this beats the vendor's datasheet."),
    "FW": ("Firmware source", "Read from the ESC firmware (AM32) source "
           "at the commit below. Excerpt archived."),
    "WEB": ("Vendor spec (web)", "Vendor or retailer specification seen "
            "through web search. Not yet checked against an archived PDF."),
    "KN": ("Known datasheet value", "A well-known datasheet figure quoted "
           "from memory. Must be checked against the archived PDF before "
           "it is relied on."),
    "EST": ("Engineering estimate", "Calculated or assumed. Replaced by a "
            "measurement at the stage shown."),
    "TEST": ("Measure", "No trustworthy datasheet exists (salvaged, "
             "generic or water-loaded parts). The bench test is the "
             "datasheet."),
}

# ----------------------------------------------------------------------
# Findings: things the KCL work changed or exposed.
# (id, title, text, severity, disposition)
# severity: "Decision" needs the owner; "Change" goes into the next issues;
# "Note" is informative.
# ----------------------------------------------------------------------
FINDINGS = [
    ("KF-01", "The baseline flight controller browns out near empty",
     "The Matek F405-TE needs at least 9 V in. Our 3S Li-ion pack is at "
     "9.6 V (resting) when the critical battery failsafe fires, and it sags "
     "under load: with acceptance-limit cells the pack resistance is about "
     "0.22 Ω. So the F405-TE would reset during the return-home it is "
     "flying, above about 1.4 A of motor current (section 5). PWR-D12 "
     "already requires supplies to hold at 9.0 V, which the F405-TE cannot "
     "meet. The SpeedyBee F405 WING APP runs from 7 V, has microSD "
     "logging, 12 DShot outputs and an ArduPilot board definition, and "
     "costs about £17 less.",
     "Decision", "CR-04 accepted (Issue B): KC-01 is the SpeedyBee F405 "
     "WING APP (ADD DD-19)"),
    ("KF-02", "Limit motor power so sag can't brown out anything",
     "Even with the SpeedyBee, full thrust on a nearly flat, high-"
     "resistance pack could pull the rail below the ESCs' 7.2 V minimum. "
     "ArduPilot's BATT_WATT_MAX (Rover) reduces maximum throttle when "
     "power exceeds a limit. Set to 70 W, it keeps the rail above 7.5 V at "
     "the critical failsafe voltage while still leaving about 2 N of "
     "thrust, against 1.1 N needed for ENV-002.",
     "Change", "HLM parameter baseline (section 7)"),
    ("KF-03", "The arming-key MOSFET must switch the positive side",
     "ICD IF-06 says 'gate pulled down → rail off', which reads like a "
     "low-side N-MOSFET, the kind of cheap trigger module sold for this. "
     "Switching the ESC negative while its signal ground is tied to the "
     "flight controller lets motor current find a way back through the "
     "signal wires, which can destroy the FC's output pins. So the key "
     "switch shall be a high-side P-MOSFET, with a gate RC to soft-start "
     "the ESC input capacitors (2 × 470 µF).",
     "Change", "ICD IF-06, SSS-PWR PWR-D07"),
    ("KF-04", "The flight controller's built-in wireless is a second, "
     "uncontrolled command path",
     "The SpeedyBee stack includes a Wi-Fi/Bluetooth board wired to UART6 "
     "and set up for MAVLink by default. That would let any phone near the "
     "boat talk to the autopilot, bypassing IF-01/IF-02 and the adult PIN. "
     "Don't fit the wireless board, and set SERIAL6_PROTOCOL = -1 as well.",
     "Change", "HLM parameter baseline, ICD IF-02"),
    ("KF-05", "Two microSD cards, not one",
     "The Pi Zero 2W boots from one card; the flight controller logs to "
     "another (DD-15). The ADD BOM counted one. +£4.",
     "Change", "ADD BOM"),
    ("KF-06", "The boat link must be 2.4 GHz",
     "The Pi Zero 2W's radio is 2.4 GHz only. The bank access point must "
     "run on 2.4 GHz (channel 1, 6 or 11). MT7610U/MT7612U USB adapters "
     "have in-kernel (mt76) drivers with access-point mode on Raspberry Pi "
     "OS, so no out-of-tree driver is needed.",
     "Change", "ICD IF-01"),
    ("KF-07", "The simulator needs our own boat physics",
     "ArduPilot's built-in motorboat model gives 50 N at full throttle "
     "(hull drag equal to thrust at 10 m/s). Ours is roughly 4 N at "
     "1.5 m/s. Simulated failsafe and weed tests would be meaningless at "
     "that scale. SITL has a JSON interface for an external physics model, "
     "so we write a small Python boat model parameterised from this list "
     "(section 8).",
     "Change", "Proposed DD-19; SSS-SIM, ICD IF-21"),
    ("KF-08", "Turn off the ESC's own low-voltage cut-off",
     "AM32 has a configurable low-voltage cut-off that stops the motor "
     "after 10 s below its threshold. On a Li-ion pack it could strand the "
     "boat while ArduPilot is still trying to bring it home. Disable it in "
     "the ESC settings; battery protection belongs to the helm "
     "(FS-001) and the BMS.",
     "Change", "SSS-PRP ESC configuration"),
    ("KF-09", "Free motor-RPM telemetry (opportunity)",
     "AM32 supports bidirectional DShot, which reports each motor's RPM "
     "to ArduPilot. That gives B7 a direct 'motor dead / prop fouled' "
     "signal instead of inferring it from track divergence (FM-16, FM-27). "
     "It needs the motors on outputs 1 and 4, the only BIDIR-capable "
     "output on each of the first two timer groups. Not in the baseline; "
     "worth a bench trial.",
     "Note", "Candidate for HLM Issue D"),
    ("KF-10", "Calibrate the battery monitor on the bench",
     "ArduPilot's board file and its README disagree on the voltage scale "
     "(11.05 against 11.5), which is a 4% difference and outside the "
     "± 1% of PWR-D13. The current scale (50 A/V) depends on the PDB fitted. "
     "Both get calibrated against a multimeter (IF-07 test).",
     "Note", "IF-07 bench test"),
    ("KF-11", "The Pi 5 has no analogue audio output",
     "The speaker must be USB (or a USB sound card), not a 3.5 mm jack "
     "speaker.",
     "Change", "MCN purchasing"),
]

# ----------------------------------------------------------------------
# Key components.
# Each: id, name, subsystem, qty, proposed part, alternatives, status,
# why it's key, values [(parameter, value, source, used by)], refs.
# ----------------------------------------------------------------------
KC = []


def kc(cid, name, ss, qty, part, alts, status, why, values, refs):
    KC.append(dict(id=cid, name=name, ss=ss, qty=qty, part=part, alts=alts,
                   status=status, why=why, values=values, refs=refs))


kc("KC-01", "Flight controller (helm)", "HLM", 1,
   "SpeedyBee F405 WING APP (FC + PDB; wireless board not fitted)",
   "Baseline: Matek F405-TE (fails KF-01). Matek F405-WTE runs from 6.8 V "
   "but is end-of-life.",
   "Baseline (CR-04 accepted)",
   "Every helm parameter, UART, ADC and output assignment comes from its "
   "board definition.",
   [("MCU", "STM32F405, 168 MHz, 1 MB flash", "AP", "V-01"),
    ("Input voltage", "2-6S; 7-36 V", "WEB", "PWR-D12, KF-01"),
    ("5 V BEC", "5.2 V, 2.4 A continuous / 3 A peak", "WEB", "IF-07, IF-22, "
     "IF-09"),
    ("IMU / baro", "ICM42688-P (SPI) / SPL06 (I2C 0x76)", "AP", "HLM"),
    ("Compass", "None on board; probes external I2C", "AP", "IF-22"),
    ("Logging", "microSD on SPI3 (FATFS); LOG_BACKEND_TYPE = 1", "AP",
     "LOG-001, DD-15"),
    ("UART map", "SERIAL1 USART1 (DMA) · SERIAL2 USART2 (SBUS inverter) · "
     "SERIAL3 USART3 (GPS) · SERIAL4 UART4 · SERIAL5 UART5 · SERIAL6 USART6 "
     "(wireless board)", "AP", "IF-04, IF-22"),
    ("Companion UART", "SERIAL1 (USART1, DMA both ways): Pi Zero MAVLink",
     "AP", "IF-04"),
    ("PWM outputs", "12, all DShot. Groups 1-2 (TIM4), 3-4 (TIM3), 5-7 "
     "(TIM8), 8-10 (TIM2), 11-12 (TIM1). BIDIR on outputs 1 and 4. "
     "Output 12 = LED pad", "AP", "IF-05, IF-09"),
    ("Battery monitor", "BATT_VOLT_PIN 10, BATT_CURR_PIN 11; scale 11.05 "
     "(hwdef) or 11.5 (README), 50 A/V: calibrate", "AP", "IF-07, KF-10"),
    ("Spare ADC", "RSSI pad = ADC pin 14, AIRSPD pad = pin 15; 3.3 V "
     "full scale, no on-board divider", "AP", "IF-06"),
    ("Current sensor", "90 A continuous, 215 A peak", "AP", "IF-07"),
    ("Mass", "≈ 25 g FC + PDB (12 g allocated)", "EST", "MEC-002"),
    ],
   ["V-01", "IF-04", "IF-05", "IF-07", "IF-09", "IF-22", "DD-15",
    "PWR-D12", "PWR-D13"])

kc("KC-02", "GNSS receiver + compass", "HLM", 1,
   "M10 GNSS with QMC5883L compass on one board (e.g. Matek/UMT "
   "M10Q-5883 or Foxeer M10Q-250-5883)",
   "Any u-blox M10 + ArduPilot-supported compass (QMC5883L/P, IST8310)",
   "Proposed",
   "Sets position noise, update rate and the compass driver, address and "
   "orientation parameters.",
   [("Receiver", "u-blox M10 (SAM-M10Q), GPS + Galileo + BeiDou + GLONASS",
     "WEB", "NAV-008"),
    ("Update rate", "5 Hz UBX with four constellations; ArduPilot "
     "configures it (GPS_TYPE auto)", "WEB", "HLM"),
    ("Default baud", "9600; ArduPilot auto-bauds and reconfigures", "WEB",
     "IF-22"),
    ("Horizontal accuracy", "≈ 1.5 m CEP open sky", "KN", "SIM model"),
    ("Supply", "4-9 V; ≈ 13 mA (receiver)", "WEB", "IF-22"),
    ("Compass", "QMC5883L on I2C, address 0x0D; ArduPilot probes it as "
     "external", "AP", "IF-22, TBC-09"),
    ("Temperature range", "−20 to 80 °C", "WEB", "-"),
    ],
   ["IF-22", "NAV-008", "V-16"])

kc("KC-03", "Electronic speed controller (×2)", "PRP", 2,
   "AM32 single ESC, 20 A, 2-6S (e.g. OddityRC AM32 6S 20A Nano)",
   "BLHeli_S ESC flashed with Bluejay (≈ £7 each; SERVO_DSHOT_ESC = 2). "
   "AM32 preferred: maintained, configurable, RPM telemetry.",
   "Proposed",
   "Its protocol, reversing, signal-loss and low-voltage behaviour are "
   "failsafe behaviour. They are modelled in SITL and tested on L2.",
   [("Protocol", "DShot300/600 and PWM", "WEB", "IF-05"),
    ("Reversible", "3D mode via SERVO_BLH_3DMASK (ArduPilot configures "
     "AM32 at boot)", "AP", "IF-05, PRP-D01"),
    ("Voltage", "7.2-25.2 V (2-6S)", "WEB", "KF-02"),
    ("Current", "20 A continuous, 30 A burst (10 s)", "WEB", "PRP-D05"),
    ("Signal loss, armed", "All phases off and reset after 0.5 s", "FW",
     "PRP-D07, FS-008, V-09"),
    ("Re-arm", "Needs > 1 s of zero command before it will drive again",
     "FW", "PRP-D08"),
    ("Low-voltage cut-off", "Configurable; stops after 10 s below "
     "threshold → disable (KF-08)", "FW", "FS-001"),
    ("Telemetry", "Bidirectional DShot RPM (optional, KF-09)", "WEB",
     "FM-16"),
    ("BEC", "5 V 1 A: leave unconnected (don't parallel with the FC BEC)",
     "WEB", "IF-07"),
    ("Mass", "2.6 g board; 36 × 24 mm", "WEB", "MEC-002"),
    ],
   ["IF-05", "PRP-D05", "PRP-D06", "PRP-D07", "PRP-D08", "V-09"])

kc("KC-04", "Thruster motor (×2)", "PRP", 2,
   "2205-2207 FPV outrunner, 1700-2300 KV, 5 mm shaft, run flooded",
   "Sealed ROV thruster motors (much dearer; future option)",
   "Class only",
   "Thrust and current against throttle are the most important simulator "
   "inputs, and no datasheet covers a small motor turning a printed prop "
   "in water.",
   [("Stator / KV", "2205-2207 / 1700-2300 KV (class)", "EST", "PRP-D02"),
    ("Static thrust, each", "≥ 2.0 N forward, ≥ 0.75 N astern (PRP-D02 "
     "split)", "EST", "SIM model"),
    ("Thrust vs throttle", "Assume T ∝ throttle² until measured", "EST",
     "SIM model"),
    ("Current at full throttle", "≤ 8 A each (PRP-D05 limit)", "TEST",
     "IF-06, TBC-06"),
    ("Spin-up time constant", "≈ 0.1 s", "EST", "SIM model"),
    ],
   ["PRP-D02", "PRP-D05", "IF-06"])

kc("KC-05", "Battery cells (×3)", "PWR", 3,
   "Salvaged 18650 Li-ion accepted to PWR-D20",
   "New cells (e.g. 3000 mAh, 15 A class) if too few pass",
   "Baseline (CR-03)",
   "Capacity and internal resistance set the failsafe thresholds, "
   "endurance and supply sag.",
   [("Capacity", "≥ 2500 mAh each at 1 A (acceptance)", "TEST",
     "PWR-D20, BATT_CAPACITY"),
    ("Internal resistance", "≤ 60 mΩ each (acceptance); matched within "
     "10 mΩ", "TEST", "KF-01, KF-02"),
    ("Voltage", "4.2 V full, 3.6 V nominal, 2.5-3.0 V empty per cell",
     "KN", "FS-001"),
    ("Pack", "3S1P: 12.6 V full, 10.8 V nominal", "EST", "IF-06"),
    ],
   ["PWR-D01", "PWR-D20", "PWR-D21"])

kc("KC-06", "Battery management system", "PWR", 1,
   "3S Li-ion BMS, 20-25 A, with balancing",
   "-", "Class only",
   "Its over-discharge cut-off is the last line after the helm failsafes; "
   "it must never act before them.",
   [("Over-discharge", "2.5-2.8 V/cell (PWR-D02)", "TEST", "FS-001"),
    ("Over-current trip", "≤ 25 A", "TEST", "PWR-D02"),
    ("Series resistance", "≈ 15 mΩ (in the sag budget)", "EST", "KF-01"),
    ],
   ["PWR-D02"])

kc("KC-07", "Arming-key switch", "PWR", 1,
   "Glass reed switch (normally open) driving a high-side P-MOSFET "
   "(AOD4185 class) on a small perfboard",
   "Low-side trigger modules are not acceptable (KF-03)",
   "Proposed",
   "Its state is what the helm senses (BATT2) to allow arming. Its "
   "switching time and inrush are part of L2 tests.",
   [("MOSFET", "P-channel, V_DS ≥ 30 V, I_D ≥ 30 A, R_DS(on) ≤ 15 mΩ at "
     "V_GS = −10 V", "EST", "IF-06"),
    ("Gate drive", "Reed closes → gate pulled toward ground via divider, "
     "V_GS clamped −10 V; open → 10 kΩ pulls gate to source (off, fails "
     "safe)", "EST", "PWR-D07"),
    ("Soft start", "Gate RC ≈ 10 ms to limit inrush into 2 × 470 µF", "EST",
     "KF-03"),
    ("Rail sense", "Divider 10 kΩ / 1 kΩ from the switched rail to the "
     "AIRSPD pad (ADC pin 15)", "EST", "PWR-D08, V-13"),
    ],
   ["IF-06", "PWR-D07", "PWR-D08", "PWR-D09", "V-13"])

kc("KC-09", "5 V buck for the mission computer", "PWR", 1,
   "Synchronous buck module, 5.1 V, ≥ 3 A continuous",
   "Pololu D36V28F5 (dearer, well documented)", "Class only",
   "Its minimum input voltage decides whether the mission computer "
   "survives sag. It is part of the sag analysis.",
   [("Output", "5.1 V ± 2%, ≥ 3 A continuous", "EST", "IF-08"),
    ("Minimum input", "≤ 6.5 V at 1 A load", "EST", "KF-02"),
    ("Ripple", "≤ 50 mV p-p", "EST", "IF-08"),
    ],
   ["IF-08", "PWR-D11", "PWR-D12"])

kc("KC-10", "Mission computer", "MCP", 1, "Raspberry Pi Zero 2 W",
   "-", "Baseline",
   "Radio band, GPIO, 1-Wire and UART assignments feed IF-01, IF-03, IF-04.",
   [("SoC", "RP3A0: 4 × Cortex-A53 at 1 GHz, 512 MB", "KN", "MCP-D01"),
    ("Wi-Fi", "2.4 GHz 802.11 b/g/n only", "KN", "IF-01, KF-06"),
    ("UART to helm", "GPIO14/15 (PL011 with Bluetooth disabled), 3.3 V",
     "KN", "IF-04"),
    ("1-Wire", "GPIO4 (w1-gpio overlay) for KC-12", "KN", "MCP-D04"),
    ("Moisture input", "GPIO with pull-up; traces short to ground when wet",
     "EST", "MCP-D03"),
    ("Power", "≈ 0.6 W idle, ≈ 3 W peak with camera", "KN", "MCP-D05"),
    ],
   ["MCP-D01", "MCP-D03", "MCP-D05", "IF-01", "IF-04"])

kc("KC-11", "Camera", "MCP", 1,
   "OV5647 5 MP module with Pi Zero ribbon (Camera Module v1 compatible)",
   "Camera Module 3 (dearer, autofocus)", "Baseline",
   "Field of view, resolution and capture latency set B2's photo "
   "geometry and timing.",
   [("Sensor", "OV5647, 2592 × 1944; libcamera driver ov5647", "KN",
     "MCP-D10"),
    ("Horizontal FOV", "≈ 54° (standard lens)", "KN", "MCP-D02"),
    ("Still capture latency", "≈ 0.3-1 s in software", "TEST", "MCP-D10"),
    ],
   ["MCP-D02", "MCP-D10", "MCP-D11"])

kc("KC-12", "Box temperature sensor", "MCP", 1, "DS18B20 (TO-92)",
   "-", "Baseline (FMEA A-11)",
   "B6 raises RTL at 60 °C box temperature from this reading.",
   [("Accuracy", "± 0.5 °C from −10 to +85 °C", "KN", "A-11"),
    ("Conversion time", "750 ms at 12-bit", "KN", "MCP-D15"),
    ("Interface", "1-Wire, 3.0-5.5 V, 4.7 kΩ pull-up", "KN", "MCP-D04"),
    ],
   ["A-11", "MCP-D15"])

kc("KC-14", "LED beacon", "REC", 1,
   "WS2812B addressable LEDs (4-8) on the FC LED pad",
   "-", "Baseline",
   "The helm drives it, so the notify-LED parameters and the output "
   "assignment depend on it.",
   [("Drive", "Output 12 (LED pad), SERVO12_FUNCTION = 120 (NeoPixel1)",
     "AP", "IF-09"),
    ("Supply / data", "5 V; 3.3 V data works on most WS2812B, marginal "
     "on some (TBC-08)", "KN", "IF-09"),
    ("Current", "≈ 60 mA per LED at full white", "KN", "IF-07"),
    ],
   ["IF-09", "REC-004"])

kc("KC-15", "Bank Wi-Fi adapter", "MCN", 1,
   "USB adapter on MT7610U or MT7612U chipset with external antenna",
   "Pi 5 on-board Wi-Fi (shorter range; no external antenna)",
   "Proposed",
   "It must run as an access point on 2.4 GHz with an in-kernel driver.",
   [("Driver", "mt76x0u / mt76x2u, in-kernel since Linux 4.19", "WEB",
     "IF-01"),
    ("AP mode", "Supported (hostapd)", "WEB", "IF-01"),
    ("Band used", "2.4 GHz, channel 1/6/11 (Pi Zero 2W limit)", "KN",
     "KF-06"),
    ],
   ["IF-01", "MCP-D16"])

kc("KC-16", "Mission Control computer", "MCN", 1,
   "Raspberry Pi 5 (owned)", "-", "Baseline",
   "Hosts C1-C10. GPIO for the panel, USB for audio and Wi-Fi.",
   [("Audio", "No analogue output: USB speaker required (KF-11)", "KN",
     "IF-12"),
    ("Power", "≈ 5 W average, ≈ 8 W peak (STT)", "EST", "MC-006"),
    ],
   ["IF-12"])

kc("KC-17", "Microphone and speaker", "MCN", 1,
   "USB microphone (16 kHz mono capable) and USB speaker",
   "USB sound card + small powered speaker", "Class only",
   "On-device STT/TTS sample rate and device names.",
   [("Mic format", "16 kHz, 16-bit mono (resampled if needed)", "EST",
     "NLI-002"),
    ("Speaker", "USB audio class, ≥ 85 dB at 1 m", "EST", "NLI-003"),
    ],
   ["NLI-002"])

kc("KC-18", "Panel buttons (×4)", "MCN", 4,
   "30 mm arcade buttons with 5 V LED",
   "12 V-LED versions need a different driver: avoid", "Class only",
   "Debounce timing and LED drive feed IF-12.",
   [("Switch", "Normally-open microswitch; bounce ≤ 10 ms", "EST", "IF-12"),
    ("LED", "5 V, ≈ 20 mA, driven through N-MOSFET", "EST", "IF-12"),
    ],
   ["IF-12", "MC-002"])

kc("KC-19", "microSD cards (×2)", "MCP", 2,
   "32 GB A1/U1 (one for the Pi Zero, one for the flight controller)",
   "-", "Proposed (KF-05)",
   "The FC needs FAT32 (≤ 32 GB). The Pi reserves ≥ 5 GB for photos.",
   [("FC card", "≤ 32 GB, FAT32", "AP", "DD-15"),
    ("Pi card", "32 GB, A1 or better; read-only root", "EST", "MCP-D13"),
    ],
   ["DD-15", "MCP-D13"])

# ----------------------------------------------------------------------
# Cost reconciliation. (group, item, £ estimate, KC refs, change note)
# Prices are estimates: UK retail sites were not reachable from the build
# environment, so they are from search results and earlier estimates.
# ----------------------------------------------------------------------
CAP, TARGET = 185, 180
NEW_BOM = [
    ("Boat", "Flight controller: SpeedyBee F405 WING APP (FC + PDB)", 45,
     ["KC-01"], "−£17 (was Matek F405-TE £62; CR-04)"),
    ("Boat", "M10 GNSS + QMC5883L compass", 14, ["KC-02"], "-"),
    ("Boat", "Pi Zero 2W", 15, ["KC-10"], "-"),
    ("Boat", "OV5647 camera + Zero cable", 8, ["KC-11"], "-"),
    ("Boat", "microSD 32 GB × 2", 8, ["KC-19"], "+£4 (KF-05)"),
    ("Boat", "2 × 2205-class motor", 12, ["KC-04"], "-"),
    ("Boat", "2 × AM32 20 A ESC", 22, ["KC-03"], "+£12 (was £10; "
     "realistic price)"),
    ("Boat", "3 × tested salvaged 18650 + 3S BMS", 7, ["KC-05", "KC-06"],
     "-"),
    ("Boat", "Box, PG7 glands, fuse", 6, [], "-"),
    ("Boat", "Foam, hi-vis, WS2812B beacon", 5, ["KC-14"], "-"),
    ("Boat", "5 V 3 A buck", 3, ["KC-09"], "-"),
    ("Boat", "Reed switch + high-side P-MOSFET switch", 4, ["KC-07"],
     "Same cost, different circuit (KF-03)"),
    ("Boat", "IP67 main power switch", 4, [], "-"),
    ("Boat", "DS18B20 box temperature sensor", 2, ["KC-12"], "-"),
    ("Bank", "4 arcade buttons (5 V LED)", 6, ["KC-18"], "-"),
    ("Bank", "USB mic + USB speaker", 8, ["KC-17"], "Speaker must be USB "
     "(KF-11)"),
    ("Bank", "USB Wi-Fi adapter, MT7610U/MT7612U", 12, ["KC-15"], "-"),
]
CONDITIONAL = [("Bank*", "2 m pole + 3 m USB extension (only if V-08 "
                "needs it)", 8)]



def old_total():
    """ADD baseline BOM, excluding conditional (starred) lines."""
    return sum(p for g, _, p in A.BOM if not g.endswith("*"))


# ----------------------------------------------------------------------
# Supply-sag analysis (KF-01, KF-02).
# ----------------------------------------------------------------------
R_CELL = 0.060           # acceptance limit per cell (PWR-D20)
R_BMS = 0.015
R_HARNESS = 0.025        # fuse, switch, connectors, wire
R_PACK = 3 * R_CELL + R_BMS + R_HARNESS
V_CRT = 9.6              # BATT_CRT_VOLT (resting, sag-compensated)
MARGIN = 0.3
LOADS = [("Cruise (1.0 m/s)", 1.0), ("Half throttle, both", 5.0),
         ("Full throttle, both (PRP-D05 limit)", 16.0)]
SUPPLY_MIN = [("Matek F405-TE (baseline)", 9.0, "WEB"),
              ("SpeedyBee F405 WING APP", 7.0, "WEB"),
              ("AM32 20 A ESC", 7.2, "WEB"),
              ("5 V buck (KC-09 spec)", 6.5, "EST")]


def i_allow(vmin):
    """Largest current keeping the rail ≥ vmin + margin at V_CRT."""
    return max(0.0, (V_CRT - vmin - MARGIN) / R_PACK)


def watt_max():
    """BATT_WATT_MAX for the proposed set, rounded down to 5 W."""
    vmin = max(v for n, v, _ in SUPPLY_MIN[1:])
    i = i_allow(vmin)
    return int((vmin + MARGIN) * i // 5 * 5)


def thrust_at_power_limit(full_w=190.0, full_n=4.0):
    """Thrust left under BATT_WATT_MAX, using T ∝ P^(2/3) (momentum
    theory, static)."""
    return full_n * (watt_max() / full_w) ** (2 / 3)


# ----------------------------------------------------------------------
# Parameter baseline delta for SSS-HLM Issue D (after CR-04).
# (parameter, value, was, source, KC/KF refs)
# ----------------------------------------------------------------------
PARAM_DELTA = [
    ("SERIAL1_PROTOCOL / SERIAL1_BAUD", "2 (MAVLink 2) / 115", "SERIAL2 "
     "(TBC-02)", "AP", ["KC-01", "IF-04"]),
    ("SERIAL2_PROTOCOL", "-1 (unused; SBUS inverter on RX)", "Companion",
     "AP", ["KC-01"]),
    ("SERIAL3_PROTOCOL", "5 (GPS)", "-", "AP", ["KC-02", "IF-22"]),
    ("SERIAL6_PROTOCOL", "-1 (wireless board not fitted)", "Board default 2",
     "AP", ["KF-04"]),
    ("SERVO1_FUNCTION / SERVO4_FUNCTION", "73 ThrottleLeft / 74 "
     "ThrottleRight", "SERVO1 / SERVO2", "AP", ["KC-01", "KF-09"]),
    ("MOT_PWM_TYPE", "6 (DShot300)", "DShot300 (TBC-05)", "AP",
     ["KC-03", "IF-05"]),
    ("SERVO_DSHOT_ESC", "1 (AM32)", "-", "AP", ["KC-03"]),
    ("SERVO_BLH_3DMASK", "9 (outputs 1 and 4 reversible)", "-", "AP",
     ["KC-03", "IF-05"]),
    ("SERVO_BLH_RVMASK", "Set on the bench so forward is forward", "-",
     "TEST", ["KC-03"]),
    ("MOT_REV_DELAY", "0.2 s (tune on L2)", "-", "EST", ["KC-03", "KC-04"]),
    ("BATT_VOLT_MULT / BATT_AMP_PERVLT", "Calibrated (≈ 11.05-11.5 / 50)",
     "Measured", "AP", ["KF-10", "IF-07"]),
    ("BATT_FS_VOLTSRC", "1 (sag-compensated)", "-", "AP", ["KF-01"]),
    ("BATT_WATT_MAX / MOT_BAT_WATT_TC", "{watt} W / 2 s", "-", "EST",
     ["KF-02"]),
    ("BATT2_MONITOR / BATT2_VOLT_PIN / BATT2_VOLT_MULT", "3 (analogue "
     "voltage) / 15 (AIRSPD pad) / 11.0", "Analogue V", "AP",
     ["KC-07", "IF-06"]),
    ("LOG_BACKEND_TYPE", "1 (file on microSD)", "File", "AP", ["KC-01"]),
    ("NTF_LED_TYPES / SERVO12_FUNCTION", "NeoPixel / 120 (LED pad)",
     "SERVO3 NeoPixel1", "AP", ["KC-14", "IF-09"]),
    ("GPS_TYPE", "1 (auto; u-blox configured by ArduPilot)", "Auto", "AP",
     ["KC-02"]),
    ("COMPASS_ORIENT / COMPASS_EXTERNAL", "Per mounting / 1", "Per module",
     "AP", ["KC-02", "IF-22"]),
]

# ----------------------------------------------------------------------
# Simulator model parameters (SITL JSON backend, proposed DD-19).
# (symbol, meaning, value, units, source, replaced by)
# ----------------------------------------------------------------------
MASS_KG = sum(m for _, m in A.MASS) / 1000
LOA, BEAM, POD_Y = 0.62, 0.36, 0.135
IZZ = MASS_KG * (LOA ** 2 + BEAM ** 2) / 12
K_SURGE = 0.5 * 1000 * 0.18 * 0.012 * 1.5    # from SSS-PRP section 6

SIM_MODEL = [
    ("m", "Mass (all-up)", f"{MASS_KG:.2f}", "kg", "EST (ADD mass budget)",
     "Weigh the build"),
    ("m_a", "Surge added mass", "10% of m", "kg", "EST", "Pool coast-down"),
    ("I_zz", "Yaw inertia, uniform box", f"{IZZ:.3f}", "kg·m²", "EST",
     "Pool turn tests"),
    ("y_pod", "Pod lateral offset (HUL-D04 / 2)", f"±{POD_Y:.3f}", "m", "EST",
     "CAD"),
    ("T_fwd", "Max forward thrust, each pod", "2.0", "N", "EST (PRP-D02)",
     "L3 bollard pull"),
    ("T_ast", "Max astern thrust, each pod", "0.75", "N", "EST (PRP-D02)",
     "L3 bollard pull"),
    ("T(u)", "Thrust law", "T_max · u·|u|", "-", "EST", "Thrust stand"),
    ("τ_m", "Motor spin-up time constant", "0.10", "s", "EST",
     "Thrust stand"),
    ("k_u", "Surge drag coefficient (F = k_u·v·|v|)", f"{K_SURGE:.2f}",
     "N·s²/m²", "EST (SSS-PRP §6)", "Pool coast-down"),
    ("k_r", "Yaw damping (M = k_r·r·|r|)", "0.05", "N·m·s²", "EST",
     "Pool turn tests"),
    ("A_w, C_d", "Windage area and drag coefficient", "0.035, 1.1",
     "m², -", "EST (SSS-PRP §6)", "-"),
    ("P(T)", "Electrical power per pod", "k_p · T^1.5, k_p set so cruise "
     "draws 8 W", "W", "EST", "Thrust stand current"),
    ("P_hotel", "Hotel load", "3.1", "W", "EST (ADD power budget)",
     "Bench"),
    ("C, R_pack", "Pack capacity and resistance", f"2.5, {R_PACK:.2f}",
     "Ah, Ω", "TEST (PWR-D20 limits)", "Cell acceptance data"),
    ("OCV(SoC)", "Open-circuit voltage curve", "Generic NMC 18650 table",
     "V", "KN", "Discharge test"),
    ("σ_gnss, f_gnss", "GNSS noise and rate", "1.0, 5", "m, Hz", "KN / WEB",
     "Static log on the bank"),
    ("V_min", "Supply brown-out thresholds", "FC 7.0, ESC 7.2, buck 6.5",
     "V", "WEB / EST", "L2 sag test"),
]

# ----------------------------------------------------------------------
# Datasheet register. url None = still to locate.
# (id, KC, document, url, status)
# status: Archived | To fetch | To locate | Measure
# ----------------------------------------------------------------------
DATASHEETS = [
    ("DS-01", "KC-01", "ArduPilot board definition, SpeedyBeeF405WING "
     "(hwdef.dat, README, defaults, pinout, wiring)",
     "https://github.com/ArduPilot/ardupilot/tree/" + AP_COMMIT +
     "/libraries/AP_HAL_ChibiOS/hwdef/SpeedyBeeF405WING", "Archived"),
    ("DS-02", "KC-01", "SpeedyBee F405 WING APP user manual",
     None, "To locate"),
    ("DS-03", "KC-01", "ArduPilot board definition, MatekF405-TE, and the "
     "F405-TE family wiki page (for the comparison)",
     "https://github.com/ArduPilot/ardupilot/tree/" + AP_COMMIT +
     "/libraries/AP_HAL_ChibiOS/hwdef/MatekF405-TE", "Archived"),
    ("DS-04", "KC-02", "Matek M10Q-5883 product page and manual",
     "https://www.mateksys.com/?portfolio=m10q-5883", "To fetch"),
    ("DS-05", "KC-02", "u-blox SAM-M10Q data sheet", None, "To locate"),
    ("DS-06", "KC-02", "QST QMC5883L data sheet", None, "To locate"),
    ("DS-07", "KC-03", "OddityRC AM32 6S 20A Nano ESC product page",
     "https://oddityrc.com/products/am32-6s-20a-nano-esc", "To fetch"),
    ("DS-08", "KC-03", "AM32 firmware source: signal-loss and re-arm logic "
     "(excerpt)", "https://github.com/am32-firmware/AM32/blob/" + AM32_COMMIT
     + "/Src/main.c", "Archived"),
    ("DS-09", "KC-04", "Motor + printed prop: thrust, current and RPM "
     "against throttle, in water", None, "Measure"),
    ("DS-10", "KC-05", "Cell acceptance records (PWR-D21)", None, "Measure"),
    ("DS-11", "KC-06", "BMS: trip thresholds measured on the bench", None,
     "Measure"),
    ("DS-12", "KC-07", "AOD4185 P-MOSFET data sheet", None, "To locate"),
    ("DS-13", "KC-10", "Raspberry Pi Zero 2 W product brief",
     "https://datasheets.raspberrypi.com/rpizero2/"
     "raspberry-pi-zero-2-w-product-brief.pdf", "To fetch"),
    ("DS-14", "KC-11", "Raspberry Pi camera documentation (OV5647 / "
     "Camera Module v1)",
     "https://www.raspberrypi.com/documentation/accessories/camera.html",
     "To fetch"),
    ("DS-15", "KC-12", "Analog Devices DS18B20 data sheet",
     "https://www.analog.com/media/en/technical-documentation/data-sheets/"
     "DS18B20.pdf", "To fetch"),
    ("DS-16", "KC-15", "MT7612U Linux support notes (morrownr/7612u)",
     "https://github.com/morrownr/7612u", "To fetch"),
    ("DS-17", "KC-16", "Raspberry Pi 5 product brief",
     "https://datasheets.raspberrypi.com/rpi5/"
     "raspberry-pi-5-product-brief.pdf", "To fetch"),
    ("DS-18", "-", "ArduPilot SITL JSON physics interface (readme)",
     "https://github.com/ArduPilot/ardupilot/tree/" + AP_COMMIT +
     "/libraries/SITL/examples/JSON", "Archived"),
    ("DS-19", "-", "ArduPilot SITL motorboat and skid-steer default "
     "parameters", "https://github.com/ArduPilot/ardupilot/tree/" + AP_COMMIT
     + "/Tools/autotest/default_params", "Archived"),
]

# ----------------------------------------------------------------------
# Consequential changes once CR-04 is decided.
# (document, change, refs)
# ----------------------------------------------------------------------
CHANGES = [
    ("ADD Issue F", "Done: KC-01 in HLM, BOM (£181) and mass budget (DD-19); "
     "own boat physics via SITL JSON (DD-20); DD-15 unchanged (microSD "
     "kept).", ["KF-01", "KF-05", "KF-07"]),
    ("ICD Issue E", "Done: IF-04 on SERIAL1 (TBC-02 closed); IF-05 outputs "
     "1 and 4, AM32 3D DShot (TBC-05 closed, bench check with V-09); IF-06 "
     "high-side switch and AIRSPD-pad sense (TBC-07 closed); SERIAL6 off; "
     "IF-21 rewritten for the JSON model (TBC-03/04 closed). IF-01 was "
     "already 2.4 GHz.", ["KF-03", "KF-04", "KF-06", "KF-07"]),
    ("SSS-HLM Issue D", "Done: parameter baseline now generated from "
     "software/params; BATT_WATT_MAX (HLM-D43) and one command path "
     "(HLM-D44).", ["KF-02", "KF-04"]),
    ("SSS-PWR Issue C", "Done: PWR-D07 high-side; PWR-D22 supplies work "
     "down to 7.5 V under the power limit.", ["KF-01", "KF-03"]),
    ("SSS-PRP Issue B", "Done: AM32 ESC and its configuration (3D, LVC "
     "off, BEC unused; PRP-D16).", ["KF-08"]),
    ("SSS-SIM Issue D", "Done: boat model from this list (SIM-D25); "
     "injections on the model side (SIM-D07).", ["KF-07"]),
    ("FMEA Issue D", "Done: FM-08 (supply brown-out) re-rated with its "
     "real cause and closed by A-21. Still open: RPM telemetry as a "
     "detection control for FM-16/FM-50 (dead motor vs weed).",
     ["KF-01", "KF-09"]),
]


# ----------------------------------------------------------------------
def valid_refs():
    srs = {r["id"] for r in SD.SRS.all_reqs()}
    derived = {d["id"] for ss in SD.SUBSYSTEMS.values()
               for d in SD.all_derived(ss)}
    ifs = {i[0] for i in A.INTERFACES}
    vs = {v[0] for v in A.VERIFY_EARLY}
    dds = {d[0] for d in A.DECISIONS}
    fm = {r[0] for r in F.ROWS} | {a[0] for a in F.ACTIONS}
    tbc = {f"TBC-{i:02d}" for i in range(1, 15)}
    own = {k["id"] for k in KC} | {f[0] for f in FINDINGS}
    return srs | derived | ifs | vs | dds | fm | tbc | own


def check():
    ok = valid_refs()
    ids = [k["id"] for k in KC]
    assert len(ids) == len(set(ids)), "duplicate KC id"
    bad = []
    for k in KC:
        assert k["values"], f"{k['id']} has no key values"
        for v in k["values"]:
            assert v[2] in SOURCES, f"{k['id']}: unknown source {v[2]}"
        bad += [r for r in k["refs"] if r not in ok]
    for p in PARAM_DELTA:
        assert p[3] in SOURCES, p
        bad += [r for r in p[4] if r not in ok]
    for b in NEW_BOM:
        bad += [r for r in b[3] if r not in ok]
    for c in CHANGES:
        bad += [r for r in c[2] if r not in ok]
    kcs = set(ids)
    for d in DATASHEETS:
        assert d[1] == "-" or d[1] in kcs, d
        assert d[4] in ("Archived", "To fetch", "To locate", "Measure"), d
        if d[4] == "To fetch":
            assert d[3], d
    assert not bad, f"unknown references: {sorted(set(bad))}"
    # Every KC except purely informative ones is costed or owned.
    costed = {r for b in NEW_BOM for r in b[3]}
    assert kcs - costed <= {"KC-16"}, kcs - costed
    total = sum(b[2] for b in NEW_BOM)
    assert total <= CAP, f"BOM £{total} exceeds cap £{CAP}"
    # The archived ArduPilot sources are from the commit the simulator is
    # built from and the helm will run (SDR RID-09).
    sitl = DOCS.parent / "software" / "boaty" / "sim" / "sitl.py"
    src = sitl.read_text()
    assert f'ARDUPILOT_COMMIT = "{AP_COMMIT}"' in src, \
        "KCL AP_COMMIT differs from software/boaty/sim/sitl.py"
    # Sag analysis must show the baseline fails and the proposal passes.
    assert i_allow(9.0) < LOADS[1][1], "F405-TE sag case no longer fails"
    assert watt_max() >= 50
    assert thrust_at_power_limit() > 1.1, "power limit starves ENV-002"
    return dict(total=total, old=old_total(),
                n=len(KC), watt=watt_max())


if __name__ == "__main__":
    print(check())
