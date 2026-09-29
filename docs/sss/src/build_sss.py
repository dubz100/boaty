"""Build the Boaty subsystem specifications (BOATY-SSS-<code>).

Run:  python3 docs/sss/src/build_sss.py
Writes docs/sss/BOATY-SSS-<code>_<name>.pdf for each subsystem and
docs/sss/Boaty_Subsystem_Specifications_Volume.pdf (all eight combined).
"""
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
sys.path.insert(0, str(DOCS / "common"))
sys.path.insert(0, str(DOCS / "icd" / "src"))

import sss_data as SD  # noqa: E402
from pdfdoc import (BLUE_T, GREEN_T, ORANGE, ORANGE_T, H1, H2, P, TINT,  # noqa: E402
                    Doc, KeepTogether, PageBreak, Paragraph, S, Spacer,
                    bullets, callout, colors, control_and_contents, cover, mm,
                    table)
from build_icd import OWNER as IF_OWNER  # noqa: E402

A = SD.A
SRS = SD.SRS
OUTDIR = HERE.parent
DATE = "28 September 2026"
ISSUE = "Issue A (for review)"
PRI_COL = {"M": "#2a78d6", "S": "#1baf7a", "C": "#9a998f"}
REQS = {r["id"]: r for r in SRS.all_reqs()}
IFS = {i[0]: i for i in A.INTERFACES}
NAMES = {s[0]: s[1] for s in A.SUBSYSTEMS} | A.EXTERNALS
ICD_SECTION = {}
for sec, ids in [("4", ["IF-01", "IF-02", "IF-04", "IF-03", "IF-10",
                        "IF-11"]),
                 ("5", ["IF-13", "IF-14", "IF-15", "IF-21"]),
                 ("6", ["IF-05", "IF-06", "IF-07", "IF-08", "IF-09",
                        "IF-22"]), ("7", ["IF-12"]),
                 ("8", ["IF-16", "IF-17", "IF-18", "IF-19", "IF-20"])]:
    for i in ids:
        ICD_SECTION[i] = sec


def pri(p):
    return Paragraph(f'<font color="{PRI_COL[p]}"><b>{p}</b></font>',
                     S["cellc"])


def short(t, n=120):
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


# ------------------------------------------------------------------ specials
def special_hul():
    L, B, D, cb = 0.60, 0.09, 0.10, 0.6
    vol = 2 * L * B * D * cb * 1000              # litres
    mass = 2.1
    awp = 2 * L * B * 0.7
    draft = mass / 1000 / awp * 1000             # mm
    s = 0.27
    i_t = 2 * (L * B * 0.7) * (s / 2) ** 2
    bm = i_t / (mass / 1000)
    rm_deg = mass * 9.81 * bm * math.sin(math.radians(1))
    heel = 0.3 * 9.81 * 0.18 / rm_deg
    worst = vol * (4 / 6)
    return [H1("6. Design analysis: buoyancy and stability"),
            P("Hand estimates that size HUL-D04 to D09. They are checked "
              "against CAD volumes and then pool tests."),
            table([["Quantity", "Working", "Result"],
                   ["Hull volume", f"2 × {L*1000:.0f} × {B*1000:.0f} × "
                    f"{D*1000:.0f} mm × Cb {cb}", f"{vol:.1f} L"],
                   ["Design mass", "Boat 1.8 kg + payload 0.3 kg",
                    f"{mass} kg"],
                   ["Draft", f"Displaced {mass:.1f} L / waterplane "
                    f"{awp*1e4:.0f} cm² (Cwp 0.7)", f"≈ {draft:.0f} mm "
                    "(≤ 35 mm)"],
                   ["Reserve buoyancy", f"{vol:.1f} L vs {mass:.1f} L",
                    f"{vol/mass:.1f}×"],
                   ["Two segments lost (worst case, no foam credit)",
                    f"{vol:.1f} × 4/6", f"{worst:.1f} L = "
                    f"{worst/mass:.1f}× design mass (≥ 1.5×)"],
                   ["Transverse BM (catamaran)", f"2·A<sub>wp</sub>·"
                    f"(s/2)² / V, s = {s*1000:.0f} mm", f"≈ {bm:.2f} m"],
                   ["Righting moment", "Δ·g·GM·sin 1°, GM ≈ BM",
                    f"≈ {rm_deg:.2f} N·m per degree"],
                   ["Heel, 300 g at 180 mm", "0.53 N·m / RM per degree",
                    f"≈ {heel:.1f}° (≤ 10°)"]],
                  [44, 76, 50]),
            P("A catamaran this wide is very stiff. The practical capsize "
              "risk is a wave or wake over a low bow, which is why HUL-D09 "
              "is demonstrated rather than calculated.", "small")]


