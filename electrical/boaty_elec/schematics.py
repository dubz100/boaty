"""Schematic sheets, drawn with schemdraw from design.py.

Every pin drawn takes its net name from the netlist: a pin is either
tagged with its net, grounded (GND / PI5_GND), or wired to another pin,
and a wire is only drawn between pins the netlist puts on one net. So a
sheet cannot disagree with the netlist; check() then proves every part
and every pin appears on some sheet.
"""
from __future__ import annotations

from collections import defaultdict

import schemdraw
import schemdraw.elements as elm

from . import design as DS

schemdraw.use("matplotlib")
PN = DS.pin_net()
SHOWN: dict[str, set] = defaultdict(set)       # ref -> pins shown
ON_SHEET: dict[str, set] = defaultdict(set)    # sheet -> refs
FONT = 8.5


class Sheet:
    def __init__(self, sid: str, title: str):
        self.sid, self.title = sid, title
        self.d = schemdraw.Drawing(show=False)
        self.d.config(fontsize=FONT, unit=2.0, lw=1.1)

    # -------------------------------------------------------------- pins
    def _mark(self, refpin: str):
        ref, pin = refpin.split(".")
        assert ref in DS.PARTS and pin in DS.PARTS[ref].pins, refpin
        SHOWN[ref].add(pin)
        ON_SHEET[self.sid].add(ref)

    def tag(self, refpin: str, p, side: str = "right", length=0.6):
        """Stub from p and a net tag (ground symbol for ground nets)."""
        self._mark(refpin)
        net = PN.get(refpin)
        if net is None:
            self.d.add(elm.NoConnect().at(p))
            return
        dx = {"right": (length, 0), "left": (-length, 0),
              "up": (0, length), "down": (0, -length)}[side]
        q = (p[0] + dx[0], p[1] + dx[1])
        self.d.add(elm.Line().at(p).to(q))
        if net == "GND":
            self.d.add(elm.Ground().at(q))
        elif net == "PI5_GND":
            self.d.add(elm.GroundChassis().at(q))
        else:
            # tags always read horizontally
            t = elm.Tag(d="left" if side == "left" else "right").at(q)
            self.d.add(t.label(net, fontsize=6.8))

    def wire(self, pa, pb, *refpins, shape="-|"):
        nets = {PN.get(r) for r in refpins}
        assert len(nets) == 1 and None not in nets, (refpins, nets)
        for r in refpins:
            self._mark(r)
        if pa[0] == pb[0] or pa[1] == pb[1]:
            self.d.add(elm.Line().at(pa).to(pb))
        else:
            self.d.add(elm.Wire(shape).at(pa).to(pb))

    def dot(self, p):
        self.d.add(elm.Dot().at(p))

    def text(self, p, s, size=FONT, **kw):
        self.d.add(elm.Label().at(p).label(s, fontsize=size, **kw))

    # -------------------------------------------------------------- parts
    def two(self, ref: str, pa: str, pb: str, p1, p2, loc="top",
            extra=""):
        """A two-terminal part from p1 (pin pa) to p2 (pin pb)."""
        part = DS.PARTS[ref]
        v = part.value
        if ref.startswith("R"):
            e = elm.Resistor()
        elif ref.startswith("C"):
            e = elm.Capacitor(polar="+" in part.pins)
        elif ref.startswith("F") and "PTC" in v:
            e = elm.Fuse()
        elif ref.startswith("F"):
            e = elm.Fuse()
        elif ref.startswith("D") and v.startswith("P6KE"):
            e = elm.DiodeTVS()
        elif ref.startswith("D") and v.startswith("BZX"):
            e = elm.Zener()
        elif ref.startswith("D"):
            e = elm.Diode()
        elif "Reed" in v:
            e = elm.SwitchReed()
        elif ref.startswith("SW"):
            e = elm.Switch()
        else:
            e = elm.Line()
        self.d.add(e.endpoints(p1, p2).label(f"{ref}\n{v}{extra}",
                                             loc=loc, fontsize=7.2))
        self._mark(f"{ref}.{pa}")
        self._mark(f"{ref}.{pb}")
        return p1, p2

    def fet(self, ref: str, source, gate_left=False, flip=False):
        """P-FET: source at the given point, drain below, gate right.
        N-FET: source at the point, drain above."""
        part = DS.PARTS[ref]
        E = elm.PFet if part.value in ("P-MOSFET",) else elm.NFet
        e = E().right().anchor("source").at(source)
        if gate_left:
            e = e.reverse()
        if flip:
            e = e.flip()
        e = self.d.add(e.label(f"{ref}\n{part.value}", fontsize=7.2,
                               loc="right" if gate_left else "left"))
        for p in ("G", "D", "S"):
            self._mark(f"{ref}.{p}")
        a = e.absanchors
        return {"S": tuple(a["source"]), "D": tuple(a["drain"]),
                "G": tuple(a["gate"])}

    def box(self, ref: str, x, y, left=(), right=(), w=4.0, pitch=0.8,
            title=None, sub=""):
        """A module or connector as a box. left/right: pin names, top to
        bottom. Returns pin name -> end of its stub."""
        part = DS.PARTS[ref]
        n = max(len(left), len(right), 1)
        h = pitch * (n + 0.6)
        for a, b in (((x, y), (x + w, y)), ((x + w, y), (x + w, y - h)),
                     ((x + w, y - h), (x, y - h)), ((x, y - h), (x, y))):
            self.d.add(elm.Line().at(a).to(b))
        self.text((x + w / 2, y + 0.35), title or f"{ref}  {part.value}",
                  size=7.6)
        if sub:
            self.text((x + w / 2, y - h - 0.35), sub, size=6.5)
        pts = {}
        for side, names in (("L", left), ("R", right)):
            for i, pn in enumerate(names):
                yy = y - pitch * (i + 1)
                xx = x if side == "L" else x + w
                q = (xx - 0.5, yy) if side == "L" else (xx + 0.5, yy)
                self.d.add(elm.Line().at((xx, yy)).to(q))
                lab = part.pins[pn].label or pn
                if len(lab) > 20:
                    lab = pn
                self.text((xx + (0.15 if side == "L" else -0.15), yy),
                          lab if len(lab) < 22 else lab[:21], size=6.2,
                          halign="left" if side == "L" else "right")
                pts[pn] = q
        return pts

    def save(self, path_stem):
        self.text((0, 3.2), f"{self.sid}  {self.title}", size=11,
                  halign="left")
        self.d.save(f"{path_stem}.pdf")
        self.d.save(f"{path_stem}.png", dpi=170)
        self.d.save(f"{path_stem}.svg")


