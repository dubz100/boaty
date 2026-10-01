"""Figures for the executive progress report.

Run:  python3 docs/report/src/figures.py

Inputs: the SITL truth traces and web-UI screenshots written by a traced
run (BOATY_TRACE_DIR, see software/tests/sitl/conftest.py), copied into
docs/report/data; software/results/sitl_results.json; the MDD render.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import (FancyArrowPatch, FancyBboxPatch,  # noqa: E402
                                Polygon, Circle)

HERE = Path(__file__).resolve().parent
REP = HERE.parent
ROOT = REP.parents[1]
OUT = REP / "figures"
DATA = REP / "data"
OUT.mkdir(exist_ok=True)

INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#9a998f"
GRID = "#e4e3dc"
BLUE = "#2a78d6"
BLUE_T = "#e8f1fb"
ORANGE = "#eb6834"
GREEN = "#1e8a55"
GREEN_T = "#e3f5ec"
AQUA = "#1baf7a"
YELLOW = "#eda100"
GREY_T = "#f4f3ee"
WATER = "#eaf3fb"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "text.color": INK, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2})


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 1. The V
DONE, NOW, NEXT = "done", "now", "next"
FILL = {DONE: GREEN_T, NOW: BLUE_T, NEXT: "white"}
EDGE = {DONE: GREEN, NOW: BLUE, NEXT: MUTED}


def vmodel():
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 112)
    ax.set_ylim(-14, 72)
    ax.axis("off")
    W, H = 24, 9.5

    def box(x, y, t, b, s, fc=None, ec=None):
        ax.add_patch(FancyBboxPatch((x, y), W, H,
                                    boxstyle="round,pad=0.2,rounding_size=1",
                                    fc=fc or FILL[s], ec=ec or EDGE[s],
                                    lw=1.5, zorder=3))
        ax.text(x + W / 2, y + H - 1.4, t, ha="center", va="top",
                fontsize=8.4, weight="bold", zorder=4)
        ax.text(x + W / 2, y + 1.1, b, ha="center", va="bottom",
                fontsize=6.8, color=INK2, linespacing=1.2, zorder=4)

    left = [(1, 56, "Needs & concept", "Concept report v1.1\n"
             "7 options scored", DONE),
            (9, 42, "System requirements", "SRS: 184 requirements\n"
             "12 failsafes, 8 stakeholder needs", DONE),
            (17, 28, "Architecture", "ADD + ICD: 22 interfaces\n"
             "FMEA, cost, mass & power budgets", DONE),
            (25, 14, "Subsystem specs", "8 specs, 247 derived reqs\n"
             "key component list", DONE),
            (33, 0, "Detailed design", "MDD: CAD & hydrostatics\n"
             "EDD: schematics & boards", NOW)]
    right = [(87, 56, "Validation", "Pond trial: explore,\n"
              "photograph, come home", NEXT),
             (79, 42, "System verification", "Pool & pond tests\n"
              "against the SRS (VCRM)", NEXT),
             (71, 28, "Integration", "HIL rigs: helm, comms,\n"
              "power on the bench", NEXT),
             (63, 14, "Subsystem test", "Board bring-up,\n"
              "hull float & stability", NEXT)]
    build = (48, -13, "Build", "Print, wire, flash\n(after CDR)", NEXT)
    for b in left + right + [build]:
        box(*b)
    arrow = dict(arrowstyle="-|>", color=MUTED, lw=1.2)
    for a, b in zip(left, left[1:]):
        ax.annotate("", (b[0] + 8, b[1] + H + .5), (a[0] + 8, a[1] - .5),
                    arrowprops=arrow)
    ax.annotate("", (build[0] - .6, build[1] + H / 2),
                (left[-1][0] + 6, left[-1][1] - .5), arrowprops=arrow)
    ax.annotate("", (right[-1][0] + W - 6, right[-1][1] - .5),
                (build[0] + W + .6, build[1] + H / 2), arrowprops=arrow)
    rr = right[::-1]
    for a, b in zip(rr, rr[1:]):
        ax.annotate("", (b[0] + W - 5, b[1] - .5), (a[0] + W - 5,
                                                    a[1] + H + .5),
                    arrowprops=arrow)
    # verification relationships across the V
    for (lx, ly, *_), (rx, ry, *_) in zip(left[:4], right):
        ax.plot([lx + W + .8, rx - .8], [ly + H / 2] * 2, ls=(0, (1, 3)),
                color=MUTED, lw=.8, zorder=0)
    # review gates, on the arrows between phases
    gates = [(13, 53.75, "Concept review", DONE, "right"),
             (37, 11.75, "SDR: GO, baselined", DONE, "right"),
             (43.2, -4.4, "CDR: next", NOW, "left"),
             (94, 39.9, "TRR", NEXT, "right"),
             (102, 53.9, "ORR", NEXT, "right")]
    for x, y, t, s, side in gates:
        c = {DONE: GREEN, NOW: ORANGE, NEXT: MUTED}[s]
        ax.add_patch(Polygon([[x, y + 2.2], [x + 2.2, y], [x, y - 2.2],
                              [x - 2.2, y]], fc=c, ec="white", lw=1,
                             zorder=6))
        dx = 4.6 if t in ("TRR", "ORR") else 3.2
        ax.text(x + (dx if side == "right" else -dx), y, t, va="center",
                ha="left" if side == "right" else "right", fontsize=7.8,
                color=c, weight="bold", zorder=6)
    # the simulator: the right of the V exercised before any hardware
    sx, sy = 44, 33
    box(sx, sy, "Software-in-the-loop", "ArduPilot SITL + boat physics\n"
        "83 scenarios: 80 pass, 3 known gaps", DONE, fc="#fff6e0",
        ec=YELLOW)
    ax.add_patch(FancyArrowPatch((sx - .6, sy + H - 2), (9 + W + .8, 47.5),
                                 connectionstyle="arc3,rad=0.15",
                                 arrowstyle="-|>", mutation_scale=11,
                                 color=YELLOW, lw=1.4, zorder=2))
    ax.add_patch(FancyArrowPatch((sx - .6, sy + 2), (17 + W + .8, 32),
                                 connectionstyle="arc3,rad=-0.1",
                                 arrowstyle="-|>", mutation_scale=11,
                                 color=YELLOW, lw=1.4, zorder=2))
    ax.text(sx + W / 2, sy - 1.5, "verifies requirements and architecture\n"
            "before anything is built", ha="center", va="top", fontsize=7,
            color="#9a6b00", style="italic")
    ax.text(36, 68.5, "define and decompose", color=INK2, fontsize=7.6,
            ha="center", style="italic")
    ax.text(76, 68.5, "integrate and verify", color=INK2, fontsize=7.6,
            ha="center", style="italic")
    hs = [Line2D([], [], marker="s", ls="", ms=9, mfc=FILL[s], mec=EDGE[s],
                 mew=1.5, label=lab) for s, lab in
          [(DONE, "complete"), (NOW, "in progress"), (NEXT, "to do")]]
    hs.append(Line2D([], [], marker="D", ls="", ms=7, mfc=GREEN, mec="white",
                     label="review gate"))
    ax.legend(handles=hs, loc="upper center", ncol=4, frameon=False,
              bbox_to_anchor=(0.5, 1.03), fontsize=7.6)
    save(fig, "vmodel.png")


# ---------------------------------------------------------------------------
# 2. The chosen concept, annotated on the CAD render
def concept_annotated():
    img = plt.imread(ROOT / "docs/mdd/figures/iso.png")
    h, w = img.shape[:2]
    fig, ax = plt.subplots(figsize=(10, 7.4))
    ax.imshow(img, extent=(0, w, h, 0))
    ax.set_xlim(-380, w + 380)
    ax.set_ylim(h + 30, -30)
    ax.axis("off")
    notes = [
        ((575, 45), (-360, 40), "GNSS + compass on the mast",
         "Away from motor fields; fence and\nreturn-home live in the "
         "autopilot"),
        ((470, 180), (-360, 220), "Hi-vis flag & LED beacon",
         "'We cannot lose it': seen\nfrom 100 m (REC)"),
        ((480, 440), (-360, 400), "Recovery hoop",
         "Snag with a cast line if\nall else fails"),
        ((90, 790), (-360, 640), "Clip-on thruster pods",
         "Differential thrust: no rudder,\nturns on the spot; weed guard"),
        ((520, 820), (-160, 925), "Foam-filled printed hulls",
         "Unsinkable even if holed;\nprinted in 190 mm segments"),
        ((680, 470), (w + 30, 590), "Sealed electronics box",
         "Autopilot, Pi Zero mission\ncomputer, battery, magnetic key"),
        ((820, 500), (w + 30, 300), "LEGO DUPLO deck",
         "The 4-year-old's bit: he\ndesigns the payload"),
        ((960, 610), (w + 30, 790), "Camera",
         "Photo points + bursts; the\npictures of ducks"),
        ((670, 470), (w + 30, 60), "Big red STOP",
         "Child-operable; motors off\n< 1 s (FS-009)"),
    ]
    for (px, py), (tx, ty), t, b in notes:
        ha = "right" if tx < 0 else "left"
        ax.annotate("", (px, py), (tx + (10 if tx < 0 else -10), ty + 10),
                    arrowprops=dict(arrowstyle="-", color=BLUE, lw=1,
                                    shrinkA=0, shrinkB=0))
        ax.add_patch(Circle((px, py), 7, color=BLUE, zorder=5))
        ax.text(tx, ty, t, ha=ha, va="bottom", fontsize=9, weight="bold")
        ax.text(tx, ty + 14, b, ha=ha, va="top", fontsize=7.6, color=INK2,
                linespacing=1.2)
    save(fig, "concept_annotated.png")


# ---------------------------------------------------------------------------
# 3. SIL: tracks from the traced run
def load_trace(pattern):
    fs = sorted((DATA / "traces").glob(pattern))
    return json.loads(fs[0].read_text()) if fs else None


def draw_site(ax, g):
    fe = g["fence"] + g["fence"][:1]
    ax.add_patch(Polygon([[p[1], p[0]] for p in g["fence"]], fc=WATER,
                         ec="none", zorder=0))
    ax.plot([p[1] for p in fe], [p[0] for p in fe], color=ORANGE, lw=1.4,
            label="geofence")
    for poly in g.get("exclusions", []):
        ax.add_patch(Polygon([[p[1], p[0]] for p in poly], fc="#d8d2c2",
                             ec=INK2, lw=.8, hatch="////", zorder=1))
    for n, e, r in g.get("circles", []):
        ax.add_patch(Circle((e, n), r, fc="#d8d2c2", ec=INK2, lw=.8,
                            hatch="////", zorder=1))
    m = g.get("mission", [])
    if m:
        ax.plot([p[1] for p in m], [p[0] for p in m], ls=(0, (3, 2)),
                color=MUTED, lw=1, marker="o", ms=3.5, label="planned route")
    ax.plot(0, 0, marker="*", ms=13, color=GREEN, mec="white", zorder=6,
            label="home / launch")
    ax.set_aspect("equal")
    ax.grid(color=GRID, lw=.5)
    ax.set_xlabel("east (m)")
    ax.set_ylabel("north (m)")


def segments(rows):
    """Split a track into driving / astern / stopped runs by true thrust."""
    def state(r):
        t = r[4] if r[4] else [0, 0]
        if max(abs(x) for x in t) < 0.02:
            return "stop"
        return "astern" if sum(t) < 0 else "drive"
    out, cur, st = [], [], None
    for r in rows:
        s = state(r)
        if s != st and cur:
            out.append((st, cur + [r]))
            cur = []
        st = s
        cur.append(r)
    if cur:
        out.append((st, cur))
    return out


TRACK = {"drive": BLUE, "astern": ORANGE, "stop": INK2}


def draw_track(ax, rows, lw=1.8):
    for st, seg in segments(rows):
        if st == "stop":
            continue
        ax.plot([r[2] for r in seg], [r[1] for r in seg], color=TRACK[st],
                lw=lw, solid_capstyle="round", zorder=4)
    ax.plot(rows[-1][2], rows[-1][1], marker="o", ms=6, mfc="white",
            mec=INK, zorder=7)


def sil_nominal():
    d = load_trace("test_e2e_explore*")
    if d is None:
        return
    fig, ax = plt.subplots(figsize=(7.4, 6.4))
    draw_site(ax, d["geo"])
    draw_track(ax, d["rows"], 2.2)
    rows = d["rows"]
    ax.set_title("MC-E2E: 'explore the bay and take photos of the island, "
                 "then come home'", fontsize=8.6, loc="left")
    hs = [Line2D([], [], color=BLUE, lw=2, label="boat (true track, "
                 "driving)"),
          Line2D([], [], color=ORANGE, lw=1.4, label="geofence"),
          Line2D([], [], color=MUTED, ls=(0, (3, 2)), marker="o", ms=3,
                 label="plan Claude proposed, validator checked"),
          Line2D([], [], marker="*", ls="", ms=11, color=GREEN,
                 label="home"),
          Line2D([], [], marker="o", ls="", ms=6, mfc="white", mec=INK,
                 label=f"end (t = {rows[-1][0]:.0f} s sim)")]
    if d["geo"].get("exclusions") or d["geo"].get("circles"):
        from matplotlib.patches import Patch
        hs.insert(2, Patch(fc="#d8d2c2", ec=INK2, hatch="////",
                           label="no-go zone (island, reeds)"))
    ax.legend(handles=hs, loc="upper right", fontsize=6.8, framealpha=.95)
    for (x, y), (tx, ty), t in [
            ((18.5, 35.5), (24, 46), "photo stop at the island:\n"
             "3-photo burst, 10 s hold"),
            ((-33, 9), (-56, 16), "explore the\nhome bay"),
            ((0, -1), (8, -7), "home: \"I'm back!\",\nauto-disarm after 60 s")]:
        ax.annotate(t, (x, y), (tx, ty), fontsize=7, color=INK,
                    arrowprops=dict(arrowstyle="-", color=INK2, lw=.7))
    save(fig, "sil_nominal.png")


EDGES = [
    ("test_sc07_mission_computer_dies*", "SC-07  Mission computer\nkilled mid-mission",
     "Pi Zero, camera and Wi-Fi all dead mid-mission: the autopilot alone "
     "finishes the route and holds at home."),
    ("test_sc27*wind*", "SC-27  Return home round\nthe island, 3 m/s wind",
     "Return-to-launch from the far side of the island, 3 m/s wind "
     "pushing towards it: the planned path goes round the no-go zone, "
     "not through it (SDR RID-01 fix)."),
    ("test_sc13*gnss-offset*", "SC-13  GNSS 20 m wrong,\nheading for the fence",
     "Heading for the fence when the satellite position jumps 20 m: the "
     "boat's true track never leaves the fence while driving."),
    ("test_sc20*", "SC-20  GNSS jump\nnext to the fence",
     "A {jump} position jump outwards for {dur}, 7 m from the fence "
     "line: the boat stays inside."),
]


CAPTIONS = []


def sil_edges():
    found = [(load_trace(p), t, s) for p, t, s in EDGES]
    found = [x for x in found if x[0]]
    CAPTIONS[:] = [(t, s) for _, t, s in found]
    fig, axs = plt.subplots(1, len(found), figsize=(2.9 * len(found), 3.6))
    for ax, (d, t, s) in zip(axs, found):
        draw_site(ax, d["geo"])
        draw_track(ax, d["rows"])
        m = re.search(r"\[(\d+)m-out(?:-(\d+)s)?\]", d["nodeid"])
        if m:
            s = s.format(jump=f"{m.group(1)} m",
                         dur=f"{m.group(2) or 2} s")
        ax.set_title(t, fontsize=8.2, loc="left",
                     weight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(labelsize=6.5)
        xs = [r[2] for r in d["rows"]] + [p[1] for p in d["geo"]["mission"]]
        ys = [r[1] for r in d["rows"]] + [p[0] for p in d["geo"]["mission"]]
        fx = [p[1] for p in d["geo"]["fence"]]
        fy = [p[0] for p in d["geo"]["fence"]]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 7
        ax.set_xlim(cx - half, cx + half)
        ax.set_ylim(cy - half, cy + half)
    hs = [Line2D([], [], color=BLUE, lw=2, label="true track (simulated "
                 "boat)"),
          Line2D([], [], color=ORANGE, lw=1.4, label="geofence"),
          Line2D([], [], color=MUTED, ls=(0, (3, 2)), marker="o", ms=3,
                 label="planned route"),
          Line2D([], [], marker="*", ls="", ms=10, color=GREEN,
                 label="home"),
          Line2D([], [], marker="o", ls="", ms=6, mfc="white", mec=INK,
                 label="end of test")]
    fig.legend(handles=hs, loc="lower center", ncol=5, frameon=False,
               fontsize=7.4, bbox_to_anchor=(0.5, -0.02))
    fig.subplots_adjust(wspace=0.3)
    save(fig, "sil_edges.png")


def weed_thrust():
    d = load_trace("test_sc06_weed*")
    if d is None:
        return
    r = d["rows"]
    t = [x[0] for x in r]
    fig, ax = plt.subplots(figsize=(7.5, 2.3))
    for i, lab, c in [(0, "left thruster", BLUE), (1, "right thruster",
                                                   AQUA)]:
        ax.plot(t, [x[4][i] if x[4] else 0 for x in r], color=c, lw=1.3,
                label=lab)
    ax.axhline(0, color=MUTED, lw=.6)
    ax.set_xlabel("simulated time (s)")
    ax.set_ylabel("thrust (N)")
    ax.grid(color=GRID, lw=.5)
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "sil_weed_thrust.png")


# ---------------------------------------------------------------------------
# 4. SIL results
CATS = [
    ("Mission & Claude planning", r"^(MC-|MCN-|SC-2[4-6]|SC-3[2-7]|B2-|SC-09)"),
    ("Failsafes", r"^(SC-0[1-8]|SC-1[0-2]|FS-|FEN-)"),
    ("Single-fault sweep", r"^SC-13"),
    ("GNSS & fence edge cases", r"^(SC-2[0-3]|SC-2[7-9]|SC-3[018]|NAV-)"),
    ("Helm contract & V-items", r"^(IF-|V-)"),
]


def categorise(rid):
    for name, pat in CATS:
        if re.match(pat, rid):
            return name
    return "Other"


def sil_results():
    recs = json.loads((ROOT / "software/results/sitl_results.json")
                      .read_text())["records"]
    by = defaultdict(Counter)
    for r in recs:
        by[categorise(r["id"])][r["outcome"]] += 1
    names = [c for c, _ in CATS] + (["Other"] if "Other" in by else [])
    names = [n for n in names if n in by][::-1]
    fig, ax = plt.subplots(figsize=(7.5, 2.9))
    p = [by[n]["passed"] for n in names]
    x = [by[n]["xfail"] for n in names]
    f = [by[n]["failed"] for n in names]
    ax.barh(names, p, color=GREEN, label="passed", height=.62)
    ax.barh(names, x, left=p, color=YELLOW, label="known gap (recorded "
            "finding)", height=.62)
    ax.barh(names, f, left=[a + b for a, b in zip(p, x)], color="#e34948",
            label="failed", height=.62)
    for i, n in enumerate(names):
        tot = p[i] + x[i] + f[i]
        ax.text(tot + .4, i, f"{p[i]}/{tot}", va="center", fontsize=7.6,
                color=INK2)
    ax.set_xlabel("scenarios")
    ax.grid(axis="x", color=GRID, lw=.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    tot = Counter(r["outcome"] for r in recs)
    ax.set_xlim(0, max(a + b + c for a, b, c in zip(p, x, f)) + 3)
    ax.legend(fontsize=7, frameon=False, loc="upper center", ncol=3,
              bbox_to_anchor=(0.45, -0.2))
    ax.set_title(f"{len(recs)} scenarios on ArduPilot Rover SITL: "
                 f"{tot['passed']} passed, {tot['xfail']} known gaps, "
                 f"{tot.get('failed', 0)} failed", fontsize=8.6, loc="left")
    save(fig, "sil_results.png")


def screenshots():
    """Copy the clearest web-UI screenshots for the report."""
    sd = DATA / "screens"
    if not sd.exists():
        return []
    return sorted(p.name for p in sd.glob("*.png"))


def key_schematic():
    """The key-switch half of EDD sheet S2, cropped for the report."""
    from PIL import Image
    im = Image.open(ROOT / "docs/edd/figures/S2.png")
    w, h = im.size
    im.crop((0, int(h * 0.47), int(w * 0.5), int(h * 0.93))).save(
        OUT / "key_schematic.png")


if __name__ == "__main__":
    key_schematic()
    vmodel()
    concept_annotated()
    sil_nominal()
    sil_edges()
    sil_results()
    print("figures:", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))
