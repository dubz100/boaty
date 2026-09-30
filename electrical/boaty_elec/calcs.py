"""Circuit calculations for BOATY-EDD-001. Every result the EDD quotes
comes from here; run() returns them as one dict.

Values marked EST in design.py are candidates: the calculation shows what
a part must achieve, and the bench checks the real one.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from . import design as DS

ROOT = Path(__file__).resolve().parents[2]

# copper resistance (mΩ/m, 20 °C) and a conservative ampacity for
# silicone-insulated wire bundled in a closed box (A)
AWG = {"16": (13.2, 22.0), "18": (21.0, 16.0), "20": (33.3, 11.0),
       "22": (53.0, 7.0), "24": (84.2, 3.5), "26": (134.0, 2.2),
       "0.25 mm²": (78.0, 3.0)}
R_XT60, R_XT30, R_MICROFIT = 0.0005, 0.001, 0.003     # per mated pair, Ω
T_BOX = 50.0                    # box air, worst case (PWR-D19 limit)


def P(ref):
    return DS.PARTS[ref]


def wire_r(wid: str) -> float:
    w = next(x for x in DS.WIRES if x.id == wid)
    return AWG[w.gauge][0] * w.length / 1000 / 1000


# ----------------------------------------------------------------------
def harness_resistance() -> dict:
    """Series resistance of the power path, battery terminals to ESC."""
    rq = P("Q1").rating["rds"]
    up = {"fuse F1": P("F1").rating["r"], "BMS lead W01+W02":
          wire_r("W01") + wire_r("W02"), "XT60": R_XT60,
          "box lead W20": wire_r("W20"), "Q1 main switch": rq,
          "PIB to PDB W22": wire_r("W22"), "negative W03+W21":
          wire_r("W03") + wire_r("W21") + R_XT60 * 0,
          "PDB shunt": 0.0003}
    down = {"PDB to PIB W23": wire_r("W23"), "Q2 key switch": rq,
            "ESC lead W24 (+)": wire_r("W24"), "ESC lead W26 (−)":
            wire_r("W26"), "XT30": R_XT30}
    return dict(up=up, down=down, r_up=sum(up.values()),
                r_down=sum(down.values()))


def sag(p_limit: float, r_pack: float = 0.22, v_rest: float = 9.6,
        r_up: float = 0.0, r_down: float = 0.0) -> dict:
    """Operating point at the helm's power limit. BATT_WATT_MAX acts on
    the power the PDB sensor measures (V at the PDB × I), so solve
    V_pdb·I = P with V_pdb = V_rest − I·(R_pack + R_up)."""
    r = r_pack + r_up
    disc = v_rest ** 2 - 4 * r * p_limit
    if disc < 0:
        return dict(ok=False)
    i = (v_rest - math.sqrt(disc)) / (2 * r)
    v_pdb = v_rest - i * r
    v_esc = v_pdb - i * r_down
    return dict(ok=True, i=i, v_pdb=v_pdb, v_esc=v_esc)


def watt_limit_for(v_min: float, hr: dict) -> float:
    lo, hi = 20.0, 90.0
    for _ in range(60):
        mid = (lo + hi) / 2
        s = sag(mid, r_up=hr["r_up"], r_down=hr["r_down"])
        if s["ok"] and s["v_esc"] >= v_min:
            lo = mid
        else:
            hi = mid
    return lo


def _kcl():
    sys.path[:0] = [str(ROOT / "docs" / "common"),
                    str(ROOT / "docs" / "kcl" / "src"),
                    str(ROOT / "docs" / "add" / "src")]
    import kcl_data as K                                   # noqa: E402
    return K


# ----------------------------------------------------------------------
def gate_drive() -> dict:
    out = {}
    for q, ra, rb in (("Q1", "R1", "R2"), ("Q2", "R3", "R4")):
        r1, r2 = P(ra).rating["ohm"], P(rb).rating["ohm"]
        f = r1 / (r1 + r2)
        out[q] = {v: -v * f for v in (12.6, 10.8, 9.0, 7.5)}
    return out


def mosfet_heat(i_q1: float, i_q2: float) -> dict:
    """Dissipation and junction temperature at the continuous current.
    R_DS(on) is rated at V_GS −10 V; at −5.6 V (7.5 V pack) take 1.5×,
    and 1.5× again for a hot junction."""
    r = P("Q1").rating["rds"] * 1.5 * 1.5
    rth, rs = P("Q1").rating["rth_ja"], P("Q1").rating["rth_sink"]
    res = {}
    for q, i in (("Q1", i_q1), ("Q2", i_q2)):
        p = i * i * r
        res[q] = dict(i=i, p=p, tj_bare=T_BOX + p * rth,
                      tj=T_BOX + p * rs, r_hot=r)
    return res


# ----------------------------------------------------------------------
def _fet(k, vov, vds):
    if vov <= 0:
        return 0.0
    return k * (2 * vov * vds - vds * vds) if vds < vov else k * vov * vov


def switch_transient(q: str, closing: bool, c_load: float, r_load: float,
                     bleed: bool, vs: float = 12.6, dt: float = 2e-6,
                     t_end: float = 0.3) -> dict:
    """Time-step one high-side switch (Q1 or Q2) with its gate network:
    the gate-source resistor, the divider resistor to the switch, and the
    gate-drain (Miller) capacitor that sets the output dV/dt. For Q2 the
    bleeder (C3, R5, D4, Q3, R9) runs on the floating KEY_N node.

    The MOSFETs are square-law, fitted to R_DS(on) at V_GS −10 V."""
    ra, rb, cm = {"Q1": ("R1", "R2", "C1"), "Q2": ("R3", "R4", "C2")}[q]
    Ra, Rb = P(ra).rating["ohm"], P(rb).rating["ohm"]
    Cgd = P(cm).rating["farad"] + 1e-9
    Cgs = 5e-9                                  # the device's own C_iss
    R5, R9, C3 = P("R5").rating["ohm"], P("R9").rating["ohm"], \
        P("C3").rating["farad"]
    vth = abs(P(q).rating["vth"])
    k = 1 / (2 * P(q).rating["rds"] * (10 - vth))
    vth3, k3 = P("Q3").rating["vth"], 1 / (2 * 0.035 * (5 - 1.5))
    vz3 = P("D4").rating["vz"]

    def q3i(vq, vr):
        lo, hi = 0.0, (vr / R9 if vr > 0 else 0.0)
        for _ in range(25):
            m = (lo + hi) / 2
            if _fet(k3, vq - vth3, max(vr - m * R9, 0)) > m:
                lo = m
            else:
                hi = m
        return lo

    def vq_of(vg, u):
        lo, hi = -1.0, vz3 + 0.5
        for _ in range(35):
            vq = (lo + hi) / 2
            iz = (vq - vz3) / 5 if vq > vz3 else (
                (vq + 0.7) / 5 if vq < -0.7 else 0.0)
            if (vg - u - vq) / Rb - vq / R5 - iz > 0:
                lo = vq
            else:
                hi = vq
        return (lo + hi) / 2

    if closing:
        vg, vo, u = vs, 0.0, 0.0
    else:
        vg, vo, u = vs * Rb / (Ra + Rb), vs, 0.0
    t, i_pk, e = 0.0, 0.0, 0.0
    t_off = t_on = t_gate_off = None
    q3_ms, trace = 0.0, []
    n = 0
    while t < t_end:
        if closing:
            vq, ir = 0.0, vg / Rb                   # switch closed
        elif bleed:
            vq = vq_of(vg, u)
            ir = (vg - (u + vq)) / Rb
        else:
            vq, ir = 0.0, 0.0                       # switch open
        i = _fet(k, (vs - vg) - vth, max(vs - vo, 0))
        i3 = q3i(vq, vo) if (bleed and not closing) else 0.0
        if vq > vth3:
            q3_ms += dt * 1e3
        G = (vs - vg) / Ra - ir
        H = i - vo / r_load - i3
        a11, a12, a21, a22 = Cgs + Cgd, -Cgd, -Cgd, c_load + Cgd
        det = a11 * a22 - a12 * a21
        dvg = (G * a22 - a12 * H) / det
        dvo = (a11 * H - a21 * G) / det
        vg += dvg * dt
        vo += dvo * dt
        if bleed and not closing:
            u += dt * ir / C3
        i_pk = max(i_pk, i)
        e += i * max(vs - vo, 0) * dt
        if not closing and t_gate_off is None and (vs - vg) < vth:
            t_gate_off = t
        if not closing and t_off is None and vo < 0.5:
            t_off = t
        if closing and t_on is None and vo > 0.95 * vs:
            t_on = t
        if n % (25 if closing else 250) == 0:
            trace.append((t * 1e3, vo, i, vq))
        n += 1
        t += dt
    return dict(i_peak=i_pk, e_mj=e * 1e3,
                t_on_ms=(t_on or t_end) * 1e3 if closing else None,
                t_off_ms=(t_off or t_end) * 1e3 if not closing else None,
                t_gate_off_ms=(t_gate_off or t_end) * 1e3
                if not closing else None,
                q3_on_ms=q3_ms, trace=trace)


def key_transient() -> dict:
    c_rail = P("C7").rating["farad"] + P("C8").rating["farad"] + 20e-6
    r_rail = 1 / (0.04 / 12.6 + 1 / (P("R6").rating["ohm"] +
                                     P("R7").rating["ohm"]))
    c_bus, r_bus = 1000e-6, 12.6 / 0.35
    return dict(
        key_in=switch_transient("Q2", True, c_rail, r_rail, False,
                                t_end=0.06),
        key_out=switch_transient("Q2", False, c_rail, r_rail, True),
        key_out_no_bleed=switch_transient("Q2", False, c_rail, r_rail,
                                          False, t_end=1.5, dt=1e-5),
        main_on=switch_transient("Q1", True, c_bus, r_bus, False,
                                 t_end=0.06),
        c_rail_uf=c_rail * 1e6, c_bus_uf=c_bus * 1e6)


# ----------------------------------------------------------------------
def rail_sense() -> dict:
    r6, r7 = P("R6").rating["ohm"], P("R7").rating["ohm"]
    k = (r6 + r7) / r7
    lsb = 3.3 / 4096 * k
    return dict(mult=k, v_adc_full=12.6 / k, v_adc_arm=9.0 / k,
                lsb_mv=lsb * 1000, i_ma=12.6 / (r6 + r7) * 1000,
                z_src=r6 * r7 / (r6 + r7),
                tau_us=r6 * r7 / (r6 + r7) * P("C4").rating["farad"]
                * 1e6)


def led_level() -> dict:
    """WS2812B needs V_IH ≥ 0.7·V_DD. The 1N4001 drops the ring supply
    so the FC's 3.3 V data is a valid high."""
    res = {}
    for v5 in (5.0, 5.2):
        for i, vf in ((0.05, 0.70), (0.25, 0.85)):
            vdd = v5 - vf
            res[f"{v5} V, {i * 1000:.0f} mA"] = dict(
                vdd=vdd, vih=0.7 * vdd, margin=3.3 - 0.7 * vdd,
                margin_no_diode=3.3 - 0.7 * v5)
    return res