# ======================================================================
def sheet_power() -> Sheet:
    s = Sheet("S1", "Power: pack, main path, supplies (PWR-1..4)")
    # pack: cells as a box, BMS, fuse, XT60, balance lead
    bt = s.box("BT1", 0, 0, right=["P", "T2", "T1", "N"], w=3.2,
               sub="3 × 18650, accepted to PWR-D20")
    bms = s.box("U1", 6, 0, left=["B+", "B2", "B1", "B-"], right=["P-"],
                w=3.4, sub="OCP ≤ 25 A, ODV 2.5-2.8 V/cell")
    for p in ("P", "T2", "T1", "N"):
        q = {"P": "B+", "T2": "B2", "T1": "B1", "N": "B-"}[p]
        s.wire(bt[p], bms[q], f"BT1.{p}", f"U1.{q}")
    j2 = s.box("J2", 6, -5.2, left=["4", "3", "2", "1"], w=3.4,
               sub="charger only (PWR-D04)")
    for p, q in (("4", "P"), ("3", "T2"), ("2", "T1"), ("1", "N")):
        s.tag(f"J2.{p}", j2[p], "left")
    # fuse from B+ (P+) to the XT60
    s.two("F1", "1", "2", (bms["B+"][0], 1.6), (13.5, 1.6),
          extra="  ≤ 50 mm from P+")
    s.wire(bms["B+"], (bms["B+"][0], 1.6), "U1.B+", "F1.1")
    j1 = s.box("J1", 14.5, 2.4, left=["1", "2"], right=["1", "2"], w=2.4,
               title="J1 XT60 (pack)", sub="plugs into J3")
    s.wire((13.5, 1.6), j1["1"], "F1.2", "J1.1")
    s.wire(bms["P-"], j1["2"], "U1.P-", "J1.2")
    j3 = s.box("J3", 19.0, 2.4, left=["1", "2"], right=["1", "2"], w=2.4,
               title="J3 XT60 (box)")
    s.wire((17.4, 1.6), j3["1"], "J1.1", "J3.1")
    s.wire((17.4, 0.8), j3["2"], "J1.2", "J3.2")
    s.tag("J3.1", (21.9, 1.6), "right")
    s.tag("J3.2", (21.9, 0.8), "right", 0.4)
    s.text((21, -1.4), "PACK_POS → PIB E1 (S2); GND → PDB BAT−", size=6.5)
    # PDB power pins
    pdb = s.box("U2", 29, 2.4, left=["BAT+", "BAT-"], right=["VBO+",
                                                            "VBO-"],
                w=5.5, title="U2 PDB (SpeedyBee F405 WING APP)",
                sub="current sensor → BATT_VOLT_PIN 10, BATT_CURR_PIN 11")
    s.tag("U2.BAT+", pdb["BAT+"], "left")
    s.tag("U2.BAT-", pdb["BAT-"], "left")
    s.tag("U2.VBO+", pdb["VBO+"], "right")
    s.tag("U2.VBO-", pdb["VBO-"], "right")
    # buck
    bk = s.box("U5", 26, -3.2, left=["VIN", "GI"], right=["VOUT", "GO"],
               w=5.5, sub="5.1 V ≥ 3 A (IF-08)")
    s.tag("U5.VIN", bk["VIN"], "left")
    s.tag("U5.GI", bk["GI"], "left")
    s.tag("U5.GO", bk["GO"], "right")
    j30 = s.box("J30", 35, -3.2, left=["1", "2"], w=3.0,
                sub="Micro-Fit → MIB (S5)")
    s.wire(bk["VOUT"], j30["1"], "U5.VOUT", "J30.1")
    s.tag("J30.2", j30["2"], "left", 0.01)
    # ESC supplies with their bulk capacitors
    for i, (esc, cap) in enumerate((("U3", "C7"), ("U4", "C8"))):
        x = 26 + 12 * i
        e = s.box(esc, x, -8.2, left=["V+", "V-"], w=4.5,
                  sub="XT30 on the lead (J20-J23)")
        s.tag(f"{esc}.V-", e["V-"], "down", 0.3)
        s.two(cap, "+", "-", (x - 2.2, -9.0), (x - 2.2, -11.2), loc="bottom")
        s.wire((x - 2.2, -9.0), e["V+"], f"{cap}.+", f"{esc}.V+")
        s.tag(f"{cap}.-", (x - 2.2, -11.2), "down", 0.3)
        s.tag(f"{esc}.V+", (x - 2.2, -9.0), "up", 0.8)
    s.text((13, -14.5), "Power path (bold nets carry motor current):\n"
           "BATT_POS → F1 → PACK_POS → Q1 (PIB) → BUS_POS → PDB sensor → "
           "VBAT_S\n→ Q2 key switch (PIB) → MOTOR_POS → ESCs; "
           "VBAT_S → F2 PTC → BUCK_IN → buck", size=6.8, halign="center")
    return s


