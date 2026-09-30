"""Boaty subsystem specifications: all eight subsystems as data.

build_sss.py renders one PDF per subsystem (BOATY-SSS-<code>) plus a combined
volume. check() enforces that:
  * every SRS requirement allocated (primary) to a subsystem by the ADD is
    traced by at least one of that subsystem's derived requirements;
  * every trace reference exists (SRS, IF, V, DD, TBC ids);
  * derived requirement IDs are unique.
"""
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DOCS / "add" / "src"))
sys.path.insert(0, str(DOCS / "fmea" / "src"))
import architecture as A  # noqa: E402

SRS = A.SRS
SUBSYSTEMS = {}


def subsystem(code, **kw):
    kw["code"] = code
    kw["groups"] = []
    SUBSYSTEMS[code] = kw
    return kw


def group(ss, heading):
    ss["groups"].append((heading, []))


def D(ss, rid, text, pri, ver, stage, trace, note=None):
    ss["groups"][-1][1].append(dict(id=rid, text=text, pri=pri, ver=ver,
                                    stage=stage, trace=trace, note=note))


# ======================================================================
# HUL  Hull & structure
# ======================================================================
h = subsystem(
    "HUL", title="Hull & structure",
    purpose="Provide a stable, unsinkable, modular catamaran platform "
            "that a 4-year-old can help assemble, carrying the "
            "electronics box, thruster pods, mast and DUPLO deck.",
    inside=["Six hull segments with closed-cell foam cores",
            "Two crossbeams with M3 rail", "Electronics box, saddle and "
            "glands", "Camera hood", "DUPLO deck plate", "Mast tube and "
            "socket", "Carry handle", "All structural fasteners"],
    outside=["Thruster pods (PRP)", "Anything inside the box (PWR, HLM, "
             "MCP)", "Flag, hoop, beacon, labels (REC)"],
    breakdown=[("HUL-1 Hull segments ×6", "Bow, mid and stern per hull; "
                "≤ 200 mm long; foam-filled PETG shells"),
               ("HUL-2 Crossbeams ×2", "Box-section beams with a 10 mm "
                "M3 hole grid on top"),
               ("HUL-3 Electronics box", "Clip-lock box, saddle, 4 × PG7 "
                "glands, key dock"),
               ("HUL-4 Deck & mast", "DUPLO plate, mast tube, socket, "
                "handle"),
               ("HUL-5 Camera hood", "Printed spray hood and window on "
                "the box front")],
    constraints=["ADD DD-14: printed foam-filled segments; PVC pontoons are "
                 "the fallback", "Build volume 200 mm cube (Ultimaker)",
                 "PETG default material; ASA for high-UV parts if needed"],
    budget=[("Mass allocation", "≤ 1000 g (estimate 930 g)"),
            ("Cost allocation", "£5 (box, glands); filament from stock"),
            ("Power", "None")],
    special="hul",
    open_items=[("TBC-11", "Final hull lines from CAD (IF-16)"),
                ("TBC-13", "Box selection and saddle (IF-18)"),
                ("TBC-14", "DUPLO stud size by test print (IF-20)")],
)
group(h, "Geometry and mass")
D(h, "HUL-D01", "Overall length shall be ≤ 620 mm and beam ≤ 360 mm. Height "
  "including the mast shall be ≤ 500 mm.", "M", "I", "BENCH",
  ["MEC-001"], "Margins of 30 mm / 40 mm under MEC-001 for build tolerance.")
D(h, "HUL-D02", "Each hull shall comprise three segments (bow, mid, stern), "
  "each ≤ 200 mm long and printable in a 200 × 200 × 200 mm volume.", "M",
  "I", "BENCH", ["MEC-005", "MEC-007"])
D(h, "HUL-D03", "Hull and structure mass (segments, beams, deck, box, mast, "
  "fasteners) shall be ≤ 1000 g.", "M", "T", "BENCH", ["MEC-002"])
D(h, "HUL-D04", "Hull centreline spacing shall be ≥ 270 mm.", "M", "A",
  "BENCH", ["MEC-004"], "Drives heel stability; see section 6.")
group(h, "Buoyancy and stability")
D(h, "HUL-D05", "Closed-cell foam shall fill ≥ 90% of each segment's "
  "internal volume.", "M", "I", "BENCH", ["MEC-006", "REC-001"])
D(h, "HUL-D06", "With the box flooded and any two segment shells breached, "
  "remaining buoyancy shall be ≥ 1.5 × design mass (2.1 kg).", "M", "T",
  "POOL", ["REC-001"])
D(h, "HUL-D07", "At design mass with 300 g on the deck, draft shall be "
  "≤ 35 mm and freeboard ≥ 50 mm.", "M", "T", "POOL", ["MEC-003"])
D(h, "HUL-D08", "Static heel with 300 g at the deck edge shall be ≤ 10°.",
  "M", "T", "POOL", ["MEC-004"])
D(h, "HUL-D09", "The boat shall not capsize in full-speed (1.5 m/s) "
  "on-the-spot turns or in 100 mm waves with 300 g at the deck edge.", "M",
  "D", "POOL", ["MEC-004", "ENV-003"])
group(h, "Materials and durability")
D(h, "HUL-D10", "Exposed and wetted printed parts shall be PETG or ASA, "
  "with ≥ 3 perimeters, ≥ 4 top/bottom layers and a hull shell ≥ 1.6 mm "
  "thick.", "M", "I", "BENCH", ["MEC-006"])
D(h, "HUL-D11", "Exposed parts shall be UV-stable (ASA, or PETG with UV "
  "coating) and keep their function after two seasons.", "C", "I", "LAKE",
  ["ENV-006"])
D(h, "HUL-D12", "Fasteners shall be A2/A4 stainless steel or plastic. No "
  "plain steel.", "S", "I", "BENCH", ["MEC-015"])
D(h, "HUL-D13", "Deck and box lid shall shed rain: no water inside the box "
  "after a 10 min drip test, and no pooling on the deck.", "S", "T",
  "BENCH", ["ENV-004"])
group(h, "Modularity and interfaces")
D(h, "HUL-D14", "Segment joints shall conform to IF-16 (captive "
  "thumb-screws, dowels).", "M", "T", "BENCH", ["IF-16", "MEC-007",
                                                "CHD-004"])
D(h, "HUL-D15", "The electronics box shall conform to IF-18 and pass 30 min "
  "at 0.3 m without ingress. Every cable entry uses a gland.", "M", "T",
  "BENCH", ["IF-18", "MEC-012"])
D(h, "HUL-D16", "The box saddle shall place the box lid ≥ 150 mm above the "
  "waterline and allow adult removal without tools.", "M", "I", "BENCH",
  ["MEC-007", "COM-002"])
D(h, "HUL-D17", "The DUPLO deck shall conform to IF-20.", "M", "T", "BENCH",
  ["IF-20", "MEC-009"])
D(h, "HUL-D18", "The mast socket shall conform to IF-19, with the GNSS "
  "≥ 150 mm from power wiring.", "M", "I", "BENCH", ["IF-19", "MEC-013"])
D(h, "HUL-D19", "The camera hood shall overhang the lens by ≥ 15 mm and "
  "leave the window reachable with a cloth, no tools.", "S", "I", "POOL",
  ["CAM-006"])
D(h, "HUL-D20", "The camera mount shall hold the lens ≥ 120 mm above the "
  "waterline, level to ± 3°, facing forward.", "S", "I", "BENCH",
  ["CAM-005"])
group(h, "Handling and child safety")
D(h, "HUL-D21", "A carry handle within ± 50 mm of the centre of gravity "
  "shall carry 3 × design mass. With the mast removed, the boat shall fit a "
  "650 × 400 × 250 mm envelope.", "S", "T", "BENCH", ["MEC-014"])
D(h, "HUL-D22", "No child-handled part (segments, deck plate, "
  "thumb-screws, pod shells) shall fit wholly inside the EN 71-1 "
  "small-parts cylinder. Fasteners the crew handles are captive.", "M",
  "T", "BENCH", ["CHD-001"])
D(h, "HUL-D23", "Child-handled edges shall have ≥ 0.6 mm chamfer or "
  "radius. Joints close face-to-face with no finger-trap geometry.", "M",
  "I", "BENCH", ["CHD-002"])
D(h, "HUL-D24", "The box and battery bay shall open only by an adult "
  "action: latches needing ≥ 40 N or a two-handed release.", "M", "T",
  "BENCH", ["CHD-003"])
D(h, "HUL-D25", "The crew's assembly steps (segments, pods, deck, flag) "
  "shall need no tools and ≤ 20 N finger force.", "M", "D", "BENCH",
  ["CHD-004", "MEC-007"])

# ======================================================================
# PRP  Propulsion
# ======================================================================
p = subsystem(
    "PRP", title="Propulsion",
    issue="Issue B (for review)",
    parents="SRS Issue F, ADD Issue F, ICD Issue E, KCL Issue B",
    history=[["B", "29 September 2026", "ESC chosen: AM32 20 A, DShot 3D "
              "set by the helm (PRP-D06); ESC configuration PRP-D16; cost "
              "from the Key Component List.", "Claude, owner decision "
              "(CR-04)"]],
    purpose="Turn helm commands into bidirectional thrust on two clip-on "
            "pods, quietly, safely and without being defeated by weed.",
    inside=["Two thruster pods (motor, prop, shroud/guard, strut, "
            "dovetail, latch)", "Two bidirectional ESCs (in the box)",
            "Pod connectors and motor leads"],
    outside=["Motor power (PWR)", "Motor commands and speed control (HLM)",
             "Transom mount features (HUL)"],
    breakdown=[("PRP-1 Thruster pod ×2", "2204-2208 outrunner running "
                "submerged; printed prop in a full shroud"),
               ("PRP-2 ESC ×2", "20-30 A, BLHeli_S/AM32, bidirectional, "
                "DShot"), ("PRP-3 Pod connector ×2", "Keyed 3-pole IP68")],
    constraints=["ADD T3/T5: submerged brushless, differential thrust, no "
                 "rudder", "Airboat pod is a future swap-in module (same "
                 "IF-17)"],
    budget=[("Mass allocation", "≤ 200 g (estimate 180 g)"),
            ("Cost allocation", "£34 (motors £12, 2 × AM32 ESC £22)"),
            ("Power", "≈ 8 W at cruise (estimate); ≤ 16 A total "
             "continuous")],
    special="prp",
    open_items=[("TBC-05", "ESC DShot and 3D-mode support (IF-05)"),
                ("TBC-06", "Measured motor current (IF-06)"),
                ("TBC-12", "Pod connector part number (IF-17)"),
                ("V-09", "ESC stop on signal loss ≤ 1 s")],
)
group(p, "Performance")
D(p, "PRP-D01", "Two identical pods, port and starboard, shall each give "
  "forward and astern thrust on command.", "M", "D", "POOL", ["NAV-001"])
D(p, "PRP-D02", "Combined static forward thrust shall be ≥ 4 N, and astern "
  "≥ 1.5 N.", "M", "T", "BENCH", ["ENV-002", "NAV-001"],
  "Sized from the section 6 estimate: ≈ 1.1 N needed for 0.5 m/s into "
  "5.4 m/s wind, with a margin of 3.5.")
D(p, "PRP-D03", "The boat shall reach 1.0 m/s in calm water at ≤ 50% "
  "throttle.", "M", "T", "POOL", ["NAV-002"])
D(p, "PRP-D04", "Combined electrical input at 1.0 m/s cruise shall be "
  "≤ 10 W.", "S", "T", "POOL", ["PWR-009"])
D(p, "PRP-D05", "Continuous current shall be ≤ 8 A per ESC at full "
  "throttle, measured.", "M", "T", "BENCH", ["IF-06"])
group(p, "Control interface and failure behaviour")
D(p, "PRP-D06", "The ESCs (AM32 20 A, KCL KC-03) shall accept commands per "
  "IF-05 (DShot300, 3D "
  "mode; PWM fallback).", "M", "T", "BENCH", ["IF-05", "NAV-001"])
D(p, "PRP-D07", "Each ESC shall stop its motor ≤ 1 s after command pulses "
  "stop.", "M", "T", "BENCH", ["FS-008", "V-09"])
D(p, "PRP-D08", "After signal loss, an ESC shall not restart until it sees "
  "a neutral command.", "M", "T", "BENCH", ["FS-008"])
group(p, "Guarding and weed")
D(p, "PRP-D09", "Each prop shall be fully shrouded, so that an 8 mm probe "
  "cannot touch a blade from any direction.", "M", "T", "BENCH",
  ["MEC-010"])
D(p, "PRP-D10", "Guard and strut leading edges shall be swept back ≥ 30°, "
  "with no forward-facing hooks. Inlet bars shall run at ≥ 45° to the flow. "
  "Prop blades shall have swept leading edges.", "S", "I", "BENCH",
  ["MEC-011", "ENV-005"])
