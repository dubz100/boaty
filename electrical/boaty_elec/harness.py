"""Harness and packaging: the wire list, the interconnect diagram, and the
layout inside the electronics box with its clearance checks."""
from __future__ import annotations

import csv
import itertools

from . import design as DS

# Inside the box: x forward from the aft wall, y to port from the
# starboard wall, z up from the floor (mm). Internal 196.8 × 126.8 × 82.8
# (MDD box, 1.6 mm walls). (name, x0, y0, z0, dx, dy, dz, heat W, ref)
BOX_IN = (196.8, 126.8, 82.8)
LAYOUT = [
    # floor
    ("Battery pack 3S (sleeve)", 16, 4, 0, 70, 62, 23, 0.2, "BT1"),
    ("XT60 + fuse holder", 16, 70, 0, 30, 20, 16, 0.0, "J3"),
    ("Buck 5.1 V", 100, 96, 0, 25, 20, 10, 0.2, "U5"),
    ("ESC port", 128, 96, 0, 32, 16, 8, 0.2, "U3"),
    ("ESC starboard", 128, 72, 0, 32, 16, 8, 0.2, "U4"),
    ("Moisture comb (low point, fwd)", 164, 20, 0, 30, 40, 2, 0.0, "S2"),
    # printed mezzanine plate on stand-offs at z 30
    ("PIB (power and interconnect)", 16, 12, 30, 107, 46, 20, 0.1, "PIB"),
    ("FC + PDB", 126, 30, 30, 52, 32, 16, 0.8, "U2"),
    ("Pi Zero + MIB", 122, 66, 48, 61, 30, 20, 1.8, "U6"),
    ("Camera (front wall)", 187, 50, 44, 9, 25, 24, 0.0, "U7"),
    ("DS18B20 (top)", 60, 100, 74, 10, 6, 5, 0.0, "U8"),
    ("Reed switch (under key dock)", 18, 55, 70, 14, 6, 6, 0.0, "SW2"),
]


def _box(item):
    _, x, y, z, dx, dy, dz, *_ = item
    return (x, y, z, x + dx, y + dy, z + dz)


def _dist(a, b) -> float:
    ax0, ay0, az0, ax1, ay1, az1 = a
    bx0, by0, bz0, bx1, by1, bz1 = b
    dx = max(bx0 - ax1, ax0 - bx1, 0)
    dy = max(by0 - ay1, ay0 - by1, 0)
    dz = max(bz0 - az1, az0 - bz1, 0)
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def box_check() -> dict:
    errs = []
    for it in LAYOUT:
        x0, y0, z0, x1, y1, z1 = _box(it)
        if min(x0, y0, z0) < 0 or x1 > BOX_IN[0] or y1 > BOX_IN[1] or \
                z1 > BOX_IN[2]:
            errs.append(f"{it[0]} outside the box")
    for a, b in itertools.combinations(LAYOUT, 2):
        if _dist(_box(a), _box(b)) == 0:
            errs.append(f"{a[0]} overlaps {b[0]}")
    bat = next(i for i in LAYOUT if i[8] == "BT1")
    esc = min(_dist(_box(bat), _box(i)) for i in LAYOUT
              if i[8] in ("U3", "U4"))
    # gland nuts: 15 mm in from the aft wall at z 26-46
    for it in LAYOUT:
        x0, y0, z0, x1, y1, z1 = _box(it)
        if x0 < 15 and z1 > 26 and z0 < 46:
            errs.append(f"{it[0]} is in the gland nuts' space")
    return dict(errors=errs, battery_to_esc=esc,
                heat=sum(i[7] for i in LAYOUT))


