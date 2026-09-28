"""Figures for the Boaty ICD. Run: python3 docs/icd/src/figures.py"""
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
WATER = "#e8f1fb"
BANK = "#f6f5f1"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5,
                     "text.color": INK})


def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def box(ax, x, y, w, h, title, body="", edge=MUTED, lw=1.3, ts=7.2, bs=6.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=0.1",
                                facecolor="white", edgecolor=edge, lw=lw,
                                zorder=2))
    ax.text(x + w / 2, y + h - 0.12, title, ha="center", va="top",
            fontsize=ts, fontweight="bold", zorder=3)
    if body:
        ax.text(x + w / 2, y + h - 0.42, body, ha="center", va="top",
                fontsize=bs, color=INK2, linespacing=1.35, zorder=3,
                family="DejaVu Sans Mono")


def link(ax, a, b, text="", color=INK2, ls="-", both=True, toff=(0, 0.13),
         fs=6.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>",
                                 mutation_scale=7, color=color, lw=0.9,
                                 linestyle=ls, zorder=1))
    if text:
        ax.text((a[0] + b[0]) / 2 + toff[0], (a[1] + b[1]) / 2 + toff[1],
                text, ha="center", va="center", fontsize=fs, color=INK2,
                zorder=4, family="DejaVu Sans Mono",
                bbox=dict(facecolor="white", edgecolor="none", pad=0.5))


def fig_network():
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.add_patch(Rectangle((0, 0), 5.9, 4.6, facecolor=BANK,
                           edgecolor="none"))
    ax.text(0.12, 4.45, "BANK", fontsize=7, color=MUTED, fontweight="bold",
            va="top")
    ax.add_patch(Rectangle((6.3, 0), 3.6, 4.6, facecolor=WATER,
                           edgecolor="none"))
    ax.text(6.42, 4.45, "BOAT", fontsize=7, color=BLUE, fontweight="bold",
            va="top")
    box(ax, 1.9, 2.3, 2.4, 1.7, "Mission Control (Pi 5)",
        "wlan1 AP 192.168.50.1/24\nusb0  DHCP from phone\nUDP 14550 MAVLink\n"
        "HTTP 8000 web UI", edge=AQUA)
    box(ax, 0.2, 0.3, 2.2, 1.4, "Phone (USB)", "usb0 e.g. 192.168.42.x\n"
        "default route → internet\nbrowser → web UI")
    box(ax, 3.2, 0.3, 2.4, 1.4, "Tablet (optional)", "Wi-Fi client\n"
        "192.168.50.100-150\nbrowser → :8000")
    box(ax, 6.6, 2.3, 3.0, 1.7, "Mission computer", "wlan0 192.168.50.10\n"
        "HTTP 8080 photo API\nmavlink-router\nUART → FC 115200", edge=AQUA)
    box(ax, 6.6, 0.3, 3.0, 1.2, "Flight controller", "MAVLink sysid 1\n"
        "SERIAL2 MAVLink2", edge=BLUE)
    link(ax, (4.3, 3.15), (6.6, 3.15), "IF-01 Wi-Fi ch. fixed\nWPA2",
         toff=(0, 0.3))
    link(ax, (1.3, 1.7), (2.5, 2.3), "IF-10 USB", toff=(-0.35, 0.05))
    link(ax, (4.4, 1.7), (3.8, 2.3), "", ls="--")
    link(ax, (8.1, 2.3), (8.1, 1.5), "IF-04 UART", toff=(0.6, 0))
    ax.text(0.2, -0.25, "Internet: only via usb0 (phone). The AP network has "
            "no route to the internet; nothing on the boat can reach it.",
            fontsize=6.3, color=INK2)
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.45, 4.7)
    ax.axis("off")
    save(fig, "network.png")


def fig_mavlink():
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    box(ax, 0.2, 1.1, 2.3, 1.5, "Mission Control", "sysid 255 compid 190\n"
        "MAV_TYPE_GCS\nheartbeat 1 Hz", edge=AQUA)
    box(ax, 3.6, 1.1, 2.5, 1.5, "mavlink-router (B1)", "UDP → 192.168.50.1\n"
        "   :14550 (client)\nUDP 127.0.0.1:14560\nUART /dev/serial0",
        edge=AQUA)
    box(ax, 7.2, 1.1, 2.4, 1.5, "ArduPilot Rover", "sysid 1 compid 1\n"
        "SYSID_MYGCS = 255\nSERIAL2 MAVLink2", edge=BLUE, lw=1.8)
    box(ax, 3.6, -0.6, 2.5, 1.1, "B2-B6 services", "sysid 1 compid 191\n"
        "MAV_TYPE_ONBOARD_CONTROLLER", edge=AQUA)
    link(ax, (2.5, 1.85), (3.6, 1.85), "IF-02 UDP", toff=(0, 0.2))
    link(ax, (6.1, 1.85), (7.2, 1.85), "IF-04 UART", toff=(0, 0.2))
    link(ax, (4.85, 0.5), (4.85, 1.1), "local UDP", toff=(0.6, 0))
    ax.set_xlim(0, 9.8)
    ax.set_ylim(-0.7, 2.7)
    ax.axis("off")
    save(fig, "mavlink.png")