D(p, "PRP-D11", "In sparse surface weed, a pod fouled at the inlet shall be "
  "clearable by ≤ 3 reverse bursts (FS-006) in ≥ 2 of 3 trials.", "S", "T",
  "LAKE", ["ENV-005"])
group(p, "Mechanical and handling")
D(p, "PRP-D12", "Pods shall mount per IF-17 and be swappable in < 2 min, "
  "tool-free, with keyed waterproof connectors.", "S", "T", "BENCH",
  ["MEC-008", "IF-17"])
D(p, "PRP-D13", "Each pod shall weigh ≤ 75 g including the motor.", "S", "T",
  "BENCH", ["MEC-002"])
D(p, "PRP-D14", "Pod shells and latches are child-handled parts "
  "(HUL-D22/D23 apply). The prop shall not be reachable while the pod is "
  "fitted or unfitted.", "M", "I", "BENCH", ["CHD-001", "CHD-002",
                                              "CHD-003"])
D(p, "PRP-D16", "ESC configuration: 3D mode set by the helm at boot "
  "(SERVO_BLH_3DMASK); low-voltage cut-off disabled, because battery "
  "protection belongs to the helm and BMS; BEC output left unconnected. "
  "AM32 stops the motor 0.5 s after signal loss and needs > 1 s of zero "
  "command to re-arm (firmware source, confirmed on the bench).", "M", "I",
  "BENCH", ["IF-05", "FS-008", "V-09"])
D(p, "PRP-D15", "Motors are consumables: rinse and dry after each session. "
  "Expected life ≥ 10 h submerged before replacement.", "S", "A", "LAKE",
  ["NAV-001"])

# ======================================================================
# PWR  Power
# ======================================================================
w = subsystem(
    "PWR", title="Power",
    issue="Issue C (for review)",
    parents="SRS Issue F, ADD Issue F, ICD Issue E, FMEA Issue D, KCL "
            "Issue B",
    history=[["B", "28 September 2026", "CR-03: tested salvaged 18650 "
              "cells (ADD DD-18) with acceptance tests PWR-D20 and records "
              "PWR-D21.", "Claude, owner decision"],
             ["C", "29 September 2026", "Key Component List and CR-04: the "
              "key switch is a high-side P-MOSFET (PWR-D07); supplies must "
              "tolerate pack sag near empty (PWR-D22).", "Claude, owner "
              "decision"]],
    purpose="Store and distribute energy safely. Give motor power only when "
            "an adult has inserted the magnetic key. Measure what's used.",
    inside=["3S Li-ion 18650 pack with BMS", "Main fuse and main switch",
            "Magnetic arming key, reed switch and MOSFET motor-rail switch",
            "Power module (V/I sense)", "5 V buck for the mission computer",
            "Harness and connectors"],
    outside=["Battery charger (owned; off-boat)", "Helm battery monitoring "
             "configuration (HLM)"],
    breakdown=[("PWR-1 Battery pack", "3 × tested salvaged 18650, 3S BMS, "
                "XT60"), ("PWR-2 Protection & switching", "20 A fuse, IP67 "
                                                          "main switch, key "
                                                          "switch"),
               ("PWR-3 Conversion & sensing", "Power module, 5 V 3 A buck, "
                "rail divider"), ("PWR-4 Harness", "Silicone wire, XT60/XT30, "
                                                   "keyed plugs")],
    constraints=["ADD DD-09: 3S Li-ion 18650 + BMS", "ADD DD-10: magnetic "
                 "key removes motor power independently of software",
                 "Charging only off-boat (PWR-007)"],
    budget=[("Mass allocation", "≤ 260 g (estimate 250 g)"),
            ("Cost allocation", "£23 (salvaged cells + BMS £7, fuse/box share £2, "
             "buck £3, key switch £4, IP67 main switch £4, sensing/wiring "
             "£3)"),
            ("Energy", "≈ 32 Wh nominal, ≈ 26 Wh usable")],
    special="pwr",
    open_items=[("TBC-06", "Motor current measurement → fuse and MOSFET "
                 "rating"), ("TBC-07 / V-13", "Arming gated on motor-rail "
                             "voltage"), ("PWR-OI-1", "Closed: IP67 main "
                                          "switch added to the ADD BOM "
                                          "(Issue C)")],
)
group(w, "Energy storage")
D(w, "PWR-D01", "The battery shall be 3S1P Li-ion 18650. Cells rated "
  "≥ 10 A continuous, measured capacity ≥ 2500 mAh; 27-36 Wh nominal.", "M",
  "I", "BENCH", ["PWR-001"])
D(w, "PWR-D02", "A 3S BMS shall provide over-discharge (2.5-2.8 V/cell), "
  "over-current (trip ≤ 25 A), short-circuit and balance protection.", "M",
  "T", "BENCH", ["PWR-002"])
D(w, "PWR-D03", "The pack shall be in a rigid sleeve with XT60 and a balance "
  "lead, removable from the box by an adult in < 30 s without tools.", "M",
  "D", "BENCH", ["PWR-007"])
D(w, "PWR-D20", "Salvaged cells shall be accepted only if each: has a "
  "known source and no dents, wrapper damage or leakage; holds ≥ 3.6 V "
  "after 7 days' rest from full (self-discharge ≤ 0.1 V); has a measured "
  "capacity ≥ 2500 mAh at 1 A; and has internal resistance ≤ 60 mΩ. The "
  "three cells shall match within 5% capacity and 10 mΩ. Anything else is "
  "rejected.", "M", "T", "BENCH", ["PWR-001", "PWR-002", "DD-18", "FM-23",
                                    "A-20"])
D(w, "PWR-D21", "Each accepted cell shall be labelled with an ID, and its "
  "test results recorded in the repository. The pack's capacity shall be "
  "re-measured each season.", "M", "I", "BENCH", ["PWR-001", "A-20"])
D(w, "PWR-D04", "The boat shall have no charging port. Charging is by "
  "external balance charger only.", "M", "I", "BENCH", ["PWR-007"])
group(w, "Protection and switching")
D(w, "PWR-D05", "A 20 A blade fuse shall sit ≤ 50 mm from the battery "
  "positive.", "M", "I", "BENCH", ["PWR-003", "IF-06"])
D(w, "PWR-D06", "The main switch shall be IP67, outside the box, and "
  "either rated ≥ 20 A or control a solid-state switch rated ≥ 30 A.", "M",
  "I", "BENCH", ["PWR-004"])
D(w, "PWR-D07", "The motor rail shall be switched by the magnetic key per "
  "IF-06: reed switch driving a high-side P-MOSFET in the positive feed, "
  "off when the key is absent, with a soft-start gate. Low-side switching "
  "is not allowed (ESC current would return through signal grounds).",
  "M", "T", "BENCH", ["MOD-003", "IF-06"])
D(w, "PWR-D22", "Every supply on the pack (flight controller, ESCs, 5 V "
  "buck) shall work down to 7.5 V, the rail voltage at the critical "
  "battery threshold (9.6 V resting) under the helm's power limit "
  "(HLM-D43) with acceptance-limit cells (0.22 Ω pack). The Matek F405-TE "
  "(9 V minimum) failed this analysis, hence CR-04.", "M", "A", "BENCH",
  ["PWR-005", "DD-19"])
D(w, "PWR-D08", "Motor-rail voltage shall be divided to the helm's second "
  "voltage input so arming is refused below 9.0 V.", "M", "T", "BENCH",
  ["MOD-003", "PRE-007", "V-13"])
D(w, "PWR-D09", "At power-up the motor rail shall be off unless the key is "
  "present. The helm is disarmed regardless (HLM-D04).", "M", "T", "BENCH",
  ["MOD-002"])
group(w, "Conversion and sensing")
D(w, "PWR-D10", "The helm shall be powered from the main bus before the key "
  "switch, through its own regulator (IF-07).", "M", "I", "BENCH",
  ["PWR-005", "IF-07"])
D(w, "PWR-D11", "The mission computer shall have a dedicated 5.1 V ≥ 3 A "
  "buck (IF-08).", "M", "T", "BENCH", ["PWR-005", "IF-08"])
D(w, "PWR-D12", "Helm and mission-computer supplies shall stay in regulation "
  "through a full reverse-to-forward thrust step at 12.6 V and at 9.0 V.",
  "M", "T", "BENCH", ["PWR-005"])
D(w, "PWR-D13", "Battery voltage and current shall be measured per IF-07 "
  "(± 1% V, ± 5% I after calibration).", "M", "T", "BENCH",
  ["PWR-006", "PRE-003"])
group(w, "Harness")
D(w, "PWR-D14", "Connectors: XT60 battery, XT30 per ESC, JST-XH balance, a "
  "keyed 2-pin for the mission computer. No connector type used for two "
  "functions. All polarised.", "M", "I", "BENCH", ["PWR-008"])
D(w, "PWR-D15", "Wire: 16 AWG battery to bus, 18 AWG to ESCs, silicone "
  "insulated. Joints soldered and heat-shrunk. Strain relief at every "
  "gland.", "M", "I", "BENCH", ["PWR-008", "MEC-012"])
D(w, "PWR-D16", "No exposed live conductor outside the box.", "M", "I",
  "BENCH", ["CHD-003"])
group(w, "Budgets and thermal")
D(w, "PWR-D17", "A power budget (docs/budgets/power.csv) shall be kept "
  "current, with ≥ 30% margin at the design endurance.", "S", "A", "BENCH",
  ["PWR-011"])
D(w, "PWR-D18", "Usable energy ≥ 25 Wh, supporting ≥ 40 min at the budgeted "
  "cruise load.", "M", "A", "BENCH", ["PWR-009"])
D(w, "PWR-D19", "The battery shall sit ≥ 30 mm from the ESCs. Box internal "
  "temperature ≤ 50 °C after 60 min at 30 °C ambient in sun.", "M", "T",
  "BENCH", ["PWR-010"])

# ======================================================================
# HLM  Helm
# ======================================================================
m = subsystem(
    "HLM", title="Helm",
    issue="Issue D (for review)",
    parents="SRS Issue F, ADD Issue F, ICD Issue E, FMEA Issue D, KCL "
            "Issue B",
    history=[["B", "28 September 2026", "CR-02: microSD logging (HLM-D02). FMEA actions A-01, A-02, "
              "A-06, A-18: HLM-D24 formalised; HLM-D39 to D41 added; "
              "parameter baseline extended.", "Claude, owner decisions "
              "(CR-02, FMEA actions)"],
             ["C", "28 September 2026", "CR-03: board class and real price "
              "(Matek F405-TE class, £62) in budget and HLM-D02.",
              "Claude, owner decision"],
             ["D", "29 September 2026", "CR-04: SpeedyBee F405 WING APP "
              "(HLM-D02). CR-05: GCS failsafe 3 s (HLM-D27). Simulator "
              "results folded into HLM-D05/08/20/24/25/26/28/29; HLM-D42 "
              "to D44 added; parameter baseline now generated from "
              "software/params.", "Claude, owner decisions"]],

    purpose="Navigate, enforce the fence and run every native failsafe on "
            "an independent RTOS processor, whatever else has failed.",
    inside=["Flight controller hardware (SpeedyBee F405 WING APP + PDB)",
            "ArduPilot Rover "
            "firmware (third party) and the controlled parameter set",
            "GNSS + compass module and mast cabling", "Fence and mission "
            "storage", "Dataflash / SD logging"],
    outside=["Everything that sends commands (MCN via IF-02, MCP via IF-04)",
             "Motor drives (PRP)", "Power sources (PWR)"],
    breakdown=[("HLM-1 Flight controller", "SpeedyBee F405 WING APP "
                "(STM32F405, ChibiOS), PDB with V/I sense, microSD"),
               ("HLM-2 Firmware", "ArduPilot Rover 4.7.1, pinned"),
               ("HLM-3 Parameter set", "software/params/boaty-mk1.parm "
                "(behaviour, also flown in SITL) + boaty-mk1-speedybee.parm "
                "(board wiring)"),
               ("HLM-4 GNSS/compass", "u-blox M10 + QMC5883L on the mast")],
    constraints=["ADD DD-19 (CR-04): SpeedyBee F405 WING APP, 7-36 V input",
                 "ADD DD-13: no "
                 "Lua; Python on the MCP covers Lua-type behaviours",
                 "No project-written code on the FC (SAF-001)"],
    budget=[("Mass allocation", "≤ 45 g (estimate 39 g: FC + PDB 25 g, "
             "GNSS 14 g)"),
            ("Cost allocation", "£63 (SpeedyBee F405 WING APP £45, GNSS £14, "
             "microSD £4)"),
            ("Power", "≈ 0.8 W including GNSS")],
    special="hlm",
    open_items=[("V-01", "Bench check of the SpeedyBee with Rover 4.7.1 "
                 "(every feature was exercised in SITL)"),
                ("V-02 … V-06, V-11 … V-17", "Answered in SITL (ADD "
                 "section 9); results folded into the requirements below"),
                ("Tuning", "MOT_THST_EXPO, CRUISE_THROTTLE, steering gains "
                 "from thrust-stand and pool data (HLM-D42)"),
                ("HLM-OI-1 / CR-02", "Closed: owner chose a flight "
                 "controller with microSD (ADD DD-15)")],
)
group(m, "Hardware and firmware")
D(m, "HLM-D01", "The helm shall run a pinned ArduPilot Rover stable release "
  "built for the chosen board: Rover 4.7.1 (tag Rover-4.7.1, commit "
  "dbe79216), the release the simulator flies. Version and hash are "
  "recorded in the repository.", "M", "I", "BENCH", ["SAF-001", "SWE-006"])