def special_prp():
    rho, s_wet, ct = 1000, 0.18, 0.012
    d_water = lambda v: 0.5 * rho * v * v * s_wet * ct  # noqa: E731
    a_air, cd = 0.035, 1.1
    d_wind = 0.5 * 1.225 * (5.4 + 0.5) ** 2 * a_air * cd
    need = d_water(0.5) * 1.5 + d_wind
    cruise = d_water(1.0) * 1.3
    return [H1("6. Design analysis: thrust and power"),
            table([["Case", "Working", "Result"],
                   ["Water drag at 0.5 m/s", f"½ρv²·S·C<sub>t</sub>, S = "
                    f"{s_wet} m², C<sub>t</sub> = {ct}, ×1.5 form",
                    f"{d_water(0.5)*1.5:.2f} N"],
                   ["Wind drag, 5.4 m/s head wind", f"½ρ<sub>air</sub>"
                    f"(5.9 m/s)²·{a_air} m²·{cd}", f"{d_wind:.2f} N"],
                   ["Needed for ENV-002", "sum", f"≈ {need:.1f} N"],
                   ["Specified thrust (PRP-D02)", "≥ 4 N combined",
                    f"margin ≈ {4/need:.1f}×"],
                   ["Drag at 1.0 m/s cruise", "with wave-making ×1.3",
                    f"≈ {cruise:.1f} N → {cruise:.1f} W at the water"],
                   ["Electrical at cruise", "overall efficiency ≈ 15%",
                    f"≈ {cruise/0.15:.0f} W (PRP-D04 ≤ 10 W)"]],
                  [44, 86, 40]),
            P("Small printed props in shrouds are inefficient. The 15% "
              "figure is deliberately pessimistic and gets replaced by "
              "bench thrust-stand data.", "small")]


def special_pwr():
    loads = [("Helm + GNSS", 0.8), ("Mission computer (avg)", 1.8),
             ("Beacon", 0.3), ("ESC idle", 0.2), ("Motors at cruise", 8.0)]
    tot = sum(x for _, x in loads)
    usable = 3 * 3.6 * 3.0 * 0.8
    return [H1("6. Design analysis: power budget"),
            table([["Load", "W"]] + [[n, f"{v:.1f}"] for n, v in loads] +
                  [["<b>Total at cruise</b>", f"<b>{tot:.1f}</b>"],
                   ["Usable energy (3S, 3.0 Ah, 80%)", f"{usable:.1f} Wh"],
                   ["Endurance estimate", f"≈ {usable/tot*60:.0f} min "
                    "(≥ 40 min required, ≥ 60 target)"],
                   ["Margin at 40 min", f"{(usable/tot*60/40 - 1):.0%}"]],
                  [130, 40]),
            P("Circuit: battery → fuse → main switch → power module → bus. "
              "The bus feeds the helm (own regulator), the 5 V buck (MCP) "
              "and, through the key-switched MOSFET, the ESCs. See ADD "
              "figure 6.", "small")]


