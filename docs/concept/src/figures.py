"""Generate the figures for the Boaty concept-selection report.

Run:  python3 docs/concept/src/figures.py
Writes PNGs into docs/concept/figures/.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

from scoring import CONCEPTS, weighted_scores

OUT = Path(__file__).resolve().parent.parent / "figures"
OUT.mkdir(exist_ok=True)

INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#9a998f"
GRID = "#e4e3dc"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
WATER = "#dcecf7"
HULL = "#f2f1ec"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "text.color": INK,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK2,
    "xtick.color": INK2,
    "ytick.color": INK2,
})


def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- scoring
def fig_scores():
    scores = weighted_scores()
    order = sorted(CONCEPTS, key=lambda c: scores[c["id"]])
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    for i, c in enumerate(order):
        s = scores[c["id"]]
        chosen = c.get("chosen", False)
        ax.barh(i, s, height=0.55, color=BLUE if chosen else "#c9c8c0",
                edgecolor="none")
        ax.text(s + 0.05, i, f"{s:.2f}", va="center", fontsize=8.5,
                color=INK if chosen else INK2,
                fontweight="bold" if chosen else "normal")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{c['id']}  {c['short']}" for c in order])
    for lbl, c in zip(ax.get_yticklabels(), order):
        if c.get("chosen"):
            lbl.set_fontweight("bold")
            lbl.set_color(INK)
    ax.set_xlim(0, 5)
    ax.set_xlabel("Weighted score (out of 5)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, "scores.png")


# ---------------------------------------------------------------- concept sketch
def hull_outline(x0, y0, length, width, bow=0.22):
    """Top-view hull: square stern at x0, pointed bow."""
    b = length * bow
    return [(x0, y0 - width / 2), (x0 + length - b, y0 - width / 2),
            (x0 + length, y0), (x0 + length - b, y0 + width / 2),
            (x0, y0 + width / 2)]


def label(ax, xy, xytext, text, ha="left"):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=7.5, color=INK, ha=ha,
                va="center",
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6,
                                shrinkA=2, shrinkB=0))


def fig_sketch():
    fig, (top, side) = plt.subplots(2, 1, figsize=(7.2, 6.4),
                                    gridspec_kw=dict(height_ratios=[1.15, 1]))
    L, W, beam = 600, 90, 340  # mm

    # ---- top view
    ax = top
    for yc in (-beam / 2 + W / 2, beam / 2 - W / 2):
        ax.add_patch(Polygon(hull_outline(0, yc, L, W), closed=True,
                             facecolor=HULL, edgecolor=INK, lw=1))
        for xs in (200, 400):  # segment joints
            ax.plot([xs, xs], [yc - W / 2, yc + W / 2], color=MUTED, lw=0.8,
                    ls="--")
    for xb in (130, 380):  # crossbeams
        ax.add_patch(Rectangle((xb - 8, -beam / 2 + 10), 16, beam - 20,
                               facecolor="#b9b8b0", edgecolor=INK, lw=0.6))
    ax.add_patch(FancyBboxPatch((170, -65), 200, 130,
                                boxstyle="round,pad=0,rounding_size=12",
                                facecolor="white", edgecolor=BLUE, lw=1.4))
    ax.text(270, 0, "Electronics\nbox (IP67)", ha="center", va="center",
            fontsize=7.5, color=BLUE)
    ax.add_patch(Circle((330, 45), 10, facecolor=ORANGE, edgecolor=INK,
                        lw=0.6))  # mast
    ax.add_patch(Rectangle((392, -12), 18, 24, facecolor=INK))  # camera
    for yc in (-beam / 2 + W / 2, beam / 2 - W / 2):
        ax.add_patch(Rectangle((-45, yc - 22), 45, 44, facecolor=AQUA,
                               edgecolor=INK, lw=0.6))
    label(ax, (-25, beam / 2 - W / 2 + 22), (-190, 290),
          "Thruster pod (clip-on module)")
    label(ax, (250, beam / 2 - W / 2), (120, 240),
          "Hull segment ≤200 mm, foam-filled")
    label(ax, (401, 12), (560, 200), "Camera", ha="left")
    label(ax, (330, 55), (420, 290), "Mast: GPS, flag, LED, hoop",
          ha="left")
    label(ax, (380, -beam / 2 + 20), (440, -290),
          "Crossbeam with M3 grid (\"Meccano\" rail)")
    label(ax, (-45, -beam / 2 + W / 2), (-190, -290), "Differential thrust:\n"
          "no rudder, turns on the spot")
    ax.annotate("", xy=(0, -beam / 2 - 25), xytext=(L, -beam / 2 - 25),
                arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.6))
    ax.text(L / 2, -beam / 2 - 48, "≈600 mm", ha="center", fontsize=7.5,
            color=INK2)
    ax.annotate("", xy=(L + 40, -beam / 2), xytext=(L + 40, beam / 2),
                arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.6))
    ax.text(L + 52, 0, "≈340 mm", rotation=90, va="center", fontsize=7.5,
            color=INK2)
    ax.set_xlim(-200, 720)
    ax.set_ylim(-320, 320)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Top view", loc="left", fontsize=9, color=INK2)

    # ---- side view
    ax = side
    wl = 0
    ax.add_patch(Rectangle((-200, -120), 950, 120, facecolor=WATER,
                           edgecolor="none"))
    ax.plot([-200, 750], [wl, wl], color=BLUE, lw=0.8)
    ax.text(700, 6, "WL", color=BLUE, fontsize=7)
    hull = [(0, -28), (430, -28), (L, 20), (L, 72), (0, 72)]
    ax.add_patch(Polygon(hull, closed=True, facecolor=HULL, edgecolor=INK,
                         lw=1))
    ax.add_patch(Rectangle((170, 72), 200, 70, facecolor="white",
                           edgecolor=BLUE, lw=1.4))
    ax.add_patch(Rectangle((370, 95), 18, 26, facecolor=INK))
    ax.plot([330, 330], [142, 330], color=INK, lw=2)
    ax.add_patch(Rectangle((305, 330), 50, 14, facecolor=INK2))
    ax.text(362, 337, "GPS + compass (away from motors)", fontsize=7,
            va="center")
    ax.add_patch(Polygon([(330, 300), (330, 270), (395, 285)],
                         facecolor=ORANGE, edgecolor=INK, lw=0.5))
    ax.add_patch(Circle((330, 250), 13, facecolor="none", edgecolor=INK,
                        lw=1.2))
    ax.text(349, 250, "Recovery hoop (snag with a cast line)", fontsize=7,
            va="center")
    ax.add_patch(Circle((330, 214), 6, facecolor=YELLOW, edgecolor=INK,
                        lw=0.5))
    ax.text(344, 214, "LED beacon", fontsize=7, va="center")
    # thruster pod
    ax.plot([-10, -10], [72, -40], color=INK, lw=2)
    ax.add_patch(FancyBboxPatch((-55, -62), 70, 30,
                                boxstyle="round,pad=0,rounding_size=12",
                                facecolor=AQUA, edgecolor=INK, lw=0.6))
    ax.add_patch(Rectangle((-78, -72), 18, 50, facecolor="none",
                           edgecolor=INK, lw=0.8, hatch="////"))
    label(ax, (-70, -72), (-150, -100), "Prop in weed guard")
    label(ax, (-20, -47), (60, -100),
          "Submerged brushless motor (fresh water)")
    label(ax, (100, 20), (60, 180), "Closed-cell foam core:\nfloats even if flooded")
    ax.text(-190, 100, "Draft ≈25–30 mm\nReserve buoyancy ≈4×",
            fontsize=7.5, color=INK2)
    ax.set_xlim(-200, 750)
    ax.set_ylim(-120, 370)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Side view (not to scale vertically)", loc="left",
                 fontsize=9, color=INK2)
    fig.tight_layout()
    save(fig, "sketch.png")


# ---------------------------------------------------------------- block diagram
def box(ax, x, y, w, h, title, body, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=0.12",
                                facecolor="white", edgecolor=edge, lw=1.3))
    ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top",
            fontsize=8.5, fontweight="bold")
    ax.text(x + w / 2, y + h - 0.55, body, ha="center", va="top",
            fontsize=7, color=INK2, linespacing=1.35)


def arrow(ax, a, b, text="", both=False, color=INK2, off=(0, 0.12)):
    ax.annotate("", xy=b, xytext=a,
                arrowprops=dict(arrowstyle="<->" if both else "->",
                                color=color, lw=1))
    if text:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], text,
                ha="center", fontsize=6.8, color=INK2)


def fig_blocks():
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    # shore side
    ax.add_patch(Rectangle((-0.2, -0.2), 3.0, 5.4, facecolor="#f6f5f1",
                           edgecolor="none"))
    ax.text(0.0, 5.0, "ON THE BANK", fontsize=7.5, color=MUTED,
            fontweight="bold")
    ax.add_patch(Rectangle((3.3, -0.2), 7.0, 5.4, facecolor=WATER,
                           edgecolor="none", alpha=0.55))
    ax.text(3.5, 5.0, "ON THE BOAT", fontsize=7.5, color=BLUE,
            fontweight="bold")

    box(ax, 0.1, 2.7, 2.5, 2.0, "Laptop / phone",
        "Mission planner app\n\"explore, find ducks,\ncome back\"\n-> Claude API", MUTED)
    box(ax, 0.1, 0.1, 2.5, 2.2, "Ground station",
        "QGroundControl\nmap, fence, RTL button,\nlive telemetry,\nvirtual joystick", MUTED)
    box(ax, 3.6, 2.6, 2.8, 2.1, "Mission brain",
        "ESP32-S3 camera board\nWi-Fi <-> MAVLink bridge\nphotos -> microSD\n"
        "(upgrade: Pi Zero 2W)", AQUA)
    box(ax, 3.6, 0.1, 2.8, 2.1, "Safety brain",
        "ArduPilot Rover on F405\nautopilot, geofence,\nfailsafes, RTL,\n"
        "stuck detection", BLUE)
    box(ax, 7.1, 2.9, 2.9, 1.8, "Sensors",
        "M10 GPS + compass\nIMU + baro (on FC)\nbattery V/I", MUTED)
    box(ax, 7.1, 0.1, 2.9, 2.2, "Propulsion",
        "2 × bidirectional ESC\n2 × brushless motor\n(skid steer)\n3S Li-ion + fuse", MUTED)

    arrow(ax, (2.6, 3.7), (3.6, 3.7), "Wi-Fi", both=True)
    arrow(ax, (2.6, 1.2), (3.6, 3.0), "", both=True)
    arrow(ax, (5.0, 2.6), (5.0, 2.2), "", both=True)
    ax.text(5.1, 2.37, "MAVLink (UART)", fontsize=6.8, color=INK2, va="center")
    arrow(ax, (7.1, 3.8), (6.4, 1.6), "")
    arrow(ax, (6.4, 1.0), (7.1, 1.0), "PWM/DShot", off=(0, 0.1))
    ax.set_xlim(-0.3, 10.3)
    ax.set_ylim(-0.3, 5.3)
    ax.axis("off")
    save(fig, "blocks.png")


# ---------------------------------------------------------------- safety layers
def fig_layers():
    layers = [
        ("5  Operate smart", "Wind blowing TOWARDS our bank · pre-launch checklist · "
         "recovery kit ready", MUTED),
        ("4  Find it", "Hi-vis hull, flag, LED beacon · last GPS fix in QGC · "
         "optional Bluetooth tag", YELLOW),
        ("3  Get it back", "Return-to-Launch on fence breach, low battery, lost link, "
         "mission end; Hold if stuck", ORANGE),
        ("2  Keep it inside", "ArduPilot polygon geofence 5 m inside the bank · islands & "
         "reeds excluded", BLUE),
        ("1  Keep it afloat", "Foam-filled hulls float even if flooded · catamaran is "
         "very hard to capsize", AQUA),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 3.2))
    n = len(layers)
    for i, (t, d, c) in enumerate(layers):
        y = i
        inset = (n - 1 - i) * 0.0
        ax.add_patch(FancyBboxPatch((inset, y + 0.08), 10 - 2 * inset, 0.84,
                                    boxstyle="round,pad=0,rounding_size=0.1",
                                    facecolor="white", edgecolor=c, lw=1.6))
        ax.add_patch(Rectangle((inset, y + 0.08), 0.18, 0.84, facecolor=c,
                               edgecolor="none"))
        ax.text(inset + 0.4, y + 0.5, t, fontsize=8.8, fontweight="bold",
                va="center")
        ax.text(inset + 2.75, y + 0.5, d, fontsize=7.3, color=INK2,
                va="center")
    ax.text(10, -0.35, "Each layer works on its own. Layers 1-3 live on the boat and need no radio link.", ha="right", fontsize=7,
            color=INK2)
    ax.set_xlim(0, 10.05)
    ax.set_ylim(-0.6, n)
    ax.axis("off")
    save(fig, "layers.png")


# ---------------------------------------------------------------- example mission
def fig_mission():
    import numpy as np
    from matplotlib.lines import Line2D
    from matplotlib.path import Path as MPath

    t = np.linspace(0, 2 * np.pi, 240)
    # an irregular pond ~100 m x 60 m
    r = 1 + 0.12 * np.sin(3 * t) + 0.07 * np.cos(5 * t + 1)
    px, py = 50 * r * np.cos(t), 30 * r * np.sin(t)
    fx, fy = 0.86 * px, 0.8 * py                      # geofence inside bank
    isl = (18, 6, 7, 5)                               # island centre / radii
    exc = (isl[0], isl[1], 13, 11)                    # exclusion zone
    fence = MPath(np.column_stack([fx, fy]))

    def ok(x, y, m=2.0):
        inside = fence.contains_point((x, y)) and all(
            fence.contains_point((x + dx, y + dy))
            for dx, dy in ((m, 0), (-m, 0), (0, m), (0, -m)))
        out_exc = ((x - exc[0]) / (exc[2] + m)) ** 2 + \
            ((y - exc[1]) / (exc[3] + m)) ** 2 > 1
        return inside and out_exc

    def lane(x):
        ys = [y for y in np.arange(-40, 40, 0.5) if ok(x, y)]
        # split into contiguous runs, keep them all
        runs, cur = [], [ys[0]]
        for y in ys[1:]:
            if y - cur[-1] > 0.6:
                runs.append(cur)
                cur = [y]
            else:
                cur.append(y)
        runs.append(cur)
        return [(r_[0], r_[-1]) for r_ in runs]

    home = (-38, -6)
    path = [home]
    photos = []
    down = False
    for x in range(-30, 40, 10):
        segs = lane(x)
        if len(segs) > 1:            # lane blocked by island: do the south run
            segs = [segs[0]]
        y0, y1 = segs[0]
        a_, b_ = ((x, y1), (x, y0)) if down else ((x, y0), (x, y1))
        path += [a_, b_]
        photos.append((x, (y0 + y1) / 2))
        down = not down
    # north of the island, a return pass heading home, then RTL
    north = [(x, max(lane(x)[-1][1] - 1, 18)) for x in (30, 18, 6)]
    path += north + [home]
    photos.append((18, north[1][1]))

    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    ax.fill(px * 1.12, py * 1.2, color="#e9f1e0", zorder=0)
    ax.fill(px, py, color=WATER, zorder=1)
    ax.plot(fx, fy, color=ORANGE, lw=1.4, ls="--", zorder=3)
    ax.fill(isl[0] + isl[2] * np.cos(t), isl[1] + isl[3] * np.sin(t),
            color="#cfe3bf", zorder=2)
    ax.plot(exc[0] + exc[2] * np.cos(t), exc[1] + exc[3] * np.sin(t),
            color=ORANGE, lw=1.2, ls="--", zorder=3)
    ax.text(isl[0], isl[1], "island\n(nesting)", ha="center", va="center",
            fontsize=6.5, color=INK2, zorder=4)
    xs, ys = zip(*path)
    ax.plot(xs, ys, color=BLUE, lw=1.5, zorder=5)
    ax.scatter(*zip(*photos), s=32, color=YELLOW, edgecolor=INK, lw=0.5,
               zorder=6)
    ducks = [(-24, 14), (-5, -20), (34, -12)]
    ax.scatter(*zip(*ducks), s=30, marker="^", color="#8a5a2b", zorder=7)
    for d in ducks:
        ax.text(d[0] + 2.2, d[1], "ducks", fontsize=6.5, va="center",
                color="#8a5a2b", zorder=7)
    ax.scatter(*home, s=80, marker="s", color=INK, zorder=8)
    ax.text(home[0] - 3, home[1], "HOME /\nlaunch", fontsize=7,
            ha="right", va="center", zorder=8)
    ax.annotate("wind towards our bank", xy=(-58, 36), xytext=(-20, 36),
                fontsize=7, color=INK2, va="center",
                arrowprops=dict(arrowstyle="->", color=INK2, lw=1))
    ax.set_aspect("equal")
    ax.set_xlim(-72, 66)
    ax.set_ylim(-42, 42)
    ax.axis("off")
    handles = [
        Line2D([], [], color=BLUE, lw=1.5, label="Planned route (survey, then RTL)"),
        Line2D([], [], color=ORANGE, lw=1.4, ls="--",
               label="Geofence (inside bank; island excluded)"),
        Line2D([], [], marker="o", ls="", color=YELLOW, markeredgecolor=INK,
               label="Photo / pause-and-look points"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=6.8, frameon=False,
              bbox_to_anchor=(1.05, -0.1))
    save(fig, "mission.png")


if __name__ == "__main__":
    fig_scores()
    fig_sketch()
    fig_blocks()
    fig_layers()
    fig_mission()
    print("figures written to", OUT)