D(m, "HLM-D02", "The flight controller shall provide: ≥ 2 free UARTs (GNSS, "
  "companion), ≥ 3 DShot-capable outputs, ≥ 2 analogue battery inputs, I2C, "
  "IMU and baro, and a microSD slot (≥ 8 GB card) for logging "
  "(CR-02), and run from ≥ 7 V so it survives pack sag near empty. "
  "Baseline: SpeedyBee F405 WING APP (7-36 V, 5 usable UARTs, 12 DShot "
  "outputs, microSD; CR-04), wireless module not fitted.", "M", "I",
  "BENCH", ["SAF-001", "PRE-008", "V-01", "DD-15", "DD-19"])
D(m, "HLM-D03", "No project-written code (including Lua) shall run on the "
  "flight controller. It runs ChibiOS only.", "M", "I", "BENCH",
  ["SAF-001", "DD-13"])
D(m, "HLM-D04", "On power-up the helm shall be disarmed with motor outputs "
  "at neutral. Auto-arming shall be disabled.", "M", "T", "BENCH",
  ["MOD-002"])
group(m, "Modes")
D(m, "HLM-D05", "Only STEERING, HOLD, LOITER, AUTO, RTL and GUIDED "
  "(weed-shedding only) shall be used. The helm shall boot and arm into "
  "HOLD (INITIAL_MODE 4), with no RC mode switch (MODE_CH 0) and any RC "
  "receiver ignored (RC_OPTIONS 1). Without these SITL armed into MANUAL.",
  "M", "T", "SIM", ["MOD-001", "DD-12"])
D(m, "HLM-D06", "At mission end the helm shall RTL and then hold at home. "
  "The mission-done behaviour is set to hold as a backstop.", "M", "S", "SIM",
  ["MOD-005", "V-04"])
D(m, "HLM-D07", "Auto-disarm after 60 s at home is performed by Mission "
  "Control (MCN-D12). The helm shall accept it.", "C", "S", "SIM",
  ["MOD-008"])
group(m, "Pre-arm checks")
D(m, "HLM-D08", "All ArduPilot arming checks shall be enabled except the "
  "RC-channels check (no receiver is fitted: ARMING_SKIPCHK 64), and "
  "failures reported as STATUSTEXT (MCN translates them).", "M", "S", "SIM",
  ["MOD-004"])
D(m, "HLM-D09", "Arming shall need a 3D fix with HDOP ≤ 1.5. The ≥ 8 "
  "satellite check is done by Mission Control (MCN-D15).", "M", "T", "BENCH",
  ["PRE-001"])
D(m, "HLM-D10", "Arming shall need the fence enabled and loaded, with home "
  "inside it.", "M", "S", "SIM", ["PRE-002", "FEN-001"])
D(m, "HLM-D11", "Arming shall need ≥ 80% battery capacity remaining.",
  "M", "S", "SIM", ["PRE-003"])
D(m, "HLM-D12", "Arming shall need calibrated, consistent compass and "
  "EKF.", "M", "T", "BENCH", ["PRE-004"])
D(m, "HLM-D13", "Arming shall be refused with motor-rail voltage < 9.0 V "
  "(key out).", "M", "T", "BENCH", ["PRE-007", "MOD-003", "V-13"])
D(m, "HLM-D14", "Arming shall need logging available.", "M", "T", "BENCH",
  ["PRE-008"])
group(m, "Navigation")
D(m, "HLM-D15", "Cruise speed shall be set to 1.0 m/s and tuned to "
  "± 0.2 m/s.", "M", "T", "POOL", ["NAV-002"])
D(m, "HLM-D16", "Waypoint and RTL speeds shall be ≤ 1.5 m/s. Maximum "
  "throttle shall be limited so full throttle in STEERING gives ≤ 1.5 m/s "
  "in calm water.", "M", "T", "POOL", ["NAV-003"])
D(m, "HLM-D17", "Waypoint acceptance radius shall default to 3 m "
  "(configurable 1-10 m).", "M", "S", "SIM", ["NAV-004"])
D(m, "HLM-D18", "Steering and speed controllers shall be tuned to ≤ 3 m RMS "
  "cross-track error and ≤ 5 m loiter error in 3 m/s wind.", "S", "T", "LAKE",
  ["NAV-005", "NAV-006"])
D(m, "HLM-D19", "RTL shall plan around exclusion zones inside the "
  "inclusion fence (fence-aware path planning).", "M", "S", "SIM",
  ["NAV-007", "V-01"])
D(m, "HLM-D20", "NAV-008 shall be met by the helm's EKF together with B7's "
  "first-motion heading check (MCP-D22). V-16 showed the EKF alone keeps a "
  "wrong heading with its single compass rotated 90°, though navigation "
  "still tracked on GNSS course.", "S", "S", "SIM", ["NAV-008", "V-16"])
group(m, "Fence")
D(m, "HLM-D21", "The helm shall hold one inclusion polygon (≤ 70 vertices) "
  "and ≤ 10 exclusion polygons or circles, plus a 100 m circle backstop "
  "about home at Milton.", "M", "S", "SIM", ["FEN-001", "OPS-006"])
D(m, "HLM-D22", "The fence shall be enforced in every armed mode used.",
  "M", "S", "SIM", ["FEN-004", "V-02"])
D(m, "HLM-D23", "A breach shall trigger RTL within 1 s.", "M", "S", "SIM",
  ["FEN-005"])
D(m, "HLM-D24", "Persistent breach (> 30 s or > 10 m outside) shall stop "
  "the motors. V-14 found no native mechanism, so B7 (MCP-D30) and Mission "
  "Control (MCN-D59) each independently command HOLD, and either "
  "suffices. The helm's fence RTL stays the primary response.", "M", "S",
  "SIM", ["FEN-006", "V-14", "A-18", "FM-14", "DD-21"])
D(m, "HLM-D25", "Fence changes while armed shall be refused by every "
  "sender: C7 (IF-14) and the IF-04 filter. V-17 showed the helm itself "
  "accepts them, so these two are the only enforcement.", "M", "S", "SIM",
  ["FEN-007", "V-17"])
group(m, "Failsafes")
D(m, "HLM-D26", "Battery failsafe: RTL at 35% remaining; at 15%, "
  "continue RTL and alarm. V-15 found no native speed reduction, so B6 "
  "lowers the RTL speed (MCP-D29).", "M", "S", "SIM", ["FS-001", "V-15"])
D(m, "HLM-D27", "GCS failsafe on system-255 heartbeats: FS_GCS_TIMEOUT 2 s "
  "+ FS_TIMEOUT 1 s = HOLD 3 s after the link goes (CR-05; both are the "
  "firmware minimums), continue in AUTO. The later RTL steps are done by "
  "MCP B4 (MCP-D12).", "M", "T", "SIM", ["FS-002", "FS-003", "V-03",
                                          "V-06", "DD-22"])
D(m, "HLM-D28", "EKF/position failsafe → HOLD as a backstop. It took 9 s "
  "in SITL, so B6 stops the motors within FS-004's 3 s (MCP-D28) and does "
  "the recovery RTL (MCP-D15).", "M", "S", "SIM", ["FS-004", "DD-21"])
D(m, "HLM-D29", "Crash/stuck check → HOLD (CRASH_THR_MIN 50%, CRASH_VEL_MIN "
  "0.1 m/s, CRASH_TIMEOUT 5 s), raising an event the MCP acts on. One "
  "noisy GNSS speed sample resets its timer (V-05), so B7's second "
  "detector backs it up.", "M", "S", "POOL", ["FS-005", "V-05"])
D(m, "HLM-D30", "No companion-computer failsafe shall be configured: the "
  "helm completes missions without the MCP.", "M", "S", "SIM",
  ["FS-007", "SAF-002"])
D(m, "HLM-D31", "When failsafes combine, motors-stopped outranks RTL, "
  "which outranks continue. Demonstrated in SITL combinations.", "M", "S",
  "SIM", ["FS-011"])
D(m, "HLM-D32", "Every failsafe shall be logged and reported by "
  "STATUSTEXT.", "M", "S", "SIM", ["FS-012"])
group(m, "Independence, identity and logging")
D(m, "HLM-D33", "All fence and failsafe functions shall work with the MCP, "
  "Mission Control and the link all absent.", "M", "S", "SIM",
  ["SAF-002"])
D(m, "HLM-D34", "Only system 255 is the GCS. Parameter writes are "
  "accepted only while disarmed through IF-14. Boat services are "
  "filtered (IF-04).", "M", "T", "SIM", ["SAF-003", "IF-02", "IF-04"])
D(m, "HLM-D35", "The GNSS/compass shall be mast-mounted ≥ 150 mm from "
  "power wiring, with motor interference ≤ 30% after a motor-interference "
  "calibration.", "M", "T", "BENCH", ["MEC-013"])
D(m, "HLM-D36", "The helm shall log position, attitude, mode, commands, "
  "battery and failsafes at ≥ 5 Hz.", "M", "T", "BENCH", ["LOG-001"])
D(m, "HLM-D37", "A spare UART shall be kept for an optional ExpressLRS "
  "receiver, with RC failsafe = RTL if fitted.", "C", "I", "BENCH",
  ["COM-007"])
D(m, "HLM-D38", "The beacon output shall be configured per IF-09.", "S",
  "T", "BENCH", ["IF-09", "REC-004"])
group(m, "FMEA-driven (Issue B)")
D(m, "HLM-D39", "GNSS glitch rejection (EKF3, glitch radius ≤ 25 m) and "
  "GNSS data-timeout detection shall be enabled. A glitch or frozen "
  "position shall not produce an uncommanded exit from the fence (SC-20, "
  "SC-21, L2-04).", "M", "S", "SIM", ["FS-004", "FS-013", "A-01", "FM-02",
                                      "FM-03"])
D(m, "HLM-D40", "Voltage thresholds shall back up the mAh battery "
  "failsafe: low 10.2 V and critical 9.6 V under load for ≥ 10 s, with "
  "the same actions. Whichever triggers first applies.", "M", "T", "BENCH",
  ["FS-001", "A-06", "FM-15"])
D(m, "HLM-D41", "Compass interference shall be measured on rig L2 at full "
  "thrust before the hull layout is frozen. Above 30%, wiring or mast "
  "height changes before build.", "M", "T", "BENCH", ["MEC-013", "A-02",
                                                      "FM-04"])
group(m, "Found in simulation (Issue D)")
D(m, "HLM-D42", "The throttle-to-thrust curve shall be linearised "
  "(MOT_THST_EXPO), because props give thrust ~ throttle^2. At the default "
  "a 180° pivot took 20 s in SITL; at 1.0 it takes 6 s. Re-tuned from "
  "thrust-stand data before the pool.", "M", "T", "POOL",
  ["NAV-001", "NAV-005"])
D(m, "HLM-D43", "Motor power shall be limited (BATT_WATT_MAX 70 W) so pack "
  "sag near empty cannot brown out the ESCs or flight controller (KCL "
  "section 5), while leaving thrust to make headway in the ENV-002 wind.",
  "M", "A", "BENCH", ["PWR-005", "DD-19"])
D(m, "HLM-D44", "The helm shall have exactly one MAVLink command path: "
  "SERIAL1 to the mission computer. The flight controller's wireless "
  "module is not fitted and SERIAL6 is disabled.", "M", "I", "BENCH",
  ["SAF-003", "IF-02", "IF-04"])

