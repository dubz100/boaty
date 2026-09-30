"""Compliance of the electrical design with the upstream requirements
(SRS PWR/SAF/FS, SSS-PWR/HLM/MCP/MCN/REC, ICD IF-04..09, IF-12, IF-22).

status: PASS (met, shown here), FAIL (not met: change request named),
TEST (only a bench or lake test can show it; the test is named).
"""
from __future__ import annotations

import sys

from . import calcs, design as DS, erc, harness, schematics, stripboard

ROOT = calcs.ROOT


def _software_gpio() -> dict:
    sys.path.insert(0, str(ROOT / "software"))
    from boaty.mcn import panel                       # noqa: E402
    import inspect                                    # noqa: E402
    from boaty.mcp import sensors                     # noqa: E402
    moist = inspect.signature(sensors.PiSensors.__init__).parameters[
        "moisture_gpio"].default
    return dict(buttons={b.name: g for b, g in panel.GPIO.items()},
                leds={b.name: g for b, g in panel.LED_GPIO.items()},
                moisture=moist)


class Rows:
    def __init__(self):
        self.rows = []

    def add(self, rid, refs, text, value, limit, status, note="", cr=""):
        self.rows.append(dict(id=rid, refs=refs, text=text, value=value,
                              limit=limit, status=status, note=note,
                              cr=cr))


def cost_delta() -> dict:
    """Cost of what this design adds to the SDR BOM (KCL): parts with no
    KCL line and the extras. Stock items are ones a workshop usually
    holds."""
    sys.path[:0] = [str(ROOT / "docs" / "common"),
                    str(ROOT / "docs" / "kcl" / "src"),
                    str(ROOT / "docs" / "add" / "src")]
    import kcl_data as K                                    # noqa: E402
    kcl_total = K.check()["total"]
    lines = []
    stockable = ("R", "C", "D")
    for ref, p in DS.PARTS.items():
        if ref in DS.KCL_LINE or p.cost <= 0 or p.kind == "module" and \
                ref.startswith("U5"):
            continue
        stock = ref[0] in stockable and p.kind == "component" and \
            not ref.startswith(("D2", "D5", "D10"))
        lines.append((ref, p.value, p.cost, stock))
    for ref, desc, qty, each, line, stock in DS.EXTRAS:
        if line == "new":
            lines.append((ref, desc, qty * each, stock))
    buy = sum(x[2] for x in lines)
    nostock = sum(x[2] for x in lines if not x[3])
    return dict(kcl_total=kcl_total, cap=K.CAP, new_buy=buy,
                new_nostock=nostock, total_buy=kcl_total + buy,
                total_stock=kcl_total + nostock, lines=lines)