def moisture() -> dict:
    r_int = 50e3                      # Pi internal pull-up, typical
    r_pu = 1 / (1 / r_int + 1 / P("R12").rating["ohm"])
    vil = 0.8
    r_trip = r_pu * vil / (3.3 - vil)
    # pond water ≈ 300 µS/cm → 33 Ω·m; comb 1 mm gap, 400 mm of edge
    rho, gap, edge, film = 33.0, 1e-3, 0.4, 1e-3
    r_wet_full = rho * gap / (edge * film)
    return dict(r_pullup=r_pu, r_trip=r_trip, r_wet_full=r_wet_full,
                cover_to_trip=r_wet_full / r_trip,
                tau_ms=P("R11").rating["ohm"] * P("C12").rating["farad"]
                * 1e3)


def i2c() -> dict:
    length = sum(next(w.length for w in DS.WIRES if w.id == i)
                 for i in ("W45", "W64", "W74")) / 1000
    c = length * 100e-12 + 30e-12 + 20e-12      # cable + FC + module
    out = dict(length_m=length, c_pf=c * 1e12)
    for r in (4700, 2200):
        out[f"tr_{r}"] = 0.8473 * r * c * 1e6
    return out


# ----------------------------------------------------------------------
def power_budget() -> dict:
    """Boat loads at cruise and at the power limit, including the new
    losses in this design (PIB switches, buck, bleed)."""
    loads = [("Flight controller + GNSS", 0.8), ("Pi Zero 2 W + camera",
                                                 1.8),
             ("LED beacon (average)", 0.3), ("ESC idle (2)", 0.2),
             ("Motors at cruise", 8.0)]
    buck_loss = 1.8 / P("U5").rating["eff"] - 1.8
    i_cruise = sum(w for _, w in loads) / 10.8
    r_q = P("Q1").rating["rds"]
    pib = (i_cruise ** 2 * r_q + (8.2 / 10.8) ** 2 * r_q +
           10.8 / (DS.PARTS["R6"].rating["ohm"] + 1000) * 10.8 +
           10.8 ** 2 / (DS.PARTS["R1"].rating["ohm"] + 3300) * 2)
    extra = [("Buck loss (90%)", buck_loss), ("PIB: switches, gate "
                                              "dividers, sense", pib)]
    total = sum(w for _, w in loads + extra)
    usable_wh = 3 * 3.6 * 2.5 * 0.8
    return dict(loads=loads, extra=extra, total=total,
                endurance_min=usable_wh / total * 60,
                budget_csv_total=11.1, usable_wh=usable_wh)