# ======================================================================
# MCP  Mission computer
# ======================================================================
c = subsystem(
    "MCP", title="Mission computer",
    issue="Issue D (for review)",
    parents="SRS Issue F, ADD Issue F, ICD Issue F, FMEA Issue E",
    history=[["B", "28 September 2026", "FMEA actions A-03, A-07, A-08, A-11: navigation monitor B7 "
              "(MCP-D22 to D25, D27) and box temperature (MCP-D26).", "Claude, owner decisions "
              "(CR-02, FMEA actions)"],
             ["C", "29 September 2026", "Simulator slice 2: B6 takes the "
              "FS-004 HOLD (MCP-D28) and the FS-001 slow RTL (MCP-D29); B7 "
              "takes FEN-006 (MCP-D30); B5 astern bursts by thrust command "
              "(MCP-D18, ICD IF-04 correction); MCP-D31 to D33 from "
              "integration. All SIM requirements now have passing "
              "scenarios (software/results).", "Claude, owner decision "
              "(slice 2)"],
             ["D", "29 September 2026", "SC-06 intermittent failure traced "
              "to B5's free test (astern drift counted as moving): MCP-D34 "
              "added (FMEA FM-58, A-29).",
              "Claude"]],

    purpose="Take and geotag photos, relay MAVLink to the bank, and run the "
            "small boat-side watchdogs, without ever being needed for "
            "safety.",
    inside=["Raspberry Pi Zero 2W, microSD, heatsink", "5 MP camera",
            "Moisture sensor", "OS image and services B1-B7 "
            "(software/boaty/mcp)"],
    outside=["Its 5 V supply (PWR)", "Camera hood and mount (HUL)",
             "Helm behaviour (HLM)"],
    breakdown=[("MCP-1 Computer", "Pi Zero 2W, 32 GB A1/U3 microSD, "
                "heatsink"), ("MCP-2 Camera", "OV5647-class 5 MP, ≤ 62° "
                              "HFOV"),
               ("MCP-3 Sensors", "Moisture traces at the box low point; "
                "DS18B20 box temperature sensor"),
               ("MCP-4 Software", "B1 router, B2 camera, B3 photo server, "
                "B4 link watchdog, B5 weed-shedding, B6 health, "
                "B7 navigation monitor")],
    constraints=["ADD DD-03 / T4: Pi Zero 2W (Python)", "ADD section 4.3 "
                 "rule: may request only safer states; B5 bounded GUIDED",
                 "SWE-001: Python services"],
    budget=[("Mass allocation", "≤ 35 g (estimate 30 g)"),
            ("Cost allocation", "£29 (Pi £15, camera £8, SD £4, "
             "temperature sensor £2); the flight controller's SD card is "
             "in HLM"),
            ("Power", "≤ 2.0 W average, ≤ 3.0 W peak")],
    special="mcp",
    open_items=[("V-10", "Thermal in the sealed box"),
                ("V-11", "Answered: the helm stops 3.9 s after the last "
                 "target (3 s timeout + deceleration); accepted"),
                ("B1", "The simulator uses a Python router with "
                 "mavlink-router's topology; the boat runs mavlink-router "
                 "itself (check on rig L1)")],
)
group(c, "Hardware")
D(c, "MCP-D01", "The mission computer shall be a Pi Zero 2W with a 32 GB "
  "A1/U3 microSD and a 5 MP camera.", "M", "I", "BENCH", ["CAM-001",
                                                         "DD-03"])
D(c, "MCP-D02", "Camera horizontal field of view shall be ≤ 62°, giving "
  "≥ 120 px across a 0.3 m duck at 5 m (at 2592 px width).", "S", "A",
  "BENCH", ["CAM-005"])
D(c, "MCP-D03", "A moisture sensor (exposed traces at the box's lowest "
  "point) shall be read by GPIO.", "S", "T", "BENCH", ["FS-010"])
D(c, "MCP-D04", "The SoC shall have a heatsink, and 60 min at 30 °C in the "
  "sealed box in sun shall give no throttling (throttled flag = 0).", "M",
  "T", "BENCH", ["PWR-010", "V-10"])
D(c, "MCP-D05", "Average power ≤ 2.0 W, peak ≤ 3.0 W.", "S", "T", "BENCH",
  ["PWR-011"])
group(c, "Platform software")
D(c, "MCP-D06", "The OS shall be Raspberry Pi OS Lite 64-bit with a "
  "read-only root filesystem and a separate data partition.", "M", "T",
  "BENCH", ["CAM-004", "IF-08"])
D(c, "MCP-D07", "Services B1-B7 shall be systemd units that restart "
  "automatically and are running ≤ 45 s after power-on.", "M", "T", "BENCH",
  ["IF-04", "IF-03"])
D(c, "MCP-D08", "The clock shall be set from helm GNSS time at start "
  "(no internet on the boat).", "S", "T", "BENCH", ["SWE-008"])
D(c, "MCP-D09", "SSH shall be key-only, and the firewall per IF-01.", "M",
  "I", "BENCH", ["COM-006", "IF-01"])
group(c, "Camera and photos (B2, B3)")
D(c, "MCP-D10", "B2 shall capture on interval (2-30 s during AUTO), at "
  "photo points (burst_n within 0.5 s of arrival) and on command.", "M", "T",
  "SIM", ["CAM-002", "IF-03"])
D(c, "MCP-D11", "Each photo shall carry UTC time, lat/lon/heading "
  "(≤ 0.5 s old, else null) and mission ID, in EXIF and the index.", "M",
  "T", "SIM", ["CAM-003"])
D(c, "MCP-D12", "B4 (link watchdog): in AUTO with no system-255 heartbeat "
  "for 60 s → RTL. In HOLD after a MANUAL link loss, at 10 s → RTL.", "M",
  "S", "SIM", ["FS-003", "FS-002"])
D(c, "MCP-D13", "≥ 5 GB shall be reserved for photos (≥ 500 at ≤ 2.5 MB). "
  "Capture stops below 500 MB free. Navigation is unaffected.", "M", "T",
  "BENCH", ["CAM-004"])
D(c, "MCP-D14", "B3 shall implement IF-03, with thumbnails made at capture "
  "time.", "M", "T", "BENCH", ["IF-03", "CAM-007"])
D(c, "MCP-D15", "B6 (health): moisture or box > 60 °C → RTL within 2 s "
  "plus STATUSTEXT, unless the position is unhealthy (then HOLD wins, "
  "FS-011). After a position-loss HOLD, RTL once the position has been "
  "healthy for 10 s.", "M", "S", "SIM", ["FS-010", "FS-004", "FS-011"])
D(c, "MCP-D16", "Photo sync throughput ≥ 11 Mbit/s with the boat ≤ 10 m "
  "from the bank (200 photos ≤ 5 min).", "S", "T", "POOL", ["CAM-007"])
D(c, "MCP-D17", "Optional live view: 320 × 240 MJPEG at 2 fps when "
  "enabled, paused during sync.", "C", "D", "POOL", ["CAM-008"])
group(c, "Weed-shedding and command filter (B5)")
D(c, "MCP-D18", "B5 shall act only on a stuck event (helm crash check or "
  "B7). Up to 3 GUIDED astern bursts (≤ 0.5 m/s, ≤ 2 s, commands at 10 "
  "Hz), then resume the previous mode; keep it if the boat is free "
  "(MCP-D34), else HOLD + alarm. Bursts use SET_ATTITUDE_TARGET thrust with "
  "zero yaw rate: a negative velocity target makes Rover turn round "
  "instead (ICD IF-04, Issue E).", "S", "S", "SIM", ["FS-006", "V-11"])
D(c, "MCP-D19", "All services shall send MAVLink only through a shared "
  "client with a default-deny filter (IF-04 list, per-service policy). "
  "Proven by fuzzing every forbidden command from every service in every "
  "helm mode (SC-30).", "M", "T", "SIM", ["SAF-003", "IF-04"])
group(c, "Future: on-board duck spotting")
D(c, "MCP-D20", "An upgrade may run an on-device bird detector at ≥ 2 fps "
  "that requests 'pause and look'.", "C", "T", "POOL", ["DET-003"])
D(c, "MCP-D21", "'Pause and look' shall only request LOITER (≤ 20 s) and "
  "then resume. It shall never steer towards the detection.", "M", "S",
  "SIM", ["DET-004"], "Applies only if MCP-D20 is implemented.")
group(c, "Navigation monitor B7 and box temperature (Issue B)")
D(c, "MCP-D22", "First-motion heading check: in the first 10 s of AUTO, "
  "RTL or STEERING, once above 0.3 m/s, a GNSS-course vs heading "
  "difference > 45° for 3 s shall request HOLD and raise an alarm.", "M",
  "S", "SIM", ["FS-013", "A-03", "FM-05", "FM-18"])
D(c, "MCP-D23", "Second stuck detector: throttle ≥ 50% and progress along "
  "the active leg < 0.1 m/s for 10 s in AUTO or RTL shall request HOLD and "
  "raise a stuck event, which B5 acts on.", "S", "S", "SIM",
  ["FS-005", "A-07", "FM-16"])
D(c, "MCP-D24", "Divergence watchdog: in AUTO or RTL, cross-track error "
  "> 10 m or heading error to target > 60° for 20 s shall request HOLD and "
  "raise an alarm.", "M", "S", "SIM", ["FS-013", "A-08", "FM-17"])
D(c, "MCP-D25", "B7 shall only request HOLD, through the IF-04 filter. It "
  "shall never resume, arm or change mode otherwise. Resuming is an adult "
  "decision at Mission Control.", "M", "T", "SIM", ["SAF-003", "IF-04"])
D(c, "MCP-D26", "A DS18B20 at the top of the box interior shall be read at "
  "1 Hz. Above 60 °C, B6 requests RTL and raises an alarm. The value is "
  "reported as box_temp_c (IF-03).", "M", "T", "BENCH",
  ["PWR-010", "IF-03", "A-11", "FM-23"])
D(c, "MCP-D27", "B7 thresholds shall be configuration, version-"
  "controlled, and exercised by SC-05, SC-29 and SC-38.", "M", "I", "SIM",
  ["SAF-007", "A-03", "A-07", "A-08"])
group(c, "Gaps the helm cannot close (ADD DD-21)")
D(c, "MCP-D28", "B6 shall request HOLD when the position has been unhealthy "
  "(no 3D fix, HDOP > 2.5 or EKF unhealthy) for 1 s as the helm reports "
  "it. The helm takes ~1.5 s to report a loss, so the motors stop within "
  "FS-004's 3 s of the loss itself (2.5-2.7 s in SITL). The native EKF "
  "failsafe alone took 9 s.", "M", "T", "SIM", ["FS-004", "DD-21"])
D(c, "MCP-D29", "At critical battery (≤ 15% or the helm's critical alarm), "
  "B6 shall reduce the RTL speed to 0.6 m/s with DO_CHANGE_SPEED and raise "
  "an alarm. It may only reduce speed, and only in RTL.", "M", "T", "SIM",
  ["FS-001", "V-15", "DD-21"])
D(c, "MCP-D30", "B7 shall request HOLD when the boat has been outside the "
  "fence for 30 s or is more than 10 m outside it (distance computed from "
  "the fence read back from the helm), in any powered mode.", "M", "T",
  "SIM", ["FEN-006", "V-14", "DD-21", "FM-14"])
group(c, "Found in integration (Issue C)")
D(c, "MCP-D31", "B7's stuck and divergence checks shall be suspended within "
  "5 m of the active target: when station-keeping at home, progress along "
  "a leg is meaningless and wind can push throttle past 50%.", "M", "T",
  "SIM", ["FS-005", "A-07"])
D(c, "MCP-D32", "A service shall not send mode-dependent commands until the "
  "helm's heartbeat reports that mode (the filter checks against the "
  "reported mode). B5 waits for GUIDED before its first burst.", "M", "T",
  "SIM", ["SAF-003", "IF-04"])
D(c, "MCP-D33", "All MAVLink shall be version 2 from the first packet "
  "(IF-02). MAVLink 1 silently drops extension fields such as "
  "mission_type.", "M", "I", "SIM", ["IF-02"])
D(c, "MCP-D34", "B5 shall judge the boat free only on forward speed (along "
  "the heading) above 0.2 m/s held for 1 s within 8 s of resuming: the "
  "burst leaves the boat drifting astern, which ground speed counts as "
  "moving (SC-06). More than 3 episodes in 120 s means HOLD and a "
  "'repeatedly stuck' alarm (a dead motor looks like weed). A refused or "
  "unconfirmed GUIDED switch is retried once, then reported as 'no "
  "control', never as 'still stuck'. Each watch is logged.", "M", "T", "SIM", ["FS-006", "FM-58"])