def special_hlm():
    return [H1("6. Controlled parameter baseline"),
            P("The configuration that implements the requirements above. "
              "<b>This table is generated from software/params/"
              "boaty-mk1.parm (behaviour, also flown in the simulator) and "
              "boaty-mk1-speedybee.parm (board wiring)</b>, so it is always "
              "the file that is flashed. Every behaviour parameter was "
              "checked against Rover 4.7.1 in SITL (IF-14-02)."),
            table([["Group", "Parameter", "Value", "Why"]] +
                  [list(r) for r in SD.HLM_PARAMS], [30, 44, 16, 80]),
            Spacer(1, 3 * mm),
            H2("6.1 Where each failsafe step lives"),
            table([["Requirement", "Helm (native)", "Boat Python (MCP)",
                    "Mission Control"],
                   ["FS-001", "RTL at 35%; RTL + alarm at 15%",
                    "Slow RTL to 0.6 m/s at 15% (B6)", "Announce"],
                   ["FS-002", "HOLD at 3 s (CR-05)", "RTL at 10 s (B4)",
                    "Show 'link lost'"],
                   ["FS-003", "Continue in AUTO", "RTL at 60 s (B4)", "-"],
                   ["FS-004", "EKF failsafe HOLD (backstop, ~9 s)",
                    "HOLD within 3 s; RTL after 10 s healthy (B6)",
                    "Announce"],
                   ["FS-005/006", "HOLD on stuck (crash check)", "Second "
                    "detector at 10 s (B7); ≤ 3 astern bursts (B5)",
                    "Announce"],
                   ["FEN-005/006", "RTL on breach", "HOLD at 30 s or 10 m "
                    "outside (B7)", "HOLD if persistent (MCN-D59)"]],
                  [24, 50, 48, 48]),
            P("Rule: nothing outside the helm is the last line of defence "
              "for an action the helm can take. Where the helm cannot "
              "(FS-001 speed, FS-004 timing, FEN-006) the boat services "
              "add the step, and each is proven in simulation "
              "(software/results).", "small")]


def special_mcp():
    return [H1("6. Timing"),
            table([["Event", "Response", "Budget"],
                   ["MISSION_ITEM_REACHED (photo point)", "First photo of "
                    "the burst", "≤ 0.5 s"],
                   ["Interval tick", "Photo captured", "± 0.2 s"],
                   ["Moisture detected", "RTL requested", "≤ 2 s"],
                   ["No system-255 heartbeat in AUTO", "RTL requested",
                    "60 s ± 1 s"],
                   ["Helm stuck event", "First astern burst", "≤ 1 s"],
                   ["Power-on", "All services running", "≤ 45 s"],
                   ["POST /v1/shutdown", "Filesystems synced, halt", "≤ 10 s"]],
                  [60, 60, 50])]


def special_mcn():
    comp = [c for c in A.COMPONENTS if c[0] == "MCN"]
    return [H1("6. Component map"),
            P("Mission Control's application components (ADD section 4.3) "
              "and the derived requirements each implements. Button "
              "behaviour by state is defined in ICD IF-12."),
            table([["ID", "Component", "Responsibility", "Derived "
                    "requirements"],
                   ["C1/C2", "Session manager, panel I/O", "States, gating, "
                    "checklist, adult key", "MCN-D08 … D15"],
                   ["C3", "Web UI", "Map, editors, photo review, manual",
                    "MCN-D16 … D24"],
                   ["C4", "Voice", "TALK, STT, TTS", "MCN-D25 … D27"],
                   ["C5", "Planner", "Claude intent, geometry, templates",
                    "MCN-D28 … D37"],
                   ["C6/C7", "Validator, helm interface", "Single mission "
                    "path, read-back, parameters", "MCN-D38 … D46"],
                   ["C8/C10", "Photos & log, logger", "Sync, finder, "
                    "captain's log, replay", "MCN-D47 … D52"],
                   ["C9", "Site store", "GeoJSON sites (IF-15)", "MCN-D19"]],
                  [14, 40, 66, 50])]


