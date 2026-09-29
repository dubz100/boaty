"""Build BOATY-KCL-001, the Key Component List.

Run:  python3 docs/kcl/src/build_kcl.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
sys.path.insert(0, str(DOCS / "common"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

import kcl_data as K  # noqa: E402
from pdfdoc import (BLUE, BLUE_T, GREEN_T, ORANGE, ORANGE_T, H1, H2,  # noqa
                    KeepTogether, P, PageBreak, Spacer, bullets, callout,
                    colors, control_and_contents, cover, fig, mm, table, Doc)

OUT = HERE.parent / "Boaty_Key_Component_List.pdf"
FIGDIR = HERE.parent / "figures"
FIGDIR.mkdir(exist_ok=True)
DOC_ID = "BOATY-KCL-001"
ISSUE = "Issue B (for review)"
DATE = "29 September 2026"
PREV = "28 September 2026"
plt.rcParams["font.family"] = "DejaVu Sans"

from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402

pdfmetrics.registerFont(TTFont("DVM", "/usr/share/fonts/truetype/dejavu/"
                               "DejaVuSansMono.ttf"))

SRC_TINT = {"AP": GREEN_T, "FW": GREEN_T, "WEB": BLUE_T, "KN": BLUE_T,
            "EST": ORANGE_T, "TEST": ORANGE_T}


def sag_fig():
    fig_, ax = plt.subplots(figsize=(8.2, 3.9))
    i = [x / 10 for x in range(0, 171)]
    for vrest, lab, c in [(K.V_CRT, f"At critical failsafe ({K.V_CRT} V "
                           "resting)", "#0b0b0b"),
                          (10.8, "Nominal (10.8 V resting)", "#9a998f")]:
        ax.plot(i, [vrest - x * K.R_PACK for x in i], color=c, lw=2, label=lab)
    cols = ["#e34948", "#1baf7a", "#2a78d6", "#eda100"]
    for (name, v, _), c in zip(K.SUPPLY_MIN, cols):
        ax.axhline(v, color=c, lw=1.1, ls="--")
        below = v == 7.0
        ax.text(1.3, v + (-0.06 if below else 0.06), f"{name}: {v} V",
                ha="left", va="top" if below else "bottom", fontsize=7.5,
                color=c)
    for lab, cur in K.LOADS:
        ax.axvline(cur, color="#c9c8c0", lw=0.8)
        ax.text(cur + 0.15, 11.15, lab, rotation=90, fontsize=7,
                color="#52514e", va="top")
    ia = K.i_allow(max(v for _, v, _ in K.SUPPLY_MIN[1:]))
    ax.axvspan(ia, 17, color="#fdf0ea", zorder=0)
    ax.text(ia + 0.2, 5.8, f"Held off by BATT_WATT_MAX = {K.watt_max()} W",
            fontsize=7.5, color="#eb6834")
    ax.set_xlim(0, 17)
    ax.set_ylim(5.6, 11.2)
    ax.set_xlabel("Total battery current (A)", color="#52514e")
    ax.set_ylabel("Supply rail voltage (V)", color="#52514e")
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.legend(loc="lower left", fontsize=7.5, frameon=False)
    fig_.savefig(FIGDIR / "sag.png", dpi=220, bbox_inches="tight",
                 facecolor="white")
    plt.close(fig_)


def power_path_fig():
    fig_, ax = plt.subplots(figsize=(8.6, 3.4))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 8)
    ax.axis("off")

    def box(x, y, w, h, t, c="#f4f3ee", e="#52514e", fs=7.6, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.02,rounding_size=0.15",
                                    facecolor=c, edgecolor=e, lw=1))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontsize=fs, fontweight="bold" if bold else "normal")

    def arrow(x1, y1, x2, y2, c="#0b0b0b", ls="-"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=1.2,
                                    linestyle=ls, shrinkA=0, shrinkB=0))

    box(0.2, 3.3, 2.2, 1.6, "3S pack\n+ BMS\nKC-05/06")
    box(3.0, 3.6, 1.6, 1.0, "Fuse\n20 A")
    box(5.1, 3.6, 1.8, 1.0, "Main\nswitch")
    box(7.4, 3.2, 2.4, 1.8, "PDB + FC\nKC-01\nV/I sense", c="#e3f5ec",
        bold=False)
    box(10.6, 3.3, 2.8, 1.6, "High-side\nP-MOSFET\nKC-07", c="#fdf0ea")
    box(10.6, 6.2, 2.8, 1.0, "Reed switch\n(magnet key)")
    box(14.3, 5.0, 2.3, 1.2, "ESC L\nKC-03")
    box(14.3, 2.0, 2.3, 1.2, "ESC R\nKC-03")
    box(17.4, 5.0, 2.3, 1.2, "Motor L\nKC-04")
    box(17.4, 2.0, 2.3, 1.2, "Motor R\nKC-04")
    box(7.4, 0.3, 2.4, 1.3, "5 V buck\nKC-09")
    box(10.6, 0.3, 2.8, 1.3, "Pi Zero 2W\nKC-10")
    arrow(2.4, 4.1, 3.0, 4.1)
    arrow(4.6, 4.1, 5.1, 4.1)
    arrow(6.9, 4.1, 7.4, 4.1)
    arrow(9.8, 4.1, 10.6, 4.1)
    arrow(13.4, 4.1, 14.3, 5.6)
    arrow(13.4, 4.1, 14.3, 2.6)
    arrow(16.6, 5.6, 17.4, 5.6)
    arrow(16.6, 2.6, 17.4, 2.6)
    arrow(12.0, 6.2, 12.0, 4.9, c="#eb6834")
    arrow(8.6, 3.2, 8.6, 1.6)
    arrow(9.8, 0.95, 10.6, 0.95)
    # sense and signal lines
    ax.plot([13.0, 13.0, 9.3], [3.3, 2.6, 2.6], color="#2a78d6", lw=1,
            ls="--")
    ax.annotate("", xy=(9.3, 3.2), xytext=(9.3, 2.6),
                arrowprops=dict(arrowstyle="-|>", color="#2a78d6", lw=1))
    ax.text(9.5, 2.2, "rail sense ÷11 → ADC 15", fontsize=7,
            color="#2a78d6")
    ax.plot([9.8, 14.0, 14.0], [4.8, 4.8, 6.6], color="#1baf7a", lw=1,
            ls=":")
    ax.text(14.1, 6.6, "DShot out 1 / 4", fontsize=7, color="#1baf7a",
            va="bottom")
    ax.text(13.7, 0.95, "MAVLink: GPIO14/15 ↔ FC SERIAL1", fontsize=7,
            color="#52514e", va="center")
    ax.text(0.2, 7.5, "Motor rail is live only with the key in; the FC and "
            "mission computer stay powered with it out.", fontsize=7.6,
            color="#52514e")
    fig_.savefig(FIGDIR / "power_path.png", dpi=220, bbox_inches="tight",
                 facecolor="white")
    plt.close(fig_)


def src_tag(code):
    return code


def build():
    res = K.check()
    sag_fig()
    power_path_fig()
    total = res["total"]

    st = cover("Key Component List",
               "The parts whose numbers feed the software, the parameters "
               "and the simulator, with where each number came from",
               [["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                ["Status", "For review. One owner decision (CR-04) before "
                 "the ADD, ICD and SSS pick it up."],
                ["Basis", "ADD Issue E, ICD Issue D, SSS Issues A-C, FMEA "
                 "Issue C"],
                ["Content", f"{len(K.KC)} key components, "
                 f"{len(K.FINDINGS)} findings, {len(K.DATASHEETS)} "
                 "datasheet entries"]])
    st += control_and_contents(
        [["A", PREV, "First issue.", "Claude (drafted)"],
         ["B", DATE, "CR-04 accepted: SpeedyBee F405 WING APP is the "
          "baseline. Section 10 now records where each change went.",
          "Claude, owner decision"]],
        "Review guidance: check the proposed parts against what you can "
        "actually buy, and the cost estimates against real prices. Every "
        "value is tagged with its source; orange-tagged values are guesses "
        "until measured.")

    # 1
    st += [H1("1. Purpose and how to read this list"),
           P("The simulator and the software need exact numbers: which UART "
             "the mission computer is on, which ADC pin senses the motor "
             "rail, how fast an ESC stops when its signal disappears, how "
             "much thrust a pod gives. Until now the specifications said "
             "'F405 class' and 'M10 GNSS'. This list turns those into "
             "specific parts and records the numbers that matter from "
             "each."),
           P("A <b>key component</b> is one whose characteristics feed the "
             "software, the ArduPilot parameters, the simulator's physics "
             "or an interface definition. Foam, glands and fasteners are "
             "not key components and stay in the ADD's BOM."),
           H2("1.1 Where the numbers come from"),
           P("Each value carries a source tag. The helm's numbers come "
             "mostly from ArduPilot's own board definition: the firmware we "
             "flash is compiled from those files, so they're more "
             "authoritative than a vendor PDF."),
           table([["Tag", "Meaning", "Trust"]] +
                 [[k, f"<b>{v[0]}.</b> {v[1]}",
                   {"AP": "High", "FW": "High", "WEB": "Medium",
                    "KN": "Medium", "EST": "Low", "TEST": "Pending"}[k]]
                  for k, v in K.SOURCES.items()], [14, 136, 20],
                 style_extra=[("BACKGROUND", (0, i), (0, i), SRC_TINT[k])
                              for i, k in enumerate(K.SOURCES, 1)]),
           P("Vendor sites (and ardupilot.org) were not reachable from the "
             "environment this list was written in; GitHub was. So "
             "ArduPilot and AM32 sources are archived in "
             "<font face='DVM'>docs/kcl/sources/</font>, and "
             "vendor datasheets are listed in section 9 with a script to "
             "fetch them.", "small"),
           PageBreak()]

    # 2 findings
    sev_c = {"Decision": ORANGE_T, "Change": BLUE_T, "Note": GREEN_T}
    rows = [["ID", "Finding", "Type", "Goes to"]]
    style = []
    for i, f in enumerate(K.FINDINGS, 1):
        rows.append([f"<b>{f[0]}</b>", f"<b>{f[1]}.</b> {f[2]}", f[3], f[4]])
        style.append(("BACKGROUND", (2, i), (2, i), sev_c[f[3]]))
    st += [H1("2. Findings"),
           callout("<b>CR-04 accepted (Issue B).</b> The baseline flight "
                   "controller (Matek F405-TE) needed 9 V, and our 3S Li-ion "
                   "pack sags below that under load near empty. The boat "
                   "could have lost its autopilot during the very "
                   "return-home that the low-battery failsafe starts. The "
                   "SpeedyBee F405 WING APP runs from 7 V, keeps microSD "
                   "logging, costs about £17 less, and is now the baseline "
                   "(ADD DD-19). Section 5 has the numbers.", BLUE, BLUE_T),
           Spacer(1, 3 * mm),
           table(rows, [13, 115, 16, 26], style_extra=style),
           PageBreak()]

    # 3 summary list
    rows = [["ID", "Component", "Qty", "Proposed part", "Status"]]
    for k in K.KC:
        rows.append([f"<b>{k['id']}</b>", f"{k['name']} "
                     f"<font color='#9a998f'>({k['ss']})</font>",
                     str(k["qty"]), k["part"], k["status"]])
    st += [H1("3. The list"),
           P("KC-08 and KC-13 are not used: the main switch and the moisture "
             "traces turned out not to feed any software value beyond what "
             "the specifications already say.", "small"),
           table(rows, [14, 42, 9, 80, 25]),
           Spacer(1, 4 * mm),
           fig(FIGDIR / "power_path.png", 170, "Figure 1. Boat power path "
               "with the proposed parts. The arming key switches the "
               "positive side of the motor rail (KF-03), and the helm "
               "senses that rail on its airspeed ADC pad."),
           PageBreak()]

    # 4 cost
    rows = [["Group", "Item", "£ (est.)", "KC", "Change from ADD Issue E"]]
    for b in K.NEW_BOM:
        rows.append([b[0], b[1], str(b[2]), ", ".join(b[3]) or "-", b[4]])
    rows.append(["", "<b>Total (excluding conditional)</b>",
                 f"<b>{total}</b>", "", f"ADD Issue F baseline "
                 f"£{res['old']} (Issue E: £182)"])
    for c in K.CONDITIONAL:
        rows.append([c[0], c[1], str(c[2]), "-", "Unchanged"])
    st += [H1("4. Cost reconciliation"),
           P(f"With the proposed parts the estimate is <b>£{total}</b>, "
             f"against the £{K.CAP} cap and £{K.TARGET} target (CON-001). "
             "Cheaper flight controller, realistic ESC price and a second "
             "microSD card roughly cancel out. The conditional pole kit "
             "would still breach the cap."),
           table(rows, [14, 72, 16, 22, 46]),
           P("Prices are estimates from search results and earlier work; UK "
             "retail sites couldn't be opened from here. Confirm at order "
             "time. If the ESCs come in dear, BLHeli_S ESCs with Bluejay "
             "firmware save about £8.", "small"),
           PageBreak()]

    # 5 sag
    rows = [["Supply", "Minimum input", "Source", "Max current at "
             f"{K.V_CRT} V resting (+{K.MARGIN} V margin)"]]
    for n, v, s in K.SUPPLY_MIN:
        rows.append([n, f"{v} V", s, f"{K.i_allow(v):.1f} A"])
    st += [H1("5. Supply sag analysis"),
           P(f"Pack resistance at the acceptance limits: 3 × "
             f"{K.R_CELL*1000:.0f} mΩ cells + {K.R_BMS*1000:.0f} mΩ BMS + "
             f"{K.R_HARNESS*1000:.0f} mΩ fuse, switch and wiring = "
             f"<b>{K.R_PACK:.2f} Ω</b>. The critical battery failsafe "
             f"(BATT_CRT_VOLT) fires at {K.V_CRT} V resting, and the boat "
             "must then drive home on what's left."),
           fig(FIGDIR / "sag.png", 165, "Figure 2. Rail voltage against "
               "battery current. The F405-TE (red) browns out above about "
               "1.4 A near empty; cruise alone is about 1 A."),
           table(rows, [52, 26, 16, 76]),
           Spacer(1, 3 * mm),
           P(f"<b>Power limit.</b> BATT_WATT_MAX = {K.watt_max()} W keeps "
             "the rail above the highest of the remaining minimums (the "
             "ESC's 7.2 V) at the critical voltage. By momentum theory "
             "(T ∝ P<super>2/3</super>) that still leaves about "
             f"{K.thrust_at_power_limit():.1f} N, against 1.1 N needed to "
             "make headway in the ENV-002 wind. On a full pack the limit "
             "rarely acts. Whether it is enough gets tested on L2 with a "
             "programmable load (PWR-D12)."),
           PageBreak()]

    # 6 component data
    st.append(H1("6. Component data"))
    for k in K.KC:
        head = table([["Part", k["part"]], ["Alternatives", k["alts"]],
                      ["Why it's key", k["why"]],
                      ["Traces", ", ".join(k["refs"])]], [30, 140],
                     header=False,
                     style_extra=[("BACKGROUND", (0, 0), (0, -1), "#f6f5f1")])
        rows = [["Parameter", "Value", "Src", "Used by"]]
        style = []
        for i, v in enumerate(k["values"], 1):
            rows.append([v[0], v[1], v[2], v[3]])
            style.append(("BACKGROUND", (2, i), (2, i), SRC_TINT[v[2]]))
        st += [KeepTogether([H2(f"{k['id']} {k['name']}"), head,
                             Spacer(1, 2 * mm)]),
               table(rows, [36, 92, 12, 30], style_extra=style),
               Spacer(1, 3 * mm)]
    st.append(PageBreak())

    # 7 helm allocation + params
    alloc = [["Function", "FC resource", "Notes"],
             ["Mission computer (IF-04)", "SERIAL1 = USART1 (DMA)",
              "Pads R1/T1; 115200 8N1"],
             ["GNSS (IF-22)", "SERIAL3 = USART3", "Board default GPS port"],
             ["Compass (IF-22)", "I2C1 (PB8/PB9)", "QMC5883L at 0x0D"],
             ["Left motor (IF-05)", "Output 1 (TIM4, BIDIR)", "DShot300, 3D"],
             ["Right motor (IF-05)", "Output 4 (TIM3, BIDIR)",
              "DShot300, 3D. Output 2/3 unused"],
             ["Beacon (IF-09)", "Output 12 (LED pad, TIM1)", "WS2812B"],
             ["Battery V/I (IF-07)", "ADC 10 / 11 via PDB", "Calibrate"],
             ["Motor-rail sense (IF-06)", "ADC 15 (AIRSPD pad)",
              "10 kΩ / 1 kΩ divider"],
             ["Unused", "SERIAL2, 4, 5; SERIAL6 disabled", "Wireless board "
              "not fitted"]]
    rows = [["Parameter", "Proposed value", "Was", "Src", "Refs"]]
    style = []
    for i, p in enumerate(K.PARAM_DELTA, 1):
        rows.append([p[0], p[1].format(watt=K.watt_max()), p[2], p[3],
                     ", ".join(p[4])])
        style.append(("BACKGROUND", (3, i), (3, i), SRC_TINT[p[3]]))
    st += [H1("7. Helm allocation and parameter changes"),
           P("From the SpeedyBeeF405WING board definition (DS-01). These "
             "close TBC-02 and most of TBC-05 once CR-04 is accepted."),
           table(alloc, [46, 60, 64]),
           Spacer(1, 4 * mm),
           H2("7.1 Parameter baseline changes for SSS-HLM Issue D"),
           table(rows, [52, 56, 26, 10, 26], style_extra=style),
           PageBreak()]

    # 8 sim model
    rows = [["Symbol", "Meaning", "Value", "Units", "Source", "Replaced by"]]
    for s in K.SIM_MODEL:
        rows.append(list(s))
    st += [H1("8. Simulator model parameters"),
           P("ArduPilot's built-in simulated motorboat gives 50 N at full "
             "throttle, for a much bigger boat (KF-07). The simulator will "
             "run the real ArduPilot firmware against a small Python boat "
             "model through SITL's JSON interface (DS-18). These are its "
             "starting parameters. Most are estimates, and the last column "
             "says which measurement replaces each one; the model is only "
             "as good as those measurements."),
           table(rows, [16, 50, 30, 16, 28, 30]),
           P("A 3-DOF model is enough: surge, sway and yaw, with thrust from "
             "two pods, quadratic drag, windage, and the battery feeding "
             "back into available thrust. Waves, heel and pitch are left "
             "out: the catamaran is stiff (SSS-HUL section 6), and none of "
             "the SC tests depend on them.", "small"),
           PageBreak()]

    # 9 datasheets
    rows = [["ID", "KC", "Document", "Status"]]
    style = []
    stc = {"Archived": GREEN_T, "To fetch": BLUE_T, "To locate": ORANGE_T,
           "Measure": ORANGE_T}
    for i, d in enumerate(K.DATASHEETS, 1):
        doc_ = d[2] + (f"<br/><font size='6.5' color='#52514e'>{d[3]}</font>"
                       if d[3] else "")
        rows.append([d[0], d[1], doc_, d[4]])
        style.append(("BACKGROUND", (3, i), (3, i), stc[d[4]]))
    n_arch = sum(1 for d in K.DATASHEETS if d[4] == "Archived")
    n_fetch = sum(1 for d in K.DATASHEETS if d[4] == "To fetch")
    st += [H1("9. Datasheet register"),
           P(f"{n_arch} archived, {n_fetch} ready to fetch, the rest to "
             "locate or to measure. <font face='DVM'>"
             "python3 docs/kcl/src/fetch_datasheets.py</font> downloads the "
             "'To fetch' entries into <font face='DVM'>"
             "docs/kcl/datasheets/</font> and records their SHA-256, so a "
             "datasheet can't silently change under us. Run it anywhere "
             "with ordinary internet access."),
           table(rows, [13, 13, 124, 20], style_extra=style),
           P("'Measure' entries are deliberate: for salvaged cells, a "
             "generic BMS and a drone motor in water, no datasheet would be "
             "trustworthy. The bench result becomes the datasheet.",
             "small"),
           PageBreak()]

    # 10 changes and open items
    rows = [["Document", "Where it went (Issue B)", "Findings"]]
    for c in K.CHANGES:
        rows.append([c[0], c[1], ", ".join(c[2])])
    st += [H1("10. Where the changes went"),
           table(rows, [30, 118, 22]),
           H2("10.1 Measurements that matter most to the simulator"),
           *bullets([
               "<b>Thrust, current and RPM against throttle</b> for one pod "
               "in water (DS-09). A luggage scale and a bucket will do. "
               "This single curve sets the model's thrust, power and "
               "endurance.",
               "<b>Cell capacity and resistance</b> from acceptance "
               "testing (DS-10). These set R_pack and the sag margin.",
               "<b>ESC signal-loss stop time</b> on the bench (V-09). The "
               "AM32 source says 0.5 s; confirm on the actual ESC.",
               "<b>Coast-down and turn tests</b> in the pool to replace the "
               "drag and inertia estimates.",
           ]),
           H1("Appendix A. Archived sources"),
           table([["Source", "Repository and commit"],
                  ["ArduPilot firmware (board definitions, SITL)",
                   f"ArduPilot/ardupilot @ {K.AP_COMMIT[:12]}"],
                  ["ArduPilot wiki (F405-TE family page)",
                   f"ArduPilot/ardupilot_wiki @ {K.WIKI_COMMIT[:12]}"],
                  ["AM32 ESC firmware (signal-loss excerpt)",
                   f"am32-firmware/AM32 @ {K.AM32_COMMIT[:12]}"]],
                 [70, 100]),
           P("ArduPilot and AM32 are GPLv3; the archived files are unmodified "
             "copies or excerpts, kept for reference.", "small")]

    doc = Doc(OUT, DOC_ID, "Key Component List", ISSUE)
    doc.multiBuild(st)
    print("wrote", OUT, res)


if __name__ == "__main__":
    build()