# ======================================================================
# MCN  Mission Control
# ======================================================================
n = subsystem(
    "MCN", title="Mission Control",
    issue="Issue E (for review)",
    parents="SRS Issue G, ADD Issue F, ICD Issue F, FMEA Issue F",
    history=[["B", "28 September 2026", "FMEA actions A-03, A-04, A-10, A-13, A-15, A-16, A-18, A-19: "
              "MCN-D53 to D60 added.", "Claude, owner decisions "
              "(CR-02, FMEA actions)"],
             ["C", "28 September 2026", "CR-03: adult PIN on the web UI "
              "replaces the panel key switch (MCN-D02, D14, D60, D61).",
              "Claude, owner decision"],
             ["D", "29 September 2026", "Simulator slice 3 (Mission "
              "Control built and flown on SITL): MCN-D29, D39, D45, D57 and "
              "D60 clarified from the evidence; MCN-D62 to D64 added.",
              "Claude"],
             ["E", "30 September 2026", "SDR decisions (CR-07): MCN-D65 "
              "nest stand-off in the site linter; MCN-D66 planner routes "
              "round large exclusions.", "Claude, owner decision"]],

    purpose="Be the only place people interact with Boaty: turn words into "
            "safe, approved missions, and show, say and record what the "
            "boat is doing.",
    inside=["Raspberry Pi 5, case and panel (4 buttons, LEDs)",
            "USB Wi-Fi adapter and antenna (pole kit if needed)",
            "USB mic and speaker", "Application components C1-C10",
            "Site files, logs, captain's logs"],
    outside=["The phone/tablet (display, internet)", "The Claude API",
             "Helm behaviour (HLM)"],
    breakdown=[("MCN-1 Hardware", "Pi 5, cooler, case, panel, radio, "
                "audio"),
               ("MCN-2 Session & UI", "C1 session manager, C2 panel I/O, "
                "C3 web UI, C4 voice"),
               ("MCN-3 Mission chain", "C5 planner, C6 validator, C7 helm "
                "interface"),
               ("MCN-4 Records", "C8 photos & log, C9 site store, C10 "
                "logger")],
    constraints=["ADD AR-2: intelligence on the bank", "ADD DD-04: LLM "
                 "returns intent; Python makes geometry", "ADD DD-06/07/08: "
                 "Pi 5 AP, on-device speech, web UI"],
    budget=[("Mass", "Not constrained (bank)"),
            ("Cost allocation", "£26 (buttons £6, mic/speaker £8, "
             "adapter £12) + £8 pole kit if needed"),
            ("Power", "≈ 6.5 W average from a USB-C PD bank")],
    special="mcn",
    open_items=[("TBC-10", "Closed: TALK button (ICD Issue B)"),
                ("V-07", "On-device speech latency and child accuracy"),
                ("V-08", "Link range with and without the pole")],
)
group(n, "Hardware and platform")
D(n, "MCN-D01", "Mission Control shall be a Pi 5 (≥ 4 GB) with an active "
  "cooler in a printed splash-resistant case with drip edges. ≥ 2.5 h on a "
  "20,000 mAh USB-C PD bank.", "M", "T", "BENCH", ["MC-001", "MC-013"])
D(n, "MCN-D02", "The panel shall have TALK, GO, COME HOME and STOP buttons "
  "(≥ 30 mm, colour + icon, LEDs), per IF-12. There is no panel key "
  "switch.", "M",
  "I", "BENCH", ["MC-002", "CHD-005", "IF-12"])
D(n, "MCN-D03", "The radio shall be a USB adapter with an RP-SMA antenna, "
  "acting as AP per IF-01 (country GB, per-site channel, WPA2+, "
  "non-default passphrase).", "M", "T", "LAKE", ["COM-001", "COM-002",
                                                 "COM-006"])
D(n, "MCN-D04", "Internet shall come only via the phone USB tether per "
  "IF-10. The boat network has no route out.", "M", "T", "BENCH",
  ["COM-005", "IF-10"])
D(n, "MCN-D05", "The application shall start automatically ≤ 60 s after "
  "power-on.", "S", "T", "BENCH", ["SWE-009"])
D(n, "MCN-D06", "The clock shall be disciplined from helm GNSS time when "
  "there's no internet. All logs are UTC.", "S", "T", "BENCH", ["SWE-008"])
D(n, "MCN-D07", "Everything except natural-language planning and cloud "
  "photo analysis shall work offline, including cached map tiles per "
  "site.", "M", "T", "BENCH", ["MC-011"])
group(n, "C1 Session manager and C2 panel")
D(n, "MCN-D08", "The session state machine (ICD Figure 4) shall gate every "
  "button. GO works only in ARMED with a verified mission. COME HOME and "
  "STOP work in every armed state.", "M", "T", "SIM", ["MC-003", "VAL-008"])
D(n, "MCN-D09", "GO shall need a 1.0 ± 0.1 s press-and-hold.", "S", "T",
  "BENCH", ["MC-004"])
D(n, "MCN-D10", "STOP shall call helm.stop() ≤ 50 ms after the button "
  "edge. End-to-end ≤ 1 s (IF-02 budget).", "M", "T", "POOL", ["FS-009"])
D(n, "MCN-D11", "An adult shall be able to command HOLD, RTL, MANUAL or "
  "STOP at any time while armed, overriding AUTO.", "M", "T", "SIM",
  ["MOD-006"])
D(n, "MCN-D12", "Mode changes shall be shown and spoken ≤ 2 s after the "
  "helm reports them. Auto-disarm after 60 s at home.", "S", "T", "SIM",
  ["MOD-007", "MOD-008"])
D(n, "MCN-D13", "The checklist shall hold every OPS-001 item and record "
  "who signed it off, and when. Arming is blocked until it's done.", "M",
  "D", "SIM", ["PRE-006", "MC-010"])
D(n, "MCN-D14", "Arming, approval, fence editing, parameter changes, "
  "manual drive and the cloud toggle shall need the adult PIN (IF-12: 6 "
  "digits, 10 min unlock, lockout after 5 failures).", "M", "T", "SIM",
  ["MC-008", "DD-17"])
D(n, "MCN-D15", "Before arming, Mission Control shall also check ≥ 8 "
  "satellites, a verified mission and ≥ 1 GB free locally.", "M", "T", "SIM",
  ["PRE-005", "PRE-001", "PRE-008"])
group(n, "C3 Web UI")
D(n, "MCN-D16", "The map view shall show boat, heading, track, fence, "
  "exclusions, home, mission, battery, link, mode and time left, at "
  "≥ 1 Hz.", "M", "D", "SIM", ["MC-005"])
D(n, "MCN-D17", "A high-contrast daylight theme (≥ 16 px text) shall work "
  "on phone and tablet.", "S", "D", "LAKE", ["MC-006"])
D(n, "MCN-D18", "The 'find my boat' view shall keep the last position, "
  "time and track after link loss.", "M", "T", "SIM", ["MC-009"])
D(n, "MCN-D19", "The fence editor shall show the 5 m guide, warn on "
  "violations, save to the site file and commit it to git.", "M", "D", "SIM",
  ["FEN-002", "FEN-003", "IF-15"])
D(n, "MCN-D20", "An adult map mission editor shall route every edit "
  "through the validator.", "S", "D", "SIM", ["MIS-006"])
D(n, "MCN-D21", "Link quality (RSSI both ends) shall be shown and logged "
  "at 1 Hz.", "S", "D", "POOL", ["COM-004"])
D(n, "MCN-D22", "Manual drive from an on-screen joystick or gamepad: 10 Hz "
  "MANUAL_CONTROL with a dead-man (release → zero).", "S", "D", "POOL",
  ["MC-012"])
D(n, "MCN-D23", "Crew photo review: large thumbnails, GO = next, "
  "COME HOME = back to start, ducks highlighted.", "S", "D", "SIM",
  ["MC-015"])
D(n, "MCN-D24", "With the application paused, QGroundControl shall be able "
  "to take over UDP 14550 as a backup ground station.", "S", "D", "SIM",
  ["MC-014"])
group(n, "C4 Voice")
D(n, "MCN-D25", "TALK held → record (≤ 15 s) → on-device STT → transcript "
  "shown to the adult. Audio is never stored or sent.", "S", "T", "BENCH",
  ["NLI-002", "V-07"])
D(n, "MCN-D26", "A typed instruction box shall be available on the web "
  "UI.", "M", "D", "SIM", ["NLI-001"])
D(n, "MCN-D27", "Spoken announcements shall use the IF-12 phrase set via "
  "on-device TTS.", "S", "D", "SIM", ["MC-007"])
group(n, "C5 Planner")
D(n, "MCN-D28", "Requests shall follow IF-11 and include site context "
  "(names, sizes, battery, limits). No coordinates.", "M", "T", "SIM",
  ["NLI-003", "IF-11"])
D(n, "MCN-D29", "Replies shall be validated against Intent v1. On failure, "
  "retry once with the problem passed back as data (≤ 2 allowed), then "
  "offer templates. Planner and validator failures count the same way.",
  "M", "T", "SIM",
  ["NLI-004"])
D(n, "MCN-D30", "The plan shall be drawn on the map, and its "
  "summary_for_child shown and spoken.", "M", "D", "SIM", ["NLI-005"])
D(n, "MCN-D31", "Declines (off-site names, chasing animals, leaving the "
  "fence) shall come from the system prompt rules and planner checks, "
  "worded for a child, with an alternative offered.", "M", "T", "SIM",
  ["NLI-006"])
D(n, "MCN-D32", "Plan display ≤ 20 s at the 95th percentile on 4G.", "S",
  "T", "LAKE", ["NLI-007"])
D(n, "MCN-D33", "The API key shall live in a 0600 file outside the "
  "repository. CI runs a secret scan.", "M", "I", "SIM", ["NLI-008"])
D(n, "MCN-D34", "The geometry generator shall make survey lanes (light "
  "20 m, medium 12 m, thorough 8 m spacing), photo stops ≥ keep_out_m from "
  "landmarks, and a final RTL.", "M", "T", "SIM", ["MIS-001", "MIS-002"])
D(n, "MCN-D35", "The duration and energy estimate shall be conservative "
  "(× 1.2) and enforce 20 min (max 30) and 50% of usable energy.", "M", "T",
  "SIM", ["MIS-003"])
D(n, "MCN-D36", "Intent, Mission and ValidationResult shall be versioned "
  "pydantic models per IF-13.", "M", "I", "SIM", ["MIS-004", "IF-13"])
D(n, "MCN-D37", "At least three offline templates, parameterised by site "
  "areas.", "M", "D", "SIM", ["MIS-005"])
group(n, "C6 Validator and C7 helm interface")
D(n, "MCN-D38", "helm.upload_mission shall accept only a ValidatedMission "
  "type that only the validator can create (type-level single path).", "M",
  "T", "SIM", ["VAL-001", "SAF-004"])
D(n, "MCN-D39", "The validator shall implement VAL-002 to VAL-005 in local "
  "ENU metres, sampling legs every ≤ 1 m, including the final straight "
  "leg home. Each leg's ends are checked against the fence first, and only "
  "legs with both ends inside are sampled (a waypoint at 0° N 0° E once "
  "cost 56 s of sampling).", "M", "T", "SIM",
  ["VAL-002", "VAL-003", "VAL-004", "VAL-005"])
D(n, "MCN-D40", "The validator shall do no I/O and be deterministic, with "
  "≥ 95% branch coverage and ≥ 50 adversarial cases.", "M", "T", "SIM",
  ["VAL-006"])
D(n, "MCN-D41", "Violations shall be reported with rule, adult and child "
  "messages, and a map location.", "M", "D", "SIM", ["VAL-007"])
D(n, "MCN-D42", "Approval shall bind to the mission checksum. Any change "
  "voids it.", "M", "T", "SIM", ["VAL-008", "VAL-009"])
D(n, "MCN-D43", "GO shall be enabled only after read-back checksum "
  "equality (IF-02).", "M", "T", "SIM", ["VAL-010", "PRE-005"])
D(n, "MCN-D44", "C7 shall implement the IF-14 Helm protocol "
  "(ArduPilotHelm, pymavlink), selected by configuration.", "M", "T", "SIM",
  ["SWE-002", "SWE-003", "IF-14"])
D(n, "MCN-D45", "On connect, C7 shall compare helm parameters with the "
  "committed file. A mismatch blocks arming and shows the difference. "
  "Values the parameter stream drops are fetched again by index, so link "
  "loss never shows as a false difference.", "S",
  "T", "SIM", ["SAF-007"])
D(n, "MCN-D46", "Telemetry ≥ 1 Hz and command latency ≤ 1 s (P95) shall be "
  "measured and logged every session.", "M", "T", "POOL", ["COM-003"])
group(n, "C8 Photos & log, C10 logger")
D(n, "MCN-D47", "Photos shall be synced per IF-03 after each mission and "
  "sha256-verified before ack. Kept locally, never published "
  "automatically. Cloud analysis off by default per session.", "M", "T",
  "BENCH", ["LOG-004", "CAM-007"])
D(n, "MCN-D48", "The waterfowl finder shall reach ≥ 80% precision on the "
  "lake test set (cloud when enabled, else on-device heuristic).", "S", "T",
  "LAKE", ["DET-001"])
