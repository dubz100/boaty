"""Build BOATY-EDD-001, the Electrical Design Description.

Run:  python3 docs/edd/src/build_edd.py

Every number comes from electrical/results/elec_results.json and every
picture from docs/edd/figures, both written by electrical/build_elec.py.
This build needs neither schemdraw nor the design sources, so CI can run
it.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
ROOT = DOCS.parent
sys.path.insert(0, str(DOCS / "common"))

import baseline as BL  # noqa: E402
from pdfdoc import (GREEN_T, ORANGE, ORANGE_T, H1, H2,  # noqa: E402
                    P, PageBreak, Spacer, bullets, callout, colors,
                    control_and_contents, cover, fig, mm, table, Doc)

OUT = HERE.parent / "Boaty_Electrical_Design_Description.pdf"
FIG = HERE.parent / "figures"
RES = json.loads((ROOT / "electrical" / "results" /
                  "elec_results.json").read_text())
DOC_ID = "BOATY-EDD-001"
ISSUE = BL.issue("EDD", "draft for CDR")
DATE = BL.DATE
ROWS = RES["rows"]
C = RES["calcs"]
K = RES["key"]
HR = C["harness"]


def row(rid):
    return next(r for r in ROWS if r["id"] == rid)


def n(s):
    return sum(r["status"] == s for r in ROWS)


STATUS_T = {"PASS": GREEN_T, "FAIL": ORANGE_T, "TEST": colors.HexColor(
    "#e8f1fb")}


def status_table(rows):
    data = [["ID", "Requirement", "Check", "Design value", "Limit",
             "Status"]]
    extra = []
    for i, r in enumerate(rows, 1):
        s = r["status"] + (f"<br/>{r['cr']}" if r["status"] == "FAIL" and
                           r["cr"] else "")
        text = r["text"] + (f"<br/><font size=6.8 color='#52514e'>"
                            f"{r['note']}</font>" if r["note"] else "")
        data.append([r["id"], r["refs"], text, r["value"], r["limit"], s])
        extra.append(("BACKGROUND", (5, i), (5, i), STATUS_T[r["status"]]))
    return table(data, [12, 25, 50, 39, 28, 16], style_extra=extra)


def parts_of(board):
    rows = [["Ref", "Value", "Description / part", "Source"]]
    for p in RES["parts"]:
        if p["board"] == board and p["value"] != "pad":
            rows.append([p["ref"], p["value"], p["desc"] + (
                f"<br/><font size=6.6 color='#52514e'>{p['mpn']}</font>"
                if p["mpn"] and p["mpn"] != p["value"] else ""), p["src"]])
    return table(rows, [13, 26, 115, 16])


# ======================================================================
def section_intro():
    return [
        H1("1. Introduction"),
        H2("1.1 Purpose and status"),
        P("This document describes the detailed electrical design of Boaty "
          "Mk1: power distribution and switching, the flight controller's "
          "wiring, the mission computer and its sensors, the mast and pod "
          "connections, and the Mission Control panel. It gives the "
          "schematics, the three custom boards, the harness and the "
          "calculations behind them, and checks the design against the "
          "requirements allocated to it. With the Mechanical Design "
          "Description it is an input to the Critical Design Review."),
        P(f"It is a <b>draft for the CDR</b>. The system documents stay as "
          f"baselined at the SDR (tag <i>{BL.TAG}</i>); where this design "
          "cannot meet one of them, section 9 proposes a numbered change "
          "request."),
        H2("1.2 How the design is held and checked"),
        P("The design is one Python file, <i>electrical/boaty_elec/"
          "design.py</i>: every part with its pins, every net, which "
          "connector halves mate, and every harness wire with its gauge, "
          "length and route. Everything else is generated from it and "
          "checked against it:"),
        *bullets([
            "an <b>electrical rule check</b>: every pin on exactly one net; "
            "every net one connected piece once boards, mated connectors "
            "and harness wires are counted, and nothing else joined; no "
            "input without a source; no pin above its maximum voltage; "
            "connector keying (fault-injected: it finds a missing wire, a "
            "pin on two nets, a wire on the wrong net, an over-voltage);",
            "the <b>schematics</b>: each drawn pin takes its net name from "
            "the netlist, and a wire can only be drawn between pins of one "
            "net, so a sheet cannot disagree with the netlist; a coverage "
            "check proves every pin is on a sheet;",
            "the <b>stripboard layouts</b>: rebuilt from copper strips, "
            "cuts and links alone and compared with the netlist (a missing "
            "link shows as an open, a missing cut as a short);",
            "the <b>calculations</b>, including a time-stepped simulation "
            "of the key switch and its bleeder, and the compliance matrix "
            "in section 8.",
        ]),
        P(f"This issue was built from commit {RES['commit']}. "
          "<i>python3 electrical/build_elec.py</i> rebuilds the schematics, "
          "netlist, wire list, BOM, layouts, figures and the results file "
          "this document reads."),
        H2("1.3 References"),
        table([["Ref", "Document"],
               ["[1]", BL.full("SRS") + " System Requirements Specification"],
               ["[2]", BL.full("ADD") + " Architecture Design Document"],
               ["[3]", BL.full("ICD") + " Interface Control Document "
                "(IF-04 to IF-09, IF-12, IF-22)"],
               ["[4]", f"Subsystem specifications: {BL.sss_all()}"],
               ["[5]", BL.full("KCL") + " Key Component List"],
               ["[6]", BL.full("MDD") + " Mechanical Design Description "
                "(draft)"],
               ["[7]", "ArduPilot SpeedyBeeF405WING board definition and "
                "README (docs/kcl/sources)"]], [14, 156]),
    ]


def section_summary():
    fails = [r for r in ROWS if r["status"] == "FAIL"]
    s70, s60 = C["sag70"], C["sag60"]
    rows = [["Quantity", "Design", "Requirement"],
            ["Checks: pass / by test / not met",
             f"{n('PASS')} / {n('TEST')} / {n('FAIL')}", f"{len(ROWS)} "
             "checks"],
            ["ERC; board layouts; schematic coverage",
             f"{len(RES['erc']['errors'])} errors; "
             f"{sum(len(b['errors']) for b in RES['boards'].values())} "
             "errors; complete", "0"],
            ["Key-in inrush; key-out to < 0.5 V",
             f"{K['key_in']['i_peak']:.1f} A; "
             f"{K['key_out']['t_off_ms']:.0f} ms", "soft; ≤ 100 ms (IF-06)"],
            ["ESC input at the power limit (critical battery)",
             f"{s70['v_esc']:.2f} V at 70 W; {s60['v_esc']:.2f} V at 60 W",
             "≥ 7.5 V (PWR-D22)"],
            ["Cruise load; endurance", f"{C['power']['total']:.2f} W; "
             f"{C['power']['endurance_min']:.0f} min", "≥ 40 min"],
            ["Box air, 30 °C in sun", f"{C['thermal']['t_box']:.0f} °C",
             "≤ 50 °C"],
            ["Bill of materials", f"£{RES['cost']['total_stock']:.0f} "
             f"(£{RES['cost']['total_buy']:.0f} buying everything)",
             f"≤ £{RES['cost']['cap']}"]]
    return [
        H1("2. Summary"),
        table(rows, [64, 60, 46]),
        Spacer(1, 3 * mm),
        callout("<b>Decisions for the owner at the CDR.</b><br/>" +
                "<br/>".join(f"• {r['id']} {r['refs']}: {r['text']}: "
                             f"{r['value']} → <b>{r['cr']}</b>"
                             for r in fails) +
                "<br/>• CR-13 (no failing check): the ICD's key-switch "
                "circuit (gate RC soft start, no discharge) does not meet "
                "IF-06's own test; this design changes the circuit.",
                ORANGE, ORANGE_T),
        Spacer(1, 2 * mm),
        P("What this design adds to the system, in one line each:"),
        *bullets([
            "a <b>power and interconnect board</b> (PIB): a solid-state main "
            "switch driven by a small IP67 toggle, the key switch with a "
            "gate-drain soft start and an active rail bleeder, the rail "
            "sense divider, surge suppressors, a PTC on the buck feed, and "
            "the mast-cable junction;",
            "a <b>mission-computer interface board</b> (MIB) on the Pi "
            "Zero's header: protected 5 V entry, UART, DS18B20 and moisture "
            "inputs;",
            "a <b>panel board</b> (PNL) for Mission Control: four button "
            "inputs and four LED drivers on the IF-12 GPIOs;",
            "an <b>M12 8-pole mast connector</b> at the handle so the mast "
            "comes off without opening the box, and <b>IP68 pod "
            "connectors</b> on the stern decks (TBC-12 still open);",
            "the <b>harness</b>: 16 AWG main path, 18 AWG ESC leads, four "
            "cables through the four PG7 glands.",
        ]),
    ]


def section_arch():
    return [
        PageBreak(),
        H1("3. Architecture"),
        fig(FIG / "interconnect.png", 165, "Figure 1. Boards, modules and "
            "cables. Blue: signals; black: power; purple: mast and switch "
            "cables; red: motor cables through the glands."),
        H2("3.1 Power path"),
        P("Battery (3 × 18650 and BMS, PWR-D01/D02) → 20 A fuse within "
          "40 mm of the BMS output → XT60 → <b>Q1</b>, the main switch on "
          "the PIB → the PDB's battery pads and current sensor → the PDB's "
          "battery output (<i>VBAT_S</i>). From VBAT_S: the flight "
          "controller's own regulator and the 5.1 V buck (both before the "
          "key, PWR-D10/D11), and <b>Q2</b>, the key switch → the motor "
          "rail → two XT30 leads to the ESCs. Every load sits behind the "
          "PDB sensor, so the helm's mAh count includes the mission "
          "computer (IF-07)."),
        P("Q1 and Q2 are high-side P-MOSFETs (PWR-D07 forbids low-side "
          "switching). The main switch is the solid-state option of "
          "PWR-D06: a small sealed IP67 toggle with a flip cover on the "
          "handle pulls Q1's gate down; the toggle carries a milliamp, so "
          "it needs no current rating and its lead goes through the fourth "
          "gland."),
        H2("3.2 Grounds"),
        P("One ground, star-connected at the PDB. Motor current returns "
          "from each ESC to the PDB on its own 18 AWG lead; the PIB's "
          "ground is a 22 AWG signal return that carries no motor current; "
          "the ESC signal grounds are twisted with their signals (IF-05). "
          "Mission Control is a separate system with its own ground "
          "(PI5_GND) and no wire to the boat."),
        H2("3.3 Connectors and keying (PWR-D14)"),
        table([["Function", "Connector", "Keying"],
               ["Battery", "XT60 (sockets on the pack)", "only XT60"],
               ["ESC supply ×2", "XT30", "only XT30; same job twice"],
               ["Balance (charger only)", "JST-XH 4", "only JST-XH"],
               ["Mission computer 5 V", "Molex Micro-Fit 2", "only "
                "Micro-Fit"],
               ["Board signals", "Molex KK 254 (2.54 mm, polarised)",
                "each board uses each pin count once (PIB 2, 3, 6, 8; MIB "
                "2, 3, 4); pin 2 of J12 and pin 4 of J34 are left empty"],
               ["Mast (GNSS, compass, LEDs)", "M12 A-coded 8-pole, IP67",
                "coded; one per boat"],
               ["Pods ×2", "3-pole IP68 (TBC-12)", "keyed; same job twice"]],
              [44, 60, 66]),
        Spacer(1, 2 * mm),
        P("JST-PH (2.0 mm) was the first choice for board signals; it does "
          "not sit on 0.1-inch stripboard, and JST-XH is the balance "
          "lead's connector, so both were ruled out.", "small"),
        H2("3.4 Cable entries (MEC-012)"),
        table([["Gland", "Size", "Cable"]] +
              [[g, s_, c] for g, s_, c in RES["glands"]], [20, 20, 130]),
    ]


def section_circuits():
    st = [PageBreak(), H1("4. Circuit design")]
    sheets = dict(RES["sheets"])
    notes = {
        "S1": "The pack, the box socket, the PDB's power pins, the buck and "
              "the ESC supplies with their 470 µF input capacitors (the "
              "load the key switch's soft start is sized for).",
        "S2": "The PIB. Q1 and Q2 are identical switches: a 10 k gate-to-"
              "source resistor holds each off; closing its switch (toggle "
              "or reed) pulls the gate through 3.3 k to V<sub>GS</sub> ≈ "
              "−9.5 V at full charge (−5.6 V at 7.5 V); a 15 V zener "
              "clamps the gate; a 470 nF gate-to-drain capacitor sets the "
              "output's rise rate. The bleeder Q3 is driven by the rising "
              "edge of KEY_N through C3, so it conducts only for a pulse "
              "after key-out. The rail sense divider feeds the AIRSPD pad "
              "(ADC 15, BATT2). TVS diodes on the bus and the motor rail "
              "absorb ESC regeneration spikes.",
        "S3": "The helm's signal connections. GNSS and compass go from the "
              "FC's GPS port through J15 and J14 on the PIB (the two "
              "headers share strips pin for pin), the M12 socket on the "
              "handle and the mast lead. The LED data passes R8 (330 Ω); "
              "the ring's supply passes D6, which lowers it to ≈ 4.3 V so "
              "the FC's 3.3 V data is a valid high (section 5.5).",
        "S4": "ESC signals from outputs 1 and 4 (BIDIR-capable, KCL KF-09) "
              "as twisted pairs; motor phases through the glands and the "
              "deck connectors.",
        "S5": "The MIB on the Pi Zero header: the 5 V feed enters on pins 2 "
              "and 4 behind a 5.8 V TVS and 470 µF (back-powering bypasses "
              "the Pi's own protection); UART on pins 8/10; DS18B20 on "
              "GPIO4; the moisture comb on GPIO17 through 1 k with a "
              "100 k pull-up and 100 nF filter. GPIO numbers match the "
              "software (sensors.py).",
        "S6": "Mission Control. Each button input has a 10 k pull-up, 1 k "
              "series resistor and 100 nF; each 5 V button LED is switched "
              "low by a 2N7000 with a 100 k gate pull-down so the LEDs are "
              "off while the Pi boots. The GPIOs are those in IF-12 and in "
              "the software (panel.py); section 8 checks they agree.",
    }
    for sid, title in sheets.items():
        st += [H2(f"{sid}  {title}"),
               fig(FIG / f"{sid}.png", 170, f"Sheet {sid}."),
               P(notes[sid])]
        if sid == "S2":
            st += [fig(FIG / "key_transient.png", 165, "Figure 2. Key "
                       "switch, simulated: key in (left) and key out with "
                       "and without the bleeder (right)."),
                   P(f"A gate-to-source capacitor (the ICD's 'gate RC ≈ "
                     f"10 ms') does not soft-start a low-R<sub>DS(on)</sub>"
                     f" MOSFET: the simulation gives a 24 A inrush in "
                     f"2.6 ms, because the FET turns fully on within a "
                     f"volt of threshold. The gate-to-drain capacitor "
                     f"holds the gate on its Miller plateau while the rail "
                     f"rises, which limits the inrush to "
                     f"{K['key_in']['i_peak']:.1f} A. Without the bleeder "
                     f"the ESCs' capacitors would hold the rail up for "
                     f"{K['key_out_no_bleed']['t_off_ms']:.0f} ms against "
                     f"IF-06's 100 ms; with it, "
                     f"{K['key_out']['t_off_ms']:.0f} ms. The bleeder "
                     f"conducts for ≈ {K['key_out']['q3_on_ms']:.0f} ms "
                     f"and then stops, so a Q2 that has failed short "
                     f"(FM-22) cannot burn it out; the checklist's rail "
                     f"test (MCN-D54) finds that failure. The main switch "
                     f"Q1 soft-starts the bus the same way "
                     f"({K['main_on']['i_peak']:.1f} A)."),
                   parts_of("PIB")]
        if sid == "S5":
            st += [parts_of("MIB")]
        if sid == "S6":
            st += [parts_of("PNL")]
    return st


def section_calcs():
    s70, s60, fb = C["sag70"], C["sag60"], C["sag70_fallback"]
    ht = C["heat"]
    rs = C["rail_sense"]
    mo = C["moisture"]
    ic = C["i2c"]
    pb = C["power"]
    th = C["thermal"]
    us = C["usb"]
    led = C["led"]
    st = [PageBreak(), H1("5. Calculations")]
    st += [H2("5.1 Supply sag at the power limit (PWR-D22, KF-01/02)"),
           P("The SDR sized the helm's power limit (BATT_WATT_MAX 70 W) so "
             "the rail stays at 7.5 V at the critical battery with "
             "acceptance-limit cells (0.22 Ω pack), with no allowance for "
             "the harness. The limit acts on the power the PDB measures, "
             "so the operating point solves V<sub>PDB</sub>·I = P with "
             "V<sub>PDB</sub> = 9.6 V − I·(R<sub>pack</sub> + "
             "R<sub>up</sub>); the ESCs see a further I·R<sub>down</sub>."),
           table([["Series element", "mΩ"]] +
                 [[k, f"{v * 1000:.1f}"] for k, v in HR["up"].items()] +
                 [["<b>battery to PDB</b>", f"<b>{HR['r_up'] * 1000:.1f}"
                   "</b>"]] +
                 [[k, f"{v * 1000:.1f}"] for k, v in HR["down"].items()] +
                 [["<b>PDB to ESC</b>", f"<b>{HR['r_down'] * 1000:.1f}"
                   "</b>"]], [120, 50]),
           Spacer(1, 2 * mm),
           fig(FIG / "sag.png", 150, "Figure 3. ESC input voltage against "
               "the power limit."),
           table([["Case", "Current", "V at PDB", "V at ESC"],
                  ["70 W, no harness (SDR)",
                   f"{C['sag70_ideal']['i']:.1f} A",
                   f"{C['sag70_ideal']['v_pdb']:.2f}",
                   f"{C['sag70_ideal']['v_esc']:.2f}"],
                  ["70 W, this harness", f"{s70['i']:.1f} A",
                   f"{s70['v_pdb']:.2f}", f"{s70['v_esc']:.2f}"],
                  ["70 W, fallback MOSFETs (20 mΩ)", f"{fb['i']:.1f} A",
                   f"{fb['v_pdb']:.2f}", f"{fb['v_esc']:.2f}"],
                  ["<b>60 W, this harness</b>", f"{s60['i']:.1f} A",
                   f"{s60['v_pdb']:.2f}", f"<b>{s60['v_esc']:.2f}</b>"]],
                 [70, 30, 35, 35]),
           P(f"With the harness the ESCs see {s70['v_esc']:.2f} V at 70 W: "
             f"below PWR-D22's 7.5 V and just below the AM32's 7.2 V. "
             f"Holding 7.5 V needs ≤ {C['watt_for_7v5']:.0f} W; 60 W gives "
             f"{s60['v_esc']:.2f} V and still "
             f"{C['thrust']['60.0']:.2f} N of thrust against the 1.1 N "
             f"ENV-002 needs (70 W: {C['thrust']['70.0']:.2f} N). CR-12 "
             "proposes 60 W. The fallback MOSFET (IRF4905) is worse still, "
             "so the ≤ 6 mΩ part matters.")]
    st += [H2("5.2 Switch MOSFETs"),
           P(f"V<sub>GS</sub> at 12.6 / 9.0 / 7.5 V: "
             f"{C['gate']['Q1']['12.6']:.1f} / {C['gate']['Q1']['9.0']:.1f}"
             f" / {C['gate']['Q1']['7.5']:.1f} V (−20 V maximum; 15 V "
             f"zener). At the power-limited "
             f"{ht['Q1']['i']:.1f} A, with R<sub>DS(on)</sub> taken 2.25 × "
             f"its −10 V rating for low gate drive and a hot junction, Q1 "
             f"dissipates {ht['Q1']['p']:.2f} W: junction "
             f"{ht['Q1']['tj_bare']:.0f} °C in free air in a 50 °C box, "
             f"{ht['Q1']['tj']:.0f} °C with a clip-on heatsink (fitted). "
             f"At cruise (≈ 1 A) the loss is negligible.")]
    st += [H2("5.3 Fuses and wires (PWR-003, PWR-D15)"),
           P(f"F1 20 A is {C['fuse']['ratio']:.1f} × the power-limited "
             "current and 1.2 × the hardware maximum (2 × 8 A, PRP-D05, "
             "plus avionics), within PWR-003's 2 ×. The BMS (≤ 25 A, fast) "
             "covers faults the fuse clears slowly, including the 18 AWG "
             f"ESC leads (16 A). F2 (PTC, {C['fuse']['f2_hold']} A hold) "
             f"protects the 20 AWG buck feed; the buck draws ≤ "
             f"{C['fuse']['i_buck_max']:.2f} A. Every wire carries its "
             "continuous current within its rating; the worst drop is "
             f"{max(w['drop_mv'] for w in RES['wires']):.0f} mV.")]
    st += [H2("5.4 Rail sense (IF-06, PWR-D08)"),
           P(f"10 k / 1 k: × {rs['mult']:.1f} (BATT2_VOLT_MULT 11.0). Full "
             f"charge {rs['v_adc_full']:.2f} V, arming threshold 9.0 V → "
             f"{rs['v_adc_arm']:.2f} V at the ADC (3.3 V full scale); "
             f"{rs['lsb_mv']:.1f} mV per count at the rail; "
             f"{rs['i_ma']:.1f} mA; source impedance "
             f"{rs['z_src']:.0f} Ω; filter {rs['tau_us']:.0f} µs.")]
    st += [H2("5.5 LED data level (IF-09, TBC-08)"),
           P("A WS2812B needs V<sub>IH</sub> ≥ 0.7·V<sub>DD</sub>. At 5.2 V "
             "that is 3.64 V, above the FC's 3.3 V output. D6 (1N4001) "
             "drops the ring's supply:"),
           table([["BEC, load", "V<sub>DD</sub> ring", "V<sub>IH</sub>",
                   "Margin", "Margin without D6"]] +
                 [[k, f"{v['vdd']:.2f}", f"{v['vih']:.2f}",
                   f"{v['margin']:.2f}", f"{v['margin_no_diode']:.2f}"]
                  for k, v in led.items()], [40, 30, 30, 30, 40]),
           P("This closes TBC-08 by design; the bench confirms it with the "
             "real ring and cable.", "small")]
    st += [H2("5.6 Moisture input (MCP-D03, FS-010)"),
           P(f"The Pi's ≈ 50 k pull-up and R12 (100 k) give "
             f"{mo['r_pullup'] / 1000:.0f} k; GPIO17 reads low below "
             f"{mo['r_trip'] / 1000:.1f} kΩ across the comb. Pond water "
             f"(≈ 300 µS/cm) 1 mm deep across the comb measures ≈ "
             f"{mo['r_wet_full']:.0f} Ω, so {mo['cover_to_trip'] * 100:.1f}"
             "% of the comb wet trips it; a condensation film does not. "
             "Traces are only energised through 33 k, so corrosion "
             "matters only once the box is already wet.")]
    st += [H2("5.7 I²C over the mast (IF-22)"),
           P(f"{ic['length_m']:.1f} m of cable, ≈ {ic['c_pf']:.0f} pF. Rise "
             f"time {ic['tr_4700']:.2f} µs with 4.7 kΩ pull-ups, "
             f"{ic['tr_2200']:.2f} µs with 2.2 kΩ: fine at 100 kHz "
             "(≤ 1 µs), marginal at 400 kHz (≤ 0.3 µs) unless the module's "
             "pull-ups are 2.2 kΩ. The board definition sets no bus speed; "
             "the bench confirms compass reads over the full cable (TEST).")]
    st += [H2("5.8 Power budget and thermal (PWR-009/010, PWR-D17/D19)"),
           table([["Load", "W"]] +
                 [[a, f"{b:.2f}"] for a, b in pb["loads"] + pb["extra"]] +
                 [["<b>Total at cruise</b>", f"<b>{pb['total']:.2f}</b>"]],
                 [120, 50]),
           P(f"Endurance {pb['endurance_min']:.0f} min on "
             f"{pb['usable_wh']:.1f} Wh (≥ 40). The budget file holds "
             f"{pb['budget_csv_total']} W; this design adds the buck and "
             "PIB losses (CR-12 updates it)."),
           P(f"Box in sun at 30 °C: {th['p_int']:.1f} W inside plus "
             f"{th['sun']:.1f} W of sun on the lid (the DUPLO plate shades "
             f"{th['shade'] * 100:.0f}%), lost from "
             f"{th['area']:.3f} m² at 7 W/m²K: {th['t_box']:.0f} °C against "
             "PWR-D19's 50 °C and B6's 60 °C RTL. Verified by V-10.")]
    st += [H2("5.9 Mission Control supply"),
           table([["USB load", "A"]] + [[a, f"{b:.2f}"] for a, b in
                                        us["loads"]] +
                 [["<b>Total</b> (limit with usb_max_current_enable=1)",
                   f"<b>{us['total']:.2f}</b> (≤ {us['limit']})"]],
                 [120, 50]),
           P(f"At {us['pi5_w']} W the 20 Ah bank lasts "
             f"{us['hours']:.1f} h (MC-001 ≥ 2.5 h).")]
    return st


def section_boards():
    st = [PageBreak(), H1("6. Custom boards")]
    st += [P("All three are 0.1-inch stripboard with the strips running "
             "left to right in the drawings (component side). A red cross is "
             "a strip cut (a drilled hole, or a knife cut between adjacent "
             "holes); a blue line is an insulated wire link. The layout "
             "tool puts each part in its own column and plans the rows so "
             "most nets are a single strip, then cuts and links what is "
             "left, and the result is rebuilt from the copper and compared "
             "with the netlist.")]
    info = {
        "PIB": "Power and interconnect board, 107 × 46 mm, on the "
               "mezzanine plate. The four high-current nets (PACK+, BUS+, "
               "VBAT_S, MOTOR+) are each one strip, reinforced with "
               "1.5 mm² tinned copper soldered along it (grey), and the "
               "16 AWG leads solder to pads E1-E4 on those strips. Q1 and "
               "Q2 lie flat with clip-on heatsinks.",
        "MIB": "Mission-computer interface board, 30 × 61 mm, the Pi "
               "Zero's footprint, on a stacking 2×20 socket. The header "
               "stands across the strips so odd pins feed left and even "
               "pins right (a knife cut between each pair).",
        "PNL": "Panel board, 112 × 61 mm, in the Mission Control case on a "
               "40-way ribbon to the Pi 5; the buttons are wired to its "
               "pads.",
    }
    for b, v in RES["boards"].items():
        s = v["stats"]
        st += [H2(f"6.{list(RES['boards']).index(b) + 1} {b}"),
               fig(FIG / f"{b}_layout.png", 80 if b == "MIB" else 170,
                   f"{b}: {s['size']}, "
                   f"{s['parts']} parts, {s['cuts']} cuts ({s['knife']} "
                   f"knife), {s['links']} links; verified: "
                   f"{len(v['errors'])} errors."),
               P(info[b])]
    return st


def section_harness():
    return [
        PageBreak(),
        H1("7. Harness and packaging"),
        fig(FIG / "box_layout.png", 170, "Figure 4. Inside the box. Floor: "
            "battery aft, ESCs and buck forward. Mezzanine plate at 30 mm: "
            "PIB aft, FC, Pi Zero and MIB forward at the camera window. "
            "The moisture comb sits at the front of the floor, the low "
            "point at design trim."),
        P(f"Battery to the nearest ESC: {RES['box']['battery_to_esc']:.0f} "
          "mm (PWR-D19 ≥ 30). No part overlaps another or the gland nuts. "
          "The reed switch sits on a bracket inside the aft wall, 15 mm "
          "under the lid's key dock, so the lid lifts off with nothing "
          "attached; the DS18B20 is at the top of the box (MCP-D26)."),
        H2("7.1 Wire list (summary)"),
        table([["Group", "Gauge", "Wires", "Note"],
               ["Pack leads", "16 AWG", "W01-W03", "fuse ≤ 50 mm"],
               ["Main path in the box", "16 AWG", "W20-W23", "XT60 → PIB → "
                "PDB → PIB"],
               ["ESC supplies", "18 AWG", "W24-W27", "XT30 pairs"],
               ["Buck feed and output", "20 AWG", "W29-W32", "PTC; "
                "Micro-Fit"],
               ["Signals in the box", "22-26 AWG", "W28, W33-W46, W52/53, "
                "W100-W107", "twisted pairs for DShot and rail sense"],
               ["Mast cable (box → handle)", "8 × 0.25 mm²", "W60-W67",
                "C3 via G3"],
               ["Mast lead (handle → masthead)", "8 × 0.25 mm²", "W70-W78",
                "C4 in the tube"],
               ["Motor cables", "3 × 0.75 mm²", "W800-W812", "C5/C6 via "
                "G1/G2 to the deck sockets"],
               ["Pod leads", "18 AWG", "W900-W912", "potted in the strut "
                "groove"],
               ["Main switch lead", "2 × 24 AWG", "W50/W51", "C2 via G4"]],
              [42, 28, 42, 58]),
        P("The full list, with every wire's ends, colour and length, is "
          "wirelist.csv in the zip.", "small"),
    ]


def section_matrix():
    groups = [("Design integrity", "D"), ("Power", "P"),
              ("Helm and mast", "H"), ("Mission computer", "M"),
              ("Mission Control", "C"), ("Safety", "S"), ("Cost", "X")]
    st = [PageBreak(), H1("8. Compliance matrix"),
          P("Computed by <i>boaty_elec/checks.py</i> at the commit on the "
            "cover. PASS: met. TEST: shown only on the bench or water; the "
            "test is named. FAIL: not met; the change request is named.")]
    for i, (t, pre) in enumerate(groups, 1):
        rs = [r for r in ROWS if r["id"].split("-")[0] == pre]
        if rs:
            st += [H2(f"8.{i} {t}"), status_table(rs)]
    return st


def section_crs():
    s70, s60 = C["sag70"], C["sag60"]
    cost = RES["cost"]
    top = sorted(RES["cost_lines"], key=lambda x: -x[2])[:8]
    return [
        PageBreak(),
        H1("9. Proposed change requests and cross-discipline actions"),
        P("Proposals only: nothing baselined changes until the owner "
          "accepts a CR at the CDR."),
        H2("CR-12  Power limit and power budget"),
        table([["", ""],
               ["Finding", f"P-06: at BATT_WATT_MAX 70 W the ESCs see "
                f"{s70['v_esc']:.2f} V at the critical battery, below "
                "PWR-D22's 7.5 V and the AM32's 7.2 V. The SDR analysis "
                "left out the harness, fuse, connectors and the two switch "
                f"MOSFETs ({(HR['r_up'] + HR['r_down']) * 1000:.0f} mΩ)."],
               ["Proposal", f"BATT_WATT_MAX 60 W: {s60['v_esc']:.2f} V at "
                f"the ESCs and {C['thrust']['60.0']:.2f} N of thrust (ENV-002 "
                "needs 1.1 N). Update power.csv with the buck and PIB "
                f"losses ({C['power']['total']:.2f} W at cruise)."],
               ["Impact", "software/params/boaty-mk1.parm (SITL re-run of "
                "the battery scenarios); SSS-HLM HLM-D43; KCL KF-02 and "
                "section 5; docs/budgets/power.csv."]],
              [30, 140], header=False),
        H2("CR-13  Key-switch circuit (IF-06, KCL KC-07)"),
        table([["", ""],
               ["Finding", "IF-06 and KC-07 specify a gate RC soft start "
                "(≈ 10 ms) and no rail discharge. Simulated, the gate RC "
                "gives a 24 A inrush in 2.6 ms, and without a discharge "
                "path the ESC capacitors hold the rail above 0.5 V for "
                f"{K['key_out_no_bleed']['t_off_ms']:.0f} ms, failing "
                "IF-06's own test (< 0.5 V within 100 ms)."],
               ["Proposal", "Replace the text with this circuit: gate-to-"
                "drain (Miller) soft start, 470 nF; active bleeder (Q3, "
                "10 Ω) pulsed by the key-out edge. Add the same soft start "
                "to the main switch (Q1). Results: inrush "
                f"{K['key_in']['i_peak']:.1f} A, key-out "
                f"{K['key_out']['t_off_ms']:.0f} ms."],
               ["Impact", "ICD IF-06; KCL KC-07; FMEA FM-22 (the bleeder "
                "is a pulse, so a shorted Q2 cannot burn it)."]],
              [30, 140], header=False),
        H2("CR-14  Cost cap"),
        table([["", ""],
               ["Finding", f"X-01: the SDR BOM (£{cost['kcl_total']}) has "
                "no lines for connectors, cables, board parts or wire. "
                f"This design adds £{cost['new_buy']:.0f} "
                f"(£{cost['new_nostock']:.0f} if wire, resistors, "
                f"stripboard and crimps come from stock): "
                f"£{cost['total_stock']:.0f} against the £{cost['cap']} "
                "cap. The mechanical design adds stock items too (MDD "
                "O-3)."],
               ["Largest items", "; ".join(f"{d} £{c:.0f}" for _r, d, c, _s
                                           in top)],
               ["Options", "(a) Raise the cap to £240 (boat and shore kit). "
                "(b) Replace the M12 mast connector with a cheaper sealed "
                "8-pin (≈ −£6) and the IP68 pod connectors with a cheaper "
                "keyed pair (≈ −£8), after the TBC-12 current check. "
                "(c) Hard-wire the pods (−£16), losing the tool-free pod "
                "swap (MEC-008). The owner decides; (a) with (b) is "
                "recommended."],
               ["Impact", "SRS CON-001 (via CR-08's price rule); ADD and "
                "KCL BOM."]], [30, 140], header=False),
        H2("9.1 Actions on the mechanical design (MDD Issue B)"),
        table([["Action", "Why"],
               ["Handle part: mounting holes for SW1 (12 mm, with the "
                "cover's anti-rotation tab) and the J40 M12 socket (PG9 / "
                "16 mm rear mount) on the uprights", "PWR-004 switch "
                "outside the box; tool-free mast removal with its cable"],
               ["Box: printed mezzanine plate on four stand-offs at 30 mm; "
                "reed-switch bracket bonded to the aft wall under the key "
                "dock", "the box layout (Figure 4)"],
               ["Stern segments: a clip holding each IP68 socket and its "
                "cap on the deck", "PWR-D16: no exposed live contact"],
               ["Pod strut: 4 mm groove for the motor lead, potted",
                "MDD O-6"],
               ["Masthead: a floor under the GNSS board with a cable "
                "gland-style exit into the tube", "strain relief (IF-22)"],
               ["Mass: the MDD mass table lacks the PIB, MIB, M12 and pod "
                "connectors and cables (estimate 60-100 g, to be weighed)",
                "feeds CR-09"]],
              [100, 70]),
        H2("9.2 TBCs"),
        table([["TBC", "Status"],
               ["TBC-08 LED data level", "Closed by design (D6); bench "
                "confirmation"],
               ["TBC-06 motor current", "Open: fuse and MOSFETs sized to "
                "the 8 A per ESC limit; bench measurement"],
               ["TBC-12 pod connector", "Open: requirement ≥ 10 A, keyed, "
                "IP68; candidate named in the BOM"],
               ["TBC-13 box", "Open (MDD): the layout fits the modelled "
                "box's 197 × 127 × 83 mm inside"]], [50, 120]),
    ]


def section_verify():
    return [
        H1("10. Verification on the bench"),
        table([["ID", "Test", "Pass"],
               ["E-V1", "Power up with the key out: rail < 0.5 V; key in: "
                "rail = battery − 0.2 V; key out: < 0.5 V within 100 ms "
                "(scope)", "IF-06"],
               ["E-V2", "Inrush on key-in and main-switch-on (current "
                "probe)", "≤ 8 A"],
               ["E-V3", "Arming refused with the key out (BATT2 < 9.0 V)",
                "V-13"],
               ["E-V4", "Calibrate BATT_VOLT_MULT and BATT_AMP_PERVLT at "
                "three loads", "± 1% V, ± 5% I"],
               ["E-V5", "Buck set-point and a full reverse-to-forward "
                "thrust step on a scope, at 12.6 V and 9.0 V", "IF-08"],
               ["E-V6", "Beacon: every pattern shows with 3.3 V data "
                "through the full cable", "TBC-08"],
               ["E-V7", "Compass reads over the mast cable at the helm's "
                "bus speed; motor-interference calibration", "IF-22"],
               ["E-V8", "Moisture: a wet cloth across the comb → B6 RTL",
                "FS-010"],
               ["E-V9", "ESC signal loss → stop ≤ 1 s", "V-09"],
               ["E-V10", "Box 60 min at 30 °C in sun, Pi throttled flag = "
                "0", "V-10"],
               ["E-V11", "Every board: continuity against the placement "
                "list before power; then the smoke test on a current-"
                "limited supply", "-"]], [16, 120, 34]),
        H2("10.1 Open items"),
        table([["ID", "Item"],
               ["EO-1", "Owner decisions on CR-12, CR-13, CR-14"],
               ["EO-2", "Confirm the PDB's battery-output pads are after "
                "its current sensor (V-01); if not, move the buck and key "
                "feed"],
               ["EO-3", "Confirm the candidate P-MOSFET's R<sub>DS(on)</sub>"
                " ≤ 6 mΩ from its datasheet before ordering"],
               ["EO-4", "Choose the pod connector (TBC-12) and the box "
                "(TBC-13)"],
               ["EO-5", "Rig L2 (iron bird) is this design on a board: "
                "build it first"]], [16, 154]),
    ]


def appendix():
    rows = [["Ref", "Value", "Board", "Part / candidate", "£"]]
    for p in RES["parts"]:
        if p["value"] == "pad":
            continue
        rows.append([p["ref"], p["value"], p["board"],
                     (p["mpn"] or "")[:70], f"{p['cost']:.2f}"])
    pin_tables = []
    for ref, title in (("U2", "Flight controller"), ("U6", "Pi Zero 2 W"),
                       ("U50", "Raspberry Pi 5")):
        pin_tables += [H2(f"B.{len(pin_tables) // 2 + 1} {title} ({ref})"),
                       table([["Pin", "Function", "Net"]] +
                             RES["pinmaps"][ref], [30, 80, 60])]
    return [PageBreak(), H1("Appendix A. Electrical parts"),
            table(rows, [14, 30, 18, 96, 12]),
            PageBreak(), H1("Appendix B. Pin maps"), *pin_tables]


def build():
    st = cover("Electrical Design<br/>Description",
               "Detailed electrical design of Boaty Mk1: power switching, "
               "schematics, custom boards, harness and calculations, for "
               "the Critical Design Review",
               [["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                ["Baseline", f"Upstream documents as tagged {BL.TAG} "
                 "(unchanged)"],
                ["Design", f"electrical/ at commit {RES['commit']}"],
                ["Compliance", f"{n('PASS')} pass, {n('TEST')} by test, "
                 f"{n('FAIL')} not met (CR-12 to CR-14 proposed)"]])
    st += control_and_contents(
        [["A", DATE, "First issue, draft for the CDR.",
          "Claude (drafted)"]],
        "Review with the electrical zip open: the schematics PDF, the wire "
        "list and the board layouts. Section 2 has the decisions; section "
        "8 every check; section 9 the change requests.")
    st += (section_intro() + section_summary() + section_arch() +
           section_circuits() + section_calcs() + section_boards() +
           section_harness() + section_matrix() + section_crs() +
           section_verify() + appendix())
    doc = Doc(OUT, DOC_ID, "Electrical Design Description", ISSUE)
    doc.multiBuild(st)
    print("wrote", OUT, f"{n('PASS')} pass, {n('TEST')} test, "
          f"{n('FAIL')} fail")


if __name__ == "__main__":
    build()