def _hs_switch(s: Sheet, q: str, rgs: str, dz: str, rdiv: str, cm: str,
               x: float, y: float):
    """A high-side P-FET switch: source at (x, y), gate network to the
    right. Returns (gate node, divider far end)."""
    f = s.fet(q, (x, y))
    s.tag(f"{q}.S", f["S"], "left", 0.8)
    s.tag(f"{q}.D", f["D"], "left", 0.8)
    xr, xz = x + 3.2, x + 5.0
    gy = y - 3.0
    s.two(rgs, "1", "2", (xr, y), (xr, gy))
    s.two(dz, "K", "A", (xz, y), (xz, gy))
    s.wire(f["S"], (xz, y), f"{q}.S", f"{rgs}.1", f"{dz}.K")
    s.wire(f["G"], (xr, gy), f"{q}.G", f"{rgs}.2", shape="|-")
    s.wire((xr, gy), (xz, gy), f"{rgs}.2", f"{dz}.A")
    s.dot((xr, gy))
    g = (xz, gy)
    s.two(cm, "2", "1", (x + 1.37, gy - 0.001), (x + 1.37, gy - 2.8),
          loc="bottom", extra="\ngate→drain")
    s.tag(f"{cm}.1", (x + 1.37, gy - 2.8), "left", 0.5)
    s.two(rdiv, "1", "2", g, (g[0] + 3.4, g[1]))
    s.dot(g)
    return g, (g[0] + 3.4, g[1])