D(n, "MCN-D49", "The captain's log shall have ≤ 6 photos, route map, "
  "distance, duration, ducks and a child-friendly story, saved as "
  "HTML/PDF.", "S", "D", "LAKE", ["DET-002"])
D(n, "MCN-D50", "The session log shall be structured JSON lines: commands, "
  "approvals, missions, LLM I/O, validator results, events, RSSI.", "M", "I",
  "SIM", ["LOG-002"])
D(n, "MCN-D51", "After each session the helm log shall be downloaded. A "
  "replay tool shows the trip and every failsafe on a map.", "M", "D", "SIM",
  ["LOG-003"])
D(n, "MCN-D52", "Sessions may sync to a home computer when on the home "
  "network, kept ≥ 12 months.", "C", "D", "SIM", ["LOG-005"])
group(n, "FMEA-driven (Issue B)")
D(n, "MCN-D53", "The site linter shall check the IF-15 rules, plus: every "
  "home is inside the inclusion fence; the site is within 1 km of its "
  "configured reference; coordinates are in [lon, lat] order and inside a "
  "UK bounding box. It runs on save and at session start, and a failure "
  "blocks arming.", "M", "T", "SIM", ["FEN-002", "IF-15", "A-04",
                                      "FM-11"])
D(n, "MCN-D54", "Checklist rail test: key out → motor rail < 0.5 V shown; "
  "key in → rail ≈ battery. Failure shows 'key switch fault' and blocks "
  "arming.", "M", "T", "BENCH", ["MOD-003", "MC-010", "A-10", "FM-22"])
D(n, "MCN-D55", "Checklist button test: TALK, GO, COME HOME and STOP each "
  "pressed, with LED and sound confirming. Failure blocks arming.", "M",
  "T", "BENCH", ["MC-002", "MC-010", "A-13", "FM-32"])
D(n, "MCN-D56", "The plan preview shall show duration, distance, photo "
  "count and furthest point from home, prominently and before the approve "
  "control.", "S", "D", "SIM", ["VAL-008", "A-15", "FM-36"])
D(n, "MCN-D57", "C7 shall detect any other system-255 heartbeat on the "
  "link. Until the other source goes it refuses every command that starts "
  "or continues motion (arm, upload, GO, manual, drive) and raises an "
  "alarm. STOP, HOLD and come home stay available.", "M", "T", "SIM",
  ["MC-014", "A-16", "FM-41"])
D(n, "MCN-D58", "Site files list launch points with suitable wind "
  "directions (IF-15). The checklist asks 'Is the wind blowing towards "
  "us?' and suggests a launch point. 'No' blocks arming.", "S", "D", "SIM",
  ["OPS-001", "IF-15", "A-19", "FM-42"])
D(n, "MCN-D59", "C1 shall command HOLD if a fence breach persists > 30 s "
  "or the boat is > 10 m outside (interim path of HLM-D24).", "M", "S",
  "SIM", ["FEN-006", "A-18", "FM-14"])
D(n, "MCN-D60", "Boat-service holds (B5, B6, B7) shall be shown and spoken "
  "with the reason, which comes from the service's event text (the mode "
  "change can arrive first). A HOLD nothing explains is announced after "
  "1 s. Weed-shedding is spoken once per episode. Resuming requires the "
  "adult PIN.", "M", "T", "SIM",
  ["MOD-007", "A-03", "A-08"])
D(n, "MCN-D61", "The PIN shall be entered only on the adult's device, "
  "never shown or spoken, and changeable in Settings. The owner changes it "
  "at the start of each season.", "M", "I", "SIM", ["MC-008", "FM-48"])
group(n, "From the simulator (Issue D)")
D(n, "MCN-D62", "C1 shall follow mission progress by item sequence: the "
  "final return-home item runs inside AUTO, so 'coming home' and photo "
  "points are announced from the sequence and position, not the mode. "
  "RTL mode during a mission means a failsafe or an adult command.", "M",
  "T", "SIM", ["MOD-007", "MC-007", "IF-13"])
D(n, "MCN-D63", "C1 shall stop the motors with the boat still armed "
  "(IF-14 halt()) for MCN-D59, so an adult can still bring it home.", "M",
  "T", "SIM", ["FEN-006", "IF-14"])
D(n, "MCN-D64", "VAL-010 shall compare the helm view of the mission "
  "(kind, position, hold, speed; ICD IF-13 Issue F). Photo counts go to "
  "the camera service and are not in the read-back.", "M", "T", "SIM",
  ["VAL-010", "IF-13"])
group(n, "From the System Design Review (Issue E)")
D(n, "MCN-D65", "The site linter shall block a site in which a nest "
  "exclusion (IF-15 wildlife = nest) is a circle under 15 m radius, and "
  "shall warn that a nest polygon must be drawn 15 m out from the nests. "
  "Landmarks at nests keep photo stops outside the exclusion (MCN-D34).",
  "M", "T", "SIM", ["OPS-005", "IF-15"])
D(n, "MCN-D66", "The planner shall route round exclusions by the shortest "
  "clear path through candidate points around them, with as many hops as "
  "needed, and shall refuse a plan it cannot route.", "M", "T", "SIM",
  ["VAL-002"])

# ======================================================================
# REC  Recovery & signalling
# ======================================================================
r = subsystem(
    "REC", title="Recovery & signalling",
    purpose="Make the boat easy to see, easy to find and easy to retrieve "
            "with no power, no software and no radio.",
    inside=["Hi-vis finish", "Flag", "Recovery hoop", "LED beacon ring "
            "(hardware)", "'If found' labels", "Optional tracker pocket",
            "Bank recovery kit"],
    outside=["Beacon drive and patterns (HLM)", "Mast (HUL)"],
    breakdown=[("REC-1 Visibility", "Fluorescent parts/tape, flag"),
               ("REC-2 Retrieval", "Hoop, recovery kit"),
               ("REC-3 Identification", "Labels, tracker pocket"),
               ("REC-4 Beacon", "WS2812 ring at the mast head")],
    constraints=["Passive measures must not depend on power (SRS 5.14 "
                 "intent)", "Child-safe finish (CHD-002)"],
    budget=[("Mass allocation", "≤ 45 g (estimate 40 g)"),
            ("Cost allocation", "£3 (LED ring, tape); kit from owned "
             "fishing gear"), ("Power", "Beacon ≤ 0.3 W average")],
    special=None,
    open_items=[("TBC-08", "Beacon data level (IF-09)"),
                ("REC-OI-1", "Owner to supply the contact number for the "
                 "labels")],
)
group(r, "Visibility and identification")
D(r, "REC-D01", "At least 50% of the visible top area shall be fluorescent "
  "orange or yellow, measured on a top-down photo.", "M", "T", "BENCH",
  ["REC-002"])
D(r, "REC-D02", "A fluorescent ripstop flag ≥ 120 × 80 mm shall fly with "
  "its top ≥ 320 mm above the waterline, below the GNSS.", "M", "I", "BENCH",
  ["REC-003", "IF-19"])
D(r, "REC-D03", "The beacon ring shall be visible at 100 m in overcast "
  "daylight and show the helm's state patterns (IF-09).", "S", "T", "LAKE",
  ["REC-004", "IF-09"])
D(r, "REC-D04", "Both hulls shall carry a waterproof 'IF FOUND' label with "
  "the owner's phone number.", "M", "I", "BENCH", ["REC-006"])
D(r, "REC-D05", "An optional sealed pocket in a mid segment shall take a "
  "≤ 35 mm tracker tag.", "C", "I", "BENCH", ["REC-007"])
group(r, "Retrieval")
D(r, "REC-D06", "A printed hoop (≥ 60 mm internal) integrated with the mast "
  "collar shall take a 50 N pull. The boat tows by it without "
  "capsizing.", "M", "T", "POOL", ["REC-005"])
D(r, "REC-D07", "The bank kit shall contain a ≥ 3 m telescopic pole with "
  "net and a casting rod with a weighted float line, packed with the "
  "boat.", "M", "I", "LAKE", ["OPS-008"])
D(r, "REC-D08", "The flag staff shall be capped, and hoop and flag edges "
  "rounded (≥ 0.6 mm).", "M", "I", "BENCH", ["CHD-002"])

# ======================================================================
# SIM  Simulation & test
# ======================================================================
s = subsystem(
    "SIM", title="Simulation & test",
    issue="Issue E (for review)",
    history=[["B", "28 September 2026", "Hardware-in-the-loop rigs L1-L3 "
              "added (SIM-D13 to D24). Test catalogue rebuilt with IDs and "
              "extended with FMEA-derived scenarios (BOATY-FMEA-001).",
              "Claude, owner request"],
             ["C", "28 September 2026", "L1-10 (adult PIN) and B-07 (cell "
              "acceptance) added for FMEA FM-48 and A-20.", "Claude, "
              "owner decision (CR-03)"],
             ["D", "29 September 2026", "Simulator built (slices 1-2): our "
              "own boat model through SITL's JSON interface (ADD DD-20), "
              "B1 router topology, real services on a simulated Pi Zero. "
              "SIM-D01/02/07 updated; SIM-D25 to D28 added; test results "
              "shown against the catalogue; SC-02 at 3 s (CR-05).",
              "Claude, owner decisions"],
             ["E", "29 September 2026", "Slice 3: Mission Control in the "
              "loop. SC-41 to SC-43 added; SIM-D29 and D30 added; SC-31 "
              "and SC-33 evidence sources named. SC-33 run against the live "
              "Claude API (39 cases).", "Claude, owner request"]],
    purpose="Let the whole system be exercised, failed on purpose and "
            "rehearsed at home, first against a simulated boat and then "
            "with more and more real hardware in the loop, with the same "
            "software throughout.",
    inside=["ArduPilot Rover 4.7.1 SITL", "Boat and battery model "
            "(JSON physics)", "Radio-link relay and B1 router stand-in",
            "Simulated camera for B2", "Scenario runner and test suites "
            "(software/tests)", "CI configuration", "Rig L1: real computers + SITL",
            "Rig L2: iron bird (real helm and power train)",
            "Rig L3: water-tank thrust and weed rig"],
    outside=["The software under test (MCN, MCP services)", "Pool and lake "
             "trials (per-subsystem and system test procedures)"],
    breakdown=[("SIM-1 Simulator", "SITL + boat model (software/boaty/sim) "
                "+ launcher; services run from software/boaty/mcp"),
               ("SIM-2 Test suites", "Unit, contract, scenario, FMEA-"
                "derived, LLM evaluation"),
               ("SIM-3 CI", "GitHub Actions workflows"),
               ("SIM-4 Rig L1", "Real Pi 5 panel, real Pi Zero + camera, "
                "real Wi-Fi; SITL on a laptop, reaching the Pi Zero UART "
                "through a USB-serial adapter"),
               ("SIM-5 Rig L2 'iron bird'", "Real FC, firmware and "
                "parameters, power board with key, ESCs and motors, GNSS, "
                "beacon, on a board; driven by the real Mission Control"),
               ("SIM-6 Rig L3 tank", "One pod in a water tub on a load cell, "
                "with current logging and real pond weed")],
    constraints=["Same parameter file as the real helm, plus sitl.parm",
                 "All timings in simulated time; runs faster than real "
                 "time (5x used)", "Runs on a laptop or the Pi 5",
                 "Rig L2 is run with props off, or in water with the tank "
                 "covered. Removing the magnetic key is the emergency stop."],
    budget=[("Cost", "£0 software (open source). Rig equipment, outside "
             "the Mk1 BOM: USB-serial adapter £3, load cell + HX711 £6, "
             "tub; bench power supply assumed owned."),
            ("LLM evaluation", "API credit, capped per run"),
            ("Mass / power", "n/a")],
    special="sim",
    open_items=[("Model", "Boat-model thrust, drag and inertia are estimates "
                 "until the thrust stand and pool replace them (KCL "
                 "section 8)"),
                ("Slice 3", "Mission Control against the simulator; C7 "
                 "impostor-GCS detection (SC-37)"),
                ("SIM-OI-1", "Rig L2 needs the first parts order (FC, ESCs, "
                 "motors, power parts). Rig L1 needs only a Pi Zero 2W and "
                 "camera.")],
)
group(s, "Simulator")
D(s, "SIM-D01", "SITL shall run the same ArduPilot version as the helm "
  "(Rover 4.7.1) and the controlled parameter file, flying our own "
  "skid-steer boat model through the JSON interface (ADD DD-20).", "M",
  "D", "SIM", ["SWE-004", "V-12", "DD-20"])
D(s, "SIM-D02", "The real B2/B3 code shall serve IF-03 in simulation, with "
  "a simulated camera rendering images at the boat's true position.", "M",
  "T", "SIM", ["SWE-004", "IF-21"])
D(s, "SIM-D03", "One command shall start the simulator on a laptop or the "
  "Pi 5 at a given site's home.", "M", "D", "SIM", ["SWE-004"])
