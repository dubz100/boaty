"""Build BOATY-MDD-001, the Mechanical Design Description.

Run:  python3 docs/mdd/src/build_mdd.py

Every number comes from mechanical/results/mech_results.json and every
picture from docs/mdd/figures, both written by mechanical/build_cad.py
(which needs CadQuery). This build needs neither, so CI can run it.
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
                    P, PageBreak, Spacer, callout,
                    colors, control_and_contents, cover, fig, mm, table, Doc)

OUT = HERE.parent / "Boaty_Mechanical_Design_Description.pdf"
FIG = HERE.parent / "figures"
RES = json.loads((ROOT / "mechanical" / "results" /
                  "mech_results.json").read_text())
DOC_ID = "BOATY-MDD-001"
ISSUE = BL.issue("MDD", "draft for CDR")
DATE = BL.DATE
D = RES["data"]
PR = RES["params"]
ROWS = RES["rows"]
FD, FL = D["float_design"], D["float_light"]
TRAY_L = PR["TRAY_X"][1] - PR["TRAY_X"][0]
BOX_OVER = PR["BOX_X0"] + PR["BOX_L"] - PR["TRAY_X"][1]
HANDLE_W = next(p["size"] for p in RES["parts"] if p["key"] == "HUL-402")[1]


def row(rid):
    return next(r for r in ROWS if r["id"] == rid)


def n(status):
    return sum(r["status"] == status for r in ROWS)


STATUS_T = {"PASS": GREEN_T, "FAIL": ORANGE_T, "TEST": colors.HexColor(
    "#e8f1fb"), "INFO": colors.white}


def status_table(rows, widths=(13, 27, 52, 34, 28, 16)):
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
    return table(data, list(widths), style_extra=extra)


# ======================================================================
def section_intro():
    return [
        H1("1. Introduction"),
        H2("1.1 Purpose and status"),
        P("This document describes the detailed mechanical design of Boaty "
          "Mk1: every part, how the parts go together, and the analysis "
          "that shows whether the design meets the mechanical requirements "
          "allocated to it. It is the mechanical input to the Critical "
          "Design Review (CDR), which the owner has chosen to hold before "
          "anything is bought."),
        P(f"It is a <b>draft for the CDR</b>. The system documentation was "
          f"baselined at the SDR (tag <i>{BL.TAG}</i>) and is not changed "
          "here. Where the design cannot meet a baselined requirement, "
          "section 10 proposes a numbered change request for the owner to "
          "accept or reject at the CDR."),
        H2("1.2 Scope"),
        P("In scope: the hull and structure (SSS-HUL), the thruster pods' "
          "mechanical parts (SSS-PRP), the recovery and signalling hardware "
          "(SSS-REC), and the mechanical interfaces IF-16 to IF-20. Not in "
          "scope: the electronics inside the box, wiring and connector "
          "selection (these are modelled only as masses and envelopes), "
          "and the bank kit."),
        H2("1.3 The CAD"),
        P("The design is a parametric CadQuery model (Python). One file, "
          "<i>mechanical/boaty_cad/params.py</i>, holds every dimension "
          "with the requirement it answers. The part builders, the "
          "assembly, the mass properties, the hydrostatics and the "
          "compliance checks all read it. <i>mechanical/build_cad.py</i> "
          "rebuilds everything: it writes STEP and STL files, the figures "
          "in this document, and the results file this document is built "
          f"from. This issue was built from commit {RES['commit']} with "
          f"CadQuery {RES['cadquery']}."),
        P("Frame: <b>x</b> forward from the stern transom, <b>y</b> to "
          "port from the boat centreline, <b>z</b> up from the keel line "
          "(the flat bottom of the mid and stern segments). All dimensions "
          "are in mm, masses in g."),
        H2("1.4 References"),
        table([["Ref", "Document"],
               ["[1]", BL.full("SRS") + " System Requirements Specification"],
               ["[2]", BL.full("ADD") + " Architecture Design Document"],
               ["[3]", BL.full("ICD") + " Interface Control Document "
                "(IF-16 to IF-20)"],
               ["[4]", f"Subsystem specifications: {BL.sss_all()}"],
               ["[5]", BL.full("KCL") + " Key Component List"],
               ["[6]", BL.full("SDR") + " System Design Review"],
               ["[7]", "EN 71-1 small-parts cylinder (Ø31.7 mm, 25.4 to "
                "57.1 mm deep)"]], [14, 156]),
    ]


def section_summary():
    fails = [r for r in ROWS if r["status"] == "FAIL"]
    rows = [["Quantity", "Design", "Requirement"],
            ["Mass, ready to sail", f"{D['mass']:.0f} g",
             "≤ 1800 g (MEC-002)"],
            ["Design mass (+ 300 g on the deck)", f"{FD['mass']:.0f} g",
             "sized at 2100 g"],
            ["Length × beam × height", " × ".join(
                f"{v:.0f}" for v in D["envelope"]) + " mm",
             "≤ 620 × 360 × 500 (HUL-D01)"],
            ["Mast off", " × ".join(f"{v:.0f}" for v in
                                    D["envelope_mast_off"]) + " mm",
             "≤ 650 × 400 × 250 (HUL-D21)"],
            ["Hull draft; least freeboard (design mass)",
             f"{FD['draft']:.1f}; {FD['freeboard']:.1f} mm",
             "≤ 35; ≥ 50 (HUL-D07)"],
            ["Trim light / design (bow down −)",
             f"{FL['trim']:+.1f}° / {FD['trim']:+.1f}°", "± 3° (HUL-D20)"],
            ["Heel, 300 g at the deck edge", f"{D['heel_edge']:.1f}°",
             "≤ 10° (HUL-D08)"],
            ["Max righting arm; vanishing angle",
             f"{D['gz_max'][1]:.0f} mm at {D['gz_max'][0]:.0f}°; "
             f"{D['vanish']:.0f}°", "no capsize (HUL-D09)"],
            ["Reserve buoyancy (2 segments breached)",
             f"{D['reserve_g']:.0f} g", "≥ 3150 g (HUL-D06)"],
            ["Largest guard opening", f"{max(D['openings'].values()):.2f} mm",
             "< 8 mm probe (MEC-010)"],
            ["GNSS to power wiring", f"{D['gnss_sep']:.0f} mm",
             "≥ 150 mm (MEC-013)"],
            ["Fluorescent share of the top view",
             f"{D['hivis_share']:.0f}%", "≥ 50% (REC-D01)"]]
    return [
        H1("2. Summary"),
        P(f"The design meets <b>{n('PASS')}</b> of the {len(ROWS)} checks "
          f"in the compliance matrix (section 9). <b>{n('TEST')}</b> can "
          "only be shown by test on the first prints and are listed with "
          f"their verification. <b>{n('FAIL')}</b> are not met; each has "
          "a proposed change request in section 10."),
        table(rows, [66, 50, 54]),
        Spacer(1, 3 * mm),
        callout("<b>Decisions for the owner at the CDR.</b><br/>"
                + "<br/>".join(f"• {r['id']} {r['refs']}: {r['text']} is "
                               f"{r['value']} against {r['limit']} → "
                               f"<b>{r['cr']}</b>" for r in fails)
                + "<br/>The one that matters is mass (CR-09): the boat "
                f"comes out about {100 * (D['mass'] / 1800 - 1):.0f}% "
                "heavier than the SRS allows, almost "
                "all of it in the hull. Everything that depends on mass "
                "(draft, freeboard, heel, stability, trim) has been "
                "checked at the real mass and passes.",
                ORANGE, ORANGE_T),
    ]


def section_config():
    return [
        PageBreak(),
        H1("3. General arrangement"),
        fig(FIG / "iso.png", 165, "Figure 1. Boaty Mk1, from forward to "
            "starboard. Fluorescent orange: hull segments, handle, hood, "
            "hoop (REC-D01). Green: DUPLO deck. Clear: the bought box."),
        P("Two hulls of three foam-cored segments each sit 270 mm apart. "
          "Two aluminium crossbeams bolt to the mid segments only, so the "
          "mid segments, the beams and everything on them form a rigid "
          "core. The bow and stern segments and the pods clip onto that "
          "core without tools: these are the crew's assembly steps "
          "(HUL-D25). The box rides on a saddle tray across both beams. "
          "The mast stands in a socket on the aft beam, and the socket "
          "part is also the carry handle, "
          f"{row('S-01')['value'].split(';')[0]} from the centre of "
          "gravity."),
        fig(FIG / "side.png", 170, "Figure 2. Side elevation from "
            f"starboard, with the design waterline ({FD['mass']:.0f} g, "
            f"trim {FD['trim']:+.1f}°) and the light waterline "
            f"({FL['mass']:.0f} g)."),
        PageBreak(),
        fig(FIG / "top.png", 150, "Figure 3. Plan view (the view the "
            "REC-D01 fluorescent share is measured on)."),
        fig(FIG / "front.png", 120, "Figure 4. From ahead: the camera "
            "hood, the pods under the sterns, the masthead."),
        PageBreak(),
        fig(FIG / "exploded.png", 170, "Figure 5. Exploded: end segments, "
            "pods, beams, tray, box, lid, deck and mast."),
        fig(FIG / "iso_aft.png", 130, "Figure 6. From aft to port: pod "
            "guards, the glands on the box's aft face, the hoop."),
        H2("3.1 Main dimensions"),
        table([["Item", "Value", "Source"],
               ["Hull section at the joints (IF-16)",
                f"{PR['B']:.0f} wide × {PR['D']:.0f} deep; bilge radius "
                f"{PR['R_BILGE']:.0f}", "closes TBC-11"],
               ["Segment lengths stern / mid / bow",
                f"{PR['L_STERN']:.0f} / {PR['L_MID']:.0f} / "
                f"{PR['L_BOW']:.0f}", "HUL-D02"],
               ["Bow keel rise at the stem", f"{PR['BOW_KEEL_RISE']:.0f}",
                "weed and wave entry"],
               ["Hull centreline spacing", f"{2 * PR['HULL_Y']:.0f}",
                "HUL-D04"],
               ["Crossbeams (x)", ", ".join(f"{x:.0f}" for x in
                                           PR["BEAM_X"]), "on the mid "
                "segments"],
               ["Box, external", f"{PR['BOX_L']:.0f} × {PR['BOX_W']:.0f} × "
                f"{PR['BOX_H']:.0f}, aft face at x {PR['BOX_X0']:.0f}",
                "IF-18"],
               ["Mast", f"Ø{PR['MAST_D']:.0f} × {PR['MAST_T']:.0f} Al at x "
                f"{PR['MAST_X']:.0f}", "IF-19"],
               ["Prop axis; duct", f"z {PR['POD_AXIS_Z']:.0f}; Ø"
                f"{PR['DUCT_ID']:.0f} / {PR['DUCT_OD']:.1f}, x "
                f"{PR['DUCT_X'][0]:.0f} to {PR['DUCT_X'][1]:.0f}", "IF-17"],
               ["Centre of gravity (light)", ", ".join(
                   f"{c:.0f}" for c in D["cg"]), "section 5"]],
              [58, 70, 42]),
    ]


def _part_list(keys):
    parts = {p["key"]: p for p in RES["parts"]}
    rows = [["Part", "Name", "Qty", "Kind", "Material", "Size (mm)"]]
    for k in keys:
        p = parts[k]
        rows.append([k, p["name"], str(p["qty"]), p["kind"], p["material"],
                     " × ".join(f"{v:.0f}" for v in p["size"])])
    return table(rows, [18, 70, 10, 17, 18, 37])


def section_parts():
    st = [PageBreak(), H1("4. Part design")]
    st += [H2("4.1 Hull segments (HUL-1, IF-16)"),
           P("Each segment is a thin ASA shell, open at every joint face, "
             "with a core of closed-cell XPS foam profiled to the section "
             "(hot-wire cut from 50 mm board, bonded in two layers, gaps "
             "filled with PU foam) and trimmed flush with the joint face. "
             "The foam is the core of a sandwich: it stabilises the 1.2 mm "
             "skin and gives the buoyancy that survives a breach "
             "(HUL-D05/D06). Each of the three designs is symmetric about "
             "its own centreline, so the same part serves both hulls."),
           fig(FIG / "hull_section.png", 170, "Figure 7. One hull cut on "
               "its centreline: shells (orange), foam cores (blue), the "
               "thumb-screw lugs at both joints (the dowels lie off this plane), "
               "the dovetail rail and the "
               "pod."),
           P("<b>Lines.</b> Mid and stern: a constant section, "
             f"{PR['B']:.0f} × {PR['D']:.0f} mm with an {PR['R_BILGE']:.0f} "
             f"mm bilge and a {PR['R_DECK']:.0f} mm deck edge. The bow "
             f"keeps the full section for {PR['BOW_FLAT']:.0f} mm, then "
             "narrows to a 10 mm rounded stem while the keel rises "
             f"{PR['BOW_KEEL_RISE']:.0f} mm, so weed and small waves ride "
             "under it."),
           P("<b>Joint (IF-16).</b> The last 6 mm of each open end is a "
             "4 mm flange; the mating faces are flat. Two Ø8 dowels, bonded "
             "10 mm into the bow and stern segments, locate in 8.3 mm holes "
             "in the mid segment low in the section. Two captive M12 × 1.75 "
             "printed thumb-screws with Ø35 knurled knobs sit on the deck, "
             "7 mm apart: the knob is on the end segment, whose lug is "
             "threaded so the screw threads through it once and then turns "
             "freely on its Ø9 neck (it cannot fall out, CHD-001), and "
             "screws into the mid segment's lug. Hand-tight (20 N at the "
             "rim) they clamp the joint at about "
             f"{D['joint']['preload']:.0f} N each, so a joint carries "
             f"{D['joint']['m_cap']:.1f} N·m of sag before it opens, "
             f"against {D['joint']['m_dem']:.1f} N·m at three times design "
             "weight with the boat supported at its ends."),
           P("<b>Other features.</b> Mid segment: four M4 heat-set insert "
             "bosses under the beams; the REC-D05 tracker pocket (Ø36 × 12, "
             "O-ring cap on three M3 screws); a 70 × 24 label recess on each "
             "side (REC-D04). Stern segment: the IF-17 dovetail rail on a "
             "solid backing block in the transom, and two cable clips on "
             "each deck edge for the motor lead."),
           _part_list(["HUL-101", "HUL-102", "HUL-103", "HUL-104",
                       "HUL-105", "HUL-106"])]
    st += [H2("4.2 Crossbeams (HUL-2)"),
           P("20 × 10 × 1.5 mm 6063 aluminium rectangular tube, 300 long, "
             "lying flat on the mid segments' decks. Two M4 A4 screws at "
             "each end go into heat-set inserts in the segment (an adult, "
             "tool step: the beams are not part of the crew's assembly). "
             "The top face carries the M3 rail grid (two rows at 10 mm "
             "pitch) named in SSS-HUL; tray and handle bolt through it with "
             "nylon-insert nuts under the tube. Printed caps are bonded "
             "into the tube ends. A printed beam would not fit the 200 mm "
             "build volume in one piece."),
           _part_list(["HUL-201", "HUL-202"])]
    st += [H2("4.3 Electronics box, saddle and latches (HUL-3, IF-18)"),
           P(f"The box is a bought clip-lock food box, modelled at "
             f"{PR['BOX_L']:.0f} × {PR['BOX_W']:.0f} × {PR['BOX_H']:.0f} "
             "external, 1.6 mm walls. Its only modifications are four "
             f"{PR['GLAND_HOLE']} mm holes in the aft face for the PG7 "
             f"glands at {PR['GLAND_PITCH']:.0f} mm pitch, and a "
             f"Ø{PR['WINDOW_D']:.0f} window hole in the front, covered by a "
             "2 mm acrylic disc bonded outside. The final box choice sets "
             "BOX_* in the parameters; the tray follows (TBC-13)."),
           P(f"The printed saddle tray ({TRAY_L:.0f} long) "
             "spans both beams, bolted with four M3 screws through the "
             "rail. Side walls and an aft stop locate the box; the box "
             f"overhangs the tray by {BOX_OVER:.0f} mm at the front, over "
             "the forward beam. Behind the box a 38 mm gap leaves room for the "
             "glands, and a slot in the tray lets the leads drop to the "
             "beam. Two over-centre latch levers pivot on M3 pins in bosses "
             "on the tray sides and hook keepers bonded to the box. The "
             "lever passes centre by 2 mm and has a flexure detent sized "
             "for ≥ 40 N at the tab (HUL-D24): an adult action, measured "
             "on the bench."),
           P("<b>Key dock.</b> A printed cup bonded to the lid over the "
             "reed switch, with KEY raised in its floor. The key is a 40 × "
             "36 × 9 mm fob with a Ø20 magnet bonded in and a lanyard "
             "slot; at 36 mm across it cannot enter the small-parts "
             "cylinder."),
           _part_list(["HUL-301", "HUL-302", "HUL-303", "HUL-304",
                       "HUL-305", "HUL-306", "HUL-307", "HUL-308"])]
    st += [H2("4.4 Camera hood (HUL-5)"),
           P(f"A three-sided hood bonded to the box front around the "
             f"window, projecting {PR['HOOD_OVERHANG']:.0f} mm (HUL-D19 asks "
             "≥ 15). It is open at the front and underneath, so the window "
             "can be wiped with a cloth and rain drains out. The lens "
             f"centre is {PR['LENS_Z_ABOVE_BOX']:.0f} mm above the box "
             f"floor: {row('H-04')['value']} above the water at design "
             "mass. The camera faces along the keel line, so its tilt is "
             "the boat's trim."),
           _part_list(["HUL-501", "HUL-502", "KC-11"])]
    st += [H2("4.5 DUPLO deck (IF-20)"),
           P(f"A {PR['PLATE_T']} mm plate with {PR['STUD_NY']} × "
             f"{PR['STUD_NX']} studs at {PR['STUD_PITCH']:.0f} mm pitch, "
             f"Ø{PR['STUD_D']} × {PR['STUD_H']} (TBC-14: tune by test print "
             "against genuine bricks). The studs are bored through so rain "
             "drains to the lid and runs off (HUL-D13). Four clip arms snap "
             "over the lid's long edges: the child lifts the plate off for "
             "the adult to open the box, and pushes it back (≤ 20 N, "
             "HUL-D25). The plate sits forward on the lid, leaving the key "
             "dock clear."),
           _part_list(["HUL-401"])]
    st += [H2("4.6 Mast, handle and masthead (HUL-4, IF-19)"),
           P("One printed part is both the mast step and the carry handle "
             f"({HANDLE_W:.0f} mm across, within the build volume). It sits on the aft "
             "beam on three feet, located by cheeks either side of the "
             "tube and bolted with M3 screws through the beam. The centre "
             "tower is the 50 mm deep IF-19 socket; a captive M8 printed "
             "thumb-screw with a Ø24 knob holds the mast. A Ø22 grip runs "
             "either side of the tower at "
             f"{PR['GRIP_Z'] - PR['D'] - PR['BEAM_H']:.0f} mm above the "
             "beam, with 41 mm finger clearance. The grip centres are "
             f"{row('S-01')['value']} from the centre of gravity (HUL-D21: "
             "± 50)."),
           P(f"The mast is Ø16 × 1 aluminium tube, "
             f"{PR['MAST_TOP_Z'] - PR['MAST_BOTTOM_Z']:.0f} long, and is "
             "also the conduit for the GNSS and LED lead, which leaves "
             "through a slot at the foot of the socket. The masthead is "
             "one translucent PETG print: a sleeve on the tube, a ring "
             "diffuser over the WS2812 LEDs (REC-D03) and a hollow dome "
             "over the GNSS/compass board. The dome's top is "
             f"{D['gnss_top_above_wl']:.0f} mm above the design waterline. "
             "IF-19 gives ≈ 450, but the ≤ 500 mm height limit, measured "
             "from the pod bottom, does not leave room for it (CR-10)."),
           _part_list(["HUL-402", "HUL-403", "HUL-404", "REC-104"])]
    st += [H2("4.7 Recovery and signalling (REC)"),
           P(f"<b>Hoop.</b> A Ø{PR['HOOP_ID']:.0f} internal ring of "
             f"{PR['HOOP_SECTION']:.0f} mm round section, horizontal and "
             "behind the mast, so a hook on the bank pole drops into it "
             f"from above. It is part of a collar at z {PR['COLLAR_Z']:.0f}, "
             "pinned to the tube by one M4 A4 cross-bolt, so it cannot slip "
             "or turn. The hoop is low on the mast: a 50 N pull puts "
             f"{D['socket_moment']:.1f} N·m on the socket, not the 15 N·m "
             "the ICD estimated (design 30)."),
           P("<b>Flag.</b> A Ø8 printed staff, 190 long, with a Ø16 ball "
             "cap (REC-D08), plugs into a socket on the collar: this is one "
             "of the child's assembly steps. The 120 × 80 fluorescent "
             "ripstop flag flies from its top, "
             f"{row('E-03')['value'].split('; ')[-1]} above the water, "
             "below the GNSS."),
           P("<b>Hi-vis.</b> The hull segments are printed in fluorescent "
             "orange ASA; the handle, hood, key dock and hoop in "
             "fluorescent PETG. Measured on the rendered plan view, "
             f"{D['hivis_share']:.0f}% of the visible top is fluorescent "
             "(REC-D01 ≥ 50%)."),
           _part_list(["REC-101", "REC-102", "REC-103"])]
    st += [H2("4.8 Thruster pod (PRP-1, IF-17)"),
           P("The pod slides sideways onto the transom's 60° dovetail rail "
             "(20 × 40 mm, 0.3 mm clearance) and a tooth on a flexure "
             "tongue in the pod's back wall drops into a detent at the "
             "centre of the rail. To release it, an adult pulls the tab "
             "aft and slides the pod off. Because the detent is central, "
             "one pod design fits either hull from either side."),
           P("A strut, its leading edge swept back "
             f"{PR['STRUT_SWEEP']:.0f}° (PRP-D10), carries the duct "
             f"(Ø{PR['DUCT_ID']:.0f} inside, "
             f"{(PR['DUCT_OD'] - PR['DUCT_ID']) / 2:.1f} mm wall) whose top "
             "is 4 mm under the keel. "
             "The duct runs 8 mm under the hull; the rest is behind the "
             "transom. A Ø28 nacelle with a conical nose carries the "
             "2205-class motor on four M2 screws, facing aft. Three inlet "
             f"vanes at {PR['VANE_ANGLE']:.0f}° hold the nacelle in the "
             "duct. The prop (Ø35, three skewed blades) sits between the "
             "bell and the rear guard. The guard is a hub, one ring and "
             "eight bars, held by two M2.5 screws: removing it is a tool "
             "step (PRP-D14)."),
           table([["Opening a probe could enter", "Largest circle (mm)"]] +
                 [[k, f"{v:.2f}"] for k, v in D["openings"].items()],
                 [120, 50]),
           Spacer(1, 2 * mm),
           P(f"Every opening is under 6 mm, against the 8 mm probe "
             f"(MEC-010). The pod weighs {D['mass_pod']:.0f} g with its "
             "motor (PRP-D13 ≤ 75)."),
           _part_list(["PRP-101", "PRP-102", "PRP-103", "KC-04"])]
    st += [PageBreak(), H2("4.9 Part gallery"),
           fig(FIG / "parts_1.png", 170, "Figure 8. Part designs (1 of 3)."),
           fig(FIG / "parts_2.png", 170, "Figure 9. Part designs (2 of 3)."),
           fig(FIG / "parts_3.png", 170, "Figure 10. Part designs (3 of 3).")]
    return st


def section_mass():
    items = D["mass_items"]
    agg: dict = {}
    for i in items:
        a = agg.setdefault(i["name"], dict(n=0, m=0.0, basis=i["basis"],
                                            group=i["group"]))
        a["n"] += 1
        a["m"] += i["mass"]
    rows = [["Item", "Qty", "Each (g)", "Total (g)", "Basis"]]
    for name, a in sorted(agg.items(), key=lambda kv: -kv[1]["m"]):
        rows.append([name, str(a["n"]), f"{a['m'] / a['n']:.1f}",
                     f"{a['m']:.0f}", a["basis"]])
    rows.append(["<b>Total</b>", "", "", f"<b>{D['mass']:.0f}</b>", ""])
    return [
        PageBreak(),
        H1("5. Mass properties"),
        P("Printed parts are weighed as a slicer prints them: walls and "
          "top and bottom skins solid, 3 perimeters (1.2 mm), 25% gyroid "
          "infill inside solid features (lugs, bosses, blocks). Thin "
          "shells come out solid. ASA 1.07, PETG 1.27, XPS foam 0.030, "
          "aluminium 2.70 g/cm³. Bought items use catalogue masses; the "
          "electronics use the ADD mass table. The electronics are "
          "placed in the box with the battery low and aft, which brings "
          "the centre of gravity back to the handle and keeps the trim "
          "within ± 3°."),
        fig(FIG / "mass.png", 150, "Figure 11. Mass by group."),
        table(rows, [62, 10, 16, 16, 66]),
        Spacer(1, 2 * mm),
        P(f"Centre of gravity (light): x {D['cg'][0]:.0f}, y "
          f"{D['cg'][1]:.0f}, z {D['cg'][2]:.0f} mm. Hull and structure "
          f"(HUL-D03 scope) {D['mass_hul']:.0f} g."),
        callout(f"<b>Mass is the design's main problem.</b> The boat is "
                f"{D['mass']:.0f} g against 1800 g. The ADD allowed 500 g "
                "for the six segments with their foam; the CAD gives "
                f"{D['mass_groups']['Hull segments, foam, joints']:.0f} g "
                "for segments, foam and joint hardware. The shell is set by "
                "area, not detail: two hulls of this size have about 0.4 m² "
                "of skin, and 1.2 mm of ASA over that is about 500 g "
                "before any foam. Section 10 (CR-09) gives the options.",
                ORANGE, ORANGE_T),
    ]


def section_hydro():
    gz = D["gz"]
    return [
        PageBreak(),
        H1("6. Hydrostatics and stability"),
        P("The underwater body is the two hulls' outer surfaces plus the "
          "pods' material (the ducts flood), tessellated at 0.15 mm. For "
          "any water plane the displaced volume and its centroid come "
          "from signed tetrahedra clipped at the plane, which is exact "
          "for the mesh. Sinkage and trim are solved together so that "
          "buoyancy equals weight and the trimming moment is zero; heel "
          "is then stepped with sinkage and trim free. Fresh water, "
          "1.000 g/cm³. The volume inside the hull envelope is "
          f"{D['hull_volume_l']:.2f} L."),
        table([["Condition", "Mass (g)", "Trim", "Hull draft (mm)",
                "Least freeboard (mm)", "Water at transom / stem"],
               ["Light (ready to sail)", f"{FL['mass']:.0f}",
                f"{FL['trim']:+.2f}°", f"{FL['draft']:.1f}",
                f"{FL['freeboard']:.1f}",
                f"{FL['wl_aft']:.0f} / {FL['wl_fwd']:.0f}"],
               ["Design (+ 300 g on the deck)", f"{FD['mass']:.0f}",
                f"{FD['trim']:+.2f}°", f"{FD['draft']:.1f}",
                f"{FD['freeboard']:.1f}",
                f"{FD['wl_aft']:.0f} / {FD['wl_fwd']:.0f}"]],
              [42, 20, 18, 26, 30, 34]),
        P("Draft is the deepest point of the hull below the water; the "
          f"pods reach deeper ({row('H-01')['note']}). Water heights are "
          "above the keel line; at the stem the keel itself is "
          f"{PR['BOW_KEEL_RISE']:.0f} mm up."),
        H2("6.1 Heel and stability"),
        fig(FIG / "gz.png", 150, "Figure 12. Righting arm at design mass, "
            "load on the centreline."),
        P(f"300 g at the outboard deck edge heels the boat "
          f"{D['heel_edge']:.1f}° (MEC-004 ≤ 10°). The righting arm peaks "
          f"at {D['gz_max'][1]:.0f} mm at {D['gz_max'][0]:.0f}°, when one "
          f"hull lifts clear, and does not vanish until {D['vanish']:.0f}°. "
          f"The maximum righting moment is {D['rm_max']:.2f} N·m."),
        P(f"<b>Turns (HUL-D09).</b> A 1.5 m/s turn on a 1 m radius puts "
          f"{D['turn_moment']:.2f} N·m of heeling moment on the boat (side "
          "force at the centre of gravity, resisted at half the draft). "
          f"That is balanced within {row('H-08')['note'].split('< ')[1]}, "
          "well short of the peak. <b>Waves:</b> a 100 mm wave of 1 m "
          f"length has a slope of about {D['wave_slope']:.0f}°, far inside "
          "the range of positive stability. Both are confirmed in the "
          "pool."),
        P(f"<b>Towing (REC-005).</b> Pulled sideways by the hoop, the boat "
          f"would capsize at {D['tow']['capsize_force']:.0f} N (lever "
          f"{D['tow']['lever']:.0f} mm). Towed through the water at 0.5 "
          f"m/s, side-on, the pull equals the drag, about "
          f"{D['tow']['drag_side']:.1f} N. A 50 N snatch is a strength "
          "case for the hoop and socket (section 7), not a steady tow: "
          "the operations manual already says to tow slowly."),
        H2("6.2 Damaged buoyancy"),
        P(f"With the box flooded (it gives no buoyancy in any case) and "
          f"the two largest segments breached, each losing the 10% of its "
          f"cavity that HUL-D05 allows to be unfilled, the hulls can still "
          f"support {D['reserve_g']:.0f} g: "
          f"{D['reserve_g'] / FD['mass']:.1f} times the design mass, "
          "against 1.5 (HUL-D06, REC-001)."),
        table([["Heel (°)"] + [str(h) for h, _ in gz[::2]],
               ["GZ (mm)"] + [f"{g:.0f}" for _, g in gz[::2]]],
              [18] + [15.2] * len(gz[::2]), header=False),
    ]


def section_structure():
    j = D["joint"]
    return [
        H1("7. Structural checks"),
        P("Load cases from the ICD: design mass 2.1 kg, factor 3. Here "
          f"they are taken at the real design mass, {FD['mass']:.0f} g."),
        table([["Case", "Calculation", "Result"],
               ["Carry by the handle, 3 × design weight (HUL-D21)",
                "Aft beam carries the load at its centre, hulls hang from "
                "its ends; 20 × 10 × 1.5 tube",
                f"{D['beam_stress']:.0f} MPa against 160 MPa yield"],
               ["Segment joint, boat supported at bow and stern, 3 × "
                "design weight (IF-16)",
                "Hand-tight preload opens the joint only when the sag "
                "moment beats preload × lever from the screws to the "
                "lower kern",
                f"{j['m_cap']:.1f} N·m capacity against "
                f"{j['m_dem']:.1f} N·m"],
               ["50 N on the hoop (REC-005, IF-19)",
                "Moment at the socket foot; hoop ring as a cantilever",
                f"{D['socket_moment']:.1f} N·m (IF-19 design 30); hoop "
                f"{D['hoop_stress']:.0f} MPa"],
               ["Pod: 10 N thrust × 3, 20 N at the tip (IF-17)",
                "Dovetail flanks bear the moment over 20 mm",
                "≈ 100 N on 40 mm of flank: low stress; pull test"],
               ["Mast tube in the socket", "Ø16 × 1 tube at the socket "
                "lip under 50 N", "≈ 6 MPa"]], [52, 70, 48]),
        P("The printed parts' strengths are all well inside PETG's "
          "≈ 50 MPa except the hoop, which the simple cantilever puts "
          "close to the limit. The real ring shares the load round both "
          "sides, so it is marked for the pull test rather than failed."),
    ]


def section_safety():
    sp = D["small_parts"]
    rows = [["Part", "Fits the cylinder?", "Why it is acceptable"]]
    why = {"HUL-105": "bonded into the segment; never loose",
           "HUL-202": "bonded into the beam end",
           "HUL-305": "bonded to the box",
           "HUL-306": "screwed into the box wall (adult)",
           "HUL-106": "held by three M3 screws",
           "PRP-102": "held by two M2.5 screws (adult, tool)",
           "PRP-103": "inside the guard; tool to reach",
           "KC-11": "inside the sealed box",
           "HUL-304": "pinned to the tray",
           "HUL-307": "bonded to the lid",
           "HUL-404": "captive in the socket"}
    for k, name, child in sp:
        rows.append([f"{k} {name}", "yes", why.get(k, "adult-only part")])
    return [
        H1("8. Child safety and guarding"),
        P("The child-handled parts (HUL-D22) are the six segments, the "
          "thumb-screws, the DUPLO plate, the pod bodies and the flag "
          "staff. None fits the EN 71-1 small-parts cylinder in any "
          "orientation (CHD-001). The smaller parts that would fit are "
          "all bonded, captive, screwed on or inside the box:"),
        table(rows, [70, 26, 74]),
        Spacer(1, 2 * mm),
        P("Edges the child touches carry ≥ 0.6 mm fillets or chamfers in "
          "the model: knobs 1.5 mm, deck edges 6 mm, clips and latch tabs "
          "0.6 to 1.5 mm (HUL-D23). Segment joints close face to face, "
          "and the knobs sit 7 mm apart with no gap a finger can be "
          "caught in when they turn. These are confirmed by inspection "
          "on the first prints. The props are behind the inlet annulus "
          "and the rear guard, whether a pod is fitted or not (PRP-D14)."),
    ]


def section_matrix():
    groups = [("Mass", "M"), ("Geometry and printing", "G"),
              ("Buoyancy and hydrostatics", "BH"), ("Structure", "S"),
              ("Propulsion guarding and mount", "P"),
              ("Mast, GNSS and flag", "E"), ("Interfaces", "I"),
              ("Child safety", "C"), ("Visibility", "V")]
    st = [PageBreak(), H1("9. Compliance matrix"),
          P("Every check below is computed by <i>boaty_cad/checks.py</i> "
            "from the CAD at the commit on the cover. PASS: met. TEST: "
            "the CAD cannot show it; the verification in section 11 "
            "will. FAIL: not met; the change request is named.")]
    for title, pre in groups:
        rows = [r for r in ROWS if r["id"].split("-")[0] in pre]
        if rows:
            st += [H2(f"9.{groups.index((title, pre)) + 1} {title}"),
                   status_table(rows)]
    return st


def section_crs():
    m_seg = D["mass_groups"]["Hull segments, foam, joints"]
    return [
        PageBreak(),
        H1("10. Proposed change requests"),
        P("These are proposals. Nothing baselined changes until the owner "
          "accepts a CR at the CDR; then the documents named are reissued "
          "and the register is updated in the same commit."),
        H2("CR-09  Mass limit and allocations"),
        table([["", ""],
               ["Finding", f"M-01: {D['mass']:.0f} g against MEC-002's "
                f"1800 g. M-02: hull and structure {D['mass_hul']:.0f} g "
                f"against HUL-D03's 1000 g. Segments, foam and joints "
                f"{m_seg:.0f} g against the ADD's 500 g."],
               ["Cause", "The ADD mass table was an estimate made before "
                "any hull lines existed. The skin area of two "
                f"{PR['X_STEM']:.0f} mm hulls "
                "with 50 mm of freeboard is about 0.4 m²; no printed shell "
                "that meets HUL-D10 weighs much less than 500 g, and the "
                "foam adds about 200 g."],
               ["What still passes", "Every requirement that the mass "
                "affects has been checked at the real mass: draft "
                f"{FD['draft']:.1f} ≤ 35, freeboard {FD['freeboard']:.0f} "
                f"≥ 50, heel {D['heel_edge']:.1f}° ≤ 10°, trim within ± 3°, "
                "reserve buoyancy 3 ×. So what exceeding the limit costs "
                "is carrying weight and draft margin, not safety."],
               ["Proposal", "Raise MEC-002 to <b>2.2 kg</b> and the design "
                "mass to 2.5 kg (ICD load cases, IF-16 to IF-19). Set "
                "HUL-D03 to 1600 g and reissue the ADD mass table from "
                "this document. Keep draft ≤ 35 mm and freeboard ≥ 50 mm "
                "as they are; they are what the owner sees."],
               ["Alternatives", "(a) EPS instead of XPS foam: about −90 g, "
                "more water uptake if breached. (b) Drop the tracker "
                "pocket and cap: −20 g. (c) Carbon mast and beams: about "
                "−80 g, +cost. (d) Shorter, deeper hulls: less skin, but "
                "draft rises past 35 mm. Even (a)+(b)+(c) leaves the boat "
                "near 2.0 kg, so the limit has to move either way."],
               ["Impact", "SRS MEC-002; SSS-HUL budget and HUL-D03; "
                "SSS-PRP budget unchanged; ADD A.MASS; ICD design mass; "
                "sim model mass (KCL MASS_KG) and the SITL runs that use "
                "it."]], [30, 140], header=False),
        H2("CR-10  Masthead height (IF-19)"),
        table([["", ""],
               ["Finding", f"E-02: the masthead top is "
                f"{D['gnss_top_above_wl']:.0f} mm above the water; IF-19 "
                "says ≈ 450. The height limit (≤ 500 mm, MEC-001 and "
                "HUL-D01) is measured from the lowest point, which is the "
                f"pod duct {-PR['POD_AXIS_Z'] + PR['DUCT_OD'] / 2:.0f} mm "
                f"below the keel. Overall height is "
                f"{D['envelope'][2]:.0f} mm."],
               ["Proposal", "Change IF-19 to 'GNSS top ≥ 400 mm above the "
                "waterline'. Nothing depends on the exact height: MEC-013's "
                f"separation is {D['gnss_sep']:.0f} mm, and the flag, below "
                "the GNSS, still flies above 320 mm."],
               ["Impact", "ICD IF-19 text only."]], [30, 140], header=False),
        H2("CR-11  Hull shell thickness (HUL-D10)"),
        table([["", ""],
               ["Finding", "HUL-D10 asks for ≥ 3 perimeters and a shell "
                "≥ 1.6 mm. With a 0.4 mm nozzle, 3 perimeters is 1.2 mm; "
                "1.6 mm needs 4. The design uses 1.2 mm ASA."],
               ["Rationale", "The shell is the skin of a foam sandwich, "
                "not a free panel: the foam carries it against impact and "
                "water pressure, and a breach does not sink the segment. "
                "1.6 mm adds about 150 g, which CR-09 cannot afford."],
               ["Proposal", "HUL-D10: 'shell ≥ 3 perimeters (≥ 1.2 mm) "
                "over a bonded foam core'. Verify with the IF-16 joint "
                "load test and a drop test of one mid segment onto gravel "
                "from 0.5 m."],
               ["Impact", "SSS-HUL HUL-D10; FMEA hull-breach rows (the "
                "occurrence estimate, not the controls)."]],
              [30, 140], header=False),
        H2("10.1 TBCs this design closes"),
        table([["TBC", "Was", "Now"],
               ["TBC-11 (IF-16)", "Section 90 × 100 at the joint",
                f"{PR['B']:.0f} × {PR['D']:.0f}, lines in the CAD"],
               ["TBC-13 (IF-18)", "Box and saddle", "Any clip-lock box "
                "within 200 × 130 × 86 external; the saddle is drawn for "
                "it. Buy the box, then set BOX_* and rebuild."],
               ["TBC-14 (IF-20)", "Stud size", "Still open: needs test "
                "prints against genuine DUPLO"],
               ["TBC-12 (IF-17)", "Pod connector", "Still open: the CAD "
                "reserves the parking clips and the lead route only"]],
              [30, 60, 80]),
    ]


def section_make():
    return [
        PageBreak(),
        H1("11. Manufacture, assembly and verification"),
        H2("11.1 Printing"),
        table([["Parts", "Material", "Settings", "Orientation"],
               ["Hull segments", "Fluorescent orange ASA", "0.4 nozzle, "
                "3 perimeters, 4 top/bottom, no infill needed (shell), "
                "enclosure", "Open joint end down (mid: either end); tree "
                "supports inside the stern's transom, removed through the "
                "open end before foaming"],
               ["Thumb-screws, dowels", "PETG", "4 perimeters, 40% infill, "
                "0.15 mm layers for the thread", "Axis vertical, knob "
                "down"],
               ["Pod body, guard, prop", "PETG (black)", "3 perimeters, 40% "
                "infill", "Pod: back face down, supports under the duct; "
                "prop: hub down"],
               ["Tray, handle, hood, collar, plate", "PETG (fluorescent "
                "where hi-vis)", "3 perimeters, 25% gyroid", "Largest flat "
                "face down"],
               ["Masthead", "Translucent PETG", "2 perimeters in the "
                "diffuser ring", "Dome up"]], [34, 34, 52, 50]),
        H2("11.2 Stock and bought items"),
        table([["Item", "Qty", "Note"],
               ["6063 Al rectangular tube 20 × 10 × 1.5", "0.6 m",
                "two 300 mm beams, drilled to the rail grid"],
               ["Al round tube Ø16 × 1", "0.33 m", "mast; one Ø4.2 hole "
                "for the collar bolt"],
               ["XPS board 50 mm, closed-cell", "≈ 7 L", "profiled cores"],
               ["Clip-lock box, 1.2-1.5 L", "1", "TBC-13"],
               ["PG7 glands", "4", "IF-18"],
               ["Acrylic 2 mm disc Ø40", "1", "camera window"],
               ["Ripstop, fluorescent", "120 × 80", "flag"],
               ["M4 heat-set inserts; M4 × 16 A4", "8; 8", "beams"],
               ["M3 × 16/20 A4, nylon-insert nuts", "8", "tray and handle "
                "through the rail"],
               ["M3 × 30 A4 pins", "2", "latch pivots"],
               ["M4 × 30 A4 and nut", "1", "collar cross-bolt"],
               ["M2.5 × 8 A2; M2 × 6 A2", "4; 8", "guards; motor mounts"],
               ["M3 inserts and M3 × 8 A2; Ø1 O-ring cord", "6; 6",
                "tracker pocket caps"]], [72, 22, 76]),
        P("The stock items are new to the bill of materials; they are to "
          "be priced into the Key Component List before the CDR and "
          "checked against the cap (open item O-3)."),
        H2("11.3 Assembly"),
        P("<b>Adult, once:</b> foam the segments; bond dowels, caps, "
          "keepers and the key dock; fit inserts; bolt the beams to the "
          "mid segments and the tray and handle to the beams; fit glands, "
          "window and hood to the box; fit the motors and props, then the "
          "guards. <b>Crew, each session</b> (no tools, ≤ 20 N): join the "
          "bow and stern segments to the core with the thumb-screws; "
          "slide on the pods until they click; plug in the pod leads "
          "(adult checks); put the mast in its socket and tighten its "
          "knob; plug in the flag; clip on the DUPLO plate."),
        H2("11.4 Verification of the first prints"),
        table([["ID", "What", "Pass"],
               ["M-V1", "Weigh each segment before and after foaming",
                "foam fill ≥ 90% of the cavity (HUL-D05)"],
               ["M-V2", "Weigh the boat ready to sail", "matches section 5 "
                "within 5%"],
               ["M-V3", "Joint load test: two joined segments, 3 × design "
                "weight at mid-span (IF-16)", "no opening or cracking"],
               ["M-V4", "Probe test on the inlet and guard (MEC-010)",
                "8 mm probe cannot touch a blade"],
               ["M-V5", "Hoop pull 50 N; tow in the pool (REC-005)",
                "no damage; no capsize"],
               ["M-V6", "Latch release force (HUL-D24)", "≥ 40 N"],
               ["M-V7", "Pod swap timed (MEC-008), pull test (IF-17)",
                "< 2 min; holds 30 N"],
               ["M-V8", "Stud fit with genuine bricks (IF-20)",
                "2×2 stays on at 45° and with shake; child removes it"],
               ["M-V9", "Box submersion 30 min at 0.3 m (MEC-012)",
                "tissue dry"],
               ["M-V10", "Float test: draft, trim, heel with 300 g at the "
                "edge", "within 3 mm and 1° of section 6"],
               ["M-V11", "Edges and small parts inspection (CHD-001/002)",
                "no sharp edges; no loose small parts"]], [16, 100, 54]),
        H2("11.5 Open items"),
        table([["ID", "Item"],
               ["O-1", "Owner decisions on CR-09, CR-10, CR-11 at the CDR"],
               ["O-2", "Choose the box; rebuild with its dimensions "
                "(TBC-13)"],
               ["O-3", "Price the stock items into the KCL and check the "
                "cap"],
               ["O-4", "Pod connector part number and parking clip "
                "(TBC-12)"],
               ["O-5", "Update the simulator's mass and inertia from "
                "section 5 when CR-09 is decided"],
               ["O-6", "Motor lead route through the strut: groove and "
                "potting detail after the connector is chosen"]],
              [16, 154]),
    ]


def appendix():
    rows = [["Part", "Name", "Qty", "Files (in the CAD zip)"]]
    for p in RES["parts"]:
        rows.append([p["key"], p["name"], str(p["qty"]),
                     "<br/>".join(p["files"])])
    return [PageBreak(), H1("Appendix A. Part list and files"),
            P("The zip holds these files, the assembly (STEP with colours, "
              "and GLB), the CadQuery source and the results file. Part "
              "files are moved to the origin; the assembly places them."),
            table(rows, [16, 62, 10, 82])]


def build():
    st = cover("Mechanical Design<br/>Description",
               "Detailed mechanical design of Boaty Mk1 in CadQuery: parts, "
               "assembly, mass, hydrostatics and compliance, for the "
               "Critical Design Review",
               [["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                ["Baseline", f"Upstream documents as tagged {BL.TAG} "
                 "(unchanged)"],
                ["CAD", f"mechanical/ at commit {RES['commit']}"],
                ["Compliance", f"{n('PASS')} pass, {n('TEST')} by test, "
                 f"{n('FAIL')} not met (CR-09 to CR-11 proposed)"]])
    st += control_and_contents(
        [["A", DATE, "First issue, draft for the CDR.",
          "Claude (drafted)"]],
        "Review this document with the CAD zip open. Section 2 has the "
        "decisions; section 9 has every check; section 10 has the change "
        "requests.")
    st += (section_intro() + section_summary() + section_config() +
           section_parts() + section_mass() + section_hydro() +
           section_structure() + section_safety() + section_matrix() +
           section_crs() + section_make() + appendix())
    doc = Doc(OUT, DOC_ID, "Mechanical Design Description", ISSUE)
    doc.multiBuild(st)
    print("wrote", OUT, f"{n('PASS')} pass, {n('TEST')} test, "
          f"{n('FAIL')} fail")


if __name__ == "__main__":
    build()
