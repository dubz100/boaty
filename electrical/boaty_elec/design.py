"""The Mk1 electrical design: the single source for every output.

Parts carry their pins; NETS say which pins are joined; MATES say which
connector halves plug together; WIRES say how the harness joins pins that
sit on different boards or modules. The ERC (erc.py) proves the three agree:
every net is one connected piece of copper once boards, mates and wires
are taken into account, and nothing else is joined.

Boards and places
  PACK      battery pack assembly (cells, BMS, fuse, leads)
  BOX       modules wired inside the electronics box
  PIB       power and interconnect board (stripboard, custom)
  MIB       mission-computer interface board (stripboard on the Pi Zero)
  HANDLE    mast step and handle (main switch, mast socket)
  MASTHEAD  GNSS and LED ring
  DECK_P/S  pod connector sockets on the stern segments
  POD_P/S   thruster pods
  MC        Mission Control case (Pi 5, USB devices, power bank)
  PNL       Mission Control panel board (stripboard, custom)

src tags follow the Key Component List: KCL (a KCL entry), AP (ArduPilot
board definition), DS (datasheet value), EST (estimate or candidate:
confirm at purchase), CALC (sized in calcs.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# pin types
PWR_OUT, PWR_IN, GND, IN, OUT, BIDIR, PAS, BUS = (
    "pwr_out", "pwr_in", "gnd", "in", "out", "bidir", "pas", "bus")


@dataclass
class Pin:
    name: str
    type: str = PAS
    vmax: float | None = None       # absolute maximum on this pin, V
    label: str = ""                  # function label on the part


@dataclass
class Part:
    ref: str
    value: str
    desc: str
    board: str
    kind: str                        # component, module, connector, cable
    pins: dict[str, Pin]
    pkg: str = ""
    mpn: str = ""
    src: str = "EST"
    cost: float = 0.0                # £ each, estimate
    rating: dict = field(default_factory=dict)
    note: str = ""
    sheet: str = ""

    def pin(self, p: str) -> str:
        return f"{self.ref}.{p}"


PARTS: dict[str, Part] = {}


def part(ref, value, desc, board, kind, pins, **kw) -> Part:
    ps = {}
    for p in pins:
        if isinstance(p, Pin):
            ps[p.name] = p
        else:
            ps[p] = Pin(p)
    pt = Part(ref, value, desc, board, kind, ps, **kw)
    assert ref not in PARTS, ref
    PARTS[ref] = pt
    return pt


def R(ref, value, board, watt=0.25, sheet="", note="", cost=0.02):
    ohm = _ohms(value)
    return part(ref, value, f"Resistor {value}, {watt} W, 1%", board,
                "component", ["1", "2"], pkg="axial 0.4\"", src="CALC",
                cost=cost, rating=dict(ohm=ohm, watt=watt), sheet=sheet,
                note=note)


def C(ref, value, board, volt, polar=False, sheet="", note="", pkg="",
      cost=0.05):
    pins = [Pin("+"), Pin("-")] if polar else ["1", "2"]
    desc = (f"Capacitor {value}, {volt} V" +
            (", low-ESR electrolytic" if polar else ", ceramic/film"))
    return part(ref, value, desc, board, "component", pins,
                pkg=pkg or ("radial" if polar else "radial 0.2\""),
                src="CALC", cost=cost,
                rating=dict(farad=_farads(value), volt=volt), sheet=sheet,
                note=note)


def D(ref, value, desc, board, sheet="", mpn="", rating=None, cost=0.1,
      pkg="DO-41"):
    return part(ref, value, desc, board, "component",
                [Pin("A"), Pin("K")], mpn=mpn or value, pkg=pkg,
                src="DS", cost=cost, rating=rating or {}, sheet=sheet)


def conn(ref, value, desc, board, n, sheet="", kind="connector",
         labels=None, cost=0.3, mpn="", pkg="", src="EST", note=""):
    pins = [Pin(str(i + 1), label=(labels[i] if labels else ""))
            for i in range(n)]
    return part(ref, value, desc, board, kind, pins, cost=cost, mpn=mpn,
                pkg=pkg, src=src, sheet=sheet, note=note)


def _ohms(v: str) -> float:
    v = v.replace("Ω", "").strip()
    m = {"k": 1e3, "M": 1e6, "R": 1.0}
    for k, f in m.items():
        if k in v:
            a, _, b = v.partition(k)
            return float((a or "0") + "." + (b or "0")) * f
    return float(v)


def _farads(v: str) -> float:
    v = v.replace("F", "").strip()
    m = {"p": 1e-12, "n": 1e-9, "µ": 1e-6, "u": 1e-6, "m": 1e-3}
    for k, f in m.items():
        if v.endswith(k):
            return float(v[:-1]) * f
    return float(v)


# ======================================================================
# PACK: PWR-1 (PWR-D01..D05, D14, D20)
# ======================================================================
S_PWR = "S1 Power"
part("BT1", "3S1P 18650", "Li-ion cells, 3 in series, accepted to PWR-D20",
     "PACK", "module",
     [Pin("P", PWR_OUT, 12.6), Pin("T2", PAS, 8.4), Pin("T1", PAS, 4.2),
      Pin("N", GND)], src="KCL", mpn="KC-05 salvaged 18650 ×3", cost=0.0,
     rating=dict(cap_ah=2.5, r_cell=0.060, v_full=12.6, v_nom=10.8),
     sheet=S_PWR, note="Pack resistance with acceptance-limit cells and "
     "BMS: 0.22 Ω (KCL section 5)")
part("U1", "3S BMS 20-25 A", "3S Li-ion protection board with balancing",
     "PACK", "module",
     [Pin("B-", GND), Pin("B1", PAS), Pin("B2", PAS), Pin("B+", PWR_IN),
      Pin("P-", GND)], src="KCL", mpn="KC-06 class", cost=3.5,
     rating=dict(ocp=25.0, odv=2.7, r_on=0.015), sheet=S_PWR)
part("F1", "20 A ATO", "Main fuse, ATO/ATC blade 20 A, in a sealed inline "
     "holder ≤ 50 mm from the BMS P+ (PWR-003, PWR-D05)", "PACK",
     "component", [Pin("1"), Pin("2")], pkg="inline holder, 16 AWG",
     src="DS", cost=1.5, rating=dict(amp=20.0, r=0.0035), sheet=S_PWR)
conn("J1", "XT60 (sockets)", "Battery lead: XT60, socket contacts so the "
     "live side is shrouded (PWR-D14)", "PACK", 2, sheet=S_PWR,
     labels=["+", "−"], cost=0.6, mpn="XT60H-F", src="DS")
conn("J2", "JST-XH 4", "Balance lead, charger only (PWR-D04, PWR-D14)",
     "PACK", 4, sheet=S_PWR, labels=["B−", "B1", "B2", "B+"], cost=0.2,
     mpn="XHP-4", src="DS")

# ======================================================================
# BOX: battery socket, flight controller + PDB, ESCs, buck
# ======================================================================
conn("J3", "XT60 (pins)", "Box battery socket on a 16 AWG pigtail",
     "BOX", 2, sheet=S_PWR, labels=["+", "−"], cost=0.6, mpn="XT60H-M",
     src="DS")
S_HLM = "S3 Helm"
part("U2", "SpeedyBee F405 WING APP", "Flight controller with PDB (helm)",
     "BOX", "module",
     [Pin("BAT+", PWR_IN, 36), Pin("BAT-", GND),
      Pin("VBO+", PWR_OUT, 36, "battery out after the current sensor"),
      Pin("VBO-", GND),
      Pin("S1", OUT, 3.3, "PWM1 / DShot, BIDIR"), Pin("G1", GND),
      Pin("S4", OUT, 3.3, "PWM4 / DShot, BIDIR"), Pin("G4", GND),
      Pin("TX1", OUT, 3.3, "USART1 TX (SERIAL1)"),
      Pin("RX1", IN, 5.0, "USART1 RX (FT pin)"), Pin("GU1", GND),
      Pin("TX3", OUT, 3.3, "USART3 TX (SERIAL3, GPS)"),
      Pin("RX3", IN, 5.0, "USART3 RX"),
      Pin("4V5", PWR_OUT, 5.0, "GPS port 4.5 V"), Pin("GGPS", GND),
      Pin("SCL", BIDIR, 3.3, "I2C1 SCL"), Pin("SDA", BIDIR, 3.3,
                                               "I2C1 SDA"),
      Pin("LED", OUT, 3.3, "PWM12 / NeoPixel"),
      Pin("5V", PWR_OUT, 5.5, "LED pad 5 V (5 V BEC)"),
      Pin("AIR", IN, 3.3, "AIRSPD pad, ADC pin 15"), Pin("GAIR", GND)],
     src="KCL", mpn="KC-01 SpeedyBee F405 WING APP", cost=45.0,
     rating=dict(vmin=7.0, bec_a=2.4, i_sense=90.0), sheet=S_HLM,
     note="Pad names as the board silkscreen and ArduPilot hwdef "
     "(docs/kcl/sources). VBO± are the PDB's battery-output pads after "
     "the current sensor: confirm at V-01.")
S_PRP = "S4 Propulsion"
for ref, side in (("U3", "port (left)"), ("U4", "starboard (right)")):
    part(ref, "AM32 20 A", f"ESC, {side}", "BOX", "module",
         [Pin("V+", PWR_IN, 25.2), Pin("V-", GND), Pin("SIG", IN, 5.0),
          Pin("SG", GND), Pin("A", PAS), Pin("B", PAS), Pin("C", PAS)],
         src="KCL", mpn="KC-03 AM32 6S 20 A", cost=11.0,
         rating=dict(vmin=7.2, amp=20.0), sheet=S_PRP)
for ref, esc in (("C7", "U3"), ("C8", "U4")):
    C(ref, "470µF", "BOX", 25, polar=True, sheet=S_PRP,
      note=f"soldered across {esc}'s input leads (KCL KC-07 soft-start "
      "sizing)", cost=0.4)
S_MCP = "S5 Mission computer"
part("U5", "Buck 5.1 V 3 A", "Synchronous buck for the mission computer "
     "(IF-08)", "BOX", "module",
     [Pin("VIN", PWR_IN, 36), Pin("GI", GND), Pin("VOUT", PWR_OUT, 5.2),
      Pin("GO", GND)], src="KCL",
     mpn="KC-09 class (the KCL's £3 module); bench-checked to IF-08. "
     "Upgrade: Pololu D24V50F5 (£12)", cost=3.0,
     rating=dict(vin_min=6.0, eff=0.90, amp=3.0), sheet=S_MCP)

# ======================================================================
# PIB: power and interconnect board (PWR-2/3, IF-06, IF-09, IF-22)
# ======================================================================
S_PIB = "S2 Power and interconnect board"
PFET = dict(vds=-30.0, id=-80.0, rds=0.006, vgs_max=20.0, vth=-2.0,
            rth_ja=62.0, rth_sink=22.5)
part("Q1", "P-MOSFET", "Main switch, high side (PWR-D06 solid-state "
     "option)", "PIB", "component",
     [Pin("G", PAS, 20), Pin("D", PAS, 30), Pin("S", PAS, 30)],
     pkg="TO-220, lying flat", src="EST",
     mpn="candidate Infineon IPP80P03P4L-04 (−30 V, R_DS(on) ≤ 6 mΩ at "
     "−10 V assumed); fallback IRF4905 (20 mΩ)", cost=1.8, rating=PFET,
     sheet=S_PIB)
part("Q2", "P-MOSFET", "Motor-rail key switch, high side (PWR-D07, IF-06)",
     "PIB", "component",
     [Pin("G", PAS, 20), Pin("D", PAS, 30), Pin("S", PAS, 30)],
     pkg="TO-220, lying flat", src="EST", mpn=PARTS["Q1"].mpn, cost=1.8,
     rating=PFET, sheet=S_PIB)
part("Q3", "IRLZ44N", "Rail bleeder, logic-level N-MOSFET", "PIB",
     "component", [Pin("G", PAS, 16), Pin("D", PAS, 55), Pin("S", PAS,
                                                              55)],
     pkg="TO-220", src="DS", mpn="IRLZ44NPbF", cost=1.0,
     rating=dict(vds=55.0, rds=0.035, vth=1.5, vgs_max=16.0), sheet=S_PIB)
R("R1", "10k", "PIB", sheet=S_PIB, note="Q1 gate to source: off unless "
  "the main switch is closed")
R("R2", "3k3", "PIB", sheet=S_PIB, note="Q1 gate divider to the switch")
C("C1", "470nF", "PIB", 25, sheet=S_PIB, note="Q1 soft start: gate to "
  "drain (Miller), sets the bus dV/dt")
D("D1", "BZX85C15", "Zener 15 V 1.3 W, Q1 gate clamp", "PIB",
  sheet=S_PIB, rating=dict(vz=15.0))
D("D2", "P6KE18A", "TVS 600 W, 15.3 V stand-off, main bus", "PIB",
  sheet=S_PIB, rating=dict(vwm=15.3, vbr=17.1, vc=25.2), cost=0.3,
  pkg="DO-15")
R("R3", "10k", "PIB", sheet=S_PIB, note="Q2 gate to source: rail off "
  "with the key out (fails safe)")
R("R4", "3k3", "PIB", sheet=S_PIB, note="Q2 gate divider to the reed")
C("C2", "470nF", "PIB", 25, sheet=S_PIB, note="Q2 soft start (IF-06): "
  "gate to drain (Miller), sets the rail dV/dt")
D("D3", "BZX85C15", "Zener 15 V, Q2 gate clamp", "PIB", sheet=S_PIB,
  rating=dict(vz=15.0))
C("C3", "1µF", "PIB", 25, sheet=S_PIB, note="Bleeder pulse coupling "
  "(film)")
R("R5", "100k", "PIB", sheet=S_PIB, note="Bleeder gate discharge: pulse "
  "length")
D("D4", "BZX85C10", "Zener 10 V, Q3 gate clamp", "PIB", sheet=S_PIB,
  rating=dict(vz=10.0))
R("R9", "10R", "PIB", watt=2.0, sheet=S_PIB, note="Bleed resistor: "
  "discharges the ESC capacitors after key-out", cost=0.2)
D("D5", "P6KE18A", "TVS 600 W, motor rail (ESC regeneration)", "PIB",
  sheet=S_PIB, rating=dict(vwm=15.3, vbr=17.1, vc=25.2), cost=0.3,
  pkg="DO-15")
R("R6", "10k", "PIB", sheet=S_PIB, note="Rail sense divider, top "
  "(IF-06)")
R("R7", "1k", "PIB", sheet=S_PIB, note="Rail sense divider, bottom: "
  "BATT2_VOLT_MULT 11.0")
C("C4", "100nF", "PIB", 16, sheet=S_PIB, note="ADC filter, 0.9 ms")
part("F2", "PTC 1.1 A", "Resettable fuse, buck feed", "PIB", "component",
     [Pin("1"), Pin("2")], pkg="radial", src="DS", mpn="RXEF110",
     cost=0.3, rating=dict(ihold=1.1, itrip=2.2, vmax=60.0), sheet=S_PIB)
D("D6", "1N4001", "LED ring supply drop: 5 V → ≈ 4.3 V so 3.3 V data "
  "is a valid high (closes TBC-08)", "PIB", sheet=S_PIB,
  rating=dict(vf=0.8, amp=1.0))
R("R8", "330R", "PIB", sheet=S_PIB, note="LED data series resistor "
  "(IF-09)")
for ref, lab in (("E1", "PACK+ in"), ("E2", "BUS+ out"),
                 ("E3", "VBAT_S in"), ("E4", "MOTOR+ out"),
                 ("E5", "BUCK+ out"), ("E6", "GND"),
                 ("E7", "RAIL_ADC out"), ("E8", "LED 5V in"),
                 ("E9", "LED data in")):
    part(ref, "pad", f"Solder pad: {lab}", "PIB", "connector",
         [Pin("1", label=lab)], src="-", sheet=S_PIB)
conn("J11", "KK254 2", "Main switch lead", "PIB", 2, sheet=S_PIB,
     labels=["SW_MAIN", "GND"], mpn="Molex 22-27-2021", src="DS")
conn("J12", "KK254 3", "Reed switch lead (pin 2 not fitted: keyed "
     "against J11)", "PIB", 3, sheet=S_PIB, labels=["KEY_N", "nc",
                                                    "GND"],
     mpn="Molex 22-27-2031", src="DS")
conn("J14", "KK254 8", "Mast cable from the gland", "PIB", 8,
     sheet=S_PIB, labels=["GPS 4V5", "GND", "FC TX3", "FC RX3", "SCL",
                          "SDA", "LED 5V", "LED DIN"], mpn="Molex 22-27-2081",
     src="DS")
conn("J15", "KK254 6", "GNSS lead to the FC GPS port", "PIB", 6,
     sheet=S_PIB, labels=["4V5", "GND", "TX3", "RX3", "SCL", "SDA"],
     mpn="Molex 22-27-2061", src="DS")

# ======================================================================
# HANDLE / MAST / DECK / POD
# ======================================================================
part("SW1", "IP67 toggle + cover", "Main switch on the handle, sealed, "
     "flip cover (PWR-004, PWR-D06, CHD-003)", "HANDLE", "component",
     [Pin("1"), Pin("2")], pkg="12 mm panel", src="EST",
     mpn="IP67 sealed miniature toggle, ≥ 0.5 A 24 V DC, with flip "
     "cover", cost=4.0, sheet=S_PWR)
part("SW2", "Reed NO", "Arming-key reed switch on a bracket inside the "
     "box under the key dock (IF-18)", "BOX", "component",
     [Pin("1"), Pin("2")], pkg="glass, 14 mm", src="EST",
     mpn="normally-open glass reed, 10-20 AT (e.g. Littelfuse 59140 "
     "housed type)", cost=1.5, sheet=S_PIB)
conn("J40", "M12 A 8-pole socket", "Mast connector, panel socket on the "
     "handle (IP67)", "HANDLE", 8, sheet=S_HLM, cost=6.0,
     mpn="M12 A-coded 8-pole panel socket, rear mount, IP67",
     labels=["4V5", "GND", "FC TX3", "FC RX3", "SCL", "SDA", "LED 5V",
             "LED DIN"])
conn("P40", "M12 A 8-pole plug", "Mast lead plug (IP67)", "MASTHEAD", 8,
     sheet=S_HLM, cost=5.0, mpn="M12 A-coded 8-pole cable plug, IP67",
     labels=PARTS["J40"].pins and [p.label for p in
                                   PARTS["J40"].pins.values()])
part("U9", "M10 GNSS + compass", "GNSS and compass (IF-22)", "MASTHEAD",
     "module", [Pin("5V", PWR_IN, 6.0), Pin("GND", GND),
                Pin("RX", IN, 3.6), Pin("TX", OUT, 3.3),
                Pin("SCL", BIDIR, 3.6), Pin("SDA", BIDIR, 3.6)],
     src="KCL", mpn="KC-02 M10 + QMC5883L", cost=14.0,
     rating=dict(amp=0.05), sheet=S_HLM)
part("U10", "WS2812B ring ×8", "LED beacon (IF-09, REC-D03)", "MASTHEAD",
     "module", [Pin("5V", PWR_IN, 5.3), Pin("DIN", IN, 5.3),
                Pin("GND", GND)], src="KCL", mpn="KC-14", cost=3.0,
     rating=dict(amp=0.25, vih_frac=0.7), sheet=S_HLM)
for side, s in (("P", "port"), ("S", "starboard")):
    conn(f"J5{'0' if side == 'P' else '1'}", "IP68 3-pole socket",
         f"Pod connector, {s} stern deck (PRP-3, IF-17)", f"DECK_{side}",
         3, sheet=S_PRP, cost=4.0, labels=["A", "B", "C"],
         mpn="TBC-12: keyed 3-pole IP68, ≥ 10 A (e.g. Weipu SP13 3-pole; "
         "confirm rating)")
    conn(f"P5{'0' if side == 'P' else '1'}", "IP68 3-pole plug",
         f"Pod lead plug, {s}", f"POD_{side}", 3, sheet=S_PRP, cost=4.0,
         labels=["A", "B", "C"], mpn="as the socket")
    part(f"M{1 if side == 'P' else 2}", "2205 outrunner",
         f"Thruster motor, {s} (KC-04)", f"POD_{side}", "module",
         [Pin("A"), Pin("B"), Pin("C")], src="KCL", mpn="KC-04",
         cost=6.0, sheet=S_PRP)

# ======================================================================
# MIB: mission-computer interface board on the Pi Zero (IF-04, IF-08)
# ======================================================================
conn("J30", "Micro-Fit 2 plug", "Mission-computer 5 V lead (the only "
     "Micro-Fit on the boat: PWR-D14)", "BOX", 2, sheet=S_MCP,
     labels=["5V", "GND"], cost=0.5, mpn="Molex 43025-0200", src="DS")
conn("J31", "Micro-Fit 2 header", "5 V in", "MIB", 2, sheet=S_MCP,
     labels=["5V", "GND"], cost=0.6, mpn="Molex 43650-0200", src="DS")
D("D10", "P6KE6.8A", "TVS 5.8 V stand-off on the 5 V feed", "MIB",
  sheet=S_MCP, rating=dict(vwm=5.8, vbr=6.45, vc=10.5), cost=0.3,
  pkg="DO-15")
C("C10", "470µF", "MIB", 10, polar=True, sheet=S_MCP, note="Hold-up "
  "and step response on the Pi's back-powered 5 V", cost=0.3)
C("C11", "10µF", "MIB", 16, sheet=S_MCP)
PI_Z = [("1", "3V3", PWR_OUT, 3.3), ("2", "5V", PWR_IN, 5.5),
        ("4", "5V", PWR_IN, 5.5), ("6", "GND", GND, None),
        ("7", "GPIO4 1-Wire", BIDIR, 3.6), ("8", "GPIO14 TXD", OUT, 3.3),
        ("9", "GND", GND, None), ("10", "GPIO15 RXD", IN, 3.6),
        ("11", "GPIO17 moisture", IN, 3.6), ("14", "GND", GND, None)]
conn("J32", "2×20 socket", "40-way socket onto the Pi Zero header (used "
     "pins only listed)", "MIB", 0, sheet=S_MCP, cost=1.0,
     mpn="2×20 2.54 mm female, stacking")
PARTS["J32"].pins = {n: Pin(n, PAS, v, lab) for n, lab, _t, v in PI_Z}
part("U6", "Raspberry Pi Zero 2 W", "Mission computer (KC-10)", "BOX",
     "module", [Pin(n, t, v, lab) for n, lab, t, v in PI_Z] +
     [Pin("CSI", BUS, None, "camera ribbon")], src="KCL",
     mpn="KC-10", cost=15.0, rating=dict(w_avg=1.8, w_peak=3.0),
     sheet=S_MCP)
part("U7", "OV5647 camera", "Camera (KC-11), 150 mm Pi Zero ribbon",
     "BOX", "module", [Pin("CSI", BUS)], src="KCL", mpn="KC-11",
     cost=8.0, sheet=S_MCP)
conn("J33", "KK254 3", "UART to the helm (IF-04)", "MIB", 3,
     sheet=S_MCP, labels=["Pi TXD", "Pi RXD", "GND"], mpn="Molex 22-27-2031",
     src="DS")
conn("J34", "KK254 4", "DS18B20 lead (pin 4 not fitted: keyed against "
     "J33)", "MIB", 4, sheet=S_MCP, labels=["3V3", "DQ", "GND", "nc"],
     mpn="Molex 22-27-2041", src="DS")
conn("J35", "KK254 2", "Moisture comb lead", "MIB", 2, sheet=S_MCP,
     labels=["SENSE", "GND"], mpn="Molex 22-27-2021", src="DS")
R("R10", "4k7", "MIB", sheet=S_MCP, note="1-Wire pull-up (KC-12)")
R("R11", "1k", "MIB", sheet=S_MCP, note="Moisture input series (ESD)")
R("R12", "100k", "MIB", sheet=S_MCP, note="Moisture pull-up (with the "
  "Pi's own ≈ 50 k)")
C("C12", "100nF", "MIB", 16, sheet=S_MCP, note="Moisture input filter")
part("U8", "DS18B20", "Box temperature (KC-12), top of the box",
     "BOX", "module", [Pin("VDD", PWR_IN, 5.5), Pin("DQ", BIDIR, 5.5),
                       Pin("GND", GND)], src="KCL", mpn="KC-12",
     cost=2.0, sheet=S_MCP)
part("S2", "Moisture comb", "Interdigitated trace board at the box low "
     "point (MCP-D03)", "BOX", "module", [Pin("A"), Pin("B")], src="EST",
     mpn="nickel-plated comb board (rain-sensor type, comb only)",
     cost=1.0, sheet=S_MCP)

# ======================================================================
# Mission Control (bank): Pi 5 and the panel (IF-12)
# ======================================================================
S_MCN = "S6 Mission Control"
BUTTONS = [("GO", "green", "17", "11", "5", "29"),
           ("HOME", "yellow", "27", "13", "6", "31"),
           ("STOP", "red", "22", "15", "13", "33"),
           ("TALK", "blue", "24", "18", "19", "35")]
PI5 = [("1", "3V3", PWR_OUT, 3.3), ("2", "5V", PWR_OUT, 5.2),
       ("6", "GND", GND, None), ("9", "GND", GND, None),
       ("14", "GND", GND, None)]
for b, _c, g, p, lg, lp in BUTTONS:
    PI5 += [(p, f"GPIO{g} {b}", IN, 3.6), (lp, f"GPIO{lg} {b} LED", OUT,
                                           3.3)]
part("U50", "Raspberry Pi 5", "Mission Control computer (KC-16)", "MC",
     "module", [Pin(n, t, v, lab) for n, lab, t, v in PI5] +
     [Pin("USBC", PWR_IN, 5.5, "USB-C power in"),
      Pin("USB1", BUS), Pin("USB2", BUS), Pin("USB3", BUS),
      Pin("USB4", BUS)], src="KCL", mpn="KC-16 (owned)", cost=0.0,
     rating=dict(w_avg=5.0, w_peak=8.0, usb_a=1.6), sheet=S_MCN)
conn("J60", "2×20 IDC header", "Panel board header, 150 mm ribbon to the "
     "Pi 5", "PNL", 0, sheet=S_MCN, cost=0.8)
PARTS["J60"].pins = {n: Pin(n, PAS, v, lab) for n, lab, _t, v in PI5}
part("BT50", "USB-C PD bank 20 Ah", "Power bank (MCN-D01)", "MC",
     "module", [Pin("USBC", PWR_OUT, 5.5)], src="EST",
     mpn="20,000 mAh USB-C PD, 5 V 3 A (owned or bought)", cost=0.0,
     rating=dict(wh=74.0), sheet=S_MCN)
for ref, name, desc, cost in (
        ("U51", "Wi-Fi adapter", "MT7610U/MT7612U USB adapter, RP-SMA "
         "antenna (KC-15)", 12.0),
        ("U52", "USB microphone", "16 kHz mono (KC-17)", 4.0),
        ("U53", "USB speaker", "≈ 3 W (KC-17)", 4.0),
        ("U54", "Phone (tether)", "Adult's phone, USB tether (IF-10)",
         0.0)):
    part(ref, name, desc, "MC", "module", [Pin("USB", BUS)], src="KCL",
         cost=cost, sheet=S_MCN)
for i, (b, colour, g, p, lg, lp) in enumerate(BUTTONS):
    n = 61 + i
    part(f"SW{n}", f"{b} button", f"30 mm arcade button, {colour}, 5 V "
         "LED (KC-18)", "MC", "component",
         [Pin("C"), Pin("NO"), Pin("LED+"), Pin("LED-")], src="KCL",
         mpn="KC-18", cost=1.5, sheet=S_MCN)
    R(f"R{61 + 10 * i}", "10k", "PNL", sheet=S_MCN, note=f"{b} pull-up")
    R(f"R{62 + 10 * i}", "1k", "PNL", sheet=S_MCN, note=f"{b} series")
    C(f"C{61 + i}", "100nF", "PNL", 16, sheet=S_MCN, note=f"{b} filter")
    part(f"Q{61 + i}", "2N7000", f"{b} LED driver", "PNL", "component",
         [Pin("G", PAS, 20), Pin("D", PAS, 60), Pin("S", PAS, 60)],
         pkg="TO-92", src="DS", mpn="2N7000", cost=0.1,
         rating=dict(vth_max=3.0, rds=5.0, id=0.2), sheet=S_MCN)
    R(f"R{63 + 10 * i}", "100R", "PNL", sheet=S_MCN, note=f"{b} gate")
    R(f"R{64 + 10 * i}", "100k", "PNL", sheet=S_MCN,
      note=f"{b} gate pull-down (LED off at boot)")
    for k, lab in (("a", "switch"), ("b", "LED")):
        part(f"E6{i}{k}", "pad", f"{b} {lab} wires", "PNL", "connector",
             [Pin("1", label="sig"), Pin("2", label="ret")], src="-",
             sheet=S_MCN)

# ======================================================================
# NETS: which pins are joined
# ======================================================================
NETS: dict[str, list[str]] = {
    # pack
    "BATT_NEG": ["BT1.N", "U1.B-", "J2.1"],
    "CELL1": ["BT1.T1", "U1.B1", "J2.2"],
    "CELL2": ["BT1.T2", "U1.B2", "J2.3"],
    "BATT_POS": ["BT1.P", "U1.B+", "F1.1", "J2.4"],
    "PACK_POS": ["F1.2", "J1.1", "J3.1", "E1.1", "Q1.S", "R1.1", "D1.K"],
    # main switch
    "Q1_G": ["Q1.G", "R1.2", "R2.1", "C1.2", "D1.A"],
    "SW_MAIN": ["R2.2", "J11.1", "SW1.1"],
    "BUS_POS": ["Q1.D", "C1.1", "D2.K", "E2.1", "U2.BAT+"],
    "VBAT_S": ["U2.VBO+", "E3.1", "Q2.S", "R3.1", "D3.K", "F2.1"],
    # key switch and bleeder
    "Q2_G": ["Q2.G", "R3.2", "R4.1", "C2.2", "D3.A"],
    "KEY_N": ["R4.2", "C3.1", "J12.1", "SW2.1"],
    "Q3_G": ["C3.2", "R5.1", "D4.K", "Q3.G"],
    "MOTOR_POS": ["Q2.D", "C2.1", "D5.K", "R6.1", "R9.1", "E4.1", "C7.+",
                  "C8.+",
                  "U3.V+", "U4.V+"],
    "BLEED": ["R9.2", "Q3.D"],
    "RAIL_ADC": ["R6.2", "R7.1", "C4.1", "E7.1", "U2.AIR"],
    "BUCK_IN": ["F2.2", "E5.1", "U5.VIN"],
    # one ground: pack P−, PDB, every return
    "GND": ["U1.P-", "J1.2", "J3.2", "U2.BAT-", "U2.VBO-", "U2.G1",
            "U2.G4", "U2.GU1", "U2.GGPS", "U2.GAIR", "D2.A", "D4.A",
            "R5.2", "Q3.S", "D5.A", "R7.2", "C4.2", "E6.1", "J11.2",
            "SW1.2", "J12.3", "SW2.2", "J14.2", "J15.2", "J40.2", "P40.2",
            "U9.GND", "U10.GND", "U3.V-", "U4.V-", "U3.SG", "U4.SG",
            "C7.-", "C8.-", "U5.GI", "U5.GO", "J30.2", "J31.2", "D10.A",
            "C10.-", "C11.2", "J32.6", "J32.9", "J32.14", "U6.6", "U6.9",
            "U6.14", "J33.3", "J34.3", "U8.GND", "J35.2", "S2.B",
            "C12.2"],
    # ESC signals (IF-05)
    "ESC_L": ["U2.S1", "U3.SIG"],
    "ESC_R": ["U2.S4", "U4.SIG"],
    # motor phases (through the glands and the IP68 connectors)
    **{f"M{m}_{ph}": [f"{esc}.{ph}", f"J5{m - 1}.{i + 1}",
                      f"P5{m - 1}.{i + 1}", f"M{m}.{ph}"]
       for m, esc in ((1, "U3"), (2, "U4"))
       for i, ph in enumerate("ABC")},
    # GNSS and compass (IF-22), LED beacon (IF-09)
    "GPS_4V5": ["U2.4V5", "J15.1", "J14.1", "J40.1", "P40.1", "U9.5V"],
    "GPS_FC_TX": ["U2.TX3", "J15.3", "J14.3", "J40.3", "P40.3", "U9.RX"],
    "GPS_FC_RX": ["U2.RX3", "J15.4", "J14.4", "J40.4", "P40.4", "U9.TX"],
    "I2C_SCL": ["U2.SCL", "J15.5", "J14.5", "J40.5", "P40.5", "U9.SCL"],
    "I2C_SDA": ["U2.SDA", "J15.6", "J14.6", "J40.6", "P40.6", "U9.SDA"],
    "LED_5V_FC": ["U2.5V", "E8.1", "D6.A"],
    "LED_5V": ["D6.K", "J14.7", "J40.7", "P40.7", "U10.5V"],
    "LED_DATA_FC": ["U2.LED", "E9.1", "R8.1"],
    "LED_DIN": ["R8.2", "J14.8", "J40.8", "P40.8", "U10.DIN"],
    # mission computer (IF-04, IF-08)
    "5V_MCP": ["U5.VOUT", "J30.1", "J31.1", "D10.K", "C10.+", "C11.1",
               "J32.2", "J32.4", "U6.2", "U6.4"],
    "3V3_MCP": ["J32.1", "U6.1", "R10.1", "J34.1", "U8.VDD", "R12.1"],
    "MCP_TX": ["J32.8", "U6.8", "J33.1", "U2.RX1"],
    "MCP_RX": ["J32.10", "U6.10", "J33.2", "U2.TX1"],
    "W1_DQ": ["J32.7", "U6.7", "R10.2", "J34.2", "U8.DQ"],
    "MOIST": ["R11.1", "J35.1", "S2.A"],
    "MOIST_GPIO": ["R11.2", "R12.2", "C12.1", "J32.11", "U6.11"],
    "CSI": ["U6.CSI", "U7.CSI"],
    # Mission Control
    "PI5_5V_IN": ["BT50.USBC", "U50.USBC"],
    "PI5_3V3": ["U50.1", "J60.1"] + [f"R{61 + 10 * i}.1" for i in
                                     range(4)],
    "PI5_5V": ["U50.2", "J60.2"] + [f"E6{i}b.1" for i in range(4)] +
              [f"SW{61 + i}.LED+" for i in range(4)],
    "PI5_GND": ["U50.6", "U50.9", "U50.14", "J60.6", "J60.9", "J60.14"] +
               [f"C{61 + i}.2" for i in range(4)] +
               [f"Q{61 + i}.S" for i in range(4)] +
               [f"R{64 + 10 * i}.2" for i in range(4)] +
               [f"E6{i}a.2" for i in range(4)] +
               [f"SW{61 + i}.C" for i in range(4)],
    "USB_WIFI": ["U50.USB1", "U51.USB"],
    "USB_MIC": ["U50.USB2", "U52.USB"],
    "USB_SPK": ["U50.USB3", "U53.USB"],
    "USB_PHONE": ["U50.USB4", "U54.USB"],
}
for i, (b, _c, g, p, lg, lp) in enumerate(BUTTONS):
    NETS[f"BTN_{b}_SW"] = [f"R{61 + 10 * i}.2", f"R{62 + 10 * i}.1",
                           f"E6{i}a.1", f"SW{61 + i}.NO"]
    NETS[f"BTN_{b}"] = [f"R{62 + 10 * i}.2", f"C{61 + i}.1", f"J60.{p}",
                        f"U50.{p}"]
    NETS[f"LED_{b}_G"] = [f"R{63 + 10 * i}.2", f"R{64 + 10 * i}.1",
                          f"Q{61 + i}.G"]
    NETS[f"LED_{b}"] = [f"R{63 + 10 * i}.1", f"J60.{lp}", f"U50.{lp}"]
    NETS[f"LED_{b}_K"] = [f"Q{61 + i}.D", f"E6{i}b.2", f"SW{61 + i}.LED-"]

# pins deliberately left unconnected
NC = ["J12.2", "J34.4"]

# ======================================================================
# MATES: connector halves that plug together (and the Pi headers)
# ======================================================================
MATES = [("J1", "J3"), ("J40", "P40"), ("J50", "P50"), ("J51", "P51"),
         ("J30", "J31"), ("J32", "U6"), ("J60", "U50")]


# ======================================================================
# WIRES: the harness. (id, net, from pin, to pin, gauge AWG or cable,
# length mm, route, note)
# ======================================================================
@dataclass
class Wire:
    id: str
    net: str
    a: str
    b: str
    gauge: str
    length: int
    route: str
    colour: str = ""
    cable: str = ""
    note: str = ""


W = Wire
WIRES: list[Wire] = [
    # pack (the pack assembly: BMS P+ lead to fuse, fuse to XT60)
    W("W01", "BATT_POS", "U1.B+", "F1.1", "16", 40, "PACK", "red",
      note="≤ 50 mm (PWR-D05)"),
    W("W02", "PACK_POS", "F1.2", "J1.1", "16", 100, "PACK", "red"),
    W("W03", "GND", "U1.P-", "J1.2", "16", 120, "PACK", "black"),
    W("W04", "BATT_POS", "BT1.P", "J2.4", "26", 100, "PACK", "red"),
    W("W05", "CELL2", "BT1.T2", "J2.3", "26", 100, "PACK", "white"),
    W("W06", "CELL1", "BT1.T1", "J2.2", "26", 100, "PACK", "white"),
    W("W07", "BATT_NEG", "BT1.N", "J2.1", "26", 100, "PACK", "black"),
    W("W08", "BATT_POS", "BT1.P", "U1.B+", "20", 30, "PACK", "red"),
    W("W09", "CELL2", "BT1.T2", "U1.B2", "26", 30, "PACK", "white"),
    W("W10", "CELL1", "BT1.T1", "U1.B1", "26", 30, "PACK", "white"),
    W("W11", "BATT_NEG", "BT1.N", "U1.B-", "16", 30, "PACK", "black"),
    # box power
    W("W20", "PACK_POS", "J3.1", "E1.1", "16", 120, "BOX", "red"),
    W("W21", "GND", "J3.2", "U2.BAT-", "16", 150, "BOX", "black"),
    W("W22", "BUS_POS", "E2.1", "U2.BAT+", "16", 100, "BOX", "red"),
    W("W23", "VBAT_S", "U2.VBO+", "E3.1", "16", 100, "BOX", "red"),
    W("W24", "MOTOR_POS", "E4.1", "U3.V+", "18", 180, "BOX", "red",
      note="ESC lead via XT30 pair (see connectors)"),
    W("W25", "MOTOR_POS", "E4.1", "U4.V+", "18", 180, "BOX", "red",
      note="ESC lead via XT30 pair"),
    W("W26", "GND", "U2.VBO-", "U3.V-", "18", 180, "BOX", "black",
      note="ESC lead via XT30 pair"),
    W("W27", "GND", "U2.VBO-", "U4.V-", "18", 180, "BOX", "black",
      note="ESC lead via XT30 pair"),
    W("W28", "GND", "U2.VBO-", "E6.1", "22", 100, "BOX", "black",
      note="PIB signal ground only: no motor current"),
    W("W29", "BUCK_IN", "E5.1", "U5.VIN", "20", 100, "BOX", "red"),
    W("W30", "GND", "U2.VBO-", "U5.GI", "20", 100, "BOX", "black"),
    W("W31", "5V_MCP", "U5.VOUT", "J30.1", "20", 150, "BOX", "red"),
    W("W32", "GND", "U5.GO", "J30.2", "20", 150, "BOX", "black"),
    W("W33", "RAIL_ADC", "E7.1", "U2.AIR", "26", 150, "BOX", "yellow",
      cable="twisted with W34"),
    W("W34", "GND", "E6.1", "U2.GAIR", "26", 150, "BOX", "black",
      cable="twisted with W33"),
    # ESC signals: twisted pairs ≤ 150 mm (IF-05)
    W("W35", "ESC_L", "U2.S1", "U3.SIG", "26", 150, "BOX", "white",
      cable="twisted pair TP1"),
    W("W36", "GND", "U2.G1", "U3.SG", "26", 150, "BOX", "black",
      cable="twisted pair TP1"),
    W("W37", "ESC_R", "U2.S4", "U4.SIG", "26", 150, "BOX", "white",
      cable="twisted pair TP2"),
    W("W38", "GND", "U2.G4", "U4.SG", "26", 150, "BOX", "black",
      cable="twisted pair TP2"),
    # LED feed from the FC LED pads to the PIB
    W("W39", "LED_5V_FC", "U2.5V", "E8.1", "24", 120, "BOX", "red"),
    W("W40", "LED_DATA_FC", "U2.LED", "E9.1", "26", 120, "BOX", "green"),
    # GNSS lead PIB J15 → FC GPS port (6-way)
    *[W(f"W4{i + 1}", n, f"J15.{i + 1}", p, "26", 150, "BOX", c,
        cable="C1 6-way GPS lead")
      for i, (n, p, c) in enumerate([
          ("GPS_4V5", "U2.4V5", "red"), ("GND", "U2.GGPS", "black"),
          ("GPS_FC_TX", "U2.TX3", "yellow"), ("GPS_FC_RX", "U2.RX3",
                                              "green"),
          ("I2C_SCL", "U2.SCL", "blue"), ("I2C_SDA", "U2.SDA", "white")])],
    # main switch and reed leads
    W("W50", "SW_MAIN", "J11.1", "SW1.1", "24", 350, "G4 gland", "red",
      cable="C2 2-core Ø4, gland G4"),
    W("W51", "GND", "J11.2", "SW1.2", "24", 350, "G4 gland", "black",
      cable="C2 2-core Ø4, gland G4"),
    W("W52", "KEY_N", "J12.1", "SW2.1", "26", 150, "BOX", "white"),
    W("W53", "GND", "J12.3", "SW2.2", "26", 150, "BOX", "black"),
    # mast cable: PIB J14 → gland G3 → M12 socket on the handle
    *[W(f"W6{i}", n, f"J14.{i + 1}", f"J40.{i + 1}", "0.25 mm²", 300,
        "G3 gland", c, cable="C3 8-core Ø5.5 (box to handle)")
      for i, (n, c) in enumerate([
          ("GPS_4V5", "red"), ("GND", "black"), ("GPS_FC_TX", "yellow"),
          ("GPS_FC_RX", "green"), ("I2C_SCL", "blue"), ("I2C_SDA", "white"),
          ("LED_5V", "brown"), ("LED_DIN", "grey")])],
    # mast lead: M12 plug → masthead (through the tube)
    *[W(f"W7{i}", n, f"P40.{i + 1}", p, "0.25 mm²", 450, "mast tube", c,
        cable="C4 8-core Ø5.5 (mast lead)")
      for i, (n, p, c) in enumerate([
          ("GPS_4V5", "U9.5V", "red"), ("GND", "U9.GND", "black"),
          ("GPS_FC_TX", "U9.RX", "yellow"), ("GPS_FC_RX", "U9.TX", "green"),
          ("I2C_SCL", "U9.SCL", "blue"), ("I2C_SDA", "U9.SDA", "white"),
          ("LED_5V", "U10.5V", "brown"), ("LED_DIN", "U10.DIN", "grey")])],
    W("W78", "GND", "U9.GND", "U10.GND", "0.25 mm²", 30, "masthead",
      "black", note="LED return at the masthead"),
    # motor cables: ESC → gland → deck socket; pod lead → motor
    *[W(f"W8{2 * (m - 1)}{i}", f"M{m}_{ph}", f"{esc}.{ph}",
        f"J5{m - 1}.{i + 1}", "18", 600, f"G{m} gland",
        ["blue", "brown", "black"][i],
        cable=f"C{4 + m} 3-core 0.75 mm² Ø6, gland G{m}")
      for m, esc in ((1, "U3"), (2, "U4")) for i, ph in enumerate("ABC")],
    *[W(f"W9{2 * (m - 1)}{i}", f"M{m}_{ph}", f"P5{m - 1}.{i + 1}",
        f"M{m}.{ph}", "18", 220, "pod strut",
        ["blue", "brown", "black"][i],
        cable=f"C{6 + m} pod lead, potted in the strut groove")
      for m in (1, 2) for i, ph in enumerate("ABC")],
    # mission computer
    W("W100", "MCP_TX", "J33.1", "U2.RX1", "26", 200, "BOX", "yellow",
      cable="C9 3-way UART"),
    W("W101", "MCP_RX", "J33.2", "U2.TX1", "26", 200, "BOX", "green",
      cable="C9 3-way UART"),
    W("W102", "GND", "J33.3", "U2.GU1", "26", 200, "BOX", "black",
      cable="C9 3-way UART"),
    W("W103", "3V3_MCP", "J34.1", "U8.VDD", "26", 150, "BOX", "red",
      cable="C10 DS18B20 lead"),
    W("W104", "W1_DQ", "J34.2", "U8.DQ", "26", 150, "BOX", "yellow",
      cable="C10 DS18B20 lead"),
    W("W105", "GND", "J34.3", "U8.GND", "26", 150, "BOX", "black",
      cable="C10 DS18B20 lead"),
    W("W106", "MOIST", "J35.1", "S2.A", "26", 120, "BOX", "white",
      cable="C11 moisture lead"),
    W("W107", "GND", "J35.2", "S2.B", "26", 120, "BOX", "black",
      cable="C11 moisture lead"),
    W("W108", "CSI", "U6.CSI", "U7.CSI", "ribbon", 150, "BOX", "",
      cable="Pi Zero camera ribbon 22-15 way"),
    W("W109", "GND", "U5.GO", "U5.GI", "-", 0, "module", "",
      note="joined inside the buck module"),
    W("W110", "GND", "U2.BAT-", "U2.VBO-", "-", 0, "module", "",
      note="joined on the PDB"),
    *[W(f"W11{i}", "GND", "U2.BAT-", f"U2.{p}", "-", 0, "module", "",
        note="FC ground plane")
      for i, p in enumerate(["G1", "G4", "GU1", "GGPS", "GAIR"])],
    W("W120", "GND", "U3.V-", "U3.SG", "-", 0, "module", "",
      note="ESC ground"),
    W("W121", "GND", "U4.V-", "U4.SG", "-", 0, "module", "",
      note="ESC ground"),
    W("W122", "MOTOR_POS", "C7.+", "U3.V+", "-", 0, "at ESC", ""),
    W("W123", "MOTOR_POS", "C8.+", "U4.V+", "-", 0, "at ESC", ""),
    W("W124", "GND", "C7.-", "U3.V-", "-", 0, "at ESC", ""),
    W("W125", "GND", "C8.-", "U4.V-", "-", 0, "at ESC", ""),
    # Mission Control
    W("W130", "PI5_5V_IN", "BT50.USBC", "U50.USBC", "USB-C", 300, "case",
      "", cable="USB-C to C, 5 A e-marked"),
    *[W(f"W13{1 + i}", n, f"U50.{u}", f"{d}.USB", "USB", 200, "case", "")
      for i, (n, u, d) in enumerate([("USB_WIFI", "USB1", "U51"),
                                     ("USB_MIC", "USB2", "U52"),
                                     ("USB_SPK", "USB3", "U53"),
                                     ("USB_PHONE", "USB4", "U54")])],
]
for i, (b, _c, g, p, lg, lp) in enumerate(BUTTONS):
    WIRES += [
        W(f"W14{i}a", f"BTN_{b}_SW", f"E6{i}a.1", f"SW{61 + i}.NO", "24",
          150, "case", "white", cable=f"C{20 + i} {b} button 4-core"),
        W(f"W14{i}b", "PI5_GND", f"E6{i}a.2", f"SW{61 + i}.C", "24", 150,
          "case", "black", cable=f"C{20 + i} {b} button 4-core"),
        W(f"W14{i}c", "PI5_5V", f"E6{i}b.1", f"SW{61 + i}.LED+", "24",
          150, "case", "red", cable=f"C{20 + i} {b} button 4-core"),
        W(f"W14{i}d", f"LED_{b}_K", f"E6{i}b.2", f"SW{61 + i}.LED-",
          "24", 150, "case", "blue", cable=f"C{20 + i} {b} button 4-core"),
    ]

# the XT30 pairs on the ESC leads (named so the BOM and drawing show
# them; electrically they are inside W24-W27)
XT30 = [("J20", "XT30 (sockets)", "port ESC lead, harness side"),
        ("J21", "XT30 (sockets)", "starboard ESC lead, harness side"),
        ("J22", "XT30 (pins)", "port ESC input"),
        ("J23", "XT30 (pins)", "starboard ESC input")]

GLANDS = [("G1", "PG7", "Port motor cable C5 (Ø6)"),
          ("G2", "PG7", "Starboard motor cable C6 (Ø6)"),
          ("G3", "PG7", "Mast cable C3 (8-core Ø5.5)"),
          ("G4", "PG7", "Main switch cable C2 (2-core Ø4)")]


def pin_net() -> dict[str, str]:
    out: dict[str, str] = {}
    for n, pins in NETS.items():
        for p in pins:
            out[p] = n
    return out

# ======================================================================
# Items with no pins of their own, for the BOM. (ref, description, qty,
# £ each, KCL BOM line it falls under or "new", stock: common workshop
# stock the owner may already hold)
# ======================================================================
EXTRAS = [
    ("J20-J23", "XT30 pairs on the ESC leads", 2, 0.8, "new", False),
    ("HS1-2", "Clip-on TO-220 heatsink, ≤ 21 K/W", 2, 0.5, "new", False),
    ("SB1", "Stripboard 100 × 160 mm (PIB, MIB, PNL cut from it)", 1,
     3.0, "new", True),
    ("C1-C11", "Cables: 8-core 0.25 mm² 1 m, 3-core 0.75 mm² 1.5 m, "
     "2-core 0.5 m", 1, 5.0, "new", False),
    ("WIRE", "Silicone wire 16/18/20/26 AWG, heat-shrink, tinned "
     "copper 1.5 mm² for PIB bus strips", 1, 6.0, "new", True),
    ("KK", "Molex KK 254 housings and crimps (2, 3, 4, 6, 8-way)", 1, 3.0,
     "new", True),
    ("F1H", "Sealed inline ATO fuse holder, 16 AWG, + spare fuse", 1, 1.5,
     "Box, PG7 glands, fuse", False),
    ("RIB", "40-way IDC ribbon 150 mm and two IDC sockets (panel)", 1, 2.0,
     "new", False),
    ("STANDOFF", "M2.5 nylon stand-offs and screws (boards, Pi)", 1, 2.0,
     "new", True),
]

# The KCL BOM line each part's cost falls under ("new" = not in the SDR
# BOM). Parts not listed here are new.
KCL_LINE = {
    "U2": "Flight controller", "U9": "M10 GNSS", "U6": "Pi Zero 2W",
    "U7": "OV5647 camera", "M1": "2 × 2205", "M2": "2 × 2205",
    "U3": "2 × AM32", "U4": "2 × AM32", "BT1": "3 × tested 18650",
    "U1": "3 × tested 18650", "F1": "Box, PG7 glands, fuse",
    "U10": "Foam, hi-vis, WS2812B", "U5": "5 V 3 A buck",
    "SW2": "Reed switch", "Q2": "Reed switch", "SW1": "IP67 main power",
    "U8": "DS18B20", "U51": "USB Wi-Fi", "U52": "USB mic",
    "U53": "USB mic", **{f"SW6{i}": "4 arcade buttons" for i in
                         range(1, 5)},
}
