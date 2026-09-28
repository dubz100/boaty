"""Figures for the Boaty SRS. Run: python3 docs/srs/src/figures.py"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent.parent / "figures"
OUT.mkdir(exist_ok=True)

INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#9a998f"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
RED = "#e34948"
WATER = "#e8f1fb"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "text.color": INK})


def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rbox(ax, cx, cy, w, h, title, body="", edge=MUTED, fill="white",
         lw=1.2, tsize=8.2):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0,rounding_size=0.12",
                                facecolor=fill, edgecolor=edge, lw=lw,
                                zorder=2))
    if body:
        ax.text(cx, cy + h / 2 - 0.2, title, ha="center", va="top",
                fontsize=tsize, fontweight="bold", zorder=3)
        ax.text(cx, cy + h / 2 - 0.5, body, ha="center", va="top",
                fontsize=6.6, color=INK2, linespacing=1.3, zorder=3)
    else:
        ax.text(cx, cy, title, ha="center", va="center", fontsize=tsize,
                fontweight="bold", zorder=3)


def link(ax, a, b, text="", color=INK2, both=False, rad=0.0, tpos=0.5,
         toff=(0, 0.12), ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>",
                                 mutation_scale=8, color=color, lw=0.9,
                                 connectionstyle=f"arc3,rad={rad}",
                                 linestyle=ls, zorder=1))
    if text:
        x = a[0] + (b[0] - a[0]) * tpos + toff[0]
        y = a[1] + (b[1] - a[1]) * tpos + toff[1]
        ax.text(x, y, text, ha="center", va="center", fontsize=6.4,
                color=INK2, zorder=4,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.6))


# ---------------------------------------------------------------- context
def fig_context():
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    # system boundary
    ax.add_patch(FancyBboxPatch((2.6, 1.0), 5.0, 4.2,
                                boxstyle="round,pad=0,rounding_size=0.2",
                                facecolor="#f7f9fc", edgecolor=BLUE, lw=1.4,
                                ls="--"))
    ax.text(2.75, 5.0, "BOATY SYSTEM", fontsize=7.5, color=BLUE,
            fontweight="bold")
    rbox(ax, 5.1, 4.1, 3.2, 1.2, "Mission Control (Pi 5)",
         "GO / COME HOME / STOP\nmap, voice, validator", edge=AQUA)
    rbox(ax, 5.1, 2.1, 3.2, 1.5, "Boat",
         "helm + independent safety layer\nmission computer + camera\n"
         "hulls, pods, DUPLO deck", edge=BLUE)
    link(ax, (5.1, 3.5), (5.1, 2.85), "Wi-Fi 2.4 GHz", both=True,
         toff=(0.75, 0))
    # externals
    ext = [
        (0.8, 4.6, "Operator (adult)", "arms, approves,\nsupervises"),
        (0.8, 3.0, "Crew (age 4)", "speaks orders,\npresses buttons,\nbuilds"),
        (0.8, 1.3, "Other water users", "anglers, swimmers,\npaddleboarders"),
        (9.4, 4.6, "Claude API", "via phone hotspot"),
        (9.4, 3.0, "GNSS satellites", "position, time"),
        (9.4, 1.3, "Lake", "wind, waves, weed,\nwildlife"),
        (5.1, 0.1, "Cambridge Sport Lakes Trust", "permission, conditions"),
    ]
    for x, y, t, b in ext:
        w = 2.6 if x == 5.1 else 1.85
        rbox(ax, x, y, w, 1.1 if x != 5.1 else 0.7, t, b, edge=MUTED,
             fill="#f6f5f1", tsize=7.2)
    link(ax, (1.7, 4.6), (3.5, 4.3), "commands,\napprovals", both=True)
    link(ax, (1.7, 3.0), (3.5, 3.9), "voice, buttons", both=True,
         tpos=0.45)
    link(ax, (1.7, 1.3), (3.5, 1.8), "keep clear\n(OPS-004)", ls="--",
         tpos=0.45)
    link(ax, (8.5, 4.6), (6.7, 4.3), "plan requests", both=True)
    link(ax, (8.5, 3.0), (6.7, 2.4), "signals")
    link(ax, (8.5, 1.3), (6.7, 1.8), "forces, obstacles", both=True,
         tpos=0.5)
    link(ax, (5.1, 0.45), (5.1, 1.35), "", ls="--")
    ax.set_xlim(-0.2, 10.4)
    ax.set_ylim(-0.35, 5.3)
    ax.axis("off")
    save(fig, "context.png")


# ---------------------------------------------------------------- modes
def fig_modes():
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    pos = {"DISARMED": (0.9, 2.1), "HOLD": (3.8, 2.1), "MANUAL": (3.8, 3.9),
           "AUTO": (7.2, 0.5), "RTL": (7.2, 3.9)}
    col = {"DISARMED": MUTED, "HOLD": BLUE, "MANUAL": YELLOW, "AUTO": AQUA,
           "RTL": ORANGE}
    for k, (x, y) in pos.items():
        rbox(ax, x, y, 1.5, 0.66, k, edge=col[k], lw=1.8)
    L = lambda a, b, t, **kw: link(ax, a, b, t, **kw)  # noqa: E731
    L((1.65, 2.2), (3.05, 2.2), "arm: adult ×2,\npre-arm OK", toff=(0, 0.33))
    L((3.05, 2.0), (1.65, 2.0), "disarm", toff=(0, -0.2))
    L((3.65, 2.43), (3.65, 3.57), "adult", toff=(-0.35, 0))
    L((3.95, 3.57), (3.95, 2.43), "link lost 2 s,\nor adult", toff=(0.6, 0))
    L((4.55, 3.9), (6.45, 3.9), "link lost 10 s, fence breach,\nCOME HOME",
      toff=(0, 0.3))
    L((4.4, 1.77), (6.45, 0.6), "GO (approved,\nverified mission)",
      toff=(-0.35, -0.3))
    L((7.2, 0.83), (7.2, 3.57), "mission end,\nfence breach,\nlow battery,"
      "\nlink lost 60 s,\nCOME HOME", toff=(0.8, 0))
    L((6.45, 3.7), (4.55, 2.35), "arrived home", toff=(0.25, 0.1))
    ax.text(0.1, 0.1, "COME HOME from HOLD → RTL. From any armed mode: STOP, position "
            "loss or stuck → HOLD with\nmotors off (FS-004, FS-005, "
            "FS-009). The fence is enforced in every armed mode (FEN-004).",
            fontsize=6.6, color=INK2)
    ax.set_xlim(0, 8.7)
    ax.set_ylim(-0.1, 4.6)
    ax.axis("off")
    save(fig, "modes.png")


# ---------------------------------------------------------------- sequence
def fig_sequence():
    lanes = ["Crew", "Operator", "Mission\nControl", "Claude API",
             "Validator", "Helm", "Mission\ncomputer"]
    xs = {n: i * 1.25 for i, n in enumerate(lanes)}
    steps = [
        ("Crew", "Mission\nControl", "\"find the ducks!\" (voice)"),
        ("Mission\nControl", "Claude API", "request + site context"),
        ("Claude API", "Mission\nControl", "mission (schema JSON)"),
        ("Mission\nControl", "Validator", "check rules VAL-002..005"),
        ("Validator", "Mission\nControl", "pass / reasons"),
        ("Mission\nControl", "Operator", "map + spoken summary"),
        ("Operator", "Mission\nControl", "approve (PIN)"),
        ("Mission\nControl", "Helm", "upload + read-back check"),
        ("Crew", "Mission\nControl", "press-and-hold GO"),
        ("Mission\nControl", "Helm", "start AUTO"),
        ("Helm", "Mission\ncomputer", "photo points / status"),
        ("Helm", "Mission\nControl", "mission end → RTL → HOLD"),
        ("Mission\ncomputer", "Mission\nControl", "photos → captain's log"),
    ]
    n = len(steps)
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    top = n * 0.42 + 0.6
    for name, x in xs.items():
        ax.text(x, top + 0.1, name, ha="center", va="bottom", fontsize=7.2,
                fontweight="bold")
        ax.plot([x, x], [0, top], color=MUTED, lw=0.8, ls=(0, (3, 3)))
    for i, (a, b, t) in enumerate(steps):
        y = top - 0.45 - i * 0.42
        xa, xb = xs[a], xs[b]
        c = ORANGE if b == "Validator" or a == "Validator" else (
            BLUE if "Helm" in (a, b) else INK2)
        ax.annotate("", xy=(xb, y), xytext=(xa, y),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=0.9,
                                    mutation_scale=8))
        ax.text((xa + xb) / 2, y + 0.07, t, ha="center", va="bottom",
                fontsize=6.3, color=INK2,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.4))
        ax.text(-0.75, y, f"{i + 1}", fontsize=6.3, color=MUTED, va="center")
    ax.set_xlim(-0.9, xs["Mission\ncomputer"] + 0.7)
    ax.set_ylim(-0.1, top + 0.5)
    ax.axis("off")
    save(fig, "sequence.png")


# ---------------------------------------------------------------- phases
def fig_phases():
    from matplotlib.patches import Polygon
    phases = [("Prepare", "home", MUTED), ("Transport", "", MUTED),
              ("Set up", "bank", BLUE), ("Plan", "", BLUE),
              ("Launch", "", AQUA), ("Mission", "", AQUA),
              ("Recover", "", ORANGE), ("Debrief", "", YELLOW),
              ("Maintain", "home", MUTED)]
    fig, ax = plt.subplots(figsize=(7.4, 1.25))
    w, h, d = 1.0, 0.7, 0.18
    for i, (t, sub, c) in enumerate(phases):
        x = i * (w + 0.04)
        pts = [(x, 0), (x + w - d, 0), (x + w, h / 2), (x + w - d, h),
               (x, h), (x + (d if i else 0), h / 2)]
        ax.add_patch(Polygon(pts, closed=True, facecolor=c, edgecolor="white",
                             alpha=0.9))
        ax.text(x + w / 2 + 0.03, h / 2, t, ha="center", va="center",
                fontsize=6.4, color="white", fontweight="bold")
    ax.annotate("", xy=(0.1, -0.12), xytext=(len(phases) * (w + 0.04) - 0.2,
                                              -0.12),
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8,
                                connectionstyle="arc3,rad=-0.08"))
    ax.text(len(phases) * (w + 0.04) / 2, -0.62, "next session", ha="center",
            fontsize=6.5, color=INK2)
    ax.set_xlim(-0.05, len(phases) * (w + 0.04))
    ax.set_ylim(-0.75, h + 0.05)
    ax.axis("off")
    save(fig, "phases.png")


# ---------------------------------------------------------------- panel
def fig_panel():
    from matplotlib.patches import Circle, Polygon
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ax.add_patch(FancyBboxPatch((0, 0), 10.6, 5.2,
                                boxstyle="round,pad=0,rounding_size=0.4",
                                facecolor="#f2f1ec", edgecolor=INK, lw=1.2))
    # screen
    ax.add_patch(Rectangle((0.5, 1.1), 5.2, 3.6, facecolor=WATER,
                           edgecolor=INK, lw=1))
    ax.add_patch(Polygon([(1.0, 1.6), (4.9, 1.5), (5.3, 3.3), (3.8, 4.3),
                          (1.3, 4.1)], closed=True, fill=False,
                         edgecolor=ORANGE, lw=1.2, ls="--"))
    ax.plot([1.6, 2.4, 3.3, 4.2, 3.4, 1.6], [2.0, 3.6, 2.2, 3.7, 2.6, 2.0],
            color=BLUE, lw=1.2)
    ax.add_patch(Rectangle((1.45, 1.85), 0.3, 0.3, facecolor=INK))
    ax.plot([3.3], [2.2], marker=">", color=INK, ms=7)
    ax.text(0.65, 4.45, "Battery 92%   Link ●   AUTO   8 min left",
            fontsize=6.3, color=INK2, va="center")
    ax.text(3.1, 0.75, "Screen: map, plan, status (tablet or display)",
            ha="center", fontsize=6.5, color=INK2)
    # buttons
    btn = [(7.2, 4.35, BLUE, "TALK", "hold to speak"),
           (7.2, 3.1, AQUA, "GO", "hold 1 s"),
           (7.2, 1.85, YELLOW, "COME HOME", ""),
           (7.2, 0.6, RED, "STOP", "")]
    for x, y, c, t, sub in btn:
        ax.add_patch(Circle((x, y), 0.5, facecolor=c, edgecolor=INK, lw=1))
        ax.text(x + 0.85, y + 0.08, t, fontsize=8, fontweight="bold",
                va="center")
        if sub:
            ax.text(x + 0.85, y - 0.3, sub, fontsize=6.3, color=INK2,
                    va="center")
    ax.add_patch(Rectangle((7.08, 4.3), 0.24, 0.35, facecolor="white"))
    ax.add_patch(Rectangle((7.17, 4.05), 0.06, 0.25, facecolor="white"))
    ax.add_patch(Polygon([(7.03, 2.85), (7.03, 3.35), (7.45, 3.1)],
                         facecolor="white"))
    ax.add_patch(Polygon([(6.9, 1.83), (7.2, 2.13), (7.5, 1.83)],
                         facecolor="white"))
    ax.add_patch(Rectangle((7.02, 1.57), 0.36, 0.27, facecolor="white"))
    ax.add_patch(Rectangle((7.0, 0.4), 0.4, 0.4, facecolor="white"))
    # adult + mic + speaker
    ax.add_patch(Circle((10.0, 4.6), 0.2, facecolor=INK2))
    ax.text(10.0, 4.15, "mic", ha="center", fontsize=6, color=INK2)
    for k in range(3):
        ax.add_patch(Circle((10.0, 3.75 - k * 0.22), 0.06, facecolor=INK2))
    ax.text(10.0, 3.05, "speaker", ha="center", fontsize=6, color=INK2)
    ax.add_patch(Rectangle((9.75, 1.0), 0.5, 0.7, facecolor="white",
                           edgecolor=INK, lw=0.8))
    ax.text(10.0, 0.7, "adult key", ha="center", fontsize=6, color=INK2)
    ax.set_xlim(-0.1, 10.7)
    ax.set_ylim(-0.1, 5.3)
    ax.set_aspect("equal")
    ax.axis("off")
    save(fig, "panel.png")


if __name__ == "__main__":
    fig_context()
    fig_modes()
    fig_sequence()
    fig_phases()
    fig_panel()
    print("figures written to", OUT)
