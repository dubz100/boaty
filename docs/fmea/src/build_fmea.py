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
ISSUE = "Issue A (for review)"
DATE = "28 September 2026"
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
                         ["Basis", "ADD Issue C, ICD Issue B, SSS Issue A/B"],
                         ["Content", f"{n} failure modes, {len(F.ACTIONS)} "
                          f"actions, {len(SD.TESTS)} catalogued tests"]])
    st += control_and_contents(
        [["A", DATE, "First issue: design FMEA at architecture level.",
          "Claude (drafted)"]],
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
             "Tests", "Actions"]]
    style = []
    for i, r in enumerate(F.ROWS, start=1):
        rows.append([f"<b>{r[0]}</b><br/>{r[1]}", r[2], r[3], r[4],
                     f"<b>{r[5]}</b>", r[6], str(r[7]),
                     f"{r[8]} / {r[9]}", str(r[10]), f"<b>{F.rpn(r)}</b>",
                     ", ".join(r[11]), ", ".join(r[12]) or "-"])
        if r[5] >= 9:
            style.append(("BACKGROUND", (4, i), (4, i),
                          colors.HexColor("#cfe1f6")))
        if F.rpn(r) >= 100:
            style.append(("BACKGROUND", (9, i), (9, i), ORANGE_T))
    st += [H1("3. FMEA worksheet"),
           P("Blue S cell = severity ≥ 9. Orange RPN cell = at or above "
             "the action threshold. Test IDs are defined in SSS-SIM "
             "Issue B, section 6.", "small"),
           table(rows, [16, 22, 30, 32, 7, 26, 7, 42, 7, 10, 30, 18],
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
           PageBreak(),
           H1("5. Actions"),
           table([["ID", "Action", "Owner", "Goes into", "Failure modes"]] +
                 [[f"<b>{a[0]}</b>", a[1], a[2], a[3], ", ".join(a[4])]
                  for a in F.ACTIONS], [14, 140, 22, 45, 36]),
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