def sheet_pib() -> Sheet:
    s = Sheet("S2", "Power and interconnect board (PIB): main switch, "
              "key switch, bleeder, rail sense")
    # --- main switch Q1 and its TVS
    g1, sw = _hs_switch(s, "Q1", "R1", "D1", "R2", "C1", 3, 0)
    s.tag("R2.2", sw, "right", 0.4)
    s.two("D2", "K", "A", (0, -5.5), (0, -8.0))
    s.tag("D2.K", (0, -5.5), "right", 0.4)
    s.tag("D2.A", (0, -8.0), "down", 0.3)
    j11 = s.box("J11", 17, -1.9, left=["1", "2"], w=2.6,
                sub="→ SW1 (handle, cable C2, G4)")
    s.tag("J11.1", j11["1"], "left")
    s.tag("J11.2", j11["2"], "left", 0.3)
    sw1 = s.box("SW1", 25, -1.9, left=["1", "2"], w=3.0,
                title="SW1 IP67 toggle", sub="flip cover")
    s.tag("SW1.1", sw1["1"], "left")
    s.tag("SW1.2", sw1["2"], "left", 0.3)
    # --- key switch Q2 and its TVS
    y2 = -12.0
    g2, kn = _hs_switch(s, "Q2", "R3", "D3", "R4", "C2", 3, y2)
    s.two("D5", "K", "A", (0, y2 - 5.5), (0, y2 - 8.0))
    s.tag("D5.K", (0, y2 - 5.5), "right", 0.4)
    s.tag("D5.A", (0, y2 - 8.0), "down", 0.3)
    j12 = s.box("J12", 19, y2 + 1.4, left=["1", "2", "3"], w=2.6,
                sub="→ SW2 reed (box, under the key dock)")
    s.wire(kn, j12["1"], "R4.2", "J12.1")
    s.tag("J12.2", j12["2"], "left", 0.01)
    s.tag("J12.3", j12["3"], "left", 0.3)
    sw2 = s.box("SW2", 27, y2 + 1.4, left=["1", "2"], w=3.0,
                title="SW2 reed (NO)")
    s.tag("SW2.1", sw2["1"], "left")
    s.tag("SW2.2", sw2["2"], "left", 0.3)
    # --- bleeder: C3 couples the KEY_N edge to Q3's gate
    s.dot(kn)
    s.two("C3", "1", "2", (kn[0], kn[1] - 0.001), (kn[0], kn[1] - 3.0))
    gq = (kn[0], kn[1] - 3.0)
    s.dot(gq)
    s.two("R5", "1", "2", gq, (gq[0], gq[1] - 3.0))
    s.tag("R5.2", (gq[0], gq[1] - 3.0), "down", 0.3)
    s.two("D4", "K", "A", (gq[0] - 2.0, gq[1]), (gq[0] - 2.0,
                                                 gq[1] - 3.0))
    s.tag("D4.A", (gq[0] - 2.0, gq[1] - 3.0), "down", 0.3)
    s.wire((gq[0] - 2.0, gq[1]), gq, "D4.K", "C3.2")
    q3 = s.fet("Q3", (gq[0] + 5.0, gq[1] - 3.2), gate_left=True)
    s.wire(gq, q3["G"], "C3.2", "Q3.G", shape="-|")
    s.tag("Q3.S", q3["S"], "down", 0.3)
    s.two("R9", "2", "1", q3["D"], (q3["D"][0], q3["D"][1] + 3.0),
          extra=" 2 W")
    s.tag("R9.1", (q3["D"][0], q3["D"][1] + 3.0), "right", 0.4)
    # --- rail sense
    rs = (36, y2 - 1.5)
    s.tag("R6.1", rs, "left", 0.5)
    s.two("R6", "1", "2", rs, (rs[0], rs[1] - 3))
    s.two("R7", "1", "2", (rs[0], rs[1] - 3), (rs[0], rs[1] - 6))
    s.tag("R7.2", (rs[0], rs[1] - 6), "down", 0.3)
    s.two("C4", "1", "2", (rs[0] + 2.2, rs[1] - 3), (rs[0] + 2.2,
                                                     rs[1] - 6))
    s.wire((rs[0], rs[1] - 3), (rs[0] + 2.2, rs[1] - 3), "R6.2", "R7.1",
           "C4.1")
    s.dot((rs[0], rs[1] - 3))
    s.tag("C4.2", (rs[0] + 2.2, rs[1] - 6), "down", 0.3)
    e7 = s.box("E7", rs[0] + 4.2, rs[1] - 2.2, left=["1"], w=2.6,
               title="E7 → FC AIR")
    s.wire((rs[0] + 2.2, rs[1] - 3), e7["1"], "C4.1", "E7.1")
    s.dot((rs[0] + 2.2, rs[1] - 3))
    # --- buck feed and the heavy pads
    s.two("F2", "1", "2", (33, -1.0), (33, -4.0))
    s.tag("F2.1", (33, -1.0), "right", 0.4)
    s.tag("F2.2", (33, -4.0), "right", 0.4)
    for i, e in enumerate(("E1", "E2", "E3", "E4", "E5", "E6")):
        pts = s.box(e, 38 + (i // 3) * 7, 1.0 - 2.4 * (i % 3),
                    right=["1"], w=2.4, title=f"{e} pad")
        s.tag(f"{e}.1", pts["1"], "right", 0.4)
    s.text((20, y2 - 12.8), "Key out: R3 holds Q2 off (fails safe); the "
           "rising KEY_N pulses Q3 on through C3 for ≈ 0.2 s and R9 "
           "empties the ESC capacitors (rail < 0.5 V in 58 ms).\n"
           "Key in: the reed pulls the gate through R4; C2 from gate to "
           "drain sets the rail's rise (inrush ≤ 6 A). Q1 works the same "
           "way from the main switch.", size=6.8)
    return s


def sheet_helm() -> Sheet:
    s = Sheet("S3", "Helm, GNSS and beacon (IF-04, IF-05, IF-06, IF-09, "
              "IF-22)")
    fc = s.box("U2", 0, 0, right=["TX3", "RX3", "4V5", "GGPS", "SCL",
                                  "SDA", "5V", "LED", "AIR", "GAIR",
                                  "TX1", "RX1", "GU1", "S1", "G1", "S4",
                                  "G4"], w=6.5, pitch=0.9,
               title="U2 SpeedyBee F405 WING APP (helm)",
               sub="SERIAL1 MAVLink, SERIAL3 GPS, output 12 NeoPixel, "
                   "BATT2 on ADC 15")
    for p in ("AIR", "GAIR", "TX1", "RX1", "GU1", "S1", "G1", "S4",
              "G4"):
        s.tag(f"U2.{p}", fc[p], "right")
    j15 = s.box("J15", 10, 0, left=["3", "4", "1", "2", "5", "6"], w=2.6,
                pitch=0.9, title="J15 KK254 6 (PIB)")
    for fp_, jp in (("TX3", "3"), ("RX3", "4"), ("4V5", "1"),
                    ("GGPS", "2"), ("SCL", "5"), ("SDA", "6")):
        s.wire(fc[fp_], j15[jp], f"U2.{fp_}", f"J15.{jp}")
    j14 = s.box("J14", 16, 0, left=["3", "4", "1", "2", "5", "6", "7",
                                    "8"], right=["3", "4", "1", "2", "5",
                                                 "6", "7", "8"],
                w=2.6, pitch=0.9, sub="PIB: J14 and J15 share strips pin for pin")
    for jp in ("3", "4", "1", "2", "5", "6"):
        s.wire(j15[jp] if False else (12.6 + 0.5, j15[jp][1]), j14[jp],
               f"J15.{jp}", f"J14.{jp}")
    # LED path on the PIB
    s.wire(fc["5V"], (7.5, fc["5V"][1]), "U2.5V", "E8.1")
    e8 = (7.5, fc["5V"][1])
    s._mark("E8.1")
    s.two("D6", "A", "K", (9.0, fc["5V"][1] - 0.001), (14.5, fc["5V"][1]
                                                       - 0.001),
          extra="  (≈ 0.8 V drop)")
    s.wire(e8, (9.0, fc["5V"][1] - 0.001), "E8.1", "D6.A")
    s.wire((14.5, fc["5V"][1] - 0.001), j14["7"], "D6.K", "J14.7")
    s.wire(fc["LED"], (7.5, fc["LED"][1]), "U2.LED", "E9.1")
    s.two("R8", "1", "2", (9.0, fc["LED"][1] - 0.001),
          (14.5, fc["LED"][1] - 0.001), loc="bottom")
    s.wire((7.5, fc["LED"][1]), (9.0, fc["LED"][1] - 0.001), "E9.1",
           "R8.1")
    s.wire((14.5, fc["LED"][1] - 0.001), j14["8"], "R8.2", "J14.8")
    # handle socket, mast plug, masthead
    j40 = s.box("J40", 22, 0, left=["3", "4", "1", "2", "5", "6", "7",
                                    "8"], w=2.8, pitch=0.9,
                title="J40 M12 socket", sub="handle; cable C3 via G3")
    for jp in ("3", "4", "1", "2", "5", "6", "7", "8"):
        s.wire(j14[jp], j40[jp], f"J14.{jp}", f"J40.{jp}")
    p40 = s.box("P40", 27, 0, left=["3", "4", "1", "2", "5", "6", "7",
                                    "8"], right=["3", "4", "1", "2", "5",
                                                 "6", "7", "8"], w=2.8,
                pitch=0.9, title="P40 M12 plug", sub="mast lead C4")
    for jp in ("3", "4", "1", "2", "5", "6", "7", "8"):
        s._mark(f"J40.{jp}")
        s._mark(f"P40.{jp}")
    s.text((25.6, -8.2), "⇄", size=12)
    u9 = s.box("U9", 34, 0, left=["RX", "TX", "5V", "GND", "SCL", "SDA"],
               w=3.6, pitch=0.9, sub="M10 + QMC5883L (0x0D)")
    for pp, jp in (("RX", "3"), ("TX", "4"), ("5V", "1"), ("GND", "2"),
                   ("SCL", "5"), ("SDA", "6")):
        s.wire(p40[jp], u9[pp], f"P40.{jp}", f"U9.{pp}")
    u10 = s.box("U10", 34, -8.2, left=["5V", "DIN", "GND"], w=3.6,
                pitch=0.9, sub="WS2812B × 8 (≤ 250 mA)")
    s.wire(p40["7"], u10["5V"], "P40.7", "U10.5V")
    s.wire(p40["8"], u10["DIN"], "P40.8", "U10.DIN")
    s.tag("U10.GND", u10["GND"], "left")
    s.text((20, -13), "I²C over ≈ 0.9 m: rise time 0.56 µs with 4.7 kΩ "
           "pull-ups (Standard mode OK; Fast mode needs ≤ 2.2 kΩ: bench "
           "check). GNSS ≥ 150 mm from power wiring (MEC-013).", size=6.6)
    return s


def sheet_prp() -> Sheet:
    s = Sheet("S4", "Propulsion: ESC signals and motor phases (IF-05, "
              "IF-17, PRP-3)")
    for i, (esc, sig, gnd_, jd, pd, m) in enumerate((
            ("U3", "S1", "G1", "J50", "P50", "M1"),
            ("U4", "S4", "G4", "J51", "P51", "M2"))):
        y = -7.5 * i
        e = s.box(esc, 6, y, left=["SIG", "SG"], right=["A", "B", "C"],
                  w=4.5, title=f"{esc} AM32 20 A ({'port' if i == 0 else 'starboard'})",
                  sub="3D mode; LVC off (KF-08)")
        f = s.box("U2", 0, y, right=[sig, gnd_], w=3.0,
                  title=f"U2 output {sig[1:]}", sub="DShot300")
        s.wire(f[sig], e["SIG"], f"U2.{sig}", f"{esc}.SIG")
        s.wire(f[gnd_], e["SG"], f"U2.{gnd_}", f"{esc}.SG")
        s.text((3.8, y - 2.6), "twisted pair ≤ 150 mm", size=6.4)
        dj = s.box(jd, 15, y, left=["1", "2", "3"], w=3.0,
                   title=f"{jd} IP68 (deck)", sub=f"cable C{5 + i} via G{1 + i}")
        dp = s.box(pd, 20, y, left=["1", "2", "3"], right=["1", "2", "3"],
                   w=3.0, title=f"{pd} IP68 (pod)")
        mm = s.box(m, 26, y, left=["A", "B", "C"], w=3.2,
                   title=f"{m} 2205", sub="flooded outrunner")
        for k, ph in enumerate("ABC"):
            s.wire(e[ph], dj[str(k + 1)], f"{esc}.{ph}", f"{jd}.{k + 1}")
            s._mark(f"{pd}.{k + 1}")
            s.wire(dp[str(k + 1)] if False else (23.5, dp[str(k + 1)][1]),
                   mm[ph], f"{pd}.{k + 1}", f"{m}.{ph}")
        s.text((18.9, y - 1.6), "⇄", size=12)
    return s


def sheet_mcp() -> Sheet:
    s = Sheet("S5", "Mission computer and its interface board (MIB): "
              "IF-03, IF-04, IF-08, MCP-D03/D26")
    j31 = s.box("J31", 0, 0, left=["1", "2"], w=2.6,
                sub="⇄ J30 from the buck (S1)")
    s.tag("J31.1", j31["1"], "left")
    s.tag("J31.2", j31["2"], "left")
    s._mark("J30.1")
    s._mark("J30.2")
    x = 5
    s.two("D10", "K", "A", (x, 0.2), (x, -2.4))
    s.two("C10", "+", "-", (x + 2, 0.2), (x + 2, -2.4))
    s.two("C11", "1", "2", (x + 4, 0.2), (x + 4, -2.4))
    s.wire((x, 0.2), (x + 4, 0.2), "D10.K", "C10.+", "C11.1")
    s.tag("C11.1", (x + 4, 0.2), "up", 0.3)
    for r in ("D10.A", "C10.-", "C11.2"):
        xx = {"D10.A": x, "C10.-": x + 2, "C11.2": x + 4}[r]
        s.tag(r, (xx, -2.4), "down", 0.3)
    hdr = s.box("J32", 13, 0, left=["2", "4", "6", "9", "14", "1", "7",
                                    "8", "10", "11"], w=3.4, pitch=0.9,
                title="J32 ⇄ Pi Zero header", sub="used pins only")
    for p in ("2", "4", "6", "9", "14", "1", "7", "8", "10", "11"):
        s.tag(f"J32.{p}", hdr[p], "left")
    pi = s.box("U6", 20, 0, right=["2", "4", "6", "9", "14", "1", "7",
                                   "8", "10", "11", "CSI"], w=5.0,
               pitch=0.9, title="U6 Raspberry Pi Zero 2 W",
               sub="dtoverlay=disable-bt, w1-gpio (GPIO4)")
    for p in ("2", "4", "6", "9", "14", "1", "7", "8", "10", "11"):
        s._mark(f"U6.{p}")
    s.text((18.1, -5), "⇄", size=12)
    cam = s.box("U7", 30, -8.6, left=["CSI"], w=3.6, sub="OV5647, ribbon")
    s.wire(pi["CSI"], cam["CSI"], "U6.CSI", "U7.CSI")
    # UART to the helm
    j33 = s.box("J33", 30, 0, left=["1", "2", "3"], w=2.6,
                sub="→ U2 RX1/TX1/G (C9)")
    for p in ("1", "2", "3"):
        s.tag(f"J33.{p}", j33[p], "left")
    s._mark("U2.RX1")
    s._mark("U2.TX1")
    # 1-Wire
    s.two("R10", "1", "2", (x, -6), (x, -9))
    s.tag("R10.1", (x, -6), "up", 0.3)
    s.tag("R10.2", (x, -9), "down", 0.3)
    j34 = s.box("J34", 0, -6, left=["1", "2", "3", "4"], w=2.6,
                sub="→ U8 DS18B20 (box top)")
    for p in ("1", "2", "3", "4"):
        s.tag(f"J34.{p}", j34[p], "left")
    u8 = s.box("U8", 30, -12.5, left=["VDD", "DQ", "GND"], w=3.0)
    for p in ("VDD", "DQ", "GND"):
        s.tag(f"U8.{p}", u8[p], "left")
    # moisture
    j35 = s.box("J35", 0, -11.5, left=["1", "2"], w=2.6,
                sub="→ S2 comb (box low point)")
    s.tag("J35.1", j35["1"], "left")
    s.tag("J35.2", j35["2"], "left")
    s.two("R11", "1", "2", (x + 1.0, -12.3), (x + 4.5, -12.3))
    s.tag("R11.1", (x + 1.0, -12.3), "left", 0.3)
    s.two("R12", "2", "1", (x + 4.5, -12.3), (x + 4.5, -9.8))
    s.tag("R12.1", (x + 4.5, -9.8), "up", 0.3)
    s.two("C12", "1", "2", (x + 6.5, -12.3), (x + 6.5, -15))
    s.wire((x + 4.5, -12.3), (x + 6.5, -12.3), "R11.2", "R12.2", "C12.1")
    s.dot((x + 4.5, -12.3))
    s.tag("C12.1", (x + 6.5, -12.3), "right", 0.4)
    s.tag("C12.2", (x + 6.5, -15), "down", 0.3)
    s2 = s.box("S2", 30, -17, left=["A", "B"], w=3.0,
               sub="wet < 10.7 kΩ → GPIO17 low")
    s.tag("S2.A", s2["A"], "left")
    s.tag("S2.B", s2["B"], "left")
    return s


def sheet_mcn() -> Sheet:
    s = Sheet("S6", "Mission Control: Raspberry Pi 5 and the panel board "
              "(IF-12, MCN-1)")
    pins = ["1", "2", "6", "9", "14"] + [p for b in DS.BUTTONS
                                         for p in (b[3], b[5])]
    pi = s.box("U50", 0, 0, right=pins + ["USBC", "USB1", "USB2", "USB3",
                                          "USB4"], w=5.5, pitch=0.8,
               title="U50 Raspberry Pi 5", sub="IF-12 GPIO (BCM)")
    for p in ("USBC", "USB1", "USB2", "USB3", "USB4"):
        s.tag(f"U50.{p}", pi[p], "right", 0.4)
    bank = s.box("BT50", 0, -25.0, right=["USBC"], w=4.0,
                 sub="20 Ah, 5 V 3 A")
    s.tag("BT50.USBC", bank["USBC"], "right", 0.4)
    for i, u in enumerate(("U51", "U52", "U53", "U54")):
        b = s.box(u, 8.5, -16.0 - 2.4 * i, left=["USB"], w=4.2, pitch=0.8)
        s.tag(f"{u}.USB", b["USB"], "left", 0.4)
    hdr = s.box("J60", 9, 0, left=pins, w=3.0, pitch=0.8,
                title="J60 panel header", sub="40-way ribbon")
    for p in pins:
        s.wire(pi[p], hdr[p], f"U50.{p}", f"J60.{p}")
    s.text((10.5, -12.0), "J60 carries each GPIO to its channel\n(net "
           "names: BTN_x, LED_x, PI5_3V3, PI5_5V)", size=6.4)
    for i, (b, colour, g, p, lg, lp) in enumerate(DS.BUTTONS):
        x = 18 + 11.0 * i
        y = 1.0
        rpu, rs = f"R{61 + 10 * i}", f"R{62 + 10 * i}"
        c, q = f"C{61 + i}", f"Q{61 + i}"
        rg, rpd = f"R{63 + 10 * i}", f"R{64 + 10 * i}"
        sw, ea, eb = f"SW{61 + i}", f"E6{i}a", f"E6{i}b"
        s.text((x + 2.5, y + 1.4), f"{b} ({colour}): GPIO{g} in, "
               f"GPIO{lg} LED", size=7.6)
        # input: pull-up, series R, filter C, switch pads
        s.tag(f"{rpu}.1", (x, y), "right", 0.3)
        s.two(rpu, "1", "2", (x, y), (x, y - 2.5))
        sw_n = (x, y - 2.5)
        s.dot(sw_n)
        s.two(rs, "1", "2", sw_n, (x + 3, y - 2.5))
        s.dot((x + 3, y - 2.5))
        s.tag(f"{rs}.2", (x + 3, y - 2.5), "right", 0.6)
        s.two(c, "1", "2", (x + 3, y - 2.5001), (x + 3, y - 4.8))
        s.tag(f"{c}.2", (x + 3, y - 4.8), "down", 0.3)
        pa = s.box(ea, x + 0.6, y - 4.2, left=["1", "2"], w=1.4, pitch=0.8,
                   title=ea)
        s.wire(sw_n, pa["1"], f"{rpu}.2", f"{ea}.1", shape="|-")
        s.tag(f"{ea}.2", pa["2"], "left", 0.3)
        # the arcade button (wired to the pads)
        swb = s.box(sw, x + 0.6, y - 7.4, right=["NO", "C", "LED+",
                                                 "LED-"],
                    w=2.4, pitch=0.9, title=f"{sw} ({colour})")
        for pp in ("NO", "C", "LED+", "LED-"):
            s.tag(f"{sw}.{pp}", swb[pp], "right", 0.3)
        # LED driver: gate R, pull-down, 2N7000, LED pads
        yl = y - 13.0
        s.tag(f"{rg}.1", (x + 0.2, yl), "right", 0.01)
        s.two(rg, "1", "2", (x + 2.0, yl), (x + 4.5, yl))
        s.d.add(elm.Line().at((x + 1.9, yl)).to((x + 2.0, yl)))
        s.dot((x + 4.5, yl))
        s.two(rpd, "1", "2", (x + 4.5, yl - 0.001), (x + 4.5, yl - 2.6),
              loc="bottom")
        s.tag(f"{rpd}.2", (x + 4.5, yl - 2.6), "down", 0.3)
        qq = s.fet(q, (x + 7.0, yl - 3.2), gate_left=True)
        s.wire((x + 4.5, yl), qq["G"], f"{rg}.2", f"{q}.G", shape="-|")
        s.tag(f"{q}.S", qq["S"], "down", 0.3)
        pb = s.box(eb, x + 7.4, yl + 1.2, left=["2"], right=["1"], w=1.2,
                   pitch=0.8, title=eb)
        s.wire(qq["D"], pb["2"], f"{q}.D", f"{eb}.2", shape="|-")
        s.tag(f"{eb}.1", pb["1"], "right", 0.3)
    s.text((30, -21.5), "Buttons: pull-up 10 k + 1 k series + 100 nF; "
           "software debounce 30 ms. LEDs: 5 V arcade LEDs switched low "
           "by 2N7000 (gate 100 Ω, 100 k pull-down: off at boot).",
           size=6.8)
    return s


SHEETS = [sheet_power, sheet_pib, sheet_helm, sheet_prp, sheet_mcp,
          sheet_mcn]


def build(out_stem_dir) -> list[tuple[str, str]]:
    SHOWN.clear()
    ON_SHEET.clear()
    made = []
    for f in SHEETS:
        s = f()
        name = s.title.split(":")[0].replace(" ", "_").replace(",", "")
        stem = f"{out_stem_dir}/{s.sid}_{name}"
        s.save(stem)
        made.append((s.sid, s.title, stem))
    return made


def check() -> list[str]:
    errs = []
    for ref, part in DS.PARTS.items():
        missing = [p for p in part.pins if p not in SHOWN.get(ref, set())]
        if missing:
            errs.append(f"{ref}: pins not on any sheet {missing}")
    return errs