D(s, "SIM-D04", "Mission Control shall run against the simulator with "
  "configuration changes only.", "M", "D", "SIM", ["SWE-004", "SWE-003"])
D(s, "SIM-D05", "A rehearsal mode shall run the physical panel against "
  "the simulator for crew practice.", "S", "D", "SIM", ["OPS-012"])
group(s, "Tests")
D(s, "SIM-D06", "Each FS-001 to FS-013 requirement shall have an automated "
  "scenario with explicit pass criteria (SC-01 to SC-13, section 6). "
  "FS-008 is proven on rig L2.", "M", "T", "SIM", ["SWE-005"])
D(s, "SIM-D07", "Fault injection shall use SITL simulation parameters "
  "(SIM_GPS1_ENABLE, SIM_MAG1_ORIENT), boat-model faults (motor loss or "
  "reversal, weed drag, wind, battery drain, key out) and radio-link "
  "impairment (cut, loss, latency), mapped per scenario in the test code.",
  "M", "T", "SIM", ["SWE-005", "IF-21"])
D(s, "SIM-D08", "Contract tests for IF-03 and IF-14 shall run against both "
  "the simulator and real hardware.", "M", "T", "SIM", ["IF-14", "IF-03"])
D(s, "SIM-D09", "The validator's adversarial suite (≥ 50 cases) and a "
  "property-based comparison against an independent geometry "
  "implementation shall run in CI (SC-31).", "M", "T", "SIM", ["VAL-006"])
D(s, "SIM-D10", "The LLM evaluation set (≥ 30 instructions, including "
  "adversarial child phrasing) shall run on demand with a per-run cost "
  "cap (SC-33).", "S", "T", "SIM", ["NLI-003", "NLI-006"])
group(s, "CI and reproducibility")
D(s, "SIM-D11", "Every push shall run ruff, mypy and unit tests. SITL "
  "scenarios shall run on pull requests and nightly.", "S", "I", "SIM",
  ["SWE-007"])
D(s, "SIM-D12", "Tool and dependency versions (SITL commit, Python lock "
  "file) shall be pinned in the repository.", "M", "I", "SIM",
  ["SWE-006"])
group(s, "Built in slices 1-2 (Issue D)")
D(s, "SIM-D25", "The boat model shall take its parameters from the Key "
  "Component List (mass, thrust ahead/astern, drag, windage, pack capacity "
  "and resistance) and be re-fitted to thrust-stand and pool data when "
  "they exist.", "M", "A", "SIM", ["SWE-004", "DD-20"])
D(s, "SIM-D26", "The simulated boat shall have the boat's MAVLink topology: "
  "SITL's port joined by a B1 router to the radio relay and to the "
  "services, so a mission-computer failure takes the bank link with it.",
  "M", "D", "SIM", ["SWE-004", "IF-04", "IF-21"])
D(s, "SIM-D27", "Every timing criterion shall be measured in simulated time "
  "from truth (commanded outputs, thrust, position), not from telemetry "
  "round trips.", "M", "I", "SIM", ["SWE-005"])
D(s, "SIM-D28", "Each run shall write per-scenario evidence (measured "
  "values against the criterion) and a report (software/results). Known "
  "native gaps are marked as such, never hidden.", "M", "I", "SIM",
  ["SWE-005", "SAF-007"])
D(s, "SIM-D29", "Mission Control shall run in the simulator as it runs on "
  "the Pi 5 (same code, simulated time), with Claude's replies from a "
  "stand-in client that produces the API's response format. The live API "
  "is exercised separately by the recorded evaluation set (SC-33).", "M",
  "I", "SIM", ["SWE-004", "IF-11"])
D(s, "SIM-D30", "Evidence that needs no simulator (validator coverage, "
  "property-based runs) shall be written to software/results/"
  "unit_evidence.json and reported with the SITL results.", "S", "I",
  "SIM", ["VAL-006", "SWE-005"])
group(s, "Hardware-in-the-loop rigs (Issue B)")
D(s, "SIM-D13", "Rig L1 shall connect SITL to the real Pi Zero 2W through "
  "a 3.3 V USB-serial adapter at 115200 baud on the Pi's UART, so the "
  "production router configuration is used unchanged. The real Pi 5 panel "
  "and Wi-Fi are used.", "M", "D", "BENCH", ["SWE-004", "IF-04", "IF-01"])
D(s, "SIM-D14", "Rig L1 shall timestamp STOP from button edge to the SITL "
  "mode change with ≤ 10 ms resolution, over ≥ 100 trials (L1-03).", "M",
  "T", "BENCH", ["FS-009", "COM-003"])
D(s, "SIM-D15", "Rig L1 shall switch the Pi Zero's 5 V supply under script "
  "control for power-cut endurance testing (L1-08).", "S", "T", "BENCH",
  ["IF-08"])
D(s, "SIM-D16", "Rig L1 shall allow the sealed box with the Pi Zero to be "
  "heat-soaked at 30 °C (heat lamp or sun) while running a mission "
  "(L1-09).", "S", "T", "BENCH", ["PWR-010"])
D(s, "SIM-D17", "Rig L2 shall mount the real FC (flashed firmware and "
  "controlled parameters), power board with fuse and magnetic key, ESCs, "
  "motors, GNSS with sky view, and beacon, driven by the real Mission "
  "Control over the real link.", "M", "D", "BENCH",
  ["SAF-001", "IF-05", "IF-06", "IF-07", "IF-09"])
D(s, "SIM-D18", "Rig L2 shall support physical fault injection: GNSS "
  "unplug and data-line cut, AP off, bench-supply voltage ramp, ESC "
  "signal cut, key removal, FC power-cycle, and thrust steps.", "M", "T",
  "BENCH", ["FS-001", "FS-002", "FS-004", "FS-008", "MOD-003",
            "PWR-005"])
D(s, "SIM-D19", "Rig L2 shall record motor current, 5 V rails and ESC "
  "signals (logic analyser or scope), and detect motor stop within 50 ms "
  "(ESC telemetry or optical).", "M", "T", "BENCH", ["FS-008", "FS-009",
                                                     "PWR-005"])
D(s, "SIM-D20", "Rig L2 shall run with props removed in air, or with pods "
  "submerged in a covered tank. Removing the key is the emergency stop, "
  "and the adult-only rules apply.", "M", "I", "BENCH", ["OPS-007",
                                                          "CHD-003"])
D(s, "SIM-D21", "Rig L3 shall measure one pod's thrust (± 0.05 N) and "
  "current, forward and astern, at 0-100% in 10% steps (L3-01).", "M", "T",
  "BENCH", ["NAV-001", "ENV-002", "IF-06"])
D(s, "SIM-D22", "Rig L3 shall introduce real pond weed at the inlet and "
  "record whether the weed-shedding routine clears it (L3-02).", "S", "T",
  "BENCH", ["ENV-005", "FS-006"])
D(s, "SIM-D23", "Every rig test shall be recorded with date, software and "
  "firmware versions, parameter hash and results, and committed to the "
  "repository.", "M", "I", "BENCH", ["SWE-006"])
D(s, "SIM-D24", "Every FMEA failure mode with severity ≥ 8 shall be "
  "exercised by at least one SIM, rig or bench test in the catalogue. The "
  "build checks this.", "M", "A", "SIM", ["SAF-006", "FS-013"])

ORDER = ["HUL", "PRP", "PWR", "HLM", "MCP", "MCN", "REC", "SIM"]


# ---------------------------------------------------------------- tables
SOFTWARE_PARAMS = DOCS.parent / "software" / "params"


def load_param_baseline():
    """The controlled parameter files, as (group, name, value, note) rows.

    The SSS no longer keeps its own copy of the baseline: this table is
    generated from software/params, the same files the helm and the
    simulator load, so the two cannot drift apart."""
    rows = []
    for fname, default_group in (("boaty-mk1.parm", "Behaviour"),
                                 ("boaty-mk1-speedybee.parm", "Board")):
        group_name = default_group
        pending = None
        for raw in (SOFTWARE_PARAMS / fname).read_text().splitlines():
            line = raw.strip()
            if line.startswith("# ---"):
                group_name = line.strip("# -").split("(")[0].strip()
                pending = None
                continue
            if line.startswith("#") and raw[:1].isspace() and pending:
                pending[3] += " " + line.lstrip("# ").strip()
                continue
            if not line or line.startswith("#"):
                pending = None
                continue
            body, _, note = raw.partition("#")
            parts = body.split()
            if len(parts) == 2:
                name, value = parts
                pending = [group_name if fname.startswith("boaty-mk1.")
                           else "Board wiring", name, value, note.strip()]
                rows.append(pending)
    return rows


HLM_PARAMS = load_param_baseline()

RESULTS_JSON = DOCS.parent / "software" / "results" / "sitl_results.json"
UNIT_EVIDENCE = {"SC-30": "Pass (unit fuzz, 6,000 cases)",
                 "SC-33": "Not run: needs the API key (tools/nli_eval.py)"}
UNIT_JSON = RESULTS_JSON.with_name("unit_evidence.json")
NLI_JSON = RESULTS_JSON.with_name("nli_eval.json")


def load_sim_results() -> dict:
    """Catalogue ID -> result from the simulator's evidence file. A
    catalogue test may have several records (e.g. SC-04 helm-only and
    with the boat services); any pass counts, else the known gap shows."""
    import json
    import re
    out = dict(UNIT_EVIDENCE)
    if UNIT_JSON.exists():
        u = json.loads(UNIT_JSON.read_text())["items"]
        p = u.get("SC-31 property-based validator check")
        if p:
            out["SC-31"] = (f"Pass ({p['missions']} generated, "
                            f"{p['accepted']} accepted, closest "
                            f"{p['closest_accepted_route_to_a_boundary_m']:.3f}"
                            " m)")
    if NLI_JSON.exists():
        n = json.loads(NLI_JSON.read_text())["summary"]
        out["SC-33"] = (("Pass" if n["criteria_met"] else "FAIL") +
                        f" (live API: {n['passed']}/{n['cases']} cases, "
                        f"declines {n['must_decline_declined']}, p95 "
                        f"{n['p95_s']:.1f} s)")
    if not RESULTS_JSON.exists():
        return out
    by_id: dict = {}
    for r in json.loads(RESULTS_JSON.read_text())["records"]:
        rid = r.get("id") or ""
        m = re.match(r"(SC-\d+|V-\d+)", rid)
        by_id.setdefault(m.group(1) if m else rid, []).append(r["outcome"])
    for tid, outs in by_id.items():
        if "passed" in outs or "xpass" in outs:
            out[tid] = "Pass"
        elif "xfail" in outs:
            out[tid] = "Known gap"
        elif "failed" in outs:
            out[tid] = "FAIL"
    if "V-05" in out:
        out["SC-05"] = out["V-05"] + " (via V-05; B7 backs up at 10 s)"
    for rec_id, tid in (("IF-14-05", "SC-40"), ("MC-E2E", "SC-41"),
                        ("MCN-D59", "SC-42"), ("MCN-D60", "SC-43")):
        if rec_id in by_id:
            out[tid] = "Pass" if "passed" in by_id[rec_id] else "FAIL"
    if out.get("SC-09") == "Pass":
        out["SC-09"] = "Pass (panel emulation, 4 armed states)"
    return out


SIM_RESULTS = load_sim_results()

