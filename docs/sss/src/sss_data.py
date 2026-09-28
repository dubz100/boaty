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
            ("Cost allocation", "£22 (motors £12, ESCs £10)"),
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
D(p, "PRP-D06", "The ESCs shall accept commands per IF-05 (DShot300, 3D "
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
D(p, "PRP-D15", "Motors are consumables: rinse and dry after each session. "
  "Expected life ≥ 10 h submerged before replacement.", "S", "A", "LAKE",
  ["NAV-001"])

# ======================================================================
# PWR  Power
# ======================================================================
w = subsystem(
    "PWR", title="Power",
    purpose="Store and distribute energy safely. Give motor power only when "
            "an adult has inserted the magnetic key. Measure what's used.",
    inside=["3S Li-ion 18650 pack with BMS", "Main fuse and main switch",
            "Magnetic arming key, reed switch and MOSFET motor-rail switch",
            "Power module (V/I sense)", "5 V buck for the mission computer",
            "Harness and connectors"],
    outside=["Battery charger (owned; off-boat)", "Helm battery monitoring "
             "configuration (HLM)"],
    breakdown=[("PWR-1 Battery pack", "3 × 18650 ≥ 3000 mAh, 3S BMS, "
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
            ("Cost allocation", "£31 (cells + BMS £15, fuse/box share £2, "
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
D(w, "PWR-D01", "The battery shall be 3S1P Li-ion 18650. Cells ≥ 3000 mAh "
  "and ≥ 10 A continuous; 30-36 Wh nominal.", "M", "I", "BENCH",
  ["PWR-001"])
D(w, "PWR-D02", "A 3S BMS shall provide over-discharge (2.5-2.8 V/cell), "
  "over-current (trip ≤ 25 A), short-circuit and balance protection.", "M",
  "T", "BENCH", ["PWR-002"])
D(w, "PWR-D03", "The pack shall be in a rigid sleeve with XT60 and a balance "
  "lead, removable from the box by an adult in < 30 s without tools.", "M",
  "D", "BENCH", ["PWR-007"])
D(w, "PWR-D04", "The boat shall have no charging port. Charging is by "
  "external balance charger only.", "M", "I", "BENCH", ["PWR-007"])
group(w, "Protection and switching")
D(w, "PWR-D05", "A 20 A blade fuse shall sit ≤ 50 mm from the battery "
  "positive.", "M", "I", "BENCH", ["PWR-003", "IF-06"])
D(w, "PWR-D06", "The main switch shall be IP67, outside the box, and "
  "either rated ≥ 20 A or control a solid-state switch rated ≥ 30 A.", "M",
  "I", "BENCH", ["PWR-004"])
D(w, "PWR-D07", "The motor rail shall be switched by the magnetic key per "
  "IF-06: reed switch + MOSFET, off when the key is absent.", "M", "T",
  "BENCH", ["MOD-003", "IF-06"])
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
    purpose="Navigate, enforce the fence and run every native failsafe on "
            "an independent RTOS processor, whatever else has failed.",
    inside=["Flight controller hardware (F405-class)", "ArduPilot Rover "
            "firmware (third party) and the controlled parameter set",
            "GNSS + compass module and mast cabling", "Fence and mission "
            "storage", "Dataflash / SD logging"],
    outside=["Everything that sends commands (MCN via IF-02, MCP via IF-04)",
             "Motor drives (PRP)", "Power sources (PWR)"],
    breakdown=[("HLM-1 Flight controller", "F405-class, ChibiOS; IMU, baro, "
                "UARTs, outputs, ADCs"),
               ("HLM-2 Firmware", "ArduPilot Rover, pinned version"),
               ("HLM-3 Parameter set", "params/boaty-mk1.parm (controlled)"),
               ("HLM-4 GNSS/compass", "u-blox M10 + magnetometer on the "
                "mast")],
    constraints=["ADD DD-02: F405-class, subject to V-01", "ADD DD-13: no "
                 "Lua; Python on the MCP covers Lua-type behaviours",
                 "No project-written code on the FC (SAF-001)"],
    budget=[("Mass allocation", "≤ 40 g (estimate 32 g)"),
            ("Cost allocation", "£39 (FC £25, GNSS £14)"),
            ("Power", "≈ 0.8 W including GNSS")],
    special="hlm",
    open_items=[("V-01", "Firmware feature check for the chosen board, "
                 "incl. path planning around fences"),
                ("V-02 … V-06", "Mode, failsafe and identity behaviours in "
                 "SITL"),
                ("V-14", "Native mechanism for FEN-006 (persistent breach → "
                 "motors stop)"),
                ("V-15", "Reduced RTL speed on critical battery (FS-001)"),
                ("V-16", "GNSS-velocity yaw fallback behaviour (NAV-008)"),
                ("V-17", "Whether the helm itself refuses fence changes "
                 "while armed"),
                ("HLM-OI-1 / CR-02", "PRE-008 asks for ≥ 1 GB free on the "
                 "helm. Many F405 boards log to 16 MB dataflash. Either "
                 "choose a board with microSD, or relax PRE-008 for the helm "
                 "(owner decision)")],
)
group(m, "Hardware and firmware")
D(m, "HLM-D01", "The helm shall run a pinned ArduPilot Rover stable release "
  "(≥ 4.5) built for the chosen board. Version and hash are recorded in the "
  "repository.", "M", "I", "BENCH", ["SAF-001", "SWE-006"])
D(m, "HLM-D02", "The flight controller shall provide: ≥ 2 free UARTs (GNSS, "
  "companion), ≥ 3 DShot-capable outputs, ≥ 2 analogue battery inputs, I2C, "
  "IMU and baro, and log storage for ≥ 2 h at the configured rate "
  "(microSD preferred; see HLM-OI-1).", "M", "I", "BENCH",
  ["SAF-001", "PRE-008", "V-01"])
D(m, "HLM-D03", "No project-written code (including Lua) shall run on the "
  "flight controller. It runs ChibiOS only.", "M", "I", "BENCH",
  ["SAF-001", "DD-13"])
D(m, "HLM-D04", "On power-up the helm shall be disarmed with motor outputs "
  "at neutral. Auto-arming shall be disabled.", "M", "T", "BENCH",
  ["MOD-002"])
group(m, "Modes")
D(m, "HLM-D05", "Only STEERING, HOLD, LOITER, AUTO, RTL and GUIDED "
  "(weed-shedding only) shall be used. No RC mode switch is configured.",
  "M", "I", "SIM", ["MOD-001", "DD-12"])
D(m, "HLM-D06", "At mission end the helm shall RTL and then hold at home. "
  "The mission-done behaviour is set to hold as a backstop.", "M", "S", "SIM",
  ["MOD-005", "V-04"])
D(m, "HLM-D07", "Auto-disarm after 60 s at home is performed by Mission "
  "Control (MCN-D12). The helm shall accept it.", "C", "S", "SIM",
  ["MOD-008"])
group(m, "Pre-arm checks")
D(m, "HLM-D08", "All ArduPilot arming checks shall be enabled, and failures "
  "reported as STATUSTEXT (MCN translates them).", "M", "S", "SIM",
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
D(m, "HLM-D20", "The heading estimate shall fall back to GNSS-velocity yaw "
  "when the compass disagrees above 0.3 m/s.", "S", "S", "SIM",
  ["NAV-008", "V-16"])
group(m, "Fence")
D(m, "HLM-D21", "The helm shall hold one inclusion polygon (≤ 70 vertices) "
  "and ≤ 10 exclusion polygons or circles, plus a 100 m circle backstop "
  "about home at Milton.", "M", "S", "SIM", ["FEN-001", "OPS-006"])
D(m, "HLM-D22", "The fence shall be enforced in every armed mode used.",
  "M", "S", "SIM", ["FEN-004", "V-02"])
D(m, "HLM-D23", "A breach shall trigger RTL within 1 s.", "M", "S", "SIM",
  ["FEN-005"])
D(m, "HLM-D24", "Persistent breach (> 30 s or > 10 m outside) shall stop "
  "the motors. Native mechanism to be confirmed (V-14). Interim: Mission "
  "Control and the MCP both command HOLD.", "M", "S", "SIM",
  ["FEN-006", "V-14"])
D(m, "HLM-D25", "Fence changes while armed shall be refused by every "
  "sender (IF-14, IF-04 filter) and by the helm if supported (V-17).", "M",
  "S", "SIM", ["FEN-007", "V-17"])
group(m, "Failsafes")
D(m, "HLM-D26", "Battery failsafe: RTL at 35% remaining; at 15%, "
  "continue RTL, alarm and reduce speed (V-15).", "M", "S", "SIM",
  ["FS-001", "V-15"])
D(m, "HLM-D27", "GCS failsafe on system-255 heartbeats: 2 s timeout, action "
  "HOLD, continue in AUTO. The later RTL steps are done by MCP B4 "
  "(MCP-D12).", "M", "S", "SIM", ["FS-002", "FS-003", "V-03", "V-06"])
D(m, "HLM-D28", "EKF/position failsafe → HOLD (motors stop). Recovery RTL "
  "is done by MCP B6 (MCP-D15).", "M", "S", "SIM", ["FS-004"])
D(m, "HLM-D29", "Crash/stuck check → HOLD, raising an event the MCP can "
  "act on.", "M", "S", "POOL", ["FS-005", "V-05"])
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

# ======================================================================
# MCP  Mission computer
# ======================================================================
c = subsystem(
    "MCP", title="Mission computer",
    purpose="Take and geotag photos, relay MAVLink to the bank, and run the "
            "small boat-side watchdogs, without ever being needed for "
            "safety.",
    inside=["Raspberry Pi Zero 2W, microSD, heatsink", "5 MP camera",
            "Moisture sensor", "OS image and services B1-B6"],
    outside=["Its 5 V supply (PWR)", "Camera hood and mount (HUL)",
             "Helm behaviour (HLM)"],
    breakdown=[("MCP-1 Computer", "Pi Zero 2W, 32 GB A1/U3 microSD, "
                "heatsink"), ("MCP-2 Camera", "OV5647-class 5 MP, ≤ 62° "
                              "HFOV"),
               ("MCP-3 Sensors", "Moisture traces at the box low point"),
               ("MCP-4 Software", "B1 router, B2 camera, B3 photo server, "
                "B4 link watchdog, B5 weed-shedding, B6 health")],
    constraints=["ADD DD-03 / T4: Pi Zero 2W (Python)", "ADD section 4.3 "
                 "rule: may request only safer states; B5 bounded GUIDED",
                 "SWE-001: Python services"],
    budget=[("Mass allocation", "≤ 35 g (estimate 30 g)"),
            ("Cost allocation", "£27 (Pi £15, camera £8, SD £4)"),
            ("Power", "≤ 2.0 W average, ≤ 3.0 W peak")],
    special="mcp",
    open_items=[("V-10", "Thermal in the sealed box"),
                ("V-11", "Helm stops if B5 dies mid-burst")],
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
D(c, "MCP-D07", "Services B1-B6 shall be systemd units that restart "
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
D(c, "MCP-D15", "B6 (health): moisture → RTL within 2 s plus STATUSTEXT. "
  "After a position-loss HOLD, RTL once the EKF has been healthy for "
  "10 s.", "M", "S", "SIM", ["FS-010", "FS-004"])
D(c, "MCP-D16", "Photo sync throughput ≥ 11 Mbit/s with the boat ≤ 10 m "
  "from the bank (200 photos ≤ 5 min).", "S", "T", "POOL", ["CAM-007"])
D(c, "MCP-D17", "Optional live view: 320 × 240 MJPEG at 2 fps when "
  "enabled, paused during sync.", "C", "D", "POOL", ["CAM-008"])
group(c, "Weed-shedding and command filter (B5)")
D(c, "MCP-D18", "B5 shall act only on a helm stuck event. Up to 3 GUIDED "
  "astern bursts (≤ 0.5 m/s, ≤ 2 s, targets at 10 Hz), then resume the "
  "previous mode if ground speed > 0.3 m/s is regained, else HOLD + "
  "alarm.", "S", "S", "SIM", ["FS-006", "V-11"])
D(c, "MCP-D19", "All services shall send MAVLink only through a shared "
  "client that blocks forbidden messages (IF-04 list).", "M", "T", "SIM",
  ["SAF-003", "IF-04"])
group(c, "Future: on-board duck spotting")
D(c, "MCP-D20", "An upgrade may run an on-device bird detector at ≥ 2 fps "
  "that requests 'pause and look'.", "C", "T", "POOL", ["DET-003"])
D(c, "MCP-D21", "'Pause and look' shall only request LOITER (≤ 20 s) and "
  "then resume. It shall never steer towards the detection.", "M", "S",
  "SIM", ["DET-004"], "Applies only if MCP-D20 is implemented.")

# ======================================================================
# MCN  Mission Control
# ======================================================================
n = subsystem(
    "MCN", title="Mission Control",
    purpose="Be the only place people interact with Boaty: turn words into "
            "safe, approved missions, and show, say and record what the "
            "boat is doing.",
    inside=["Raspberry Pi 5, case and panel (4 buttons, key switch, LEDs)",
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
            ("Cost allocation", "£29 (buttons/key £9, mic/speaker £8, "
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
  "(≥ 30 mm, colour + icon, LEDs) and an adult key switch, per IF-12.", "M",
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
  "manual drive and the cloud toggle shall need the adult key switch "
  "(PIN fallback).", "M", "T", "SIM", ["MC-008"])
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
  "retry ≤ 2 times, then offer templates.", "M", "T", "SIM",
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
  "ENU metres, sampling legs every ≤ 1 m.", "M", "T", "SIM",
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
  "committed file. A mismatch blocks arming and shows the difference.", "S",
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
    purpose="Let the whole system be exercised, failed on purpose and "
            "rehearsed at home, with the same Mission Control software as "
            "on the bank.",
    inside=["ArduPilot SITL (Rover, boat frame)", "Camera stub (IF-03)",
            "Launch scripts", "Scenario runner and test suites", "CI "
            "configuration"],
    outside=["The software under test (MCN, MCP services)", "Hardware "
             "tests (bench rigs are per-subsystem)"],
    breakdown=[("SIM-1 Simulator", "SITL + camera stub + launcher"),
               ("SIM-2 Test suites", "Unit, contract, scenario, LLM "
                "evaluation"), ("SIM-3 CI", "GitHub Actions workflows")],
    constraints=["Same parameter file as the real helm, plus SIM_* "
                 "overrides", "Runs on a laptop or the Pi 5"],
    budget=[("Cost", "£0 (open-source tools); LLM evaluation runs cost "
             "API credit, so they're capped"), ("Mass / power", "n/a")],
    special="sim",
    open_items=[("TBC-03 / V-12", "SITL skid boat frame"),
                ("TBC-04", "Fault injection parameters per scenario")],
)
group(s, "Simulator")
D(s, "SIM-D01", "SITL shall run the same ArduPilot version as the helm, "
  "with a skid-steer boat frame and the controlled parameter file.", "M",
  "D", "SIM", ["SWE-004", "V-12"])
D(s, "SIM-D02", "The camera stub shall implement IF-03 exactly, serving "
  "test images geotagged from SITL.", "M", "T", "SIM", ["SWE-004", "IF-21"])
D(s, "SIM-D03", "One command shall start the simulator on a laptop or the "
  "Pi 5 at a given site's home.", "M", "D", "SIM", ["SWE-004"])
D(s, "SIM-D04", "Mission Control shall run against the simulator with "
  "configuration changes only.", "M", "D", "SIM", ["SWE-004", "SWE-003"])
D(s, "SIM-D05", "A rehearsal mode shall run the physical panel against "
  "the simulator for crew practice.", "S", "D", "SIM", ["OPS-012"])
group(s, "Tests")
D(s, "SIM-D06", "Each FS-001 to FS-013 requirement shall have an automated "
  "scenario with explicit pass criteria (section 6). FS-008 is bench-only "
  "and is marked as such.", "M", "T", "SIM", ["SWE-005"])
D(s, "SIM-D07", "Fault injection shall use SITL simulation parameters and "
  "network impairment, mapped per scenario.", "M", "T", "SIM",
  ["SWE-005", "IF-21"])
D(s, "SIM-D08", "Contract tests for IF-03 and IF-14 shall run against both "
  "the simulator and real hardware.", "M", "T", "SIM", ["IF-14", "IF-03"])
D(s, "SIM-D09", "The validator's adversarial suite (≥ 50 cases) shall run "
  "in CI.", "M", "T", "SIM", ["VAL-006"])
D(s, "SIM-D10", "The LLM evaluation set (≥ 30 instructions) shall run on "
  "demand with a per-run cost cap.", "S", "T", "SIM", ["NLI-003",
                                                        "NLI-006"])
group(s, "CI and reproducibility")
D(s, "SIM-D11", "Every push shall run ruff, mypy and unit tests. SITL "
  "scenarios shall run on pull requests and nightly.", "S", "I", "SIM",
  ["SWE-007"])
D(s, "SIM-D12", "Tool and dependency versions (SITL commit, Python lock "
  "file) shall be pinned in the repository.", "M", "I", "SIM",
  ["SWE-006"])

ORDER = ["HUL", "PRP", "PWR", "HLM", "MCP", "MCN", "REC", "SIM"]


# ---------------------------------------------------------------- tables
HLM_PARAMS = [
    ("Vehicle", "FRAME_CLASS", "Boat", "MOD-001", "V-01"),
    ("Motor outputs", "SERVO1_FUNCTION / SERVO2_FUNCTION",
     "ThrottleLeft (73) / ThrottleRight (74)", "NAV-001, IF-05", "Bench"),
    ("Output protocol", "MOT_PWM_TYPE", "DShot300", "IF-05", "TBC-05"),
    ("Throttle cap", "MOT_THR_MAX", "Tuned: full throttle ≤ 1.5 m/s",
     "NAV-003", "Pool"),
    ("Cruise", "CRUISE_SPEED / CRUISE_THROTTLE", "1.0 m/s / measured",
     "NAV-002", "Pool"),
    ("Waypoints", "WP_SPEED / WP_RADIUS", "1.0 m/s / 3 m", "NAV-004", "SITL"),
    ("RTL", "RTL_SPEED", "0 (= WP_SPEED)", "NAV-007", "SITL"),
    ("Loiter", "LOIT_RADIUS", "2 m", "NAV-006", "Lake"),
    ("Path planning", "OA_TYPE", "Dijkstra (fence-aware)", "NAV-007",
     "V-01"),
    ("Identity", "SYSID_THISMAV / SYSID_MYGCS", "1 / 255", "IF-02", "V-06"),
    ("Companion port", "SERIAL2_PROTOCOL / SERIAL2_BAUD", "2 (MAVLink 2) / "
     "115", "IF-04", "TBC-02"),
    ("Fence", "FENCE_ENABLE / FENCE_TYPE / FENCE_ACTION", "1 / polygon + "
     "circle / RTL", "FEN-001, FEN-005", "V-02"),
    ("Fence backstop", "FENCE_RADIUS / FENCE_MARGIN", "100 m / 3 m",
     "OPS-006", "SITL"),
    ("Battery", "BATT_MONITOR / BATT_CAPACITY", "Analogue V+I / measured "
     "(≈ 3000 mAh)", "PWR-006", "Bench"),
    ("Battery failsafe", "BATT_LOW_MAH / BATT_CRT_MAH", "35% / 15% of "
     "capacity", "FS-001", "SITL"),
    ("Battery actions", "BATT_FS_LOW_ACT / BATT_FS_CRT_ACT", "RTL / RTL",
     "FS-001", "V-15"),
    ("Arming capacity", "BATT_ARM_MAH", "80% of capacity", "PRE-003",
     "SITL"),
    ("Motor rail", "BATT2_MONITOR / BATT2_ARM_VOLT", "Analogue V / 9.0 V",
     "MOD-003, PRE-007", "V-13"),
    ("GCS failsafe", "FS_GCS_ENABLE / FS_TIMEOUT / FS_ACTION", "2 (continue "
     "in AUTO) / 2 s / Hold", "FS-002, FS-003", "V-03"),
    ("EKF failsafe", "FS_EKF_ACTION", "Hold", "FS-004", "SITL"),
    ("Stuck", "FS_CRASH_CHECK", "Hold", "FS-005", "V-05"),
    ("GNSS", "GPS_TYPE / GPS_HDOP_GOOD", "Auto / 150", "PRE-001", "Bench"),
    ("Arming", "ARMING_CHECKS", "All", "MOD-004", "SITL"),
    ("Heading", "COMPASS_ORIENT (+ EKF3 GSF yaw)", "Per module / default "
     "on", "NAV-008", "TBC-09, V-16"),
    ("Beacon", "NTF_LED_TYPES / SERVO3_FUNCTION", "NeoPixel / NeoPixel1",
     "REC-004, IF-09", "Bench"),
    ("Logging", "LOG_BACKEND_TYPE / LOG_BITMASK", "File / default + ≥ 5 Hz",
     "LOG-001", "Bench"),
    ("Mission end", "MIS_DONE_BEHAVE", "Hold (backstop)", "MOD-005", "V-04"),
]

SIM_SCENARIOS = [
    ("FS-001", "Battery drain to 35% then 15%", "Simulated battery "
     "capacity/drain", "RTL at 35%; alarm at 15%; reaches home"),
    ("FS-002", "Drop UDP 14550 in STEERING", "Network impairment",
     "HOLD ≤ 2 s; RTL at 10 s (B4)"),
    ("FS-003", "Drop UDP 14550 in AUTO", "Network impairment", "Mission "
     "continues; RTL at 60 s (B4)"),
    ("FS-004", "GNSS failure for 5 s then restore", "SITL GPS failure "
     "parameter", "Motors stop ≤ 3 s; RTL after 10 s healthy (B6)"),
    ("FS-005", "Heavy added drag, throttle ≥ 50%", "SITL drag/wind "
     "parameters", "HOLD ≤ 5 s + event"),
    ("FS-006", "As FS-005, drag released after burst 2", "SITL + B5",
     "≤ 3 bursts; resumes mission"),
    ("FS-007", "Kill all MCP services mid-mission", "Stop the camera stub "
     "and B-services", "Mission completes; RTL; HOLD at home"),
    ("FS-008", "Helm signal loss to ESCs", "<b>Bench only</b>",
     "Motors stop ≤ 1 s (PRP-D07)"),
    ("FS-009", "Press STOP (panel or API) in each state", "Panel "
     "emulation", "Motors stop ≤ 1 s"),
    ("FS-010", "Moisture flag set in the stub", "Stub health = moisture",
     "RTL ≤ 2 s"),
    ("FS-011", "GNSS loss during battery RTL", "Combined injections",
     "Motors stop (HOLD) wins"),
    ("FS-012", "All of the above", "Log inspection", "Every event logged "
     "and announced ≤ 2 s"),
    ("FS-013", "Sweep of single faults across mission phases", "Scripted "
     "matrix", "Never leaves the inclusion fence under power"),
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