def box_thermal(p_int: float) -> dict:
    """Sealed box in sun at 30 °C: internal dissipation plus absorbed
    sun on the lid, lost by natural convection and radiation from the
    walls (h ≈ 7 W/m²K). The DUPLO plate shades part of the lid."""
    L, Wd, H = (DS.PARTS and (0.200, 0.130, 0.086))
    area = 2 * (L * Wd + L * H + Wd * H)
    lid = L * Wd
    shade = 0.128 * 0.096 / lid
    sun = 800 * lid * (1 - shade) * 0.5 + 800 * lid * shade * 0.2
    h = 7.0
    rise = (p_int + sun) / (h * area)
    return dict(area=area, p_int=p_int, sun=sun, rise=rise,
                t_box=30 + rise, shade=shade)


def usb_budget() -> dict:
    loads = [("Wi-Fi adapter (TX)", 0.45), ("USB speaker (peaks)", 0.50),
             ("USB microphone", 0.05), ("Phone on the tether (SDP)", 0.50)]
    total = sum(a for _, a in loads)
    return dict(loads=loads, total=total, limit=1.6,
                pi5_w=6.5, bank_wh=74.0 * 0.85,
                hours=74.0 * 0.85 / 6.5)


def wires_check(i_cont: dict) -> list[dict]:
    """Each wire at its own continuous current (i_cont by wire id; any
    wire not listed is a signal wire at ≤ 50 mA)."""
    rows = []
    for w in DS.WIRES:
        if w.gauge not in AWG:
            continue
        i = i_cont.get(w.id, 0.05)
        amp = AWG[w.gauge][1]
        drop = i * AWG[w.gauge][0] * w.length / 1e6
        rows.append(dict(id=w.id, net=w.net, gauge=w.gauge,
                         length=w.length, i=i, amp=amp, drop_mv=drop *
                         1000, ok=i <= amp))
    return rows


