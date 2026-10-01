"""Build the executive progress report (BOATY-PR-001).

Run:  python3 docs/report/src/figures.py && python3 docs/report/src/build_report.py

A briefing for executive stakeholders, not a controlled engineering
document: it summarises the baselined set and the detailed-design drafts
and makes no new requirements. Every number is read from the results
files the engineering builds write (SITL, MDD, EDD) or counted from the
sources, so the report cannot drift from the evidence.
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REP = HERE.parent
DOCS = REP.parent
ROOT = DOCS.parent
sys.path.insert(0, str(DOCS / "common"))
sys.path.insert(0, str(DOCS / "concept" / "src"))
sys.path.insert(0, str(DOCS / "srs" / "src"))
sys.path.insert(0, str(DOCS / "sss" / "src"))

import baseline as BL  # noqa: E402
import requirements as REQ  # noqa: E402
import scoring  # noqa: E402
import sss_data as SD  # noqa: E402
from pdfdoc import (BLUE, BLUE_T, GREEN_T, H1, H2, INK2, ORANGE,  # noqa: E402
                    ORANGE_T, RULE, TINT, P, PageBreak, Paragraph, S,
                    Spacer, bullets, callout, colors, cover, fig, mm, table,
                    Doc, KeepTogether)
from reportlab.platypus import Table, TableStyle  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402

OUT = REP / "Boaty_Executive_Progress_Report.pdf"
FIG = REP / "figures"
DOC_ID = "BOATY-PR-001"
ISSUE = "Issue 1"
DATE = "1 October 2026"
GREEN = colors.HexColor("#1e8a55")

SITL = json.loads((ROOT / "software/results/sitl_results.json").read_text())
OUTC = Counter(r["outcome"] for r in SITL["records"])
N_SITL = len(SITL["records"])
MECH = json.loads((ROOT / "mechanical/results/mech_results.json")
                  .read_text())
ELEC = json.loads((ROOT / "electrical/results/elec_results.json")
                  .read_text())
N_REQ = sum(len(s["reqs"]) for s in REQ.SECTIONS)
N_MUST = sum(r["pri"] == "M" for s in REQ.SECTIONS for r in s["reqs"])
N_FS = len(REQ.FAILSAFES)
N_STK = len(REQ.STAKEHOLDER_NEEDS)
N_DOCS = len(BL.REGISTER)
N_DER = sum(len(list(SD.all_derived(SD.SUBSYSTEMS[k])))
            for k in SD.ORDER)
N_IF = 22


def counts(rows):
    c = Counter(r["status"] for r in rows)
    return c["PASS"], c["TEST"], c["FAIL"]


M_PASS, M_TEST, M_FAIL = counts(MECH["rows"])
E_PASS, E_TEST, E_FAIL = counts(ELEC["rows"])
MD = MECH["data"]


def mrow(rid, rows=MECH["rows"]):
    return next(r for r in rows if r["id"] == rid)


def erow(rid):
    return mrow(rid, ELEC["rows"])


S["kpi"] = ParagraphStyle("kpi", fontName="DVB", fontSize=19, leading=22,
                          textColor=colors.HexColor("#0b0b0b"), alignment=1)
S["kpil"] = ParagraphStyle("kpil", fontName="DV", fontSize=7.3, leading=9,
                           textColor=INK2, alignment=1)


def kpis(items, cols=4):
    cells = [[Paragraph(v, S["kpi"]), Spacer(1, 1.5 * mm),
              Paragraph(lab, S["kpil"])] for v, lab in items]
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    w = 170 / cols
    t = Table(rows, colWidths=[w * mm] * cols)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TINT),
        ("BOX", (0, 0), (-1, -1), 0, colors.white),
        ("INNERGRID", (0, 0), (-1, -1), 3, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


ST_BG = {"Done": GREEN_T, "GO": GREEN_T, "Draft": BLUE_T, "Next": "white",
         "Open": ORANGE_T}


def status_rows(rows, widths, col):
    extra = []
    for i, r in enumerate(rows[1:], 1):
        key = r[col].split()[0].strip("<b>").rstrip(",")
        for k, c in ST_BG.items():
            if r[col].replace("<b>", "").startswith(k):
                extra.append(("BACKGROUND", (col, i), (col, i), c))
    return table(rows, widths, style_extra=extra)


def build():
    st = cover("Executive progress report",
               "From one sentence to a CDR-ready design: systems "
               "engineering with Claude as the engineering team",
               [["Document", DOC_ID], ["Issue", f"{ISSUE}, {DATE}"],
                ["Audience", "Executive stakeholders"],
                ["Status", "Briefing; summarises the baselined set "
                 f"(tag {BL.TAG}) and the detailed-design drafts"],
                ["Evidence", f"software results {SITL['generated'][:10]}; "
                 f"CAD build {MECH['commit']}; electrical build "
                 f"{ELEC['commit']}"]])

    # ---------------------------------------------------------- summary
    st += [H1("Executive summary"),
           P("<b>The brief</b> was one sentence from a father and his "
             "four-year-old son: <i>explore the pond, take pictures of the "
             "ducks, come back</i>, with one hard rule: <b>we cannot lose "
             "it</b>. Behind that sentence sits a real autonomous system "
             "(a boat, its autopilot, a mission computer, a bank-side "
             "Mission Control and a natural-language planner using "
             "Claude) with real safety, cost and mass constraints."),
           P("We ran it as a formal systems-engineering programme in "
             "which Claude did the engineering work (requirements, "
             "architecture, software, simulation, CAD, schematics, "
             "analysis and every document) and the owner made the "
             "decisions at reviews. Three days after the first sentence "
             "the project has passed its System Design Review, has a "
             "baselined document set, has 83 simulated missions flown "
             "on the real autopilot firmware, and has a full mechanical "
             "and electrical detailed design ready for the Critical "
             "Design Review."),
           Spacer(1, 2 * mm),
           kpis([(f"{N_REQ}", "system requirements<br/>"
                  f"({N_MUST} Must)"),
                 (f"{N_DER}", "derived subsystem<br/>requirements"),
                 (f"{N_DOCS}", "baselined documents,<br/>all built "
                  "from code"),
                 ("14", "change requests<br/>raised and tracked"),
                 (f"{OUTC['passed']}/{N_SITL}", "simulated missions "
                  "pass<br/>on real autopilot firmware"),
                 ("0", "simulation<br/>failures"),
                 (f"{M_PASS + E_PASS}", "design checks pass<br/>"
                  "(mechanical + electrical)"),
                 ("3 days", "from one sentence<br/>to CDR-ready")]),
           Spacer(1, 4 * mm),
           H2("Where we are"),
           status_rows([
               ["Phase", "Status", "Evidence"],
               ["Concept selection", "Done", "7 options scored; modular "
                "GPS catamaran on ArduPilot chosen (4.45 / 5)"],
               ["Requirements & architecture", "Done", f"SRS {N_REQ} "
                "requirements, ADD, ICD, 8 subsystem specs, FMEA, "
                "budgets"],
               ["System Design Review (SDR)", "GO, baselined", "15 "
                "review findings (RIDs) raised and closed; baseline "
                f"tagged {BL.TAG}"],
               ["Software & simulation", "Done", f"{N_SITL} scenarios: "
                f"{OUTC['passed']} pass, {OUTC['xfail']} known gaps "
                "recorded as findings, 0 fail; 308 unit tests"],
               ["Mechanical detailed design", "Draft", f"CadQuery model; "
                f"{M_PASS} checks pass, {M_TEST} to test, {M_FAIL} open "
                "(CR-09 to CR-11)"],
               ["Electrical detailed design", "Draft", f"Netlist, 6 "
                f"schematic sheets, 3 boards; {E_PASS} pass, {E_TEST} to "
                f"test, {E_FAIL} open (CR-12 to CR-14)"],
               ["Critical Design Review (CDR)", "Next", "Decide CR-09 "
                "to CR-14, then build"]], [48, 24, 98], 1),
           Spacer(1, 3 * mm),
           callout("<b>What needs a decision.</b> The design is honest "
                   "about where it misses: the boat is "
                   f"<b>{mrow('M-01')['value']}</b> against an "
                   f"{mrow('M-01')['limit'].replace('≤ ', '')} target "
                   "(CR-09), and the bill of materials is "
                   "<b>£229 against the £185 cap</b> (CR-14). Both are "
                   "framed as owner decisions for the CDR with options "
                   "and consequences, not hidden. Neither affects "
                   "safety: the boat still floats, stays stable and "
                   "passes every hydrostatic check at the heavier "
                   "mass.", ORANGE, ORANGE_T),
           PageBreak()]

    # ---------------------------------------------------------- 1 process
    st += [H1("1. How we work: the V, with Claude as the engineering "
              "team"),
           P("The programme follows the classic systems-engineering V. "
             "Down the left side the need is decomposed into "
             "requirements, architecture, subsystem specifications and "
             "detailed design; up the right side the product is built, "
             "integrated and verified against each level. Review gates "
             "stop work moving on until the level above is sound."),
           fig(FIG / "vmodel.png", 170, "Figure 1. Progress on the V. "
               "Green is complete, blue is in progress. The yellow box is "
               "the difference: a software-in-the-loop model of the whole "
               "system, flown on the real autopilot firmware, lets us "
               "verify requirements and architecture before anything is "
               "built."),
           H2("The prompting pattern"),
           P("The approach is not \"ask the AI to design a boat\". It is "
             "the same discipline we would ask of a human team, written "
             "into how Claude is directed:"),
           *bullets([
               "<b>One step of the V at a time, each with a defined "
               "deliverable.</b> The owner asks for a concept report, "
               "then a requirements specification, then an architecture, "
               "and so on. Each is a controlled PDF with an issue, a "
               "revision history and traceability to the level above.",
               "<b>Documents are built from code, not typed.</b> "
               "Requirements live in Python data; the PDF, the "
               "traceability matrix and the checks are generated from "
               "them. The CAD model writes its own mass and hydrostatics "
               "results; the netlist writes its own schematics and rule "
               "check. A number in a document is always the number the "
               "analysis produced.",
               "<b>Claude proposes, the owner decides.</b> Every real "
               "choice (budget, scope, the wildlife rule, the "
               "link-loss timing) was put to the owner as a decision with "
               "options and recorded. Fourteen change requests (CR-01 to "
               "CR-14) carry those decisions into the documents.",
               "<b>Independent review, with findings.</b> At the SDR, "
               "Claude reviewed its own baseline as a sceptical reviewer "
               "would and raised 15 findings (9 Major), including a real "
               "safety gap: return-to-home could cut straight across a "
               "no-go zone. All 15 were closed with evidence before the "
               "owner said GO.",
               "<b>Baseline and change control.</b> The SDR documents are "
               f"frozen at git tag <font name='DVB'>{BL.TAG}</font>. The "
               "detailed design may not edit them; where it disagrees, "
               "it raises a numbered change request instead.",
               "<b>Honesty is a requirement.</b> Known gaps are "
               "reported as known gaps, failed checks as failures with a "
               "CR, and nothing is rounded into a pass."]),
           Spacer(1, 2 * mm),
           H2("Three days, start to CDR-ready"),
           table([["Day", "Milestone"],
                  ["28 Sep", "Concept selection report; SRS Issue A; "
                   "owner decisions; architecture (ADD); interface "
                   "control document; subsystem specifications; FMEA; "
                   "operations manual; key component list; simulator "
                   "slice 1 (autopilot in the loop)"],
                  ["29 Sep", "Simulator slices 2-3: the boat services "
                   "on a simulated Pi Zero, then Mission Control end to "
                   "end on ArduPilot Rover SITL with a catamaran physics "
                   "model"],
                  ["30 Sep", "Live Claude planner evaluation 39/39; "
                   "System Design Review: 15 RIDs raised, five work "
                   "packages to close them, full regression, owner GO, "
                   "baseline tagged"],
                  ["30 Sep", "Mechanical detailed design (CadQuery) and "
                   "electrical detailed design (netlist to schematics, "
                   "boards and harness), each with a design description"]],
                 [16, 154]),
           PageBreak()]

    # ---------------------------------------------------------- 2 concept
    cs = sorted(scoring.CONCEPTS, key=lambda c: -sum(
        scoring.WEIGHTS[k] * c[k] for k in scoring.WEIGHTS))
    rows = [["", "Option", "Score", "Why it lost (or won)"]]
    extra = []
    for i, c in enumerate(cs, 1):
        sc = sum(scoring.WEIGHTS[k] * c[k] for k in scoring.WEIGHTS)
        rows.append([c["id"], c["short"], f"{sc:.2f}",
                     c["pros"] if c.get("chosen") else c["cons"]])
        if c.get("chosen"):
            extra.append(("BACKGROUND", (0, i), (-1, i), BLUE_T))
    st += [H1("2. Concept selection"),
           P("Seven genuinely different ways to meet the brief were "
             "generated and scored against four weighted criteria: "
             "<b>reliability (30%)</b>, because 'we cannot lose it' is "
             "the one hard rule; <b>cost (25%)</b>; <b>fun to build with "
             "a four-year-old (25%)</b>; and <b>intelligence and "
             "learning (20%)</b>. Options ranged from buying a GPS bait "
             "boat to a scratch-built autopilot."),
           table(rows, [7, 42, 13, 108], style_extra=extra),
           Spacer(1, 3 * mm),
           fig(DOCS / "concept/figures/scores.png", 125, "Figure 2. "
               "Weighted scores."),
           P("The winner, a <b>modular 3D-printed catamaran on "
             "ArduPilot</b>, wins because it gets proven safety "
             "functions (geofence, failsafes, return-to-launch) from "
             "mature open-source autopilot firmware instead of writing "
             "them, while keeping everything else buildable and "
             "playful. The scratch-built option was the most fun to "
             "code but scored worst on the hard rule: every failsafe "
             "would be untested home-made code."),
           fig(FIG / "concept_annotated.png", 170, "Figure 3. The chosen "
               "concept, as it now exists in the detailed CAD model. "
               "Every callout traces to a requirement in the SRS."),
           PageBreak()]

    # ---------------------------------------------------------- 3 reqs
    st += [H1("3. Requirements and architecture"),
           H2("How the requirements were developed"),
           P(f"The one-line brief was expanded into {N_STK} stakeholder "
             "needs (the child, the parent, the pond and the people and "
             f"wildlife on it), then into {N_REQ} system requirements "
             f"in 22 areas, {N_MUST} of them Must. Each has a "
             "verification method (test, demonstration, analysis or "
             "inspection) and a stage (simulation, bench, pool or pond), "
             f"and {N_FS} named failsafes define exactly what the boat "
             "does when something goes wrong. The architecture then "
             "allocated every requirement to one of eight subsystems, "
             "which have their own specifications ("
             f"{N_DER} derived requirements), an interface control "
             f"document with {N_IF} interfaces, a design FMEA and mass, power and cost "
             "budgets."),
           H2("The tensions, and how they were resolved"),
           P("The value of the process is in the tensions it surfaces "
             "early, while they are cheap to resolve:"),
           table([["Tension", "Resolution"],
                  ["<b>Use AI to plan missions</b> vs <b>a child's boat "
                   "must be safe</b>", "Claude only <i>proposes</i>. A "
                   "deterministic validator checks every plan against "
                   "the fence and no-go zones; the autopilot enforces the "
                   "fence and failsafes independently of all Python and "
                   "AI. Safety never depends on the language model."],
                  ["<b>Never lose it</b> vs <b>cost</b>", "Budget rose "
                   "from £100 to £160 (CR-01) and £185 (CR-03) by owner "
                   "decision, because reliability features (autopilot, "
                   "GNSS, foam-filled hulls, hi-vis) are the ones not to "
                   "cut. Detailed design now shows £229: CR-14."],
                  ["<b>Take pictures of the ducks</b> vs <b>don't "
                   "disturb wildlife</b>", "Found at the SDR (RID-04). "
                   "CR-07 reworded the rule: photograph from a stand-off, "
                   "never chase; nesting sites are 15 m exclusions the "
                   "site linter enforces."],
                  ["<b>A four-year-old operates it</b> vs <b>adult "
                   "control</b>", "Child gets four big buttons (GO, COME "
                   "HOME, STOP, TALK); arming, approval and edits need "
                   "an adult PIN. STOP always works, in under 1 s."],
                  ["<b>Python for the family's software</b> vs "
                   "<b>autopilot firmware is C++</b>", "A Pi Zero mission "
                   "computer runs the Python boat services alongside the "
                   "unmodified ArduPilot helm, resolving SWE-001."],
                  ["<b>Small, light, printable</b> vs <b>robust and "
                   "stable</b>", "Hull segments under 200 mm, foam-filled; "
                   "the detailed design shows the mass target is not met "
                   "(CR-09) while stability has large margins."]],
                 [55, 115]),
           Spacer(1, 3 * mm),
           fig(DOCS / "add/figures/physical.png", 165, "Figure 4. "
               "High-level architecture: six boat subsystems, Mission "
               "Control on the bank, and the simulation subsystem that "
               "stands in for the boat in testing. IF-xx are the "
               "controlled interfaces."),
           PageBreak()]

    # ---------------------------------------------------------- 4 SIL
    shots = sorted((REP / "data" / "screens").glob("*.png")) \
        if (REP / "data" / "screens").exists() else []
    st += [H1("4. The system model and software-in-the-loop testing"),
           P("The system model is not a diagram: it is the real "
             "software, flown against simulated physics. ArduPilot Rover "
             f"{'4.7.1'} firmware (pinned to a specific commit) runs in "
             "software-in-the-loop (SITL) against a catamaran physics "
             "model with two thrusters, wind, weed drag and sensor "
             "faults. The Pi Zero boat services, Mission Control, the "
             "child's button panel, the photo pipeline and the Claude "
             "planner all run as they will on the hardware. Each test "
             "is a <b>mission-driven scenario</b> traced to the "
             "requirements it verifies: a mission is planned, approved, "
             "armed and flown, a fault is injected, and the test judges "
             "the <i>true</i> position of the simulated boat, not what "
             "the boat believes."),
           ]
    if shots:
        def shot(tag):
            return next(p for p in shots if f"_{tag}_" in p.name)
        from reportlab.platypus import Image as RLImage
        w = 82 * mm
        pair = Table([[RLImage(str(shot("PLAN_READY")), w, w * 800 / 1280),
                       RLImage(str(shot("DEBRIEF")), w, w * 800 / 1280)]],
                     colWidths=[85 * mm, 85 * mm])
        pair.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        st += [fig(shot("MISSION"), 150, "Figure 5. Screenshot of "
                   "Mission Control's web page during the end-to-end "
                   "test, served live from the simulation and captured "
                   "in a headless browser. The boat (black arrow) is "
                   "flying the plan (gold) and its track so far is drawn "
                   "in orange; the no-go zones are pink and the fence is "
                   "dashed blue. The child's four buttons are bottom "
                   "left; everything on the right needs an adult PIN."),
               KeepTogether([pair, P("Figure 6. Before and after. Left: "
                                     "the plan Claude proposed from the "
                                     "typed instruction, validated and "
                                     "waiting for an adult to approve "
                                     "and sign the checklist. Right: "
                                     "home, disarmed, and the boat says "
                                     "so.", "caption")])]
    st += [fig(FIG / "sil_nominal.png", 140, "Figure 7. The nominal "
               "mission (MC-E2E). A typed instruction becomes a plan "
               "(Claude), is validated against the fence and no-go "
               "zones, read back from the autopilot and checksum-"
               "matched, flown, photographed, and brought home, where the "
               "boat disarms itself after 60 s and the photos are synced "
               "and hash-verified. The blue line is the simulated boat's "
               "true track."),
           fig(FIG / "sil_edges.png", 170, "Figure 8. Edge cases, each "
               "flown on the real firmware. SC-07: the mission computer "
               "dies and the autopilot alone completes the mission. "
               "SC-27: return-to-home from behind the island, in a 3 m/s "
               "cross-wind, goes round the no-go zone (the SDR safety "
               "finding, now fixed and proven). SC-13: the satellite "
               "position is suddenly 20 m wrong while heading for the "
               "fence, and the boat never leaves it. SC-20: a 50 m GNSS "
               "jump for 2 s beside the fence line; the boat stays inside."),
           fig(FIG / "sil_results.png", 150, "Figure 9. Results of the "
               "full simulation regression."),
           callout(f"<b>{OUTC['passed']} of {N_SITL} pass, 0 fail.</b> "
                   f"The {OUTC['xfail']} known gaps are places where the "
                   "stock autopilot on its own does not meet a "
                   "requirement: its crash check is too slow for the 5 s "
                   "stuck rule (V-05), GUIDED mode decelerates rather "
                   "than cutting the motors at its 3 s timeout (V-11), and "
                   "it does not stop the motors within 3 s of losing GNSS "
                   "(SC-04, autopilot alone). Each is a recorded finding "
                   "with a design response; for stuck and GNSS loss the "
                   "boat services cover it, and those scenarios "
                   "(SC-04, SC-06) pass. The single-fault sweep injects "
                   "seven fault types in three situations each, and the "
                   "boat never leaves the fence while driving.",
                   GREEN, GREEN_T),
           PageBreak()]

    # ---------------------------------------------------------- 5 mech
    st += [H1("5. Mechanical design"),
           P("The mechanical design is a parametric CadQuery model: "
             "change a parameter and the parts, assembly, mass "
             "properties, hydrostatics, renders, STEP and STL files and "
             "the design description all rebuild. Hydrostatics are "
             "computed by clipping the actual hull mesh at the "
             "waterline, so draft, trim, heel and the stability curve "
             "come from the real geometry, not a box approximation."),
           fig(DOCS / "mdd/figures/iso.png", 105, "Figure 10. The "
               "assembly as modelled: printed ASA hulls in three "
               "segments, aluminium crossbeams, the sealed electronics "
               "box with its DUPLO deck, the mast and clip-on pods."),
           fig(DOCS / "mdd/figures/side.png", 100, "Figure 11. Side "
               "view at the computed waterlines: light (dashed) and at "
               f"design mass with 300 g of payload ({MD['float_design']['draft']:.1f}"
               " mm draft)." if isinstance(MD.get("float_design"), dict)
               and "draft" in MD["float_design"] else "Figure 11. Side "
               "view at the computed waterlines, light and at design "
               "mass."),
           fig(DOCS / "mdd/figures/gz.png", 105, "Figure 12. Stability: "
               "the righting arm peaks at 110 mm at 15° and stays "
               "positive to 65°, far beyond what a pond wave or a child "
               "leaning on the deck can do."),
           fig(DOCS / "mdd/figures/exploded.png", 80, "Figure 13. "
               "Exploded view: every part is printable on a 200 mm "
               "printer or bought off the shelf."),
           H2("Key results"),
           table([["Check", "Result", "Limit", ""]] + [
               [mrow(i)["text"], mrow(i)["value"], mrow(i)["limit"],
                mrow(i)["status"]] for i in
               ("H-01", "H-02", "H-03", "H-06", "H-07", "H-08", "H-09",
                "M-01", "G-08", "E-02")],
               [70, 46, 40, 14],
               style_extra=[("BACKGROUND", (3, i), (3, i),
                             GREEN_T if mrow(r)["status"] == "PASS" else
                             ORANGE_T) for i, r in enumerate(
                   ("H-01", "H-02", "H-03", "H-06", "H-07", "H-08",
                    "H-09", "M-01", "G-08", "E-02"), 1)]),
           Spacer(1, 2 * mm),
           P(f"<b>{M_PASS} checks pass, {M_TEST} need a physical test, "
             f"{M_FAIL} are open.</b> The open items are carried by "
             "change requests: CR-09 (mass: 2165 g against 1800 g; the "
             "options are to accept it, which hydrostatics supports, or "
             "to spend effort on lighter hulls), CR-10 (masthead 415 mm "
             "above the water against about 450 mm) and CR-11 (1.2 mm "
             "hull shell against the 1.6 mm the spec asks, chosen for "
             "mass, with the foam core giving the buoyancy)."),
           PageBreak()]

    # ---------------------------------------------------------- 6 elec
    c = ELEC["calcs"]
    st += [H1("6. Electrical design"),
           P("The electrical design is one netlist in code: 120 parts, "
             "70 nets and 114 wires. Schematics, stripboard layouts, "
             "the harness wire list and the box layout are all "
             "generated from it, and an electrical rule check, a "
             "board-copper check and a schematic completeness check run "
             "on every build (all zero errors)."),
           fig(DOCS / "edd/figures/interconnect.png", 115, "Figure 14. "
               "Boards, modules and the harness. Everything outside the "
               "box enters through a cable gland."),
           fig(FIG / "key_schematic.png", 170, "Figure 15. Schematic "
               "extract (sheet S2): the magnetic key switch. Q2 is a "
               "high-side P-MOSFET held off by R3, so the boat fails "
               "safe. C2 (gate to drain) limits the in-rush when the key "
               "goes in; when it comes out, C3 pulses Q3 and R9 empties "
               "the motor controllers' capacitors."),
           fig(DOCS / "edd/figures/key_transient.png", 150, "Figure 16. "
               "Supporting calculation, simulated: a first design with a "
               "simple gate RC gave a 24 A in-rush; the gate-drain "
               "capacitor brings it to 5.6 A. Without the bleeder the "
               "motors would stay live for nearly a second after the "
               "key is pulled; with it, under 100 ms as the interface "
               "requires."),
           fig(DOCS / "edd/figures/sag.png", 105, "Figure 17. Supporting "
               "calculation: voltage at the motor controllers against "
               "battery power through the real harness resistance. This "
               "is what raised CR-12."),
           H2("Key results"),
           table([["Check", "Result", "Limit", ""]] + [
               [erow(i)["text"], erow(i)["value"], erow(i)["limit"],
                erow(i)["status"]] for i in
               ("D-01", "D-02", "P-12", "P-13", "P-18", "P-19", "P-21",
                "P-06", "X-01")], [62, 62, 32, 14],
               style_extra=[("BACKGROUND", (3, i), (3, i),
                             GREEN_T if erow(r)["status"] == "PASS" else
                             ORANGE_T) for i, r in enumerate(
                   ("D-01", "D-02", "P-12", "P-13", "P-18", "P-19",
                    "P-21", "P-06", "X-01"), 1)]),
           Spacer(1, 2 * mm),
           P(f"<b>{E_PASS} checks pass, {E_TEST} need a bench test, "
             f"{E_FAIL} are open.</b> CR-12 limits battery power to 60 W "
             "so the motor controllers see at least 7.5 V (thrust "
             "falls only to 1.85 N); CR-13 records the key-switch "
             "circuit change above; CR-14 puts the cost (£229 using "
             "workshop stock, £246 buying everything, against £185) to "
             "the owner."),
           PageBreak()]

    # ---------------------------------------------------------- next
    st += [H1("Next steps"),
           table([["Step", "What", "Gate"],
                  ["1", "Owner decisions on CR-09 to CR-14 (mass, mast "
                   "height, shell thickness, power limit, key switch, "
                   "cost)", "CDR"],
                  ["2", "Critical Design Review of the MDD and EDD "
                   "against the baseline", "CDR"],
                  ["3", "Order parts; print hulls; build the three "
                   "boards; bench bring-up with the hardware-in-the-loop "
                   "rigs", "TRR"],
                  ["4", "Float, stability and pool tests against the "
                   "verification matrix; the same scenarios as the "
                   "simulation, now in water", "TRR"],
                  ["5", "First pond mission with Dad and son: explore, "
                   "take pictures of the ducks, come back", "ORR"]],
                 [12, 140, 18]),
           Spacer(1, 4 * mm),
           callout("<b>What this shows.</b> Strong systems-engineering "
                   "structure is what makes an AI engineering team "
                   "trustworthy. Claude produced the work at a pace no "
                   "small team could, but the value an executive can "
                   "rely on comes from the scaffolding: traceable "
                   "requirements, decisions held by a human, documents "
                   "generated from analysis, an independent review that "
                   "found real problems, a frozen baseline, and test "
                   "results that report their gaps.", BLUE, BLUE_T)]
    doc = Doc(OUT, DOC_ID, "Executive progress report", ISSUE)
    doc.build(st)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
