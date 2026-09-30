"""Build BOATY-FMEA-001 (design FMEA), landscape A4.

Run:  python3 docs/fmea/src/build_fmea.py
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
sys.path.insert(0, str(DOCS / "common"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib.pagesizes import A4, landscape  # noqa: E402

import fmea_data as F  # noqa: E402
from pdfdoc import (ORANGE, ORANGE_T, H1, H2, P, Doc, PageBreak, KeepTogether,  # noqa
                    Paragraph, S, Spacer, bullets, callout, colors,
                    control_and_contents, cover, fig, mm, table)

SD = F.SD
OUT = HERE.parent / "Boaty_Design_FMEA.pdf"
FIGDIR = HERE.parent / "figures"
FIGDIR.mkdir(exist_ok=True)
DOC_ID = "BOATY-FMEA-001"
ISSUE = "Issue F (for review)"
DATE = "30 September 2026"
PREV_E = "29 September 2026"
PREV = "28 September 2026"
W = 257  # usable width in mm (landscape A4 minus margins)


def pareto():
    rows = sorted(F.ROWS, key=F.rpn, reverse=True)[:15][::-1]
    fig_, ax = plt.subplots(figsize=(9.5, 4.2))
    for i, r in enumerate(rows):
        hi = r[5] >= 9
        ax.barh(i, F.rpn(r), height=0.6,
                color="#2a78d6" if hi else "#c9c8c0")
        ax.text(F.rpn(r) + 3, i, f"{F.rpn(r)}", va="center", fontsize=8,
                color="#0b0b0b" if hi else "#52514e")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"{r[0]}  {r[3][:38]}" for r in rows], fontsize=8)
    ax.axvline(100, color="#52514e", lw=0.8, ls="--")
    ax.text(101, len(rows) - 0.4, "action threshold (RPN 100)", fontsize=7,
            color="#52514e", va="top")
    ax.set_xlabel("RPN = S × O × D", color="#52514e")
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(True, color="#e4e3dc")
    ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#2a78d6", label="Severity ≥ 9"),
                       Patch(color="#c9c8c0", label="Severity < 9")],
              loc="lower right", fontsize=7.5, frameon=False)
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig_.savefig(FIGDIR / "pareto.png", dpi=220, bbox_inches="tight",
                 facecolor="white")
    plt.close(fig_)


def build():
    n = F.check()
    F.check_b()
    SD.check()
    pareto()
    tests = {t[0]: t for t in SD.TESTS}
    acts = Counter(a for r in F.ROWS for a in r[12])
    sev = Counter(r[5] for r in F.ROWS)
    hi = [r for r in F.ROWS if r[5] >= 8]

    st = cover("Design FMEA", "Failure modes and effects analysis of the "
               "Mk1 architecture, used to drive simulator, rig and bench "
               "tests", [["Document", DOC_ID], ["Issue", ISSUE],
                         ["Date", DATE], ["Status", "Design stage (before "
                                          "hardware). Updated after rigs, "
                                          "pool and before the first lake "
                                          "trial (SAF-006)."],
                         ["Basis", "ADD Issue F, ICD Issue E, SSS Issues "
                          "B-D, simulator slices 1-2"],
                         ["Content", f"{n} failure modes, {len(F.ACTIONS)} "
                          f"actions, {len(SD.TESTS)} catalogued tests"]])
    st += control_and_contents(
        [["A", PREV, "First issue: design FMEA at architecture level.",
          "Claude (drafted)"],
         ["B", PREV, "Actions carried into SSS-HLM/MCP/MCN Issue B, ICD "
          "Issue C and ADD Issue D; status and post-action ratings added. "
          "A-05, A-09, A-17 await the operations manual.",
          "Claude, owner request"],
         ["C", PREV, "CR-03: salvaged cells (FM-23 O 1 → 2; A-20 cell "
          "acceptance) and adult PIN (new FM-48). Operations manual "
          "BOATY-OPS-001 closes A-05, A-09, A-11, A-17, A-19.",
          "Claude, owner decision"],
         ["D", PREV_E, "Simulator evidence (software/results): FM-08 re-rated "
          "with its real cause (KCL); FM-49 to FM-53 added; actions A-21 to "
          "A-24 incorporated; A-18 closed (V-14: no native mechanism); "
          "detection re-rated where a scenario now passes.",
          "Claude, owner decisions (CR-04, CR-05)"],
         ["E", PREV_E, "Mission Control in the simulator (slice 3): FM-54 to "
          "FM-58 added from what the runs found, actions A-25 to A-29 "
          "incorporated; FM-09, 10, 34, 35, 41 re-rated now SC-24, 25, 31, "
          "32 and 37 pass; FM-37 re-rated after the live Claude "
          "evaluation (SC-33).", "Claude"],
         ["F", DATE, "SDR decision CR-07: FM-44 controls now include the "
          "15 m nest stand-off enforced by the site linter (MCN-D65); "
          "SC-26 added to its tests. SDR WP2: FM-13 re-rated (O 3 → 2, "
          "D 3 → 2) now path planning is configured and SC-27 passes; "
          "FM-59 (RTL stalls near a zone) added from what SC-27 found. "
          "WP3: A-30 (B6 position-jump HOLD) after SC-20 found a sustained "
          "GNSS offset leaves the fence; FM-02 after-action RPN 108 → 72; "
          "FM-60 (home reset by re-arming on the water); S ≥ 9 rule text "
          "matches the build check.",
          "Claude, owner decision"]],
        "Review guidance: challenge the ratings, especially occurrence, "
        "which is a judgement before any hardware exists. And look for "
        "missing failure modes: an FMEA is only as good as its "
        "imagination.")

    # 1-2
    st += [H1("1. Purpose and scope"),
           P("This design FMEA looks for ways Boaty Mk1 can fail and asks "
             "three questions of each. How bad is the effect? How likely is "
             "it? Will our planned tests find it before the boat goes on "
             "the lake? It works at the level of the ADD's subsystems and "
             "interfaces, before detailed design. It has two jobs:"),
           *bullets([
               "<b>Drive the tests.</b> Every failure mode with severity ≥ 8 "
               "must be exercised by a simulator, rig or bench test in the "
               "SSS-SIM catalogue. The build checks this.",
               "<b>Change the design early.</b> Where a risk is high, "
               "actions go into the next subsystem-spec issues while "
               "changes are still cheap.",
           ]),
           P("It supports SAF-006 (FMEA before the first lake trial) and "
             "FS-013 (no single failure leaves the fence under power). It "
             "is a living document: ratings are revisited with rig, pool "
             "and lake evidence.", "small"),
           H1("2. Method"),
           H2("2.1 Rating scales")]
    st.append(table(
        [["S", "Severity (effect)", "O", "Occurrence", "D",
          "Detection by planned verification"]] +
        [[str(F.SEVERITY[i][0]), F.SEVERITY[i][1],
          str(F.OCCURRENCE[i][0]) if i < len(F.OCCURRENCE) else "",
          F.OCCURRENCE[i][1] if i < len(F.OCCURRENCE) else "",
          str(F.DETECTION[i][0]) if i < len(F.DETECTION) else "",
          F.DETECTION[i][1] if i < len(F.DETECTION) else ""]
         for i in range(len(F.SEVERITY))],
        [8, 88, 8, 58, 8, 87]))
    st += [H2("2.2 Rules"), *bullets(F.RULES),
           P("D rates our <i>verification</i> (will we find it before "
             "the lake?), not detection in operation. In-operation "
             "detection is listed separately as a control.", "small"),
           PageBreak()]

    # 3 worksheet
    rows = [["ID", "Item / function", "Failure mode", "Effect", "S",
             "Cause", "O", "Controls: prevent / detect in use", "D", "RPN",
             "After", "Tests", "Actions"]]
    style = []
    for i, r in enumerate(F.ROWS, start=1):
        rows.append([f"<b>{r[0]}</b><br/>{r[1]}", r[2], r[3], r[4],
                     f"<b>{r[5]}</b>", r[6], str(r[7]),
                     f"{r[8]} / {r[9]}", str(r[10]), f"<b>{F.rpn(r)}</b>",
                     (f"<b>{F.rpn_after(r)}</b>" if r[0] in F.POST
                      else "-"),
                     ", ".join(r[11]), ", ".join(r[12]) or "-"])
        if r[5] >= 9:
            style.append(("BACKGROUND", (4, i), (4, i),
                          colors.HexColor("#cfe1f6")))
        if F.rpn(r) >= 100:
            style.append(("BACKGROUND", (9, i), (9, i), ORANGE_T))
        if r[0] in F.POST and F.rpn_after(r) >= 100:
            style.append(("BACKGROUND", (10, i), (10, i), ORANGE_T))
    st += [H1("3. FMEA worksheet"),
           P("Blue S cell = severity ≥ 9. Orange RPN cell = at or above "
             "the action threshold. 'After' = RPN once the incorporated "
             "actions are in (Issue B); '-' = unchanged. Test IDs are "
             "defined in SSS-SIM Issue B, section 6.", "small"),
           table(rows, [16, 22, 29, 31, 7, 25, 7, 40, 7, 10, 11, 29, 17],
                 style_extra=style),
           PageBreak()]

    # 4 results
    st += [H1("4. Results"),
           fig(FIGDIR / "pareto.png", 200, "Figure 1. The 15 highest RPNs. "
               "Severity ≥ 9 rows need action or a direct test whatever "
               "their RPN."),
           P(f"Severity profile: {sev[10]} rows at S10, {sev[9]} at S9, "
             f"{sev[8]} at S8; {len(hi)} rows at S ≥ 8, all with tests. "
             f"{sum(1 for r in F.ROWS if F.needs_action(r))} rows meet an "
             "action rule. Those with a direct test (D ≤ 3) are covered by "
             "the test; the rest have actions."),
           H2("4.1 What the FMEA changed"),
           *bullets([
               "<b>Three new boat-side safeguards</b> (actions A-03, A-07, "
               "A-08). A first-motion heading check catches a reversed "
               "compass or motor. A second stuck detector covers weed "
               "creep. A navigation-divergence watchdog catches a dead "
               "motor. All three only request HOLD, so they stay within "
               "the ADD's rule for boat-side Python.",
               "<b>Procedures matter as much as code.</b> The fence-vs-shore "
               "offset (A-05), the launch point for the wind (A-19), the "
               "lookout for other water users (A-17) and key-out handling "
               "(A-09) come from operational failure modes. They go into "
               "an operations manual.",
               "<b>Twenty FMEA-derived simulator scenarios (SC-20 to "
               "SC-39)</b> and thirteen iron-bird rig tests. The first "
               "catalogue only covered the failsafes we'd already "
               "designed.",
           ]),
           H2("4.2 After the incorporated actions"),
           P("Every action is now incorporated: in the subsystem specs, the "
             "ICD or the operations manual (BOATY-OPS-001). Rows still at or "
             "above the action threshold after their actions: " +
             ", ".join(f"<b>{r[0]}</b> ({F.rpn_after(r)})" for r in
                       sorted(F.ROWS, key=F.rpn_after, reverse=True)
                       if F.rpn_after(r) >= 100) + ". "
             "FM-43 (other water users near the boat) is a severity-9 "
             "hazard with no sensor to detect it; detection relies on the "
             "lookout procedure (OP-10), and it is an accepted residual "
             "risk (section 6). FM-02 (GNSS glitch near the fence) stays "
             "above the threshold until SC-20 runs in the simulator; "
             "Issue C wrongly listed FM-43 as the only such row. Highest "
             "RPNs now: " +
             ", ".join(f"{r[0]} {F.rpn_after(r)}" for r in
                       sorted(F.ROWS, key=F.rpn_after, reverse=True)[:6]) +
             "."),
           H2("4.3 What the simulator changed (Issue D)"),
           *bullets([
               "<b>The worst failure mode was a specification error.</b> "
               "FM-52: the ICD's astern-burst command (a negative velocity "
               "target) makes Rover turn round and drive forwards into the "
               "weed. RPN 420 before the fix, the highest in this FMEA, and "
               "no planned test before simulation would have caught it.",
               "<b>Supply brown-out (FM-08) was under-rated.</b> The Key "
               "Component List showed the baseline flight controller's 9 V "
               "minimum is crossed by pack sag near empty (CR-04).",
               "<b>Three configuration or integration faults</b> (FM-51, "
               "FM-53) were found and fixed the first time the parts ran "
               "together.",
               "<b>Two new, accepted behaviours</b> (FM-49 gale "
               "misdiagnosis, FM-50 dead motor looks like weed) end safely "
               "in HOLD with an alarm.",
               "<b>Detection improved</b> where a scenario now passes "
               "(FM-05, FM-14, FM-17). FM-16 is unchanged: the helm's crash "
               "check is noise-sensitive, and B7 backs it up at 10 s.",
           ]),
           PageBreak(),
           H1("5. Actions"),
           table([["ID", "Action", "Owner", "Failure modes", "Status (Issue "
                   "D)", "Carried by"]] +
                 [[f"<b>{a[0]}</b>", a[1], a[2], ", ".join(a[4]),
                   F.STATUS[a[0]][0], ", ".join(F.STATUS[a[0]][1]) or "-"]
                  for a in F.ACTIONS], [14, 110, 20, 30, 45, 38]),
           P("A-12 is unused: it was merged into A-13 during drafting. "
             "Actions going into 'SSS-x Issue B' are carried into those "
             "specification issues next.", "small"),
           KeepTogether([H1("6. Residual risks accepted for Mk1"),
                         table([["Ref", "Residual risk and rationale"]] +
                               [list(x) for x in F.RESIDUAL], [26, 231])]),
           PageBreak(),
           H1("7. Test coverage of severe failure modes")]
    cov = [["FM", "S", "Failure mode", "Tests (kind)"]]
    for r in sorted(hi, key=lambda r: -r[5]):
        cov.append([r[0], str(r[5]), r[3],
                    ", ".join(f"{t} ({tests[t][1]})" for t in r[11])])
    st.append(table(cov, [16, 8, 110, 123]))

    doc = Doc(OUT, DOC_ID, "Design FMEA", ISSUE, pagesize=landscape(A4))
    doc.multiBuild(st)
    print("wrote", OUT, f"({n} rows, {len(F.ACTIONS)} actions)")


if __name__ == "__main__":
    build()
