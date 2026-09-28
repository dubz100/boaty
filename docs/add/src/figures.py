"""Figures for the Boaty ADD. Run: python3 docs/add/src/figures.py"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

import architecture as A

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
RED = "#e34948"
WATER = "#e8f1fb"
BANK = "#f6f5f1"
SS_COL = {"HUL": MUTED, "PRP": MUTED, "PWR": YELLOW, "HLM": BLUE,
          "MCP": AQUA, "MCN": AQUA, "REC": ORANGE, "SIM": MUTED}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "text.color": INK})


def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rbox(ax, x, y, w, h, title, body="", edge=MUTED, fill="white", lw=1.2,
         ts=7.2, bs=6.4):
    """Box with lower-left corner at (x, y)."""
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=0.1",
                                facecolor=fill, edgecolor=edge, lw=lw,
                                zorder=2))
    if body:
        ax.text(x + w / 2, y + h - 0.13, title, ha="center", va="top",
                fontsize=ts, fontweight="bold", zorder=3)
        ax.text(x + w / 2, y + h - 0.42, body, ha="center", va="top",
                fontsize=bs, color=INK2, linespacing=1.3, zorder=3)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=ts, fontweight="bold", zorder=3)


def arrow(ax, a, b, text="", color=INK2, both=False, ls="-", rad=0.0,
          toff=(0, 0.1), fs=6.2, lw=0.9):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>",
                                 mutation_scale=7, color=color, lw=lw,
                                 linestyle=ls, zorder=1,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((a[0] + b[0]) / 2 + toff[0], (a[1] + b[1]) / 2 + toff[1],
                text, ha="center", va="center", fontsize=fs, color=INK2,
                zorder=4, bbox=dict(facecolor="white", edgecolor="none",
                                    pad=0.5))


# ---------------------------------------------------------------- candidates
def fig_candidates():
    # which blocks each candidate has on boat / bank, and where the "brain" is
    spec = {
        "AR-1": dict(boat=[("Helm", BLUE), ("Companion:\nplan + validate", AQUA),
                           ("Camera", MUTED)],
                     bank=[("Thin remote", MUTED)], link="Wi-Fi"),
        "AR-2": dict(boat=[("Helm", BLUE), ("Pi Zero:\ncamera + relay", AQUA)],
                     bank=[("Pi 5: plan, validate,\nUI, voice, photos", AQUA)],
                     link="Wi-Fi (pole)"),
        "AR-3": dict(boat=[("Helm", BLUE), ("Wi-Fi bridge", MUTED),
                           ("Action cam", MUTED)],
                     bank=[("Pi 5: everything", AQUA)], link="Wi-Fi"),
        "AR-4": dict(boat=[("Helm", BLUE), ("Pi Zero:\ncamera", AQUA)],
                     bank=[("Pi 5: everything", AQUA)],
                     link="868 MHz + Wi-Fi"),
        "AR-5": dict(boat=[("Helm", BLUE), ("Pi Zero:\ncamera + relay", AQUA)],
                     bank=[("Phone app", MUTED)], link="Wi-Fi"),
    }
    fig, axes = plt.subplots(1, 5, figsize=(7.6, 2.5))
    for ax, c in zip(axes, A.CANDIDATES):
        s = spec[c["id"]]
        chosen = c.get("chosen")
        ax.add_patch(Rectangle((0, 0), 2.2, 4.2, facecolor=WATER,
                               edgecolor="none"))
        ax.add_patch(Rectangle((0, 4.6), 2.2, 1.6, facecolor=BANK,
                               edgecolor="none"))
        ax.text(0.08, 4.05, "BOAT", fontsize=5.5, color=BLUE, va="top",
                fontweight="bold")
        ax.text(0.08, 6.1, "BANK", fontsize=5.5, color=MUTED, va="top",
                fontweight="bold")
        for i, (t, col) in enumerate(s["boat"]):
            rbox(ax, 0.15, 3.0 - i * 1.0, 1.9, 0.8, t, edge=col, ts=5.6)
        for i, (t, col) in enumerate(s["bank"]):
            rbox(ax, 0.15, 4.75, 1.9, 1.0, t, edge=col, ts=5.6)
        ax.annotate("", xy=(1.1, 4.75), xytext=(1.1, 3.8),
                    arrowprops=dict(arrowstyle="<|-|>", color=INK2, lw=0.8,
                                    mutation_scale=6))
        ax.text(1.2, 4.28, s["link"], fontsize=5.2, color=INK2, va="center")
        ax.set_title(f"{c['id']}\n{c['name']}", fontsize=7.2,
                     fontweight="bold" if chosen else "normal",
                     color=BLUE if chosen else INK)
        if chosen:
            ax.add_patch(Rectangle((-0.05, -0.05), 2.3, 6.3, fill=False,
                                   edgecolor=BLUE, lw=1.6))
        ax.set_xlim(-0.1, 2.3)
        ax.set_ylim(-0.1, 6.3)
        ax.axis("off")
    fig.tight_layout(w_pad=0.6)
    save(fig, "candidates.png")


def fig_scores():
    cs = sorted(A.CANDIDATES, key=A.candidate_score)
    fig, ax = plt.subplots(figsize=(6.2, 2.1))
    for i, c in enumerate(cs):
        s = A.candidate_score(c)
        ch = c.get("chosen")
        ax.barh(i, s, height=0.55, color=BLUE if ch else "#c9c8c0")
        ax.text(s + 0.05, i, f"{s:.2f}", va="center", fontsize=8,
                fontweight="bold" if ch else "normal",
                color=INK if ch else INK2)
    ax.set_yticks(range(len(cs)))
    ax.set_yticklabels([f"{c['id']}  {c['name']}" for c in cs])
    for lbl, c in zip(ax.get_yticklabels(), cs):
        if c.get("chosen"):
            lbl.set_fontweight("bold")
    ax.set_xlim(0, 5)
    ax.set_xlabel("Weighted score (out of 5)", color=INK2)
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, "cand_scores.png")


# ---------------------------------------------------------------- physical
def fig_physical():
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    ax.add_patch(Rectangle((0, 0), 6.6, 6.4, facecolor=WATER,
                           edgecolor="none"))
    ax.text(0.15, 6.2, "BOAT", fontsize=8, color=BLUE, fontweight="bold",
            va="top")
    ax.add_patch(Rectangle((7.0, 0), 4.0, 6.4, facecolor=BANK,
                           edgecolor="none"))
    ax.text(7.15, 6.2, "BANK", fontsize=8, color=MUTED, fontweight="bold",
            va="top")
    # boat blocks
    rbox(ax, 0.3, 4.2, 2.8, 1.6, "HLM  Helm", "F405 + ArduPilot Rover\n"
         "M10 GNSS + compass (mast)\nfence, failsafes, modes", edge=BLUE,
         lw=1.8)
    rbox(ax, 3.5, 4.2, 2.8, 1.6, "MCP  Mission computer", "Pi Zero 2W + "
         "5 MP camera\nrouter, camera, watchdogs\nmoisture sensor", edge=AQUA,
         lw=1.6)
    rbox(ax, 0.3, 1.9, 2.8, 1.5, "PRP  Propulsion", "2 × bidirectional ESC\n"
         "2 × clip-on thruster pod", edge=MUTED)
    rbox(ax, 3.5, 1.9, 2.8, 1.5, "PWR  Power", "3S Li-ion + BMS, fuse\n"
         "magnetic arming key\npower module, 5 V buck", edge=YELLOW, lw=1.6)
    rbox(ax, 0.3, 0.2, 2.8, 1.2, "REC  Recovery", "hi-vis, flag, hoop,\n"
         "LED beacon", edge=ORANGE)
    rbox(ax, 3.5, 0.2, 2.8, 1.2, "HUL  Hull & structure", "segments, "
         "beams, DUPLO deck,\nbox saddle, mast", edge=MUTED)
    # bank
    rbox(ax, 7.3, 3.4, 3.4, 2.4, "MCN  Mission Control", "Raspberry Pi 5\n"
         "GO / COME HOME / STOP / TALK\nkey switch, mic, speaker\nUSB Wi-Fi "
         "(pole if needed)\nPython application", edge=AQUA, lw=1.8)
    rbox(ax, 7.3, 1.8, 1.6, 1.1, "Phone", "USB tether\n+ web UI", ts=7)
    rbox(ax, 9.1, 1.8, 1.6, 1.1, "Claude API", "HTTPS", ts=7)
    rbox(ax, 7.3, 0.2, 3.4, 1.1, "SIM  Simulation (home)", "SITL + camera "
         "stub + tests", ts=7, edge=MUTED)
    # links
    arrow(ax, (3.1, 5.0), (3.5, 5.0), "IF-04", both=True, toff=(0, 0.22))
    arrow(ax, (6.3, 5.0), (7.3, 5.0), "IF-01 Wi-Fi\n(IF-02, IF-03)",
          both=True, toff=(0, 0.62))
    arrow(ax, (1.7, 4.2), (1.7, 3.4), "IF-05", toff=(0.35, 0))
    arrow(ax, (3.5, 2.7), (3.1, 2.7), "IF-06", toff=(0, 0.2))
    arrow(ax, (4.2, 3.4), (2.6, 4.2), "IF-07", toff=(-0.1, 0.12))
    arrow(ax, (4.9, 3.4), (4.9, 4.2), "IF-08", toff=(0.35, 0))
    ax.plot([0.3, 0.15, 0.15], [4.6, 4.6, 0.8], color=INK2, lw=0.9,
            zorder=1)
    arrow(ax, (0.15, 0.8), (0.3, 0.8))
    ax.text(0.2, 2.9, "IF-09", rotation=90, fontsize=6.2, color=INK2,
            ha="center", va="center", bbox=dict(facecolor=WATER,
                                                edgecolor="none", pad=0.4))
    arrow(ax, (8.1, 3.4), (8.1, 2.9), "IF-10", both=True, toff=(0.35, 0))
    arrow(ax, (9.9, 3.4), (9.9, 2.9), "IF-11", both=True, toff=(0.35, 0))
    arrow(ax, (9.0, 1.3), (9.0, 3.4), "IF-21", ls="--", toff=(0, -0.35))
    ax.set_xlim(-0.1, 11.1)
    ax.set_ylim(-0.1, 6.5)
    ax.axis("off")
    save(fig, "physical.png")


# ---------------------------------------------------------------- software
def fig_software():
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    ax.add_patch(Rectangle((0, 0), 7.2, 7.0, facecolor=BANK,
                           edgecolor="none"))
    ax.text(0.15, 6.85, "MISSION CONTROL (Pi 5, Python)", fontsize=7.2,
            color=INK2, fontweight="bold", va="top")
    ax.add_patch(Rectangle((7.5, 0), 3.6, 7.0, facecolor=WATER,
                           edgecolor="none"))
    ax.text(7.65, 6.85, "BOAT", fontsize=7.2, color=BLUE, fontweight="bold",
            va="top")
    W, H = 2.1, 0.75
    pos = {"C2": (0.2, 5.6), "C3": (2.5, 5.6), "C4": (4.8, 5.6),
           "C1": (2.5, 4.4), "C5": (0.2, 3.1), "C6": (2.5, 3.1),
           "C7": (4.8, 3.1), "C9": (0.2, 1.7), "C10": (2.5, 1.7),
           "C8": (4.8, 1.7)}
    comp = {c[1]: c for c in A.COMPONENTS}
    for k, (x, y) in pos.items():
        col = ORANGE if k == "C6" else (BLUE if k == "C7" else AQUA)
        rbox(ax, x, y, W, H, f"{k} {comp[k][2]}", edge=col, ts=6.6)
    bpos = {"B1": (7.8, 4.4), "B6": (9.5, 4.4), "B2": (7.8, 3.1),
            "B4": (9.5, 3.1), "B3": (7.8, 1.7), "B5": (9.5, 1.7),
            "B7": (8.4, 0.45)}
    for k, (x, y) in bpos.items():
        rbox(ax, x, y, 2.1 if k == "B7" else 1.55, 0.75,
             f"{k}\n{comp[k][2]}", edge=AQUA, ts=6.0)
    rbox(ax, 7.8, 5.55, 3.25, 1.0, "A1 ArduPilot Rover (FC)",
         "modes · fence · failsafes · AUTO", edge=BLUE, lw=1.8, ts=6.8)
    # flows
    arrow(ax, (1.25, 5.6), (2.8, 5.15), "")
    arrow(ax, (5.85, 5.6), (4.4, 5.15), "")
    arrow(ax, (3.55, 5.6), (3.55, 5.15), "", both=True)
    arrow(ax, (3.0, 4.4), (1.3, 3.85), "request", toff=(-0.3, 0.08))
    arrow(ax, (2.3, 3.47), (2.5, 3.47), "")
    arrow(ax, (4.6, 3.47), (4.8, 3.47), "")
    arrow(ax, (1.25, 2.45), (1.25, 3.1), "site", toff=(-0.3, 0))
    arrow(ax, (5.85, 3.85), (4.5, 4.4), "status", both=True, toff=(0.3, 0.1))
    arrow(ax, (6.9, 3.6), (7.8, 4.75), "IF-02\nMAVLink", both=True,
          toff=(-0.15, 0.3))
    arrow(ax, (6.9, 2.07), (7.8, 2.07), "IF-03", both=True, toff=(0, 0.2))
    arrow(ax, (8.55, 5.15), (8.55, 5.55), "IF-04", both=True,
          toff=(0.45, 0))
    arrow(ax, (8.55, 3.1), (8.55, 2.45), "")
    ax.text(0.2, 0.6, "Mission path: C4/C3 → C5 planner (Claude intent + "
            "geometry) → C6 validator → adult\napproval in C1 → C7 upload "
            "+ read-back → A1 AUTO. Every source goes through C6.",
            fontsize=6.5, color=INK2)
    ax.set_xlim(-0.1, 11.2)
    ax.set_ylim(0, 7.1)
    ax.axis("off")
    save(fig, "software.png")


# ---------------------------------------------------------------- link
def fig_link():
    import numpy as np
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    d = 100.0
    x = np.linspace(0, d, 200)
    lam = 3e8 / 2.44e9
    r = np.sqrt(lam * x * (d - x) / d)
    for hb, col, lab in ((0.5, RED, "bank antenna 0.5 m (box on the "
                          "ground)"), (2.0, AQUA, "bank antenna 2.0 m "
                                       "(pole)")):
        hbt = 0.3
        los = hb + (hbt - hb) * x / d
        ax.plot(x, los, color=col, lw=1.4, label=lab)
        ax.fill_between(x, los - 0.6 * r, los + 0.6 * r, color=col,
                        alpha=0.12)
    ax.axhline(0, color=BLUE, lw=1)
    ax.fill_between(x, -0.6, 0, color=WATER)
    ax.text(50, -0.35, "water", ha="center", fontsize=6.5, color=BLUE)
    ax.text(97, 0.45, "boat\n0.3 m", fontsize=6.5, ha="right", color=INK2)
    ax.set_xlabel("Distance from bank (m)", color=INK2)
    ax.set_ylabel("Height (m)", color=INK2)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, 3.2)
    ax.legend(fontsize=6.5, frameon=False, loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "link.png")


# ---------------------------------------------------------------- power
def fig_power():
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    rbox(ax, 0.1, 1.5, 1.6, 1.2, "Battery", "3S Li-ion\n+ BMS", edge=YELLOW,
         lw=1.6)
    rbox(ax, 2.1, 1.7, 1.2, 0.8, "Fuse", edge=MUTED, ts=7)
    rbox(ax, 3.7, 1.7, 1.4, 0.8, "Main switch", edge=MUTED, ts=6.6)
    rbox(ax, 5.5, 1.5, 1.6, 1.2, "Power module", "V / I sense", edge=YELLOW)
    rbox(ax, 7.6, 2.9, 2.0, 0.9, "Key switch", "reed + MOSFET", edge=ORANGE,
         ts=6.8)
    rbox(ax, 10.1, 2.9, 1.6, 0.9, "ESCs →\nmotors", edge=MUTED, ts=6.4)
    rbox(ax, 7.6, 1.6, 2.0, 0.9, "FC (own reg.)", edge=BLUE, ts=6.8)
    rbox(ax, 7.6, 0.2, 2.0, 0.9, "5 V 3 A buck", edge=MUTED, ts=6.8)
    rbox(ax, 10.1, 0.2, 1.6, 0.9, "Pi Zero 2W", edge=AQUA, ts=6.6)
    arrow(ax, (1.7, 2.1), (2.1, 2.1))
    arrow(ax, (3.3, 2.1), (3.7, 2.1))
    arrow(ax, (5.1, 2.1), (5.5, 2.1))
    arrow(ax, (7.1, 2.4), (7.6, 3.35), "motor rail", toff=(-0.3, 0.2))
    arrow(ax, (9.6, 3.35), (10.1, 3.35))
    arrow(ax, (7.1, 2.05), (7.6, 2.05), "V/I", toff=(0, 0.2))
    arrow(ax, (7.1, 1.7), (7.6, 0.65), "", )
    arrow(ax, (9.6, 0.65), (10.1, 0.65))
    arrow(ax, (8.6, 2.9), (8.6, 2.5), "rail sense", ls="--", toff=(0.5, 0))
    ax.set_xlim(0, 11.8)
    ax.set_ylim(0, 4.0)
    ax.axis("off")
    save(fig, "power.png")


# ---------------------------------------------------------------- pipeline
def fig_pipeline():
    steps = [("Voice / text\n/ template", MUTED), ("STT\n(on-device)", MUTED),
             ("Claude:\nintent JSON", AQUA), ("Planner:\ngeometry", AQUA),
             ("Validator", ORANGE), ("Adult\napproval", YELLOW),
             ("Upload +\nread-back", BLUE), ("ArduPilot\nAUTO → RTL", BLUE)]
    fig, ax = plt.subplots(figsize=(7.6, 1.5))
    w, g = 1.05, 0.22
    for i, (t, c) in enumerate(steps):
        x = i * (w + g)
        rbox(ax, x, 0.3, w, 0.9, t, edge=c, lw=1.5, ts=6.2)
        if i:
            arrow(ax, (x - g, 0.75), (x, 0.75))
    ax.annotate("", xy=(3 * (w + g) + w / 2, 0.3),
                xytext=(4 * (w + g) + w / 2, 0.3),
                arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=0.8,
                                connectionstyle="arc3,rad=-0.6"))
    ax.text(3.5 * (w + g) + w / 2, -0.3, "reject → reasons, retry ≤ 2, "
            "then templates", fontsize=6, color=ORANGE, ha="center",
            va="center")
    ax.set_xlim(-0.05, len(steps) * (w + g))
    ax.set_ylim(-0.45, 1.3)
    ax.axis("off")
    save(fig, "pipeline.png")


# ---------------------------------------------------------------- N2
def fig_n2():
    nodes = [s[0] for s in A.SUBSYSTEMS] + list(A.EXTERNALS)
    labels = [s[0] for s in A.SUBSYSTEMS] + ["Phone", "Claude", "People"]
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    cell = {}
    for i in A.INTERFACES:
        a, b = i[2], i[3]
        cell.setdefault((idx[a], idx[b]), []).append(i[0][3:])
        if a != b:
            cell.setdefault((idx[b], idx[a]), []).append(i[0][3:])
    fig, ax = plt.subplots(figsize=(6.8, 6.0))
    for r in range(n):
        for c in range(n):
            if r == c:
                ax.add_patch(Rectangle((c, n - 1 - r), 1, 1,
                                       facecolor=BLUE if r < 8 else MUTED,
                                       edgecolor="white", lw=1.5))
                ax.text(c + 0.5, n - 1 - r + 0.5, labels[r], ha="center",
                        va="center", fontsize=6.3 if r < 8 else 5.3,
                        color="white", fontweight="bold")
                if (r, c) in cell:
                    ax.text(c + 0.5, n - 1 - r + 0.15, ",".join(cell[(r, c)]),
                            ha="center", va="center", fontsize=5,
                            color="white")
            else:
                has = (r, c) in cell
                ax.add_patch(Rectangle((c, n - 1 - r), 1, 1,
                                       facecolor="#dcebfa" if has else
                                       "#f6f5f1", edgecolor="white", lw=1.5))
                if has:
                    ax.text(c + 0.5, n - 1 - r + 0.5,
                            "\n".join(sorted(set(cell[(r, c)]))),
                            ha="center", va="center", fontsize=6,
                            color=INK)
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect("equal")
    ax.axis("off")
    save(fig, "n2.png")


if __name__ == "__main__":
    fig_candidates()
    fig_scores()
    fig_physical()
    fig_software()
    fig_link()
    fig_power()
    fig_pipeline()
    fig_n2()
    print("figures written to", OUT)