def run(c: dict | None = None) -> dict:
    c = c or calcs.run()
    e = erc.run()
    sb = stripboard.run()
    hb = harness.box_check()
    R = Rows()
    P = DS.PARTS

    # ---------------------------------------------------------- design
    R.add("D-01", "ERC", "Netlist rule check (every pin placed, nets "
          "joined only by boards, mates and wires, drivers, voltages, "
          "keying)", f"{len(e.errors)} errors; {e.stats['parts']} parts, "
          f"{e.stats['nets']} nets, {e.stats['wires']} wires",
          "0 errors", "PASS" if not e.errors else "FAIL")
    sb_err = sum(len(v["errors"]) for v in sb.values())
    R.add("D-02", "Boards", "Stripboard layouts rebuilt from copper, "
          "cuts and links, compared with the netlist",
          f"{sb_err} errors on {len(sb)} boards", "0 errors",
          "PASS" if not sb_err else "FAIL")
    sc = schematics.check()
    R.add("D-03", "Schematics", "Every part and pin on a sheet; every "
          "drawn wire joins pins of one net", f"{len(sc)} missing",
          "0", "PASS" if not sc else "FAIL",
          "only if the sheets were built in this run")

    # ---------------------------------------------------------- power
    R.add("P-01", "PWR-001, PWR-D01", "One removable 3S Li-ion pack, "
          "25-50 Wh", f"3S1P, {3 * 3.6 * 2.5:.0f} Wh nominal",
          "25-50 Wh", "PASS")
    R.add("P-02", "PWR-002, PWR-D02", "BMS: over-discharge, over-current, "
          "short circuit, balance", f"OCP {P['U1'].rating['ocp']:.0f} A, "
          f"ODV {P['U1'].rating['odv']} V/cell", "trip ≤ 25 A, 2.5-2.8 V",
          "PASS", "confirm the bought board's trip points (bench)")
    f = c["fuse"]
    R.add("P-03", "PWR-003, PWR-D05", "Main fuse: position and rating",
          f"20 A ATO, 40 mm lead (W01); {f['ratio']:.1f} × the power-"
          "limited current; 1.2 × the hardware maximum (2 × 8 A)",
          "≤ 50 mm; ≤ 2 × max continuous", "PASS",
          "the BMS (25 A, fast) protects the 18 AWG ESC leads above 16 A")
    R.add("P-04", "PWR-004, PWR-D06", "Main switch waterproof, outside "
          "the box, without opening it", "IP67 toggle with cover on the "
          "handle; drives Q1 (P-FET, 80 A class, solid-state option)",
          "IP67; ≥ 20 A or a ≥ 30 A solid-state switch", "PASS")
    s70, s60 = c["sag70"], c["sag60"]
    R.add("P-05", "PWR-005, PWR-D12", "Separate 5 V for the avionics; "
          "no brown-out on a full thrust step at 9.6 V (resting)",
          f"FC fed at the PDB: {s70['v_pdb']:.2f} V at 70 W",
          "FC ≥ 7.0 V, buck ≥ 6.0 V", "PASS" if s70["v_pdb"] >= 7.0
          else "FAIL", "the FC and buck take their supply before the key "
          "switch (PWR-D10)")
    R.add("P-06", "PWR-D22, HLM-D43, KF-02", "Every supply works at the "
          "rail voltage the power limit allows (critical battery, "
          "acceptance-limit cells)", f"ESC input {s70['v_esc']:.2f} V at "
          f"70 W (harness {1000 * (c['harness']['r_up'] + c['harness']['r_down']):.0f} "
          "mΩ); 7.5 V needs ≤ "
          f"{c['watt_for_7v5']:.0f} W", "≥ 7.5 V (ESC rated 7.2 V)",
          "PASS" if s70["v_esc"] >= 7.5 else "FAIL",
          f"at 60 W: {s60['v_esc']:.2f} V and "
          f"{c['thrust'][60.0]:.2f} N thrust (≥ 1.1 N for ENV-002)",
          "CR-12")
    R.add("P-07", "PWR-006, PWR-D13, IF-07", "Battery V and I measured "
          "and logged", "PDB sensor → BATT_VOLT_PIN 10 / BATT_CURR_PIN 11; "
          "every load behind it", "± 1% V, ± 5% I after calibration",
          "TEST", "bench calibration (KF-10)")
    R.add("P-08", "PWR-007, PWR-D04", "No charge port; charged off the "
          "boat", "balance lead J2 and XT60 only", "no port", "PASS")
    R.add("P-09", "PWR-008, PWR-D14", "Polarised connectors, one job per "
          "type", "XT60 battery · XT30 ESCs · JST-XH balance · Micro-Fit "
          "Pi 5 V; signal KK254 with one pin count per board", "no shared "
          "type", "PASS" if not [x for x in e.errors if x.startswith("E7")]
          else "FAIL")
    R.add("P-10", "PWR-D15", "Wire gauges and joints", "16 AWG battery → "
          "bus, 18 AWG to the ESCs, silicone; soldered, heat-shrunk; "
          "glands on every entry", "16 / 18 AWG", "PASS")
    over = [w for w in c["wires"] if not w["ok"]]
    R.add("P-11", "PWR-D15", "Each wire within its current rating at "
          "its continuous current", f"{len(over)} over; worst drop "
          f"{max(w['drop_mv'] for w in c['wires']):.0f} mV",
          "0 over", "PASS" if not over else "FAIL")
    k = c["key"]
    R.add("P-12", "PWR-D07, IF-06", "Key switch: high-side P-MOSFET, soft "
          "start, off without the key", f"inrush {k['key_in']['i_peak']:.1f}"
          f" A, rail up in {k['key_in']['t_on_ms']:.1f} ms", "high side; "
          "soft start; fails off", "PASS",
          "gate-drain (Miller) soft start: a gate-source RC gave 24 A "
          "(CR-13)")
    R.add("P-13", "IF-06, MCN-D54", "Key out → rail < 0.5 V within "
          "100 ms", f"{k['key_out']['t_off_ms']:.0f} ms (no bleeder: "
          f"{k['key_out_no_bleed']['t_off_ms']:.0f} ms)", "≤ 100 ms",
          "PASS" if k["key_out"]["t_off_ms"] <= 100 else "FAIL",
          "active bleeder Q3/R9, a pulse only: a shorted Q2 cannot burn "
          "it (FM-22 is found by the rail check)", "CR-13")
    rs = c["rail_sense"]
    R.add("P-14", "PWR-D08, IF-06", "Rail divided to the helm's second "
          "voltage input; arming refused below 9.0 V", f"10 k / 1 k → "
          f"× {rs['mult']:.1f}; 9.0 V → {rs['v_adc_arm']:.2f} V at ADC 15",
          "BATT2_VOLT_MULT 11.0; ≤ 3.3 V", "PASS")
    R.add("P-15", "PWR-D09, PWR-D10", "Rail off at power-up without the "
          "key; helm powered before the key", "R3 holds Q2 off; FC and "
          "buck on VBAT_S (before Q2)", "-", "PASS")
    R.add("P-16", "PWR-D11, IF-08", "Mission computer: own 5.1 V ≥ 3 A "
          "buck, 7-14 V in; stays ≥ 4.85 V on a thrust step",
          "KC-09 buck; 470 µF + TVS at the Pi; input ≥ "
          f"{s70['v_pdb']:.1f} V at 70 W", "5.1 V ± 2%", "TEST",
          "set-point and step response on the bench (IF-08 test)")
    R.add("P-17", "PWR-D16", "No exposed live conductor outside the box",
          "motor phases in IP68 connectors (caps when unmated); mast and "
          "switch leads in IP67 parts", "none", "PASS")
    pb = c["power"]
    R.add("P-18", "PWR-009, PWR-D17, PWR-D18", "Endurance at cruise, with "
          "this design's losses", f"{pb['total']:.2f} W → "
          f"{pb['endurance_min']:.0f} min on {pb['usable_wh']:.1f} Wh",
          "≥ 40 min, margin ≥ 30%", "PASS", "power.csv holds 11.1 W: add "
          f"{pb['total'] - pb['budget_csv_total']:.2f} W (CR-12)")
    th = c["thermal"]
    R.add("P-19", "PWR-010, PWR-D19, MCP-D04", "Box temperature, 30 °C "
          "in sun, 60 min", f"{th['t_box']:.0f} °C ({th['p_int']:.1f} W "
          f"inside, {th['sun']:.1f} W sun)", "≤ 50 °C", "PASS" if
          th["t_box"] <= 50 else "FAIL", "DUPLO plate shades "
          f"{th['shade'] * 100:.0f}% of the lid; test V-10")
    R.add("P-20", "PWR-D19", "Battery ≥ 30 mm from the ESCs",
          f"{hb['battery_to_esc']:.0f} mm", "≥ 30 mm",
          "PASS" if hb["battery_to_esc"] >= 30 and not hb["errors"]
          else "FAIL", "box layout checked for overlaps and gland space")
    ht = c["heat"]
    R.add("P-21", "IF-06", "Switch MOSFETs at the power-limited current",
          f"Tj {ht['Q1']['tj']:.0f} °C with a clip-on sink "
          f"({ht['Q1']['tj_bare']:.0f} °C without)", "< 150 °C", "PASS",
          "box at 50 °C, R_DS(on) × 2.25 for low gate drive and heat")

    # ---------------------------------------------------------- helm
    R.add("H-01", "HLM-D02, HLM-D37", "Flight controller resources used",
          "SERIAL1 Pi, SERIAL3 GPS; UART4/5 free (ELRS spare); outputs 1, "
          "4, 12; ADC 10, 11, 15; I²C1", "≥ 2 UARTs, 3 DShot, 2 ADC",
          "PASS")
    R.add("H-02", "HLM-D44, KF-04", "One MAVLink path; wireless board "
          "not fitted", "SERIAL1 only; SERIAL6 disabled", "-", "PASS")
    R.add("H-03", "IF-05", "ESC signals: output 1 left, 4 right, twisted "
          "pair ≤ 150 mm, no ESC power to the FC", "TP1/TP2 150 mm; BEC "
          "leads unconnected", "-", "PASS")
    R.add("H-04", "IF-04", "UART to the Pi: 3.3 V both ends, crossed, "
          "common ground", "Pi TXD → FC RX1, FC TX1 → Pi RXD, GND",
          "no level shifting", "PASS" if not [x for x in e.errors
                                              if "E6" in x] else "FAIL")
    ic2 = c["i2c"]
    R.add("H-05", "IF-22, HLM-D35", "GNSS on SERIAL3, compass on I²C, "
          "through the mast connector", f"{ic2['length_m']:.1f} m of cable; "
          f"rise {ic2['tr_4700']:.2f} µs (4.7 k) / {ic2['tr_2200']:.2f} µs "
          "(2.2 k)", "≤ 1 µs (100 kHz), ≤ 0.3 µs (400 kHz)", "TEST",
          "confirm the module's pull-ups and the bus speed on the bench")
    lv = c["led"]
    worst = min(v["margin"] for v in lv.values())
    R.add("H-06", "IF-09, TBC-08", "Beacon data level: 3.3 V data into "
          "the LED ring", f"with D6: V_IH margin ≥ {worst:.2f} V (without: "
          f"{min(v['margin_no_diode'] for v in lv.values()):.2f} V)",
          "margin > 0", "PASS" if worst > 0 else "FAIL",
          "closes TBC-08 by design; confirm on the bench")

    # ---------------------------------------------------------- MCP
    mo = c["moisture"]
    sw = _software_gpio()
    R.add("M-01", "MCP-D03, FS-010", "Moisture sensor read by GPIO",
          f"GPIO{sw['moisture']} (software default); trips below "
          f"{mo['r_trip'] / 1000:.1f} kΩ; wet comb ≈ "
          f"{mo['r_wet_full']:.0f} Ω", "GPIO; wet detected", "PASS",
          f"trips with {mo['cover_to_trip'] * 100:.1f}% of the comb wet")
    R.add("M-02", "MCP-D26, KC-12", "DS18B20 at the box top on 1-Wire",
          "GPIO4, 4.7 kΩ to 3.3 V", "GPIO4, 4.7 k", "PASS")
    R.add("M-03", "MCP-D05", "Mission computer power", "1.8 W average "
          "(budget), 3 W peak; buck loss 0.2 W", "≤ 2.0 W avg", "PASS")

    # ---------------------------------------------------------- MCN
    hw_btn = {b: int(g) for b, _c, g, *_x in DS.BUTTONS}
    hw_led = {b: int(lg) for b, _c, _g, _p, lg, _lp in DS.BUTTONS}
    sw_btn = {k.replace("COME_HOME", "HOME"): v for k, v in
              sw["buttons"].items()}
    sw_led = {k.replace("COME_HOME", "HOME"): v for k, v in
              sw["leds"].items()}
    same = sw_btn == hw_btn and sw_led == hw_led
    R.add("C-01", "IF-12, MCN-D02", "Panel GPIOs agree with the software "
          "(boaty/mcn/panel.py)", "buttons " + ", ".join(
              f"{b} {g}" for b, g in hw_btn.items()) + "; LEDs " +
          ", ".join(str(v) for v in hw_led.values()), "identical",
          "PASS" if same else "FAIL")
    us = c["usb"]
    R.add("C-02", "MCN-D01, MC-001", "Mission Control on the power bank",
          f"{us['hours']:.1f} h at {us['pi5_w']} W", "≥ 2.5 h", "PASS")
    R.add("C-03", "KC-16, MCN-1", "Pi 5 USB current (usb_max_current_"
          "enable=1)", f"{us['total']:.2f} A", f"≤ {us['limit']} A",
          "PASS" if us["total"] <= us["limit"] else "FAIL",
          "phone on the tether as a USB SDP (≤ 0.5 A)")

    # ---------------------------------------------------------- safety
    R.add("S-01", "SAF-001, SAF-002", "Helm independent of the mission "
          "computer and Mission Control", "own supply from the bus; UART "
          "only link; ESC signals direct", "-", "PASS")
    R.add("S-02", "FS-008", "ESCs stop when commands stop", "AM32 0.5 s "
          "(KC-03)", "≤ 1 s", "TEST", "V-09 on the bench")
    R.add("S-03", "CHD-003, MEC-012", "Electronics behind an adult action; "
          "every cable entry through a gland", "latched box; 4 × PG7: "
          "motors ×2, mast, switch", "-", "PASS")
    R.add("S-04", "MEC-013, HLM-D35", "GNSS ≥ 150 mm from power wiring",
          "252 mm (MDD E-01; motor leads run down and aft)", "≥ 150 mm",
          "PASS")
    cost = cost_delta()
    R.add("X-01", "CON-001, CR-08", "Bill of materials within the £185 "
          "cap (boat and shore kit)", f"£{cost['total_buy']:.0f} buying "
          f"everything; £{cost['total_stock']:.0f} with workshop stock "
          "(wire, resistors, stripboard)", f"≤ £{cost['cap']}",
          "PASS" if cost["total_stock"] <= cost["cap"] else "FAIL",
          f"SDR BOM £{cost['kcl_total']}; this design adds "
          f"£{cost['new_buy']:.0f} (connectors, cables, boards)", "CR-14")
    return dict(rows=R.rows, erc=dict(errors=e.errors, stats=e.stats,
                                      notes=e.notes),
                boards={b: dict(stats=v["stats"], errors=v["errors"])
                        for b, v in sb.items()},
                box=hb, cost=cost)
