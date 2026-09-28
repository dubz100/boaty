"""Boaty Architecture Design Document: the architecture as data.

build_add.py renders this; check() verifies that every SRS requirement is
allocated and that every interface joins known subsystems.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "srs" / "src"))
import requirements as SRS  # noqa: E402

# ------------------------------------------------------------------ drivers
DRIVERS = [
    ("SAF-001/002", "Fence and failsafes on an independent RTOS processor, "
     "working with everything else dead.", "Where safety logic may live"),
    ("FS-001..013", "Thirteen failsafe behaviours, most with timings.",
     "Which layer implements each one"),
    ("VAL-001..010", "Every mission passes one deterministic validator, "
     "then adult approval, then read-back.", "A single mission path"),
    ("NLI-001..008", "Spoken or typed instructions turned into missions via "
     "the Claude API.", "Where language processing happens"),
    ("SWE-001/003", "All project code in Python. Helm behind a swappable "
     "interface.", "Rules out C++ firmware of our own"),
    ("COM-002/005", "At least 100 m over water. Internet via phone. Boat link "
     "independent of internet.", "Link topology"),
    ("MC-001..015", "Pi 5 bank station, big buttons, voice, daylight "
     "display.", "Bank-side hardware"),
    ("CHD-*, MEC-007/009", "Tool-free chunky modules and a DUPLO deck for a "
     "4-year-old.", "Mechanical modularity"),
    ("CON-001", "Mk1 bill of materials ≤ £160 (target £150; raised from £120 by CR-01).",
     "Pushes against everything above"),
]

QUALITY_ORDER = [
    ("1", "Safety and recoverability", "The boat comes back, or stops "
     "inside the fence, whatever fails."),
    ("2", "Simplicity", "Fewest parts and processes that can be built, "
     "understood and debugged by one person."),
    ("3", "Crew experience", "It's his boat: buttons, voice, DUPLO, photos."),
    ("4", "Cost", "Close to the £100 target."),
    ("5", "Extensibility", "Room for duck spotting, a Python helm, longer "
     "range."),
]

# ------------------------------------------------------------------ divergence
# Morphological chart: (dimension, [options], index of selected option)
MORPH = [
    ("Where the intelligence lives (plan, validate, UI)",
     ["On the boat", "On the bank (Pi 5)", "Split: bank plans, boat "
      "re-plans", "In the cloud"], 1),
    ("Helm hardware",
     ["F405 flight controller (1 MB)", "H743 flight controller (2 MB, Lua)",
      "Pixhawk-class", "Linux autopilot HAT"], 0),
    ("On-boat mission computer",
     ["None (FC + Wi-Fi bridge)", "ESP32-S3 camera (C++)",
      "Pi Zero 2W + camera", "Pi 5 on the boat"], 2),
    ("Camera",
     ["Camera on mission computer", "FC-triggered action camera",
      "Live video, capture on bank", "Old phone on the boat"], 0),
    ("Boat-bank link",
     ["Boat is Wi-Fi AP", "Pi 5 is AP, antenna on 2 m pole", "Travel "
      "router on the bank", "868 MHz telemetry + Wi-Fi for photos"], 1),
    ("Internet on the bank",
     ["Phone Wi-Fi hotspot", "Phone USB tether to Pi 5", "LTE dongle",
      "Plan at home only"], 1),
    ("Language → mission",
     ["LLM writes waypoints", "LLM picks intent; Python makes geometry",
      "Templates only", "LLM in the loop during the mission"], 1),
    ("Speech",
     ["Cloud speech-to-text", "On-device STT + TTS on Pi 5",
      "Phone dictation", "Typed only"], 1),
    ("Display",
     ["Screen built into the box", "Phone / tablet web UI",
      "Buttons and voice only", "e-ink panel"], 1),
    ("Arming interlock",
     ["Software only", "Waterproof toggle switch",
      "Magnetic key switching motor power", "Pull-pin"], 2),
    ("Hull construction",
     ["Printed foam-filled segments", "PVC pipe pontoons, printed ends",
      "Carved XPS foam, skinned", "Printed monohull + outriggers"], 0),
    ("Battery",
     ["3S Li-ion 18650 + BMS", "3S LiPo", "10-cell NiMH",
      "Two packs (motors / avionics)"], 0),
]

CANDIDATES = [
    dict(id="AR-1", name="Smart boat",
         idea="The boat plans and validates its own missions on a companion "
              "computer. The bank is a thin remote.",
         pros="Keeps working if the link drops after launch.",
         cons="Needs internet on the boat for language. More compute and "
              "power afloat. Hardest to debug. Most code on the water.",
         scores=dict(saf=4, link=4, cost=3, simp=2, cover=3, ext=4)),
    dict(id="AR-2", name="Smart bank",
         idea="The Pi 5 does language, planning, validation, UI and photo "
              "processing. The boat has the ArduPilot helm and a small Pi "
              "Zero 2W for camera and link.",
         pros="Intelligence where power, internet and debugging are easy. "
              "The boat is simple. All project code is Python.",
         cons="Costs more than the minimal boat. Photos depend on a second "
              "boat computer.",
         scores=dict(saf=5, link=4, cost=4, simp=4, cover=5, ext=5),
         chosen=True),
    dict(id="AR-3", name="Minimal boat",
         idea="No mission computer. The FC plus an off-the-shelf Wi-Fi "
              "MAVLink bridge, with an FC-triggered action camera. The bank "
              "does everything.",
         pros="Cheapest and fewest parts. No project code on the boat.",
         cons="Photos only after the session, from the camera's SD card. No "
              "path to on-board duck spotting. Weak Wi-Fi bridge.",
         scores=dict(saf=5, link=4, cost=5, simp=4, cover=2, ext=2)),
    dict(id="AR-4", name="Dual-link",
         idea="AR-2 plus an 868 MHz telemetry radio for command and "
              "control. Wi-Fi only for photos near home.",
         pros="Much longer control range; link loss rarer.",
         cons="+£30 and two radios to integrate. UK 869 MHz duty-cycle "
              "limits. Range we don't need in a 100 m bay.",
         scores=dict(saf=5, link=5, cost=2, simp=2, cover=5, ext=4)),
    dict(id="AR-5", name="Phone as Mission Control",
         idea="A phone app replaces the Pi 5. The boat is as in AR-2.",
         pros="Cheap and portable, with a screen, GPS and internet built in.",
         cons="Touchscreen instead of big buttons. App code isn't Python. "
              "Ignores the owned Pi 5 (CON-002). Phone shared with a "
              "4-year-old.",
         scores=dict(saf=5, link=3, cost=5, simp=3, cover=2, ext=1)),
]

CRITERIA = [("saf", "Safety independence", 0.25),
            ("link", "Link-loss robustness", 0.15),
            ("cost", "Cost", 0.15),
            ("simp", "Simplicity / buildability", 0.15),
            ("cover", "Requirement coverage", 0.15),
            ("ext", "Python & extensibility", 0.15)]


def candidate_score(c, weights=None):
    w = weights or {k: v for k, _, v in CRITERIA}
    return sum(c["scores"][k] * w[k] for k in w)


def candidate_sensitivity():
    out = {}
    for k, _, _ in CRITERIA:
        w = {kk: v for kk, _, v in CRITERIA}
        w[k] *= 2
        tot = sum(w.values())
        w = {kk: v / tot for kk, v in w.items()}
        out[k] = max(CANDIDATES, key=lambda c: candidate_score(c, w))["id"]
    return out


# Focused trade studies: (id, title, [(option, for, against)], decision)
TRADES = [
    ("T1", "Turning words into missions", [
        ("LLM writes waypoints", "Maximum flexibility",
         "Geometry mistakes; hard to test; many validator rejections"),
        ("LLM picks an intent; Python planner makes the geometry",
         "Language to the LLM, geometry to deterministic code. Testable. "
         "Landmarks like 'the island' work",
         "Only understands intents we've built (the list grows)"),
        ("Templates only", "Simplest; offline", "No 'just ask'"),
        ("LLM in the loop during the mission", "Adapts live",
         "Needs link and internet mid-mission; no safety case"),
    ], "Intent + Python planner. Templates become pre-filled intents in the "
       "same pipeline, which is also the offline fallback (MIS-005)."),
    ("T2", "Boat-bank link and internet", [
        ("Boat is the Wi-Fi AP", "No bank hardware",
         "Boat antenna is 0.3 m up in a box; Pi 5 would need a second radio "
         "for internet"),
        ("Pi 5 is the AP, USB adapter on a 2 m pole; phone USB-tethered",
         "Antenna height fixes the over-water Fresnel problem (section 4.4). "
         "Internet and link are separate (COM-005)",
         "A pole and an adapter to carry (+£20)"),
        ("Travel router on the bank", "Good radio",
         "Another box, battery and config"),
        ("868 MHz telemetry + Wi-Fi", "Long range", "Cost, duty cycle, two "
         "radios"),
    ], "Pi 5 as AP with a pole-mounted USB adapter; phone USB tether for "
       "internet. Closes TBD-04. The pole is bought only if the first lake "
       "range test fails with the adapter at box height (COM-002)."),
    ("T3", "Helm hardware", [
        ("F405 flight controller, 1 MB flash (~£25)", "Cheap, common, "
         "ArduPilot Rover builds exist",
         "1 MB builds leave out Lua scripting and some features"),
        ("H743 flight controller, 2 MB (~£45-50)", "Full feature set, Lua",
         "+£20-25"),
        ("Linux autopilot HAT", "Everything on one Pi",
         "General-purpose OS: fails SAF-001"),
    ], "F405-class, if the chosen board's firmware has every feature in "
       "V-01. Behaviours that would need Lua are done in Python on the "
       "mission computer instead (weed-shedding, link watchdog). Fallback: "
       "an H743 board, same wiring."),
    ("T4", "Mission computer on the boat", [
        ("None", "Cheapest", "No live photo pipeline; no DET-003 path"),
        ("ESP32-S3 camera board", "£14, low power",
         "Firmware would be C++: conflicts with SWE-001"),
        ("Pi Zero 2W + 5 MP camera", "Python, picamera2, mavlink-router; "
         "can grow into duck spotting", "+£9; Linux SD-card care needed"),
        ("Pi 5 on the boat", "Powerful", "3-7 W and heat in a sealed box"),
    ], "Pi Zero 2W. This resolves the SWE-001 conflict found during SRS "
       "review."),
    ("T5", "Hull construction", [
        ("Printed foam-filled segments", "Modular, child-assemblable, "
         "printable", "Print time; seams"),
        ("PVC pipe pontoons", "Cheap, very robust", "Less for the crew to "
         "build; fixed length"),
        ("Carved XPS foam, skinned", "Light", "Messy; not modular"),
        ("Monohull + outriggers", "Different look", "Worse camera "
         "platform; more parts"),
    ], "Printed segments, as in the concept. PVC pontoons are the fallback "
       "if printing proves troublesome. The foam fill makes seams "
       "non-critical."),
    ("T6", "Speech in and out", [
        ("Cloud speech-to-text", "Accurate", "Child's voice leaves the "
         "device; needs internet"),
        ("On-device STT (Whisper-class) + TTS (Piper-class) on the Pi 5",
         "Private, offline, free", "A few seconds' latency; child speech "
         "accuracy to prove"),
        ("Phone dictation", "Easy", "Goes to a third party; phone in "
         "child's hands"),
    ], "On-device. Closes TBD-05. Adult approval (VAL-008) catches "
       "mis-hearing."),
    ("T7", "Battery", [
        ("3S Li-ion 18650 pack + BMS", "Hard cells, safer in a sealed box, "
         "cheap, ample current", "Heavier per Wh than LiPo"),
        ("3S LiPo", "Light, high current", "Soft pouch; puncture/swell risk; "
         "current not needed"),
        ("NiMH", "Very safe", "Heavy, low energy"),
    ], "3S Li-ion 18650 with BMS. Closes TBD-07."),
    ("T8", "Arming interlock (step 1 of MOD-003)", [
        ("Software only", "No parts", "Doesn't meet MOD-003"),
        ("Waterproof toggle", "Simple", "A gland and a switch a child can "
         "flick"),
        ("Magnetic key switching motor power", "No hole in the box; the "
         "adult holds the key; cuts motor power independently of software",
         "Reed switch + MOSFET switch to build"),
    ], "Magnetic key. The helm senses motor-rail voltage, so arming is "
       "refused while the key is out."),
    ("T9", "Display", [
        ("Screen built into the box", "Always there", "Glare, cost, power"),
        ("Phone / tablet web UI served by the Pi 5", "Any device, daylight "
         "brightness, no extra cost", "Needs a clamp"),
    ], "Web UI on the operator's phone (already USB-tethered) or a tablet "
       "clamped to the box. Closes TBD-06."),
]

# ------------------------------------------------------------------ convergence
PRINCIPLES = [
    ("Safety lives in the helm.", "Fence, failsafes and motor authority "
     "are ArduPilot's, on its own RTOS processor. Nothing we write can "
     "disable them while armed."),
    ("Intelligence lives on the bank.", "Language, planning, validation, "
     "UI and photo analysis run on the Pi 5, where power, internet and a "
     "keyboard are."),
    ("The boat carries only what it must.", "Helm, camera, link relay and "
     "small watchdogs."),
    ("Every link can fail.", "The loaded mission always ends in RTL. Losing "
     "Wi-Fi, internet or a computer degrades function, never safety."),
    ("Words become intent; code makes geometry.", "The LLM proposes, the "
     "planner draws, the validator checks, the adult approves, the helm "
     "enforces."),
    ("Python everywhere we write code; one simulator for everything.",
     "The same Mission Control code drives SITL and the real boat."),
]

SUBSYSTEMS = [
    ("HUL", "Hull & structure", "Boat",
     "Six foam-filled printed hull segments, two crossbeams with M3 rail, "
     "DUPLO deck plate, electronics-box saddle, mast and sockets, carry "
     "handle."),
    ("PRP", "Propulsion", "Boat",
     "Two clip-on thruster pods (submerged brushless motor, printed prop, "
     "finger/weed guard, strut, dovetail), two bidirectional ESCs, keyed "
     "waterproof pod connectors."),
    ("PWR", "Power", "Boat",
     "3S Li-ion 18650 pack with BMS, main fuse, main switch, magnetic "
     "arming key and motor-rail MOSFET switch, power module (V/I sense), "
     "5 V buck for the mission computer, harness."),
    ("HLM", "Helm", "Boat",
     "F405-class flight controller running ArduPilot Rover (boat frame), "
     "M10 GNSS + compass on the mast, controlled parameter set, fence and "
     "mission storage, notify-LED output for the beacon."),
    ("MCP", "Mission computer", "Boat",
     "Pi Zero 2W, 5 MP camera, microSD, moisture sensor. Python services: "
     "MAVLink router, camera, photo server, link watchdog, weed-shedding, "
     "health."),
    ("MCN", "Mission Control", "Bank",
     "Raspberry Pi 5, USB Wi-Fi adapter (pole-mountable), GO / COME HOME / "
     "STOP / TALK buttons, adult key switch, USB mic, speaker, status LEDs, power "
     "bank, case, phone/tablet display. Python application: session "
     "manager, web UI, voice, planner, validator, helm interface, photo "
     "sync, captain's log, site store, logger."),
    ("REC", "Recovery & signalling", "Boat + bank",
     "Hi-vis finish, flag, recovery hoop, LED beacon (driven by HLM), 'if "
     "found' label, bank recovery kit (pole + net, casting rod), optional "
     "tracker tag."),
    ("SIM", "Simulation & test", "Home",
     "ArduPilot SITL (Rover, boat), simulated mission computer (camera "
     "stub serving test images), scenario runner (pytest), CI on push."),
]
EXTRA_ALLOC = [("SYS", "System level", "Verified on the integrated system"),
               ("OPS", "Operations", "Procedures, checklists, manual")]

COMPONENTS = [
    # (subsystem, id, name, responsibility, key reqs)
    ("MCN", "C1", "Session manager", "Session state machine; gates GO; "
     "checklist; arming sequence", "MC-003, VAL-008/009, PRE-006"),
    ("MCN", "C2", "Panel I/O", "GPIO buttons, key switch, LEDs, "
     "press-and-hold", "MC-002/004/008"),
    ("MCN", "C3", "Web UI", "Map, plan preview, status, checklist, "
     "fence editor, photo review", "MC-005/006/009/015, FEN-002"),
    ("MCN", "C4", "Voice", "On-device STT (push-to-talk) and TTS "
     "announcements", "NLI-002, MC-007"),
    ("MCN", "C5", "Planner", "Claude client (intent schema) + geometry "
     "generator + templates", "NLI-003..006, MIS-001..006"),
    ("MCN", "C6", "Validator", "Pure, deterministic mission checks",
     "VAL-001..007"),
    ("MCN", "C7", "Helm interface", "Helm API; ArduPilotHelm over MAVLink "
     "(pymavlink)", "SWE-002/003, VAL-010"),
    ("MCN", "C8", "Photos & log", "Photo sync, waterfowl finder, captain's "
     "log", "CAM-007, DET-001/002, LOG-004"),
    ("MCN", "C9", "Site store", "Fences, exclusions, landmarks, home "
     "points (GeoJSON, in git)", "FEN-001/002, OPS-005/006"),
    ("MCN", "C10", "Logger", "Structured session logs, LLM I/O, approvals",
     "LOG-002/003"),
    ("MCP", "B1", "MAVLink router", "FC UART ↔ UDP to Mission Control; "
     "local endpoint for B2-B6", "COM-003, SAF-003"),
    ("MCP", "B2", "Camera service", "Capture policy (interval, photo "
     "points, command); geotags from MAVLink", "CAM-001..004"),
    ("MCP", "B3", "Photo server", "Photo index and download over HTTP",
     "CAM-007"),
    ("MCP", "B4", "Link watchdog", "No Mission Control heartbeat for 60 s "
     "in AUTO → command RTL", "FS-003"),
    ("MCP", "B5", "Weed-shedding", "On stuck → up to 3 bounded GUIDED "
     "reverse bursts, then resume or stay in HOLD", "FS-006"),
    ("MCP", "B6", "Health", "Moisture → RTL + alarm; temperature; storage",
     "FS-010, PWR-010, CAM-004"),
    ("HLM", "A1", "ArduPilot Rover", "Navigation, modes, fence, "
     "failsafes, logging (third-party firmware + our parameters)",
     "NAV-*, FEN-*, FS-*, LOG-001"),
]

# Interfaces: (id, name, a, b, type, medium, content, reqs)
INTERFACES = [
    ("IF-01", "Boat-bank radio link", "MCN", "MCP", "Data",
     "Wi-Fi 2.4 GHz 802.11n, WPA2, Pi 5 is AP",
     "Carries IF-02 and IF-03", "COM-001..006"),
    ("IF-02", "Command & telemetry", "MCN", "HLM", "Data",
     "MAVLink 2 over UDP, relayed by B1", "Modes, arming, mission upload "
     "and read-back, fence, status ≥ 1 Hz", "COM-003, VAL-010, MOD-006"),
    ("IF-03", "Photo & health service", "MCN", "MCP", "Data",
     "HTTP/JSON over IF-01", "Photo index and files, capture commands, "
     "health", "CAM-007, FS-010"),
    ("IF-04", "Companion link", "MCP", "HLM", "Data",
     "MAVLink 2 over UART (FC TELEM port)", "Router traffic, position for "
     "geotags, watchdog and weed-shedding commands", "FS-003/006, CAM-003"),
    ("IF-05", "Motor commands", "HLM", "PRP", "Data",
     "2 × DShot or PWM (bidirectional)", "Left/right thrust ±100%",
     "NAV-001, FS-008"),
    ("IF-06", "Motor power", "PWR", "PRP", "Power",
     "11.1 V nominal via key-switched MOSFET, XT30", "≤ 20 A per ESC",
     "PWR-003/008, MOD-003"),
    ("IF-07", "Helm power & sensing", "PWR", "HLM", "Power",
     "Power module: supply + analogue V/I; motor-rail sense",
     "Battery V, I, mAh; key state", "PWR-005/006, PRE-003"),
    ("IF-08", "Mission computer power", "PWR", "MCP", "Power",
     "Dedicated 5 V 3 A buck", "Isolated from motor transients",
     "PWR-005"),
    ("IF-09", "Beacon drive", "HLM", "REC", "Data",
     "Notify-LED output (WS2812-type)", "Armed / failsafe / low-battery "
     "patterns", "REC-004"),
    ("IF-10", "Internet uplink", "MCN", "EXT-PH", "Data",
     "USB tethering (RNDIS/NCM)", "HTTPS to Claude API", "COM-005"),
    ("IF-11", "Claude API", "MCN", "EXT-AI", "Data",
     "HTTPS, Messages API with tool use", "Instruction + site context → "
     "intent JSON; photos → captions (opt-in)", "NLI-003/004, LOG-004"),
    ("IF-12", "Crew & operator panel", "MCN", "EXT-US", "HMI",
     "4 buttons, key switch, LEDs, mic, speaker, web UI",
     "Commands, approvals, announcements", "MC-002..008, CHD-005"),
    ("IF-13", "Mission format", "MCN", "MCN", "Software",
     "JSON schema v1 (intent → mission → MAVLink items)",
     "Contract between planner, validator and helm interface",
     "MIS-004, VAL-*"),
    ("IF-14", "Helm API", "MCN", "MCN", "Software",
     "Python abstract class", "arm, disarm, mode, upload, read back, start, "
     "hold, rtl, stop, fence, status", "SWE-002/003"),
    ("IF-15", "Site data", "MCN", "SIM", "Software",
     "GeoJSON in git", "Fence, exclusions, landmarks, home points",
     "FEN-001/002"),
    ("IF-16", "Hull segment joint", "HUL", "HUL", "Mechanical",
     "Flange + printed thumb-screws", "Alignment, load path, tool-free",
     "MEC-007, CHD-004"),
    ("IF-17", "Pod mount", "PRP", "HUL", "Mechanical",
     "Dovetail + retaining pin; keyed 3-pin waterproof connector",
     "Thrust load, alignment, swap < 2 min", "MEC-008"),
    ("IF-18", "Box & glands", "PWR", "HUL", "Mechanical",
     "Saddle on rail; PG7 glands", "Sealing, cable entry, access",
     "MEC-012"),
    ("IF-19", "Mast socket", "HLM", "HUL", "Mechanical",
     "Socket on rail; GNSS ≥ 150 mm from power wiring", "GNSS/compass, "
     "flag, beacon, hoop loads", "MEC-013, REC-005"),
    ("IF-20", "DUPLO deck", "HUL", "EXT-US", "Mechanical",
     "DUPLO-compatible stud grid", "Grip / release force", "MEC-009"),
    ("IF-21", "Simulation link", "SIM", "MCN", "Data",
     "MAVLink 2 UDP from SITL; camera stub with the IF-03 API",
     "Same traffic as IF-02/03", "SWE-004/005"),
    ("IF-22", "GNSS & compass", "HLM", "HLM", "Data",
     "UART (u-blox) + I2C compass", "Position, time, heading",
     "PRE-001, NAV-008"),
]
EXTERNALS = {"EXT-PH": "Phone", "EXT-AI": "Claude API",
             "EXT-US": "Operator & crew"}

MODE_MAP = [
    ("DISARMED", "Disarmed (any mode)", "Motors inhibited; key out → motor "
     "rail unpowered."),
    ("HOLD (station-keeping)", "LOITER", "Boats hold position within the "
     "loiter radius."),
    ("HOLD (motors off)", "HOLD", "After STOP, position loss or stuck. "
     "Boat drifts."),
    ("MANUAL", "STEERING (speed-controlled)", "Speed limit applies; fence "
     "enforcement in this mode to confirm (V-02)."),
    ("AUTO", "AUTO", "Validated mission; last item is RTL."),
    ("RTL", "RTL", "Ends loitering at home; to confirm (V-04)."),
]

FS_ALLOC = [
    ("FS-001", "Low / critical battery", "HLM", "Battery failsafe "
     "(two thresholds)", "Native"),
    ("FS-002", "Link loss, MANUAL", "HLM", "GCS failsafe", "Native (V-03)"),
    ("FS-003", "Link loss, AUTO", "HLM + MCP", "GCS failsafe set to "
     "continue in AUTO; B4 watchdog commands RTL at 60 s", "Native + "
     "Python"),
    ("FS-004", "Position loss", "HLM", "EKF failsafe → HOLD", "Native"),
    ("FS-005", "Stuck", "HLM", "Crash check → HOLD", "Native (V-05)"),
    ("FS-006", "Weed-shedding", "MCP", "B5 bounded GUIDED reverse bursts via MAVLink (V-11)",
     "Python"),
    ("FS-007", "Mission computer down", "HLM", "Mission continues; "
     "nothing depends on the companion", "By design"),
    ("FS-008", "Helm down", "PRP", "ESC stops on signal loss", "ESC firmware "
     "(V-09)"),
    ("FS-009", "STOP", "MCN → HLM", "Mode HOLD (+ disarm) over MAVLink",
     "Native command"),
    ("FS-010", "Water ingress", "MCP → HLM", "B6 commands RTL", "Python"),
    ("FS-011", "Priority", "HLM", "ArduPilot failsafe ordering + design "
     "rule for B4-B6", "Native + rule"),
    ("FS-012", "Log & announce", "HLM + MCN", "Helm log; C10 + C4 "
     "announce", "Native + Python"),
    ("FS-013", "No single failure leaves fence", "System", "FMEA + SITL "
     "fault injection", "Analysis"),
]

DECISIONS = [
    ("DD-01", "Architecture AR-2 'Smart bank'", "Section 3.3", "-"),
    ("DD-02", "ArduPilot Rover on an F405-class flight controller, subject "
     "to V-01", "T3", "-"),
    ("DD-03", "Pi Zero 2W + 5 MP camera as the mission computer", "T4",
     "Resolves SWE-001 conflict"),
    ("DD-04", "LLM returns an intent; the Python planner generates the "
     "geometry", "T1", "-"),
    ("DD-05", "Missions run natively in ArduPilot AUTO; no streamed "
     "GUIDED control", "Section 4.8", "Keeps FS-007"),
    ("DD-06", "Pi 5 is the Wi-Fi AP (USB adapter, pole if needed); phone "
     "USB tether for internet", "T2", "Closes TBD-04"),
    ("DD-07", "On-device speech-to-text and text-to-speech on the Pi 5",
     "T6", "Closes TBD-05"),
    ("DD-08", "Web UI on phone or tablet as the display", "T9",
     "Closes TBD-06"),
    ("DD-09", "3S Li-ion 18650 pack with BMS", "T7", "Closes TBD-07"),
    ("DD-10", "Magnetic arming key cutting motor power; helm senses the "
     "rail", "T8", "-"),
    ("DD-11", "LED beacon driven by the helm, not the mission computer",
     "Section 4.2", "Works with MCP dead"),
    ("DD-12", "SRS modes mapped to ArduPilot modes as in section 4.6",
     "Section 4.6", "-"),
    ("DD-13", "Behaviours needing Lua are done in Python on the MCP",
     "T3", "FS-003/006/010"),
    ("DD-14", "Printed foam-filled hull segments; PVC pontoons as fallback",
     "T5", "-"),
]

VERIFY_EARLY = [
    ("V-01", "Chosen F405 board's ArduPilot Rover firmware includes: polygon "
     "fence with exclusion zones, battery, GCS and EKF failsafes, crash "
     "check, notify-LED output, second voltage input.", "Bench", "DD-02"),
    ("V-02", "Fence is enforced in the mode used for MANUAL.", "SITL",
     "FEN-004"),
    ("V-03", "GCS failsafe can 'continue in AUTO', with a 2 s timeout.",
     "SITL", "FS-002/003"),
    ("V-04", "Boat loiters at home at the end of RTL.", "SITL", "MOD-005"),
    ("V-05", "Crash check thresholds can meet FS-005.", "SITL + pool",
     "FS-005"),
    ("V-06", "Helm counts only Mission Control heartbeats as GCS (system "
     "IDs).", "SITL", "FS-002/003"),
    ("V-07", "On-device STT ≤ 5 s for a 5 s utterance; usable accuracy on "
     "a child's voice.", "Bench", "NLI-002"),
    ("V-08", "Link ≥ 100 m over water; with and without the pole.",
     "Lake", "COM-002"),
    ("V-09", "ESCs stop motors ≤ 1 s after signal loss.", "Bench",
     "FS-008"),
    ("V-10", "Pi Zero 2W in the sealed box at 30 °C for 60 min without "
     "throttling.", "Bench", "PWR-010"),
    ("V-11", "In GUIDED, the helm stops within 3 s if velocity targets stop "
     "arriving, so a B5 crash mid-burst is safe.", "SITL", "FS-006"),
    ("V-12", "A skid-steer boat frame is available in SITL and behaves "
     "plausibly.", "SITL", "SWE-004"),
    ("V-13", "The second voltage input can gate arming on motor-rail "
     "voltage (key in).", "SITL + bench", "MOD-003"),
    ("V-14", "Native mechanism to stop motors on persistent fence breach "
     "(FEN-006).", "SITL", "FEN-006"),
    ("V-15", "Reduced speed during RTL on critical battery (FS-001).",
     "SITL", "FS-001"),
    ("V-16", "GNSS-velocity yaw fallback when the compass disagrees "
     "(NAV-008).", "SITL", "NAV-008"),
    ("V-17", "Whether the helm refuses fence changes while armed "
     "(FEN-007).", "SITL", "FEN-007"),
]

RISKS = [
    ("R-01", "F405 firmware lacks a needed feature", "Medium",
     "V-01 before purchase of other parts; H743 fallback (+£20-25)"),
    ("R-02", "Bill of materials over the £160 cap (was High at £120; "
     "CR-01 accepted)", "Medium", "£6 headroom on the £154 baseline; the "
     "pole kit only if V-08 needs it, offset by cost-down levers"),
    ("R-03", "Wi-Fi range over water", "Medium",
     "Pole antenna; safety independent of the link"),
    ("R-04", "Pi Zero SD-card corruption on power loss", "Medium",
     "Read-only root filesystem; photos on a separate partition; clean "
     "shutdown on disarm"),
    ("R-05", "Speech recognition struggles with a 4-year-old", "Medium",
     "Adult approval, templates, a short phrase set, typed fallback"),
    ("R-06", "LLM intent variability", "Low",
     "Schema-constrained output, validator, retries, templates"),
    ("R-07", "Weed", "High", "Guards, stuck detection, B5, site choice"),
]

MASS = [("Hull segments + foam (6)", 500), ("Crossbeams (2)", 120),
        ("DUPLO deck plate", 60), ("Electronics box, tray, glands", 150),
        ("Mast, GNSS, flag, hoop, beacon", 110), ("Flight controller", 12),
        ("Pi Zero 2W + camera + SD", 30), ("ESCs (2)", 30),
        ("Thruster pods (2)", 150), ("Battery 3S 18650 + BMS", 160),
        ("Power module, buck, key switch", 30), ("Wiring and connectors", 60),
        ("Fasteners", 50)]

POWER_BOAT = [("Flight controller + GNSS", 0.8), ("Pi Zero 2W + camera + "
              "Wi-Fi (average)", 1.8), ("LED beacon", 0.3),
              ("ESC idle (2)", 0.2), ("Motors at cruise (estimate)", 8.0)]
POWER_BANK = [("Raspberry Pi 5 (average; peaks ~8 W during STT)", 5.0),
              ("USB Wi-Fi adapter", 1.0), ("Speaker, mic, LEDs", 0.5)]

BOM = [
    ("Boat", "F405-class flight controller", 25),
    ("Boat", "M10 GNSS + compass", 14),
    ("Boat", "Pi Zero 2W", 15),
    ("Boat", "5 MP camera (OV5647-class) + Zero cable", 8),
    ("Boat", "microSD 32 GB", 4),
    ("Boat", "2 × brushless motor", 12),
    ("Boat", "2 × bidirectional ESC", 10),
    ("Boat", "3 × 18650 + 3S BMS", 15),
    ("Boat", "Box, PG7 glands, fuse", 6),
    ("Boat", "Foam, hi-vis, LED beacon", 5),
    ("Boat", "5 V 3 A buck", 3),
    ("Boat", "Reed switch + MOSFET switch module (arming key)", 4),
    ("Boat", "IP67 main power switch (added in Issue C)", 4),
    ("Bank", "4 arcade buttons (incl. TALK), key switch", 9),
    ("Bank", "USB mic + small speaker", 8),
    ("Bank", "USB Wi-Fi adapter with antenna", 12),
    ("Bank*", "2 m pole + 3 m USB extension (only if V-08 needs it)", 8),
]


# ------------------------------------------------------------------ allocation
AREA_DEFAULT = {
    "MOD": ("HLM", ["MCN"]), "PRE": ("HLM", ["MCN"]), "NAV": ("HLM", []),
    "FEN": ("HLM", ["MCN"]), "FS": ("HLM", []), "SAF": ("HLM", ["MCN"]),
    "MIS": ("MCN", ["HLM"]), "NLI": ("MCN", []), "VAL": ("MCN", []),
    "CAM": ("MCP", []), "DET": ("MCN", []), "MC": ("MCN", []),
    "COM": ("MCN", ["MCP"]), "REC": ("REC", []), "MEC": ("HUL", []),
    "PWR": ("PWR", []), "SWE": ("MCN", ["MCP"]), "LOG": ("MCN", []),
    "ENV": ("SYS", []), "CHD": ("HUL", ["PRP"]), "OPS": ("OPS", []),
    "CON": ("SYS", []),
}
OVERRIDE = {
    "MOD-002": ("HLM", ["PWR"]), "MOD-003": ("PWR", ["HLM", "MCN"]),
    "MOD-006": ("MCN", ["HLM"]), "MOD-007": ("MCN", []),
    "MOD-008": ("HLM", []),
    "PRE-003": ("HLM", ["PWR"]), "PRE-005": ("MCN", ["HLM"]),
    "PRE-006": ("MCN", ["OPS"]), "PRE-007": ("HLM", ["PWR"]),
    "PRE-008": ("HLM", ["MCN", "MCP"]),
    "NAV-001": ("PRP", ["HLM"]), "NAV-002": ("HLM", ["PRP"]),
    "NAV-003": ("HLM", ["PRP"]),
    "FEN-002": ("MCN", []), "FEN-003": ("MCN", []),
    "FEN-007": ("HLM", ["MCN"]),
    "FS-003": ("HLM", ["MCP"]), "FS-006": ("MCP", ["PRP"]),
    "FS-007": ("HLM", ["MCP"]), "FS-008": ("PRP", ["HLM"]),
    "FS-009": ("MCN", ["HLM"]), "FS-010": ("MCP", ["HLM"]),
    "FS-012": ("HLM", ["MCN"]), "FS-013": ("SYS", []),
    "SAF-004": ("MCN", []), "SAF-005": ("N/A", []), "SAF-006": ("SYS", []),
    "SAF-007": ("MCN", ["HLM"]),
    "CAM-005": ("MCP", ["HUL"]), "CAM-006": ("HUL", ["MCP"]),
    "CAM-007": ("MCP", ["MCN"]), "CAM-008": ("MCP", ["MCN"]),
    "DET-003": ("MCP", []), "DET-004": ("MCP", ["HLM"]),
    "MC-014": ("MCN", ["HLM"]),
    "COM-005": ("MCN", []), "COM-007": ("HLM", []),
    "REC-001": ("HUL", []), "REC-004": ("REC", ["HLM"]),
    "MEC-002": ("SYS", []), "MEC-008": ("PRP", ["HUL"]),
    "MEC-010": ("PRP", []), "MEC-011": ("PRP", []),
    "MEC-012": ("HUL", ["PWR"]), "MEC-013": ("HLM", ["HUL"]),
    "PWR-005": ("PWR", ["HLM", "MCP"]), "PWR-006": ("PWR", ["HLM"]),
    "PWR-009": ("SYS", ["PWR", "PRP"]), "PWR-010": ("MCP", ["HLM", "HUL"]),
    "SWE-001": ("SYS", []), "SWE-002": ("MCN", []), "SWE-003": ("MCN", []),
    "SWE-004": ("SIM", ["MCN", "MCP"]), "SWE-005": ("SIM", []),
    "SWE-006": ("SYS", []), "SWE-007": ("SIM", []),
    "SWE-008": ("MCN", ["MCP", "HLM"]), "SWE-009": ("MCN", []),
    "LOG-001": ("HLM", []), "LOG-004": ("MCN", ["MCP"]),
    "ENV-002": ("PRP", ["HUL", "HLM"]), "ENV-003": ("HUL", []),
    "ENV-004": ("HUL", ["PWR"]), "ENV-005": ("PRP", ["MCP"]),
    "ENV-006": ("HUL", []),
    "CHD-003": ("HUL", ["PWR", "PRP"]), "CHD-005": ("MCN", []),
    "CHD-006": ("SYS", []),
    "OPS-001": ("OPS", ["MCN"]),
    "CON-002": ("SYS", ["MCN"]),
}


def allocation():
    out = {}
    for r in SRS.all_reqs():
        area = r["id"].split("-")[0]
        out[r["id"]] = OVERRIDE.get(r["id"], AREA_DEFAULT[area])
    return out


def check():
    SRS.check()
    alloc = allocation()
    known = {s[0] for s in SUBSYSTEMS} | {"SYS", "OPS", "N/A"}
    for rid, (p, sec) in alloc.items():
        assert p in known and set(sec) <= known, rid
    assert set(OVERRIDE) <= set(alloc), set(OVERRIDE) - set(alloc)
    ends = {s[0] for s in SUBSYSTEMS} | set(EXTERNALS)
    for i in INTERFACES:
        assert i[2] in ends and i[3] in ends, i[0]
    return len(alloc)


if __name__ == "__main__":
    print(check(), "requirements allocated")
    for c in CANDIDATES:
        print(c["id"], round(candidate_score(c), 2))
    print(candidate_sensitivity())
    print("BOM", sum(p for _, _, p in BOM), "mass", sum(m for _, m in MASS))