def special_sim():
    def tt(kind, ids=None):
        rows = [["ID", "Test", "Injection / method", "Pass criterion",
                 "Refs", "Result"]]
        style = []
        for t in SD.TESTS:
            if t[1] == kind and (ids is None or t[0] in ids):
                res = SD.SIM_RESULTS.get(t[0], "-") if kind == "SIM" else "-"
                rows.append([f"<b>{t[0]}</b>", t[2], t[3], t[4],
                             ", ".join(t[5]), res])
                if res.startswith("Pass"):
                    style.append(("BACKGROUND", (5, len(rows) - 1),
                                  (5, len(rows) - 1), GREEN_T))
                elif res != "-":
                    style.append(("BACKGROUND", (5, len(rows) - 1),
                                  (5, len(rows) - 1), ORANGE_T))
        return table(rows, [13, 40, 36, 40, 23, 18], style_extra=style)

    fs_ids = {f"SC-{i:02d}" for i in range(1, 14)}
    fm_ids = {t[0] for t in SD.TESTS if t[1] == "SIM"} - fs_ids
    earlier = [
        ("FS-009 STOP ≤ 1 s", "BENCH / POOL", "L1-03 (to helm), L2-11 (to "
         "motors stopped)", "On-water confirmation (POOL)"),
        ("COM-003 telemetry and latency", "POOL", "L1-03, L1-05",
         "Range effects (LAKE)"),
        ("CAM-007 / MCP-D16 photo sync", "POOL", "L1-04", "-"),
        ("MCN-D21 link quality display", "POOL", "L1-07", "-"),
        ("MCN-D22 manual drive", "POOL", "L2 (motors follow the joystick)",
         "Handling (POOL)"),
        ("NAV-001 bidirectional thrust", "POOL", "L2-01, L3-01", "-"),
        ("PRP-D02 thrust ≥ 4 N", "BENCH (estimate)", "L3-01 (measured)",
         "-"),
        ("PRP-D03/D04 cruise throttle and power", "POOL", "L3-03 (estimate "
         "from data)", "Confirm (POOL)"),
        ("PRP-D11 / ENV-005 weed", "LAKE", "L3-02 (real weed)", "Confirm "
         "(LAKE)"),
        ("FS-005/006 stuck and shedding", "POOL", "SC-05/06 + L3-02",
         "Confirm (POOL)"),
        ("FS-001 / FS-004 on real hardware", "SIM only", "L2-09, L2-03/04",
         "-"),
        ("REC-D03 beacon patterns", "LAKE", "L2-12 (patterns)",
         "Visibility (LAKE)"),
        ("PWR-010 thermal", "BENCH", "L1-09 under a real workload", "-"),
    ]
    return [H1("6. Test catalogue"),
            P("Every test has an ID, which the FMEA (BOATY-FMEA-001) and "
              "the test procedures reference. SC = simulator scenario; "
              "L1/L2/L3 = rig tests; B = bench; R = rehearsal; P = pool. "
              "Injection parameter names are fixed per SITL version "
              "and kept in the scenario code. <b>Result</b> is read from "
              "software/results/sitl_results.json (slices 1-2); '-' means "
              "not yet built (mostly slice 3, Mission Control)."),
            H2("6.1 Failsafe scenarios (one per FS requirement)"),
            tt("SIM", fs_ids),
            H2("6.2 FMEA-derived simulator scenarios"),
            tt("SIM", fm_ids),
            H2("6.3 Rig L1: real computers, simulated boat"),
            tt("L1"),
            H2("6.4 Rig L2: iron bird"),
            tt("L2"),
            H2("6.5 Rig L3: water tank"),
            tt("L3"),
            H2("6.6 Bench, rehearsal and pool items referenced by the FMEA"),
            table([["ID", "Kind", "Test", "Pass criterion", "Refs"]] +
                  [[f"<b>{t[0]}</b>", t[1], t[2], t[4], ", ".join(t[5])]
                   for t in SD.TESTS if t[1] in ("BENCH", "REHEARSAL",
                                                 "POOL")],
                  [14, 22, 50, 58, 26]),
            H2("6.7 What the rigs verify earlier"),
            table([["Item", "First verified (Issue A)", "Now also by",
                    "Still needs"]] + [list(e) for e in earlier],
                  [52, 34, 50, 34]),
            P("The FMEA check (SIM-D24) confirms that every failure mode "
              "with severity ≥ 8 has at least one test here.", "small")]


SPECIALS = {"hul": special_hul, "prp": special_prp, "pwr": special_pwr,
            "hlm": special_hlm, "mcp": special_mcp, "mcn": special_mcn,
            "sim": special_sim}