# Test catalogue (SSS-SIM Issue B). kind: SIM, L1, L2, L3.
# (id, kind, title, injection / method, pass criterion, refs)
TESTS = [
    ("SC-01", "SIM", "Battery drain to 35% then 15%", "Simulated battery "
     "drain", "RTL at 35%; alarm at 15%; reaches home", ["FS-001"]),
    ("SC-02", "SIM", "Link cut in STEERING", "Drop UDP 14550",
     "HOLD ≤ 3 s (CR-05); RTL at 10 s (B4)", ["FS-002"]),
    ("SC-03", "SIM", "Link cut in AUTO", "Drop UDP 14550", "Mission "
     "continues; RTL at 60 s (B4)", ["FS-003", "FM-31"]),
    ("SC-04", "SIM", "GNSS failure 5 s then restore", "SITL GPS failure",
     "Motors stop ≤ 3 s; RTL after 10 s healthy (B6)", ["FS-004", "FM-01",
                                                       "FM-06"]),
    ("SC-05", "SIM", "Heavy drag at throttle ≥ 50%", "SITL drag / wind",
     "HOLD ≤ 5 s plus event", ["FS-005", "FM-16"]),
    ("SC-06", "SIM", "Drag released after burst 2", "SITL + B5",
     "≤ 3 bursts; resumes mission", ["FS-006", "FM-27"]),
    ("SC-07", "SIM", "Kill all MCP services mid-mission", "Stop stub and "
     "B-services", "Mission completes; RTL; HOLD at home", ["FS-007",
                                                            "FM-26"]),
    ("SC-08", "SIM", "Helm signal loss to ESCs", "Covered by L2-10",
     "See L2-10", ["FS-008"]),
    ("SC-09", "SIM", "STOP in every state", "Panel emulation",
     "Motors stop ≤ 1 s", ["FS-009"]),
    ("SC-10", "SIM", "Moisture flagged", "Stub health = moisture",
     "RTL ≤ 2 s", ["FS-010", "FM-24"]),
    ("SC-11", "SIM", "GNSS loss during battery RTL", "Combined",
     "Motors-stopped (HOLD) wins", ["FS-011"]),
    ("SC-12", "SIM", "Log and announce audit", "Log inspection over SC-01 "
     "to SC-11", "Every event logged, announced ≤ 2 s", ["FS-012"]),
    ("SC-13", "SIM", "Single-fault sweep across mission phases", "Scripted "
     "matrix of SC-20 to SC-39 faults", "Never leaves the fence under "
     "power", ["FS-013"]),
    ("SC-20", "SIM", "GNSS glitch: 20-50 m jump for 2 s near the fence",
     "SITL GPS glitch", "No uncommanded exit; glitch rejected or HOLD",
     ["FM-02"]),
    ("SC-21", "SIM", "GNSS frozen: stale position while moving", "SITL GPS "
     "freeze", "Detected; motors stop ≤ 3 s", ["FM-03"]),
    ("SC-22", "SIM", "Compass offset 30° and 90°", "SITL compass offset",
     "Yaw fallback or HOLD; stays inside the fence", ["FM-04", "FM-05"]),
    ("SC-23", "SIM", "Helm restart mid-mission", "Restart SITL process",
     "Motors stop; boots disarmed; alarm at Mission Control", ["FM-07"]),
    ("SC-24", "SIM", "Parameter differs from baseline", "Change one "
     "failsafe parameter", "Arming blocked; difference shown", ["FM-09"]),
    ("SC-25", "SIM", "Fence missing or disabled", "Skip the fence upload",
     "Arming refused", ["FM-10"]),
    ("SC-26", "SIM", "Site file lat/lon swapped; wrong site", "Corrupt the "
     "site file", "Linter and pre-arm both refuse", ["FM-11"]),
    ("SC-27", "SIM", "Breach on the far side of the island", "Push the "
     "boat out with wind", "RTL path avoids the exclusion", ["FM-13"]),
    ("SC-28", "SIM", "Persistent breach (wind pushing out)", "Strong "
     "offshore wind", "Motors stop by 30 s / 10 m", ["FM-14"]),
    ("SC-29", "SIM", "Single motor failure", "Zero one output", "Divergence "
     "watchdog → HOLD ≤ 20 s", ["FM-17"]),
    ("SC-30", "SIM", "Boat-service command fuzz", "Random forbidden "
     "commands", "All blocked by the filter", ["FM-27"]),
    ("SC-31", "SIM", "Validator adversarial + property-based", "Hypothesis "
     "vs independent geometry", "No accepted mission crosses a boundary",
     ["FM-34"]),
    ("SC-32", "SIM", "Read-back corruption", "Alter one item in transfer",
     "GO stays disabled", ["FM-35", "FM-47"]),
    ("SC-33", "SIM", "LLM evaluation with adversarial phrasing", "Recorded "
     "instruction set", "Schema-valid; must-decline declined", ["FM-36",
                                                                "FM-37"]),
    ("SC-34", "SIM", "Link degradation: 30/60/90% loss, 2 s latency",
     "Network impairment", "FS-002/003 behaviour holds; STOP latency "
     "logged", ["FM-39", "FM-40"]),
    ("SC-35", "SIM", "Home sanity", "Arm with GNSS unsettled / far from "
     "site home", "Refused or warned before GO", ["FM-46"]),
    ("SC-36", "SIM", "Interrupted upload", "Drop the link mid-transfer",
     "No partial mission accepted", ["FM-47"]),
    ("SC-37", "SIM", "Foreign GCS heartbeat", "Second system-255 source",
     "C7 refuses to operate; alarm", ["FM-41"]),
    ("SC-38", "SIM", "First-motion heading check", "Compass reversed",
     "HOLD ≤ 10 s after start", ["FM-05", "FM-18"]),
    ("SC-39", "SIM", "Capacity overstated by 30%", "Wrong capacity "
     "parameter", "Voltage backstop triggers RTL in time", ["FM-15"]),
    ("SC-40", "SIM", "Arm lands in HOLD", "Arm with default RC input "
     "present", "Armed in HOLD, motors off", ["FM-53"]),
    ("SC-41", "SIM", "Instruction to captain's log", "Typed instruction, "
     "stand-in Claude reply, full Mission Control", "Validated, read back "
     "equal, flown inside the fence, home, auto-disarm at 60 s, photos "
     "sha256-verified before ack", ["SWE-004", "VAL-010", "MCN-D47"]),
    ("SC-42", "SIM", "Persistent breach with B7 absent", "Gale; boat "
     "services not running", "C1 stops motors before 30 s or 10 m outside",
     ["FM-14", "MCN-D59"]),
    ("SC-43", "SIM", "Boat stops itself", "Dead motor mid-mission",
     "Reason spoken ≤ 2 s after HOLD; resume needs the PIN", ["MCN-D60"]),
    ("L1-01", "L1", "End-to-end mission, real computers", "Voice → "
     "captain's log over real Wi-Fi and UART", "Completes; all artefacts "
     "logged", ["SWE-004"]),
    ("L1-02", "L1", "Panel self-test and state × button table", "Real "
     "buttons", "Matches ICD IF-12", ["FM-32", "FM-33"]),
    ("L1-03", "L1", "STOP latency, 100 trials", "Button edge → SITL mode",
     "P99 ≤ 0.5 s", ["FM-40", "FS-009"]),
    ("L1-04", "L1", "Photo sync, 200 photos", "Real Wi-Fi at 10 m",
     "≤ 5 min; hashes verified", ["CAM-007"]),
    ("L1-05", "L1", "UART load", "Maximum telemetry + services", "GCS "
     "heartbeat jitter < 0.5 s", ["FM-28"]),
    ("L1-06", "L1", "Mission Control power pulled mid-mission", "Unplug "
     "the Pi 5", "B4 RTL at 60 s", ["FM-31"]),
    ("L1-07", "L1", "Range walk on land", "Walk the Pi Zero away", "RSSI "
     "vs distance; flap behaviour as SC-34", ["FM-39"]),
    ("L1-08", "L1", "Pi Zero power-cut ×50", "Switched 5 V", "No filesystem "
     "damage", ["FM-26"]),
    ("L1-09", "L1", "Sealed-box heat soak 30 °C", "Heat lamp", "No "
     "throttling for 60 min", ["PWR-010"]),
    ("L2-01", "L2", "Motor direction and channel map", "Props off",
     "Left/right and sense correct", ["FM-18"]),
    ("L2-02", "L2", "Arming gated on the key", "Key in/out", "Refused with "
     "key out; rail < 0.5 V", ["FM-22", "MOD-003"]),
    ("L2-03", "L2", "GNSS unplugged", "Pull connector", "EKF failsafe HOLD",
     ["FM-01"]),
    ("L2-04", "L2", "GNSS data line cut, power on", "Cut TX", "Detected ≤ "
     "3 s", ["FM-03"]),
    ("L2-05", "L2", "Compass vs motor current", "Motor-interference "
     "calibration", "Interference ≤ 30%", ["FM-04"]),
    ("L2-06", "L2", "Heading vs reference", "Known bearing", "Within 10°",
     ["FM-05"]),
    ("L2-07", "L2", "FC power-cycle with motors running", "Interrupt FC "
     "supply", "Motors stop; boots disarmed", ["FM-07"]),
    ("L2-08", "L2", "Thrust-step brownout", "Full reverse → forward",
     "5 V rails in regulation", ["FM-08", "PWR-005"]),
    ("L2-09", "L2", "Supply voltage ramp", "Bench supply", "Battery "
     "failsafe at thresholds", ["FM-15"]),
    ("L2-10", "L2", "ESC signal cut and restore", "Cut the signal lead",
     "Stop ≤ 1 s; restart only from neutral", ["FM-19", "FM-20", "FS-008"]),
    ("L2-11", "L2", "STOP to motors stopped", "Panel STOP", "≤ 1 s",
     ["FS-009", "FM-40"]),
    ("L2-12", "L2", "Beacon patterns", "Cycle states", "Each state "
     "distinguishable", ["REC-004"]),
    ("L2-13", "L2", "Key-switch short detection", "Bridge the MOSFET",
     "Checklist rail test flags it", ["FM-22"]),
    ("L3-01", "L3", "Thrust and current curves", "Load cell, 0-100%",
     "≥ 2 N forward per pod; current ≤ 8 A", ["NAV-001", "IF-06"]),
    ("L3-02", "L3", "Weed fouling trials", "Real pond weed", "Cleared in "
     "≥ 2 of 3", ["FM-16", "ENV-005"]),
    ("L3-03", "L3", "Cruise power estimate", "Thrust vs drag model",
     "≤ 10 W at 1.0 m/s", ["PWR-009"]),
    ("B-01", "BENCH", "Prop guard probe", "8 mm probe", "No blade contact",
     ["FM-21", "FM-45"]),
    ("B-02", "BENCH", "BMS protection", "Over-current and short on the "
     "pack", "BMS trips; fuse intact", ["FM-23"]),
    ("B-03", "BENCH", "Box dunk", "30 min at 0.3 m", "No ingress",
     ["FM-24"]),
    ("B-04", "BENCH", "Harness pull and connector", "Tug test", "No "
     "disconnect", ["FM-25"]),
    ("B-05", "BENCH", "Camera failure", "Unplug camera", "Health reports "
     "fault; mission unaffected", ["FM-29"]),
    ("L1-10", "L1", "Adult PIN: unlock, timeout, lockout", "Web UI",
     "10 min unlock; 5 failures → 5 min lockout; motors still need the "
     "key", ["FM-48", "MC-008"]),
    ("B-07", "BENCH", "Salvaged cell acceptance", "PWR-D20 tests",
     "Only compliant cells accepted and recorded", ["FM-23"]),
    ("B-06", "BENCH", "Clock without GNSS", "Boot offline", "Timestamps "
     "flagged until GNSS time", ["FM-30"]),
    ("R-01", "REHEARSAL", "Operator contingency rehearsal", "SIM rehearsal "
     "mode", "All section 3.5 scenarios rehearsed", ["FM-42", "FM-43",
                                                     "FM-44", "FM-12"]),
    ("P-01", "POOL", "Internet absent", "Phone disconnected", "Templates "
     "offered", ["FM-38"]),
]


# ---------------------------------------------------------------- checks
def all_derived(ss):
    for _, reqs in ss["groups"]:
        yield from reqs


def check():
    srs_ids = {r["id"] for r in SRS.all_reqs()}
    if_ids = {i[0] for i in A.INTERFACES}
    v_ids = {v[0] for v in A.VERIFY_EARLY} | {"V-14", "V-15", "V-16",
                                             "V-17"}
    dd_ids = {d[0] for d in A.DECISIONS}
    import fmea_data as FM  # noqa: E402  (imports this module)
    dd_ids |= {r[0] for r in FM.ROWS} | {a[0] for a in FM.ACTIONS}
    alloc = A.allocation()
    seen = set()
    for code in ORDER:
        ss = SUBSYSTEMS[code]
        traced = set()
        for d in all_derived(ss):
            assert d["id"] not in seen, d["id"]
            seen.add(d["id"])
            assert d["id"].startswith(code + "-D"), d["id"]
            assert d["pri"] in "MSC" and d["stage"] in (
                "SIM", "BENCH", "POOL", "LAKE"), d["id"]
            for t in d["trace"]:
                assert t in srs_ids | if_ids | v_ids | dd_ids, (d["id"], t)
            traced |= set(d["trace"])
        prim = {k for k, (p, _) in alloc.items() if p == code}
        missing = prim - traced
        assert not missing, (code, sorted(missing))
    ids = [t[0] for t in TESTS]
    assert len(ids) == len(set(ids)), "duplicate test ids"
    return len(seen)


def new_verify_items():
    return [("V-14", "Native mechanism to stop motors on persistent fence "
             "breach (FEN-006).", "SITL", "FEN-006"),
            ("V-15", "Reduced speed during RTL on critical battery "
             "(FS-001).", "SITL", "FS-001"),
            ("V-16", "GNSS-velocity yaw fallback when the compass "
             "disagrees (NAV-008).", "SITL", "NAV-008"),
            ("V-17", "Whether the helm refuses fence changes while armed "
             "(FEN-007).", "SITL", "FEN-007")]


if __name__ == "__main__":
    print(check(), "derived requirements; all allocations covered")
