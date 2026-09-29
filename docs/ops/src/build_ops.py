"""Build the Boaty Operations Manual (BOATY-OPS-001).

Run:  python3 docs/ops/src/build_ops.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
sys.path.insert(0, str(DOCS / "common"))
sys.path.insert(0, str(DOCS / "fmea" / "src"))
sys.path.insert(0, str(DOCS / "sss" / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

import fmea_data as F  # noqa: E402
import ops_data as O  # noqa: E402
import sss_data as SD  # noqa: E402
from pdfdoc import (BLUE, BLUE_T, GREEN_T, ORANGE, ORANGE_T, H1, H2,  # noqa
                    KeepTogether, P, PageBreak, Paragraph, S, Spacer,
                    bullets, callout, colors, control_and_contents, cover, fig,
                    mm, table, Doc)

OUT = HERE.parent / "Boaty_Operations_Manual.pdf"
FIGDIR = HERE.parent / "figures"
FIGDIR.mkdir(exist_ok=True)
DOC_ID = "BOATY-OPS-001"
ISSUE = "Issue C (for review)"
DATE = "29 September 2026"
PREV = "28 September 2026"
BOX = "☐"


def valid_refs():
    srs = {r["id"] for r in SD.SRS.all_reqs()}
    derived = {d["id"] for ss in SD.SUBSYSTEMS.values()
               for d in SD.all_derived(ss)}
    ifs = {i[0] for i in SD.A.INTERFACES}
    fm = {r[0] for r in F.ROWS} | {a[0] for a in F.ACTIONS}
    return srs | derived | ifs | fm


def crew_card_fig():
    fig_, ax = plt.subplots(figsize=(7.0, 4.2))
    cols = [("#2a78d6", "TALK"), ("#1baf7a", "GO"), ("#eda100", "COME HOME"),
            ("#e34948", "STOP")]
    for i, (c, t) in enumerate(cols):
        x = 1.2 + i * 2.4
        ax.add_patch(Circle((x, 2.6), 0.95, facecolor=c, edgecolor="#0b0b0b",
                            lw=1.5))
        if t == "TALK":
            ax.add_patch(Rectangle((x - 0.2, 2.55), 0.4, 0.6, color="white"))
            ax.add_patch(Rectangle((x - 0.05, 2.1), 0.1, 0.45, color="white"))
        elif t == "GO":
            ax.add_patch(Polygon([(x - 0.3, 2.15), (x - 0.3, 3.05),
                                  (x + 0.45, 2.6)], color="white"))
        elif t == "COME HOME":
            ax.add_patch(Polygon([(x - 0.5, 2.6), (x, 3.1), (x + 0.5, 2.6)],
                                 color="white"))
            ax.add_patch(Rectangle((x - 0.32, 2.05), 0.64, 0.55,
                                   color="white"))
        else:
            ax.add_patch(Rectangle((x - 0.35, 2.25), 0.7, 0.7, color="white"))
        ax.text(x, 1.3, t, ha="center", fontsize=14, fontweight="bold")
    ax.text(5.0, 0.35, "Stay behind the line  ·  Only grown-ups touch the "
            "boat  ·  Never go in the water", ha="center", fontsize=10,
            color="#52514e")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.8)
    ax.set_aspect("equal")
    ax.axis("off")
    fig_.savefig(FIGDIR / "crew_card.png", dpi=220, bbox_inches="tight",
                 facecolor="white")
    plt.close(fig_)


def build():
    O.check()
    ok = valid_refs()
    bad = sorted(r for r in O.all_refs() if r not in ok)
    assert not bad, f"unknown references: {bad}"
    crew_card_fig()

    st = cover("Operations Manual", "How to prepare, run and recover a "
               "Boaty session safely: procedures, checklist, contingency "
               "cards and the crew card",
               [["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                ["Status", "For review by the project owner (who is also "
                 "its main user)"],
                ["Basis", "SRS Issue F (OPS-001 to OPS-012), ConOps/ConUse, "
                 "FMEA Issue D actions A-05, A-09, A-11, A-17, A-19"],
                ["Content", f"{len(O.PROCEDURES)} procedures, "
                 f"{len(O.CHECKLIST)}-item checklist, {len(O.CONTINGENCY)} "
                 "contingency cards"]])
    st += control_and_contents(
        [["A", PREV, "First issue.", "Claude (drafted)"],
         ["B", DATE, "Simulator findings: K-03 (a dead motor looks like "
          "weed), K-05 (the boat stops itself 30 s or 10 m outside the "
          "fence), K-11 (a heading alarm in strong wind may be wind drift).",
          "Claude, from simulator slice 2"],
         ["C", DATE, "Mission Control findings: CL-13 (arm at the jetty: "
          "home is taken where the boat is armed) and CL-18 (close any "
          "other ground station) added.", "Claude, from simulator slice 3"]],
        "Review guidance: read it as if it's your first lake session. "
        "Anything you wouldn't actually do, or that's missing, is a finding. "
        "Sections 7 and 8 are meant to be printed and laminated.")

    # 1 intro
    st += [H1("1. About this manual"),
           P("This is the manual for using Boaty, from the day before a "
             "session to putting the battery away. It turns the "
             "operations requirements (OPS-001 to OPS-012) and the "
             "procedural FMEA actions into things to do, in order. It "
             "assumes the boat and software meet their specifications. "
             "Where software helps (the checklist, alarms, spoken "
             "messages), the procedure says so."),
           *bullets([
               "<b>Section 5, the pre-launch checklist,</b> is the same "
               "list Mission Control shows before it allows arming "
               "(MCN-D13). Edit it here, and both change.",
               "<b>References</b> in brackets (e.g. OPS-004, A-17) point to "
               "the requirement or FMEA action each step satisfies. That "
               "tells you why a step exists before you're tempted to skip "
               "it.",
               "<b>Sections 7 and 8</b> (crew card, quick reference) are "
               "one page each, for printing.",
           ]),
           H1("2. Roles and golden rules"),
           table([["Role", "Responsibilities"]] + [list(r) for r in O.ROLES],
                 [34, 136]),
           Spacer(1, 4 * mm)]
    for i, (rule, why, refs) in enumerate(O.GOLDEN_RULES, 1):
        st += [callout(f"<b>{i}. {rule}</b> {why} "
                       f"<font color='#52514e' size='7'>({', '.join(refs)})"
                       "</font>", ORANGE if i <= 3 else BLUE,
                       ORANGE_T if i <= 3 else BLUE_T),
               Spacer(1, 2 * mm)]
    st.append(PageBreak())

    # 3 kit
    st += [H1("3. Kit lists")]
    rows = [["", "Group", "Item"]]
    for g, items in O.KIT:
        for it in items:
            rows.append([BOX, g, it])
    st += [table(rows, [8, 34, 128]), PageBreak()]

    # 4 procedures
    st.append(H1("4. Procedures"))
    for p in O.PROCEDURES:
        head = table([["When", p["when"], "Who", p["who"]]], [16, 70, 14, 70],
                     header=False,
                     style_extra=[("BACKGROUND", (0, 0), (0, 0), BLUE_T),
                                  ("BACKGROUND", (2, 0), (2, 0), BLUE_T)])
        block = [H2(f"{p['id']} {p['title']}"), head, Spacer(1, 1.5 * mm),
                 P(f"<i>{p['purpose']}</i>", "small")]
        if p["id"] == "OP-13":
            block.append(table([["Interval", "Tasks", "Refs"]] +
                               [[m[0], m[1], ", ".join(m[2])]
                                for m in O.MAINTENANCE], [34, 106, 30]))
        else:
            rows = [["#", "Step", "Why"]]
            for n, (txt, refs) in enumerate(p["steps"], 1):
                rows.append([str(n), txt, ", ".join(refs)])
            block.append(table(rows, [8, 132, 30]))
        if p["notes"]:
            block.append(P(p["notes"], "small"))
        st += [KeepTogether(block[:4]), *block[4:], Spacer(1, 3 * mm)]
    st.append(PageBreak())

    # 5 checklist
    rows = [["", "ID", "Group", "Check", "How", "Why"]]
    for c in O.CHECKLIST:
        rows.append([BOX, c[0], c[1], c[2], c[3], ", ".join(c[4])])
    st += [H1("5. Pre-launch checklist"),
           P("Every item must be ticked before Mission Control allows "
             "arming (PRE-006). 'Automatic' items are ticked by the system "
             "and can't be overridden. Record of who signed off and when is "
             "kept in the session log (MC-010)."),
           table(rows, [7, 13, 24, 76, 26, 24]),
           PageBreak()]

    # 6 contingencies
    st += [H1("6. Contingency cards"),
           P("What to do when something goes wrong. The first move is "
             "almost always the same: <b>people first, then STOP or COME "
             "HOME, then think.</b>")]
    for k in O.CONTINGENCY:
        t = table([[f"<b>{k[0]} {k[1]}</b>", ""],
                   ["You'll notice", k[2]], ["Operator", k[3]],
                   ["Crew", k[4]], ["Refs", ", ".join(k[5])]],
                  [30, 140], header=False,
                  style_extra=[("SPAN", (0, 0), (1, 0)),
                               ("BACKGROUND", (0, 0), (1, 0),
                                ORANGE_T if k[0] in ("K-06", "K-07", "K-12")
                                else TINT_OR()),
                               ("BACKGROUND", (0, 1), (0, -1),
                                colors.HexColor("#f6f5f1"))])
        st += [KeepTogether([t]), Spacer(1, 3 * mm)]
    st.append(PageBreak())

    # 7 crew card
    st += [H1("7. Crew card (print me)"),
           fig(FIGDIR / "crew_card.png", 170),
           table([["Button", "Looks like", "What it does"]] +
                 [list(c) for c in O.CREW_CARD], [34, 40, 96]),
           P("Read it together before every session (OP-07). The crew "
             "can't break anything by pressing a button: GO only works when "
             "the grown-up has made it safe.", "small"),
           PageBreak()]

    # 8 quick reference
    seq = ["OP-04 Day before: inspect and charge battery, pack kits",
           "OP-06 Bank: notices, other users, wind → launch point",
           "Checklist (section 5) → OP-07 crew briefing",
           "OP-08 TALK → check plan → approve with PIN",
           "OP-09 Boat on water → step back → KEY IN → arm → GO",
           "OP-10 Lookout the whole time → STOP if in doubt",
           "OP-11 Home → disarm → KEY OUT → lift by handle",
           "OP-12 Sync photos, rinse, wash hands, storage-charge"]
    st += [H1("8. Quick reference (print me)"),
           table([["Golden rules"]] + [[f"{i}. {r[0]}"] for i, r in
                                       enumerate(O.GOLDEN_RULES, 1)], [170]),
           Spacer(1, 3 * mm),
           table([["A session in eight lines"]] + [[x] for x in seq], [170]),
           Spacer(1, 3 * mm),
           table([["If…", "Do"]] +
                 [[k[1], k[3].split(". ")[0] + "."] for k in O.CONTINGENCY],
                 [50, 120]),
           PageBreak()]

    # appendix
    need = [f"OPS-{i:03d}" for i in range(1, 13)]
    reqs = {r["id"]: r for r in SD.SRS.all_reqs()}
    rows = [["Requirement", "Text (abridged)", "Met in"]]
    for rid in need:
        t = reqs[rid]["text"]
        rows.append([rid, t if len(t) < 110 else t[:108] + "…",
                     ", ".join(O.where(rid))])
    acts = {a[0]: a for a in F.ACTIONS}
    arows = [["FMEA action", "Action", "Met in"]]
    for aid in ["A-05", "A-09", "A-11", "A-17", "A-19"]:
        arows.append([aid, acts[aid][1], ", ".join(O.where(aid))])
    st += [H1("Appendix A. Traceability"),
           table(rows, [22, 108, 40]), Spacer(1, 4 * mm),
           table(arows, [22, 108, 40])]

    doc = Doc(OUT, DOC_ID, "Operations Manual", ISSUE)
    doc.multiBuild(st)
    print("wrote", OUT)


def TINT_OR():
    return colors.HexColor("#f4f3ee")


if __name__ == "__main__":
    build()
