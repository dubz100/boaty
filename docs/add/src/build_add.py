"""Build the Boaty Architecture Design Document PDF.

Run:  python3 docs/add/src/figures.py && python3 docs/add/src/build_add.py
Writes docs/add/Boaty_Architecture_Design_Document.pdf
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "common"))

import architecture as A  # noqa: E402
from pdfdoc import (BLUE_T, GREEN_T, ORANGE, ORANGE_T, H1, H2, P,  # noqa: E402
                    Doc, KeepTogether, PageBreak, Spacer, bullets, callout,
                    colors, control_and_contents, cover, fig, mm, table)

SRS = A.SRS
FIG = HERE.parent / "figures"
OUT = HERE.parent / "Boaty_Architecture_Design_Document.pdf"
DOC_ID = "BOATY-ADD-001"
ISSUE = "Issue D (for review)"
DATE = "28 September 2026"


def F(name, w, cap):
    return fig(FIG / name, w, cap)


def build():
    n_alloc = A.check()
    alloc = A.allocation()
    reqs = {r["id"]: r for r in SRS.all_reqs()}
    ss_codes = [s[0] for s in A.SUBSYSTEMS] + ["SYS", "OPS"]
    ss_names = {s[0]: s[1] for s in A.SUBSYSTEMS} | \
        {c: n for c, n, _ in A.EXTRA_ALLOC}
    boat_bom = sum(p for w, _, p in A.BOM if w == "Boat")
    bank_bom = sum(p for w, _, p in A.BOM if w == "Bank")
    deferred = sum(p for w, _, p in A.BOM if w.endswith("*"))
    base = boat_bom + bank_bom
    mass = sum(m for _, m in A.MASS)
    p_boat = sum(p for _, p in A.POWER_BOAT)
    p_bank = sum(p for _, p in A.POWER_BANK)
    usable_wh = 3 * 3.6 * 3.0 * 0.8
    chosen = next(c for c in A.CANDIDATES if c.get("chosen"))
    sens = A.candidate_sensitivity()

    st = cover("Architecture Design<br/>Document",
               "Mk1 system architecture: design-space exploration, selected "
               "architecture, interfaces and requirement allocation",
               [["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                ["Status", "AR-2 and CR-01 accepted by the owner"],
                ["Inputs", "SRS BOATY-SRS-001 Issue D; Concept Selection "
                 "Report v1.1"],
                ["Outcome", f"Architecture {chosen['id']} '{chosen['name']}': "
                 f"8 subsystems, {len(A.INTERFACES)} interfaces, "
                 f"{n_alloc} requirements allocated"]])
    st += control_and_contents(
        [["A", DATE, "First issue, for review.", "Claude (drafted)"],
         ["B", DATE, "Owner accepted AR-2 and CR-01 (cap £160, SRS Issue C). "
          "Weed-shedding mechanism refined during ICD work (bounded GUIDED "
          "velocity bursts); V-11 to V-13 added.", "Claude, owner "
          "decisions"],
         ["C", DATE, "TALK button added (ICD TBC-10 closed, SRS Issue D): "
          "BOM +£2, MCN and IF-12 descriptions updated. From subsystem "
          "specification work: IP67 main switch added to BOM (+£4, "
          "previously omitted); V-14 to V-17 added.", "Claude, owner "
          "decision"],
         ["D", DATE, "CR-02 accepted: flight controller with microSD "
          "(DD-15, +£10 est.). FMEA actions: navigation monitor B7 "
          "(DD-16) and box temperature sensor (+£2). Baseline now over "
          "the cap: CR-03 raised.", "Claude, owner decision"]],
        "Review guidance: section 3 is deliberately divergent, so challenge "
        "the options and the scoring. Section 4 onwards is the converged "
        "architecture that the ICD and subsystem specifications will build "
        "on. The decisions needing your input are summarised in section 10.")

    # ---------------- 1 introduction
    st += [H1("1. Introduction"),
           H2("1.1 Purpose"),
           P("This document defines the Mk1 system architecture. It covers "
             "the subsystems, how they connect, where each requirement is "
             "met, and why this architecture was chosen over the "
             "alternatives. It is the parent of the Interface Control "
             "Document (ICD) and the subsystem requirement specifications."),
           H2("1.2 Approach: diverge, then converge"),
           P("The concept report went from a concept to an outline "
             "architecture quickly. This document steps back first."),
           *bullets([
               "<b>Drivers (section 2).</b> The requirements and quality "
               "attributes that actually shape the architecture.",
               "<b>Diverge (section 3).</b> A morphological chart of twelve "
               "design dimensions. Five deliberately different candidate "
               "architectures, scored against the drivers. Nine focused "
               "trade studies on the dimensions that matter most.",
               "<b>Converge (sections 4-8).</b> Principles, subsystems, "
               "software, network, power, modes, failsafes, interfaces, "
               "allocation and budgets. Then the design decisions and the "
               "assumptions to prove early.",
           ]),
           P("Some things were already fixed and are not reopened: the "
             "catamaran concept, ArduPilot as the helm (SRS Issue B), the "
             "Pi 5, and the SRS itself. Everything else was open.", "small"),
           H2("1.3 Related documents"),
           table([["Ref", "Document"],
                  ["[1]", "BOATY-SRS-001 System Requirements Specification, "
                   "Issue B"],
                  ["[2]", "Concept Selection Report v1.1"],
                  ["[3]", "ArduPilot Rover documentation (ardupilot.org/"
                   "rover) and MAVLink common message set (mavlink.io)"],
                  ["[4]", "BOATY-ICD-001 Interface Control Document (next)"],
                  ["[5]", "BOATY-SSS-xxx Subsystem specifications (next)"]],
                 [14, 156]),
           PageBreak()]

    # ---------------- 2 drivers
    st += [H1("2. Architecture drivers"),
           P("Most of the 184 requirements could be met by almost any "
             "architecture. These are the ones that can't:"),
           table([["Requirements", "What they demand", "Architectural "
                   "question"]] + [list(d) for d in A.DRIVERS],
                 [28, 86, 56]),
           H2("2.1 Quality attributes, in priority order"),
           P("When options conflict, the higher attribute wins:"),
           table([["#", "Attribute", "Meaning here"]] +
                 [list(q) for q in A.QUALITY_ORDER], [8, 42, 120]),
           PageBreak()]

    # ---------------- 3 divergence
    morph_rows = [["Dimension", "Option 1", "Option 2", "Option 3",
                   "Option 4"]]
    shade = []
    for r, (dim, opts, sel) in enumerate(A.MORPH, start=1):
        morph_rows.append([f"<b>{dim}</b>"] + opts + [""] * (4 - len(opts)))
        shade.append(("BACKGROUND", (sel + 1, r), (sel + 1, r),
                      colors.HexColor("#cfe1f6")))
    st += [H1("3. Exploring the design space"),
           H2("3.1 Morphological chart"),
           P("Twelve independent design dimensions, each with the realistic "
             "options. Any combination of one option per row is an "
             "architecture. That's over 16 million, so the chart is used to "
             "build a few deliberately different candidates (3.2) and to "
             "focus the trade studies (3.4). The options selected in the end "
             "are shaded blue."),
           table(morph_rows, [44, 31.5, 31.5, 31.5, 31.5], style_extra=shade),
           PageBreak(),
           H2("3.2 Five candidate architectures"),
           P("Each candidate takes a different position on the biggest "
             "question: <i>where does the intelligence live, and how does "
             "it talk to the boat?</i>"),
           F("candidates.png", 170, "Figure 1. Candidate architectures. Blue "
             "= helm, green = where the project's intelligence runs.")]
    st.append(table([["ID", "Idea", "For", "Against"]] +
                    [[f"<b>{c['id']}</b><br/>{c['name']}", c["idea"],
                      c["pros"], c["cons"]] for c in A.CANDIDATES],
                    [22, 56, 44, 48]))
    short = {"saf": "Safety", "link": "Link loss", "cost": "Cost",
             "simp": "Simplicity", "cover": "Coverage", "ext": "Python / ext."}
    crit_rows = [["Candidate"] + [short[k] for k, _, _ in A.CRITERIA] +
                 ["Score"]]
    for c in sorted(A.CANDIDATES, key=lambda c: -A.candidate_score(c)):
        crit_rows.append([f"{c['id']} {c['name']}"] +
                         [str(c["scores"][k]) for k, _, _ in A.CRITERIA] +
                         [f"<b>{A.candidate_score(c):.2f}</b>"])
    crit_rows.append(["<i>Weight</i>"] +
                     [f"{w:.0%}" for _, _, w in A.CRITERIA] + [""])
    st += [H2("3.3 Evaluation and selection"),
           table(crit_rows, [44, 18, 18, 15, 20, 20, 21, 14],
                 style_extra=[("BACKGROUND", (0, 1), (-1, 1), BLUE_T)]),
           Spacer(1, 3 * mm),
           F("cand_scores.png", 135, "Figure 2. Weighted candidate scores."),
           P(f"<b>AR-2 'Smart bank' is selected.</b> It stays the winner "
             f"when any single weight is doubled "
             f"({', '.join(f'{k}: {v}' for k, v in sens.items())}). Its "
             "nearest rivals each win on one axis. AR-3 is cheaper, but "
             "gives up the live photo pipeline and the route to duck "
             "spotting. AR-4 has more range, which a 100 m home bay doesn't "
             "need; it remains the upgrade path if V-08 fails. Two ideas "
             "from the losing candidates are kept:"),
           *bullets(["From AR-3: no project code in the safety path. The "
                     "boat's Python services can only make requests.",
                     "From AR-1: the boat must carry on safely with the "
                     "link gone. The loaded mission always ends in RTL, and "
                     "the boat-side watchdog (B4) needs no bank."]),
           PageBreak(),
           H2("3.4 Focused trade studies")]
    for tid, title, opts, decision in A.TRADES:
        rows = [["Option", "For", "Against"]] + [list(o) for o in opts]
        st.append(KeepTogether([
            P(f"<b>{tid}. {title}</b>", "body"),
            table(rows, [52, 60, 58]),
            Spacer(1, 1.5 * mm),
            callout(f"<b>Decision:</b> {decision}", colors.HexColor(
                "#1baf7a"), GREEN_T),
            Spacer(1, 4 * mm)]))
    st.append(PageBreak())

    # ---------------- 4 selected architecture
    st += [H1("4. Selected architecture"),
           H2("4.1 Architecture principles"),
           table([["#", "Principle", "Meaning"]] +
                 [[str(i), f"<b>{p}</b>", m] for i, (p, m) in
                  enumerate(A.PRINCIPLES, 1)], [8, 62, 100]),
           H2("4.2 Physical architecture and subsystems"),
           F("physical.png", 168, "Figure 3. Physical architecture: 8 "
             "subsystems and the main interfaces (IF-xx, section 5)."),
           table([["Code", "Subsystem", "Where", "Contents"]] +
                 [[f"<b>{c}</b>", n, w, d] for c, n, w, d in A.SUBSYSTEMS],
                 [14, 30, 18, 108]),
           P("The LED beacon is driven by the helm, not the mission "
             "computer (DD-11). A boat with a crashed Pi Zero still shows "
             "its state.", "small"),
           PageBreak(),
           H2("4.3 Software architecture"),
           P("Two Python applications and one third-party firmware. The "
             "Mission Control application does the thinking. The boat "
             "services are small and single-purpose. ArduPilot has the "
             "final say."),
           F("software.png", 168, "Figure 4. Software components and data "
             "flows. Orange = the validator gate; blue = the helm."),
           table([["ID", "Component", "Responsibility", "Key reqs"]] +
                 [[f"<b>{c[1]}</b>", c[2], c[3], c[4]] for c in
                  A.COMPONENTS], [11, 30, 89, 40]),
           Spacer(1, 3 * mm),
           callout("<b>Rule for boat-side Python (B4-B6):</b> these services "
                   "may only <i>request</i> safer states through MAVLink: "
                   "HOLD, LOITER or RTL. The one exception is B5's "
                   "weed-shedding. It may use GUIDED for bounded reverse "
                   "bursts (at most 0.5 m/s astern, 2 s each, 3 in total), "
                   "and must then hand back to HOLD. V-11 confirms the helm "
                   "stops if B5 dies mid-burst. These services never arm, "
                   "never change the fence or parameters, and never command "
                   "AUTO or MANUAL (FS-007, SAF-003).", ORANGE, ORANGE_T),
           H2("4.4 Network and link"),
           P("The Pi 5 runs the Wi-Fi access point, using a USB adapter "
             "with an external antenna. The boat's Pi Zero joins it as a "
             "client and relays MAVLink between the helm and Mission "
             "Control. The operator's phone is USB-tethered to the Pi 5. "
             "That single cable gives internet for the Claude API and a "
             "route for the phone's browser to reach the web UI. Losing "
             "internet affects only planning (COM-005, MC-011)."),
           F("link.png", 150, "Figure 5. Why antenna height matters over "
             "water. The shaded bands are 60% of the first Fresnel zone "
             "(1.06 m radius at mid-path for 100 m at 2.4 GHz). Where a "
             "band dips into the water, reflections cost signal."),
           table([["Link budget (100 m / 200 m)", "Value"],
                  ["Free-space path loss, 2.44 GHz", "80 dB / 86 dB"],
                  ["Pi Zero 2W transmit (typ.) + antenna", "≈ +13 dBm, "
                   "0 dBi"],
                  ["Bank antenna gain", "≈ +5 dBi"],
                  ["Received (free space)", "≈ −62 dBm / −68 dBm"],
                  ["Needed for a low-rate link", "≈ −85 dBm"],
                  ["Margin before Fresnel / reflection losses",
                   "≈ 23 dB / 17 dB"]], [100, 70]),
           P("There's plenty of free-space margin. The real risk is the "
             "over-water geometry, hence the pole option (V-08).", "small"),
           KeepTogether([H2("4.5 Power architecture"),
                         F("power.png", 150, "Figure 6. Boat power "
                           "distribution. The magnetic key removes motor "
                           "power independently of all software. The helm "
                           "senses the rail and refuses to arm without "
                           "it.")]),
           PageBreak(),
           H2("4.6 Mode mapping (SRS → ArduPilot Rover)"),
           table([["SRS mode", "ArduPilot mode", "Notes"]] +
                 [list(m) for m in A.MODE_MAP], [40, 45, 85]),
           H2("4.7 Failsafe implementation"),
           P("Where each failsafe lives. 'Native' means an ArduPilot "
             "parameter on the independent helm. 'Python' means a "
             "boat-side service, used only where ArduPilot on a 1 MB board "
             "can't do it and the requirement isn't the last line of "
             "defence."),
           table([["Req", "Failsafe", "Layer", "Mechanism", "Type"]] +
                 [list(f) for f in A.FS_ALLOC], [16, 36, 20, 70, 28]),
           H2("4.8 Mission pipeline"),
           F("pipeline.png", 170, "Figure 7. From words to motion. Every "
             "mission source (voice, text, template, map editor) enters "
             "before the planner or validator. Nothing bypasses the "
             "validator (VAL-001)."),
           *bullets([
               "<b>Intent, not waypoints.</b> The Claude API returns a small "
               "JSON intent, e.g. <i>explore(area='home bay', coverage="
               "'medium'), photo_stops(n=3, near='island'), "
               "return_home()</i>. The request uses tool use, so the output "
               "must match the schema (NLI-004).",
               "<b>Planner.</b> Deterministic Python turns the intent into "
               "geometry, using the site store's fence, exclusions and named "
               "landmarks: survey lanes, photo points and legs.",
               "<b>Native execution.</b> The mission becomes standard "
               "ArduPilot mission items (waypoints, timed loiters at photo "
               "points, final RTL) and runs in AUTO. The mission computer "
               "takes photos by watching mission progress over MAVLink. "
               "Nothing streams live steering, so the boat never depends on "
               "a companion to finish (DD-05).",
           ]),
           Spacer(1, 4 * mm)]

    # ---------------- 5 interfaces
    st += [H1("5. Interfaces"),
           P("The N² diagram shows which pairs of elements interact, with "
             "subsystems and externals on the diagonal. The register "
             "defines each interface to the level needed to scope the ICD."),
           F("n2.png", 130, "Figure 8. N² diagram (interface numbers; "
             "diagonal entries are interfaces internal to a subsystem)."),
           PageBreak(),
           H2("5.1 Interface register"),
           table([["ID", "Interface", "Between", "Type", "Medium / "
                   "protocol", "Content", "Reqs"]] +
                 [[f"<b>{i[0]}</b>", i[1],
                   f"{i[2]} ↔ {A.EXTERNALS.get(i[3], i[3])}", i[4], i[5],
                   i[6], i[7]] for i in A.INTERFACES],
                 [12, 24, 20, 17, 37, 36, 24]),
           P("Every interface gets an ICD section with: owner, "
             "message/signal/geometry definitions, timing, error handling "
             "and a verification method. MAVLink interfaces (IF-02, IF-04) "
             "define only the subset used; the standard is referenced, not "
             "copied.", "small"),
           PageBreak()]

    # ---------------- 6 allocation
    counts = {}
    for rid, (p, sec) in alloc.items():
        area = rid.split("-")[0]
        counts.setdefault(area, Counter())[p] += 1
        for s in sec:
            counts[area][s.lower()] += 1
    areas = [s["key"] for s in SRS.SECTIONS]
    rows = [["Area"] + ss_codes]
    shade = []
    for ri, area in enumerate(areas, start=1):
        row = [area]
        for ci, s in enumerate(ss_codes, start=1):
            p, sec = counts[area][s], counts[area][s.lower()]
            txt = (f"<b>{p}</b>" if p else "") + (f" +{sec}" if sec else "")
            row.append(txt)
            if p:
                shade.append(("BACKGROUND", (ci, ri), (ci, ri),
                              colors.HexColor("#cfe1f6")))
        rows.append(row)
    prim_tot = Counter(p for p, _ in alloc.values())
    rows.append(["<b>Primary</b>"] + [f"<b>{prim_tot[s]}</b>"
                                       for s in ss_codes])
    st += [H1("6. Requirement allocation"),
           P(f"All {n_alloc} SRS requirements are allocated to one "
             "<b>primary</b> owner (bold), which is responsible for meeting "
             "and verifying it. Some also have <b>supporting</b> subsystems "
             "(+n) that must provide something for it. SYS = verified only "
             "on the integrated system. OPS = met by procedure. SAF-005 is "
             "not applicable (Route A). The build script checks that "
             "nothing is left unallocated."),
           table(rows, [16] + [15.4] * len(ss_codes),
                 style_extra=shade + [("ALIGN", (1, 0), (-1, -1), "CENTER")]),
           P("Table: requirements per area and subsystem. The per-subsystem "
             "lists in Appendix A are the starting content of each subsystem "
             "specification.", "caption"),
           PageBreak()]

    # ---------------- 7 budgets
    bom_rows = [["Where", "Item", "£"]] + [[w, i, str(p)] for w, i, p in
                                           A.BOM]
    bom_rows += [["", "<b>Baseline (boat + bank, excluding *)</b>",
                  f"<b>{base}</b>"],
                 ["", "Boat only / bank only", f"{boat_bom} / {bank_bom}"],
                 ["", "If the pole kit (*) is needed", f"{base + deferred}"],
                 ["", "SRS cap (CON-001, Issue C) / target", "160 / 150"]]
    st += [H1("7. Budgets"),
           H2("7.1 Mass"),
           table([["Item", "g"]] + [[i, str(m)] for i, m in A.MASS] +
                 [["<b>Total (estimate)</b>", f"<b>{mass}</b>"],
                  ["Limit MEC-002 / margin", f"1800 / "
                   f"{(1800 - mass) / 1800:.0%}"]], [130, 40]),
           H2("7.2 Power and endurance"),
           table([["Boat load", "W"]] + [[i, f"{p:.1f}"] for i, p in
                                         A.POWER_BOAT] +
                 [["<b>Total at cruise</b>", f"<b>{p_boat:.1f}</b>"],
                  ["Usable energy: 3S 18650, 3.0 Ah, 80% usable",
                   f"{usable_wh:.1f} Wh"],
                  ["Estimated endurance (PWR-009 needs ≥ 40 min)",
                   f"≈ {usable_wh / p_boat * 60:.0f} min"]], [130, 40]),
           Spacer(1, 2 * mm),
           table([["Bank load", "W"]] + [[i, f"{p:.1f}"] for i, p in
                                         A.POWER_BANK] +
                 [["<b>Total</b>", f"<b>{p_bank:.1f}</b>"],
                  ["20,000 mAh power bank (≈ 55 Wh delivered) → runtime "
                   "(MC-001 needs ≥ 2.5 h)", f"≈ {55 / p_bank:.0f} h"]],
                 [130, 40]),
           P("Motor power is the dominant unknown. It is measured on the "
             "bench and in the pool before the endurance claim is "
             "verified.", "small"),
           PageBreak(),
           H2("7.3 Cost"),
           table(bom_rows, [16, 130, 24]),
           Spacer(1, 3 * mm),
           callout(f"<b>CR-01 accepted (Issue B):</b> the CON-001 cap is now "
                   f"£160, target £150 (SRS Issue C). <b>Issue D position:</b> "
                   f"the baseline is £{base}, <b>£{base - 160} over the "
                   f"cap</b> (£{base + deferred} with the pole kit). This "
                   "follows the microSD flight controller (CR-02, +£10 "
                   "estimate) and the FMEA box temperature sensor (+£2). "
                   "<b>Owner decision CR-03:</b> (a) raise the cap to £170; "
                   "(b) use tested salvaged 18650 cells (−£8) and a PIN "
                   "instead of the panel key switch (−£3), giving "
                   f"£{base - 11}; or (c) confirm real prices first, since "
                   "the £35 flight controller is an estimate. As "
                   "originally raised: the baseline was over the old £120 "
                   "cap. "
                   "Compared with the concept estimate (£117 including the "
                   "Mission Control extras), the growth comes from nine "
                   "changes:<br/>"
                   "• Python on the boat (Pi Zero instead of ESP32): +£9<br/>"
                   "• Bank radio (USB adapter + antenna): +£12<br/>"
                   "• Independent motor-power interlock: +£4<br/>"
                   "• Dedicated 5 V supply: +£3<br/>"
                   "• Adult key switch on the panel: +£3<br/>"
                   "• TALK button (added in Issue C): +£2<br/>"
                   "• IP67 main switch (omitted before Issue C): +£4<br/>"
                   "• microSD flight controller (CR-02): +£10 (est.)<br/>"
                   "• Box temperature sensor (FMEA A-11): +£2<br/>"
                   "The cheapest candidate, AR-3, would fit the cap, but it "
                   "gives up the live photo pipeline. <b>Owner decision "
                   "CR-01:</b> (a) raise the CON-001 cap to £160, target "
                   "£150; or (b) keep £120 and adopt AR-3's action-camera "
                   "photo path. <b>Owner chose (a).</b>", ORANGE, ORANGE_T),
           PageBreak()]

    # ---------------- 8 decisions + 9 verification/risks
    st += [H1("8. Design decisions register"),
           table([["ID", "Decision", "Basis", "Effect"]] +
                 [list(d) for d in A.DECISIONS], [15, 105, 22, 28]),
           P("Updated SRS open items: TBD-04, TBD-05, TBD-06 and TBD-07 "
             "are closed by DD-06 to DD-09. TBD-02 (which lake) and TBD-03 "
             "(the Trust's permission) remain open.", "small"),
           H1("9. Assumptions to prove early, and risks"),
           P("The architecture rests on a few assumptions about ArduPilot "
             "and the hardware. They are cheap to check in SITL or on the "
             "bench, so they're checked <b>first</b>, before most parts are "
             "bought or code is written."),
           table([["ID", "Assumption to confirm", "Where", "Protects"]] +
                 [list(v) for v in A.VERIFY_EARLY], [12, 110, 22, 26]),
           Spacer(1, 3 * mm),
           table([["ID", "Risk", "Level", "Mitigation"]] +
                 [list(r) for r in A.RISKS], [12, 58, 16, 84]),
           Spacer(1, 6 * mm)]

    # ---------------- 10 next steps
    st += [H1("10. Decisions and next documents"),
           table([["#", "Decision", "Status"],
                  ["1", "Accept AR-2 'Smart bank' as the Mk1 architecture",
                   "<b>Accepted</b> (owner, 28 Sep 2026)"],
                  ["2", "CR-01: cost cap (section 7.3)", "<b>Accepted</b>: "
                   "cap £160, target £150"],
                  ["3", "Pi Zero 2W instead of ESP32 on the boat (DD-03)",
                   "<b>Accepted</b> as part of AR-2"],
                  ["4", "Order of work: prove V-01 to V-06 in SITL and on "
                   "the bench before the main parts order",
                   "Recommended; not yet confirmed"],
                  ["5", "CR-02: helm log storage", "<b>Accepted</b>: "
                   "microSD flight controller (DD-15)"],
                  ["6", "CR-03: cost cap after CR-02 and the FMEA actions "
                   "(section 7.3)", "<b>Open</b>: recommend (c) then (b)"]],
                 [8, 100, 62]),
           Spacer(1, 4 * mm),
           P("Then, from this document:"),
           table([["Document", "Content", "Source here"],
                  ["BOATY-ICD-001", "One section per interface IF-01 to "
                   "IF-22: definitions, timing, errors, verification",
                   "Section 5"],
                  ["BOATY-SSS-HUL/PRP/PWR", "Mechanical and electrical "
                   "subsystem specs", "Appendix A, sections 4.2 and 4.5"],
                  ["BOATY-SSS-HLM", "Helm spec: controlled ArduPilot "
                   "parameter set, mode and failsafe config, verification",
                   "Sections 4.6 and 4.7"],
                  ["BOATY-SSS-MCP / MCN", "Software and hardware specs for "
                   "both computers", "Section 4.3, Appendix A"],
                  ["BOATY-SSS-SIM", "Simulation and test environment",
                   "SWE-004/005, section 9"]],
                 [36, 94, 40]),
           PageBreak()]

    # ---------------- Appendix A
    st.append(H1("Appendix A. Requirements by subsystem"))
    for code in ss_codes:
        prim = [r for r, (p, _) in alloc.items() if p == code]
        sup = [r for r, (_, s) in alloc.items() if code in s]
        st.append(P(f"<b>{code} {ss_names[code]}</b>: primary "
                    f"{len(prim)}, supporting {len(sup)}", "body"))
        st.append(P("<b>Primary:</b> " + ", ".join(prim), "small"))
        if sup:
            st.append(P("<b>Supporting:</b> " + ", ".join(sup), "small"))
        st.append(Spacer(1, 2 * mm))
    na = [r for r, (p, _) in alloc.items() if p == "N/A"]
    st.append(P("<b>Not applicable:</b> " + ", ".join(na), "small"))

    doc = Doc(OUT, DOC_ID, "Architecture Design Document", ISSUE)
    doc.multiBuild(st)
    print("wrote", OUT, f"(base BOM £{base})")


if __name__ == "__main__":
    build()