def fig_sequence():
    lanes = ["Session\nmanager (C1)", "Helm\ninterface (C7)", "ArduPilot"]
    xs = [0.8, 3.4, 6.4]
    steps = [
        (0, 1, "upload(fence, mission)"),
        (1, 2, "MISSION_COUNT (type FENCE, n)"),
        (2, 1, "MISSION_REQUEST_INT seq 0..n-1"),
        (1, 2, "MISSION_ITEM_INT ×n"),
        (2, 1, "MISSION_ACK ACCEPTED"),
        (1, 2, "same for type MISSION"),
        (1, 2, "MISSION_REQUEST_LIST (read-back)"),
        (2, 1, "MISSION_COUNT + items"),
        (1, 0, "verified: SHA-256 equal"),
        (0, 1, "arm()  [key in, adult]"),
        (1, 2, "COMMAND_LONG 400 (arm) → ACK"),
        (0, 1, "start()  [GO held 1 s]"),
        (1, 2, "COMMAND_LONG 176 mode AUTO (10)"),
        (2, 1, "COMMAND_ACK + HEARTBEAT mode 10"),
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    top = len(steps) * 0.33 + 0.4
    for x, n in zip(xs, lanes):
        ax.text(x, top + 0.05, n, ha="center", va="bottom", fontsize=7,
                fontweight="bold")
        ax.plot([x, x], [0, top], color=MUTED, lw=0.8, ls=(0, (3, 3)))
    for i, (a, b, t) in enumerate(steps):
        y = top - 0.3 - i * 0.33
        c = BLUE if 2 in (a, b) else INK2
        ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=0.9,
                                    mutation_scale=7))
        ax.text((xs[a] + xs[b]) / 2, y + 0.05, t, ha="center", va="bottom",
                fontsize=5.9, color=INK2, family="DejaVu Sans Mono",
                bbox=dict(facecolor="white", edgecolor="none", pad=0.3))
    ax.set_xlim(-0.2, 7.4)
    ax.set_ylim(-0.1, top + 0.5)
    ax.axis("off")
    save(fig, "sequence.png")


def fig_states():
    fig, ax = plt.subplots(figsize=(7.4, 2.2))
    st = [("IDLE", MUTED), ("PLANNING", AQUA), ("PLAN_READY", YELLOW),
          ("APPROVED", YELLOW), ("ARMED", BLUE), ("MISSION", BLUE),
          ("RETURNING", ORANGE), ("DEBRIEF", AQUA)]
    w, g = 0.95, 0.22
    for i, (n, c) in enumerate(st):
        x = i * (w + g)
        ax.add_patch(FancyBboxPatch((x, 0.6), w, 0.6,
                                    boxstyle="round,pad=0,rounding_size=0.08",
                                    facecolor="white", edgecolor=c, lw=1.5))
        ax.text(x + w / 2, 0.9, n, ha="center", va="center", fontsize=5.6,
                fontweight="bold")
        if i:
            ax.annotate("", xy=(x, 0.9), xytext=(x - g, 0.9),
                        arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.8,
                                        mutation_scale=6))
    labels = ["talk", "plan ok", "adult\napproves", "adult\narms", "GO",
              "end / COME\nHOME / failsafe", "home,\ndisarm"]
    for i, t in enumerate(labels):
        x = (i + 1) * (w + g) - g / 2
        ax.text(x, 1.42, t, ha="center", va="bottom", fontsize=5.4,
                color=INK2)
    ax.text(0, 0.2, "STOP from any armed state → motors stop, HOLD, then "
            "disarm → IDLE (or DEBRIEF if photos exist). Any edit to an "
            "approved plan → PLAN_READY.", fontsize=6.2, color=INK2)
    ax.set_xlim(-0.1, len(st) * (w + g))
    ax.set_ylim(0, 1.9)
    ax.axis("off")
    save(fig, "states.png")


if __name__ == "__main__":
    fig_network()
    fig_mavlink()
    fig_sequence()
    fig_states()
    print("figures written to", OUT)