def cost_rollup() -> dict:
    by_board: dict[str, float] = {}
    for p in DS.PARTS.values():
        by_board[p.board] = by_board.get(p.board, 0) + p.cost
    new = {b: v for b, v in by_board.items()
           if b in ("PIB", "MIB", "PNL", "HANDLE", "DECK_P", "DECK_S",
                    "POD_P", "POD_S")}
    return dict(by_board=by_board, new=new)


# ----------------------------------------------------------------------
def run() -> dict:
    K = _kcl()
    hr = harness_resistance()
    s70 = sag(70.0, r_up=hr["r_up"], r_down=hr["r_down"])
    s70_ideal = sag(70.0)
    w75 = watt_limit_for(7.5, hr)
    w72 = watt_limit_for(7.2, hr)
    thrust = {w: K.thrust_at_power_limit(full_w=190.0, full_n=4.0) *
              (w / 70.0) ** (2 / 3) for w in (70.0, round(w75), 60.0)}
    # fallback part (IRF4905, 20 mΩ)
    hr_fb = dict(hr)
    hr_fb["r_up"] += 0.020 - P("Q1").rating["rds"]
    hr_fb["r_down"] += 0.020 - P("Q1").rating["rds"]
    s70_fb = sag(70.0, r_up=hr_fb["r_up"], r_down=hr_fb["r_down"])
    i_motor = s70["i"] - 0.35
    heat = mosfet_heat(s70["i"], i_motor)
    kt = key_transient()
    s60 = sag(60.0, r_up=hr["r_up"], r_down=hr["r_down"])
    pb = power_budget()
    p_int = (0.8 + 1.8 + 0.2 + pb["extra"][0][1] + pb["extra"][1][1] +
             0.05 * 8.0 + (8.0 / 10.8) ** 2 * 0.22)
    it, ie = s70["i"], i_motor / 2
    i_cont = {**{w: it for w in ("W01", "W02", "W03", "W08", "W11",
                                 "W20", "W21", "W22", "W23")},
              "W04": 0.2, "W05": 0.2, "W06": 0.2, "W07": 0.2,
              "W09": 0.2, "W10": 0.2,
              **{w: ie for w in ("W24", "W25", "W26", "W27")},
              "W28": 0.3, "W29": 0.45, "W30": 0.45, "W31": 0.6,
              "W32": 0.6, "W39": 0.25, "W61": 0.3, "W66": 0.25,
              "W71": 0.3, "W76": 0.25, "W78": 0.25, "W41": 0.06,
              "W60": 0.06, "W70": 0.06,
              **{w.id: ie * 0.82 for w in DS.WIRES
                 if w.net[:2] in ("M1", "M2")}}
    fuse = dict(f1=P("F1").rating["amp"], ocp=P("U1").rating["ocp"],
                i_max_cont=s70["i"], ratio=P("F1").rating["amp"] /
                s70["i"], f2_hold=P("F2").rating["ihold"],
                i_buck_max=3.0 / 0.9 / 7.2)
    return dict(
        harness=hr, sag70=s70, sag70_ideal=s70_ideal, sag70_fallback=s70_fb,
        watt_for_7v5=w75, watt_for_7v2=w72, thrust=thrust, sag60=s60,
        gate=gate_drive(), heat=heat, key=kt, rail_sense=rail_sense(),
        led=led_level(), moisture=moisture(), i2c=i2c(), power=pb,
        thermal=box_thermal(p_int), usb=usb_budget(), fuse=fuse,
        wires=wires_check(i_cont), cost=cost_rollup())


if __name__ == "__main__":
    import json
    r = run()
    for k in ("harness", "sag70", "sag70_ideal", "sag70_fallback",
              "watt_for_7v5", "watt_for_7v2", "thrust", "gate", "heat",
              "rail_sense", "led", "moisture", "i2c", "power", "thermal",
              "usb", "fuse", "cost"):
        print(k, json.dumps(r[k], default=float)[:600])
    for k in ("key_in", "key_out", "key_out_no_bleed", "main_on"):
        print(k, {a: b for a, b in r["key"][k].items() if a != "trace"})
    print("sag60", r["sag60"])
    print("wires over", [w for w in r["wires"] if not w["ok"]])