def draw_box(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.6),
                            gridspec_kw=dict(width_ratios=[1.55, 1]))
    cols = {"BT1": "#e8b04a", "U3": "#6b8fd6", "U4": "#6b8fd6",
            "PIB": "#c98a4b", "U2": "#555", "U6": "#58a55c", "U5": "#999",
            "J3": "#d05050"}
    for ax, (i, j, lab) in zip(axs, ((0, 1, "plan (from above)"),
                                     (0, 2, "side (from starboard)"))):
        W = (BOX_IN[i], BOX_IN[j])
        ax.add_patch(Rectangle((0, 0), *W, fill=False, lw=1.6))
        for it in sorted(LAYOUT, key=lambda t: t[3] if j == 1 else t[2]):
            b = _box(it)
            ax.add_patch(Rectangle((b[i], b[j]), b[i + 3] - b[i],
                                   b[j + 3] - b[j],
                                   color=cols.get(it[8], "#bbb"),
                                   alpha=0.55, ec="k", lw=0.6))
            ax.text(b[i] + 1.5, b[j] + (b[j + 3] - b[j]) / 2, it[0],
                    fontsize=5.6, va="center")
        if j == 2:
            for g in range(4):
                ax.add_patch(Rectangle((-12, 30), 12, 12, color="#333"))
            ax.text(-11, 45, "glands\n(aft)", fontsize=5.5)
        else:
            for k in range(4):
                y = BOX_IN[1] / 2 + 25 * (k - 1.5)
                ax.add_patch(Rectangle((-12, y - 6), 12, 12, color="#333"))
        ax.set_xlim(-16, W[0] + 4)
        ax.set_ylim(-4, W[1] + 4)
        ax.set_aspect("equal")
        ax.set_title(lab, fontsize=8)
        ax.tick_params(labelsize=6)
        ax.set_xlabel("x forward (mm)", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def draw_interconnect(path):
    """Boards and modules as blocks; cables between them labelled with
    their cable id, gauge and gland."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    blocks = {
        "PACK": (0, 6.4, "Battery pack\nBT1 · U1 BMS · F1 20 A"),
        "J3": (3.2, 6.4, "XT60\nJ1 ⇄ J3"),
        "PIB": (6.4, 6.4, "PIB\nQ1 main · Q2 key\nbleeder · sense"),
        "U2": (6.4, 3.0, "U2 FC + PDB\n(helm)"),
        "U3": (11.0, 5.4, "U3 ESC port"),
        "U4": (11.0, 2.4, "U4 ESC stbd"),
        "U5": (3.2, 3.0, "U5 buck\n5.1 V"),
        "MIB": (3.2, 0.5, "MIB + U6\nPi Zero 2 W\ncamera · sensors"),
        "REED": (0.0, 8.8, "SW2 reed\n(under key dock)"),
        "HANDLE": (6.4, 11.4, "Handle: SW1 main\nswitch · J40 M12"),
        "MAST": (11.0, 11.4, "Masthead\nU9 GNSS · U10 LEDs"),
        "PODP": (15.2, 5.4, "Port pod\nJ50/P50 · M1"),
        "PODS": (15.2, 2.4, "Stbd pod\nJ51/P51 · M2"),
    }
    links = [
        ("PACK", "J3", "16 AWG\nW02/W03", "k", 0.5),
        ("J3", "PIB", "16 AWG\nW20", "k", 0.5),
        ("PIB", "U2", "16 AWG W22 BUS+\nW23 VBAT_S\n22 AWG W28 GND\n"
         "W33/34 rail sense\nC1 GPS lead\nW39/40 LED", "k", 0.45),
        ("PIB", "U3", "18 AWG W24 + XT30", "k", 0.45),
        ("PIB", "U4", "18 AWG W25 + XT30", "k", 0.72),
        ("U2", "U3", "TP1 DShot S1 ≤ 150", "#1f5fbf", 0.3),
        ("U2", "U4", "TP2 DShot S4 ≤ 150", "#1f5fbf", 0.5),
        ("PIB", "U5", "20 AWG W29\nvia F2", "k", 0.78),
        ("U5", "MIB", "20 AWG\nMicro-Fit J30/J31", "k", 0.5),
        ("MIB", "U2", "C9 UART (IF-04)", "#1f5fbf", 0.5),
        ("PIB", "HANDLE", "C3 8-core via G3\nC2 2-core via G4",
         "#8a3fbf", 0.62),
        ("HANDLE", "MAST", "C4 8-core in the tube", "#8a3fbf", 0.5),
        ("U3", "PODP", "C5 3-core\nvia G1", "#c0182a", 0.5),
        ("U4", "PODS", "C6 3-core\nvia G2", "#c0182a", 0.5),
        ("REED", "PIB", "W52/53 to J12", "#1f5fbf", 0.45),
    ]
    fig, ax = plt.subplots(figsize=(11, 7.4))
    for k, (x, y, lab) in blocks.items():
        ax.add_patch(FancyBboxPatch((x, y), 2.6, 1.5,
                                    boxstyle="round,pad=0.05",
                                    fc="#eef3fb" if k not in ("PODP",
                                                              "PODS",
                                                              "MAST",
                                                              "HANDLE")
                                    else "#fdf0ea", ec="#333"))
        ax.text(x + 1.3, y + 0.75, lab, ha="center", va="center",
                fontsize=7)
    for a, b, lab, c, t in links:
        xa, ya, _ = blocks[a]
        xb, yb, _ = blocks[b]
        pa = (xa + 1.3, ya + 0.75)
        pb = (xb + 1.3, yb + 0.75)
        ax.annotate("", xy=pb, xytext=pa,
                    arrowprops=dict(arrowstyle="-", color=c, lw=1.3,
                                    shrinkA=28, shrinkB=28))
        ax.text(pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1]),
                lab,
                fontsize=5.8, ha="center", va="center", color=c,
                bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.85))
    ax.add_patch(FancyBboxPatch((-0.3, 0.2), 14.2, 10.5,
                                boxstyle="round,pad=0.1", fill=False,
                                ls="--", ec="#888"))
    ax.text(0, 10.4, "inside the electronics box", fontsize=7,
            color="#666")
    ax.set_xlim(-0.6, 18.2)
    ax.set_ylim(0, 13.2)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def write_wirelist(path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wire", "net", "from", "to", "gauge", "length_mm",
                    "colour", "route", "cable", "note"])
        for x in DS.WIRES:
            if x.gauge == "-":
                continue
            w.writerow([x.id, x.net, x.a, x.b, x.gauge, x.length,
                        x.colour, x.route, x.cable, x.note])