# ------------------------------------------------------------------ document
def build_one(code):
    ss = SD.SUBSYSTEMS[code]
    alloc = A.allocation()
    derived = list(SD.all_derived(ss))
    prim = [k for k, (p, _) in alloc.items() if p == code]
    supp = [k for k, (_, s) in alloc.items() if code in s]
    by_parent = {}
    for d in derived:
        for t in d["trace"]:
            by_parent.setdefault(t, []).append(d["id"])
    doc_id = f"BOATY-SSS-{code}"
    issue = ss.get("issue", ISSUE)
    pc = Counter(d["pri"] for d in derived)

    st = cover(f"Subsystem Specification<br/>{ss['title']}",
               ss["purpose"],
               [["Document", doc_id], ["Issue", issue],
                ["Date", (ss.get("history") or [[None, DATE]])[-1][1]],
                ["Status", "For review by the project owner"],
                ["Parents", ss.get("parents", "SRS Issue D, ADD Issue C, "
                                   "ICD Issue B")],
                ["Content", f"{len(prim)} allocated SRS requirements → "
                 f"{len(derived)} subsystem requirements ({pc['M']} M, "
                 f"{pc['S']} S, {pc['C']} C)"]])
    st += control_and_contents(
        [["A", DATE, "First issue, for review.", "Claude (drafted)"]] +
        ss.get("history", []),
        "Review guidance: section 5 is what will be built and tested. Check "
        "that each requirement is right, sufficient and testable. Section 4 "
        "shows every parent requirement is covered (the build script "
        "checks this).")

    # 1 scope
    st += [H1("1. Scope"),
           H2("1.1 Purpose"), P(ss["purpose"]),
           H2("1.2 Boundary"),
           table([["Inside this subsystem", "Outside (and who owns it)"],
                  ["<br/>".join("• " + x for x in ss["inside"]),
                   "<br/>".join("• " + x for x in ss["outside"])]],
                 [85, 85]),
           H2("1.3 Breakdown"),
           table([["Item", "Description"]] + [list(b) for b in
                                              ss["breakdown"]], [55, 115]),
           H2("2. Applicable documents"),
           table([["Document", "Use"],
                  ["BOATY-SRS-001 Issue D", "Parent requirements"],
                  ["BOATY-ADD-001 " + ("Issue D" if ss.get("parents") else
                                       "Issue C"), "Allocation, decisions, "
                   "budgets, early verification items"],
                  ["BOATY-ICD-001 " + ("Issue C" if ss.get("parents") else
                                       "Issue B"), "Interface definitions "
                   "(all listed in section 3 apply in full)"]] +
                 ([["BOATY-FMEA-001 Issue B", "Failure modes and actions "
                    "carried into this issue"]] if ss.get("parents") else []),
                 [55, 115])]

    # 3 interfaces
    rows = [["Interface", "Other end", "Role", "ICD"]]
    for i in A.INTERFACES:
        if code in (i[2], i[3]):
            other = i[3] if i[2] == code else i[2]
            other = "internal" if other == code else NAMES.get(other, other)
            role = "Owner" if IF_OWNER[i[0]] == code else "Conforms"
            rows.append([f"<b>{i[0]}</b> {i[1]}", other, role,
                         f"§{ICD_SECTION[i[0]]}"])
    st += [H1("3. Interfaces"),
           P("The subsystem shall meet every interface below as defined in "
             "the ICD. 'Owner' means this subsystem maintains the "
             "definition."),
           table(rows, [72, 50, 24, 24])]

    # 4 parents
    prow = [["SRS", "Pri", "Requirement (abridged)", "Met by"]]
    for k in prim:
        r = REQS[k]
        prow.append([f"<b>{k}</b>", pri(r["pri"]), short(r["text"]),
                     ", ".join(by_parent.get(k, []))])
    st += [PageBreak(), H1("4. Parent requirements"),
           P(f"<b>Primary ({len(prim)}):</b> this subsystem is responsible "
             "for meeting and verifying these SRS requirements."),
           table(prow, [18, 9, 100, 43])]
    if supp:
        st += [Spacer(1, 3 * mm),
               P(f"<b>Supporting ({len(supp)}):</b> another subsystem owns "
                 "these, but this subsystem must provide something for "
                 "them. Where relevant, section 5 includes the "
                 "contribution.", "body"),
               P(", ".join(f"{k}" for k in supp), "small")]

    # 5 derived
    st += [PageBreak(), H1("5. Subsystem requirements"),
           P(f"Requirements are numbered {code}-Dnn. Pri, Ver and Stage "
             "follow SRS conventions (M/S/C; Test, Demonstration, "
             "Inspection, Analysis, Simulation; SIM, BENCH, POOL, LAKE). "
             "'Trace' lists the parent SRS requirements, interfaces (IF), "
             "decisions (DD) and early verification items (V) it "
             "implements.", "small")]
    for gi, (heading, reqs) in enumerate(ss["groups"], start=1):
        rows = [["ID", "Requirement", "Pri", "Ver", "Stage", "Trace"]]
        for d in reqs:
            txt = [Paragraph(d["text"], S["cell"])]
            if d["note"]:
                txt.append(Paragraph(d["note"], S["note"]))
            rows.append([Paragraph(f"<b>{d['id']}</b>", S["cell"]), txt,
                         pri(d["pri"]), d["ver"].replace(",", ", "),
                         d["stage"], ", ".join(d["trace"])])
        st += [H2(f"5.{gi} {heading}"),
               table(rows, [17, 88, 8, 12, 13, 32])]

    # 6 special
    if ss.get("special"):
        st += [PageBreak()] + SPECIALS[ss["special"]]()

    # 7 constraints & budgets
    n7 = "7" if ss.get("special") else "6"
    st += [H1(f"{n7}. Design constraints and budgets"),
           *bullets(ss["constraints"]),
           Spacer(1, 2 * mm),
           table([["Budget", "Allocation"]] + [list(b) for b in
                                               ss["budget"]], [45, 125])]

    # 8 verification + open items
    n8 = str(int(n7) + 1)
    stages = ["SIM", "BENCH", "POOL", "LAKE"]
    methods = ["T", "D", "I", "A", "S"]
    grid = Counter()
    for d in derived:
        for mth in d["ver"].split(","):
            grid[(d["stage"], mth)] += 1
    vrows = [["Stage", "Test", "Demo", "Inspect", "Analysis", "Sim",
              "Reqs"]]
    for sg in stages:
        vrows.append([sg] + [str(grid[(sg, mm_)] or "-") for mm_ in methods]
                     + [f"<b>{sum(1 for d in derived if d['stage'] == sg)}"
                        "</b>"])
    st += [H1(f"{n8}. Verification and open items"),
           P("Each requirement is verified at its stage using the method "
             "shown. Test procedures are written per stage and reference "
             "these IDs."),
           table(vrows, [30, 22, 22, 22, 22, 22, 30]),
           Spacer(1, 4 * mm),
           table([["Ref", "Open item"]] + [list(o) for o in
                                           ss["open_items"]], [30, 140])]

    path = OUTDIR / f"{doc_id}_{ss['title'].replace(' & ', '_and_').replace(' ', '_')}.pdf"
    doc = Doc(path, doc_id, f"Subsystem Specification: {ss['title']}", issue)
    doc.multiBuild(st)
    return path, len(derived), len(prim)


def main():
    n = SD.check()
    paths = []
    for code in SD.ORDER:
        path, nd, npr = build_one(code)
        paths.append(path)
        print(f"{code}: {npr} parents → {nd} derived  {path.name}")
    import pymupdf
    vol = pymupdf.open()
    toc = []
    for code, pth in zip(SD.ORDER, paths):
        src = pymupdf.open(pth)
        start = vol.page_count + 1
        vol.insert_pdf(src)
        toc.append([1, f"{code} {SD.SUBSYSTEMS[code]['title']}", start])
        for lvl, title, page in src.get_toc():
            toc.append([lvl + 1, title, start + page - 1])
    vol.set_toc(toc)
    out = OUTDIR / "Boaty_Subsystem_Specifications_Volume.pdf"
    vol.save(out)
    print(f"{n} derived requirements in total; volume {vol.page_count} pages "
          f"→ {out.name}")


if __name__ == "__main__":
    main()
