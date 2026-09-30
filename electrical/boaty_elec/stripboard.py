"""Stripboard layouts for the three custom boards, proved against the
netlist.

Strips run along the rows (0.1" pitch). Each part sits in its own
column(s) with its pins down the column. The router then
  1. cuts a strip wherever two pins of different nets share it (at a free
     hole between them; a knife cut between holes when they are adjacent),
  2. joins the pieces of each net with wire links between free holes,
and verify() rebuilds the connectivity from the strips, cuts, links and
pins alone and compares it with design.NETS for that board: every net's
pins joined, no two nets touching.

High-current nets (HEAVY) must sit on one strip piece with no links: the
piece is reinforced with 1.5 mm² tinned copper soldered along it.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from . import design as DS

HEAVY = {"PACK_POS", "BUS_POS", "VBAT_S", "MOTOR_POS"}

# footprints: pin name -> (dcol, drow). Parts stand in a column.
TO220 = {"G": (0, 0), "D": (0, 1), "S": (0, 2)}
TO92 = {"S": (0, 0), "G": (0, 1), "D": (0, 2)}


def line(n):
    return {str(i + 1): (0, i) for i in range(n)}


def pins2(a, ra, b, rb):
    """A two-lead part in one column: pin a at row offset ra, b at rb."""
    return {a: (0, ra), b: (0, rb)}


def header40(odd_right: bool = True):
    """2×20 header standing across the strips: pins 2i+1 and 2i+2 share
    a row (a knife cut between them), one side feeds each way."""
    fp = {}
    for i in range(20):
        fp[str(2 * i + 1)] = (1 if odd_right else 0, i)
        fp[str(2 * i + 2)] = (0 if odd_right else 1, i)
    return fp


PAD = {"1": (0, 0)}


def _pnl_parts():
    parts = [("J60", 3, 2, header40(odd_right=True))]
    for i in range(4):
        c = 7 + 9 * i
        parts += [
            (f"R{61 + 10 * i}", c, 2, pins2("1", 0, "2", 4)),     # 3V3→SW
            (f"R{62 + 10 * i}", c + 1, 6, pins2("1", 0, "2", 3)),  # SW→BTN
            (f"C{61 + i}", c + 2, 9, pins2("1", 0, "2", 2)),       # BTN→GND
            (f"E6{i}a", c + 3, 6, pins2("1", 0, "2", 1)),          # SW, GND
            (f"R{63 + 10 * i}", c + 4, 12, pins2("1", 0, "2", 4)),  # LED→G
            (f"R{64 + 10 * i}", c + 5, 16, pins2("1", 0, "2", 1)),  # G→GND
            (f"Q{61 + i}", c + 6, 15, {"D": (0, 0), "G": (0, 1),
                                       "S": (0, 2)}),
            (f"E6{i}b", c + 7, 14, pins2("1", 0, "2", 1)),         # 5V, K
        ]
    return parts


# Row plans: each strip row carries one net where it can, so most pins
# meet on the copper and links are few.
LAYOUT = {
    "PIB": dict(cols=42, rows=18, parts=[
        # A. main switch. r1 Q1_G, r2 BUS_POS, r3 PACK_POS, r5 SW_MAIN,
        #    r6 GND
        ("Q1", 1, 1, TO220), ("E2", 3, 2, PAD), ("E1", 3, 3, PAD),
        ("R1", 5, 1, pins2("2", 0, "1", 2)),
        ("D1", 6, 1, pins2("A", 0, "K", 2)),
        ("C1", 7, 1, pins2("2", 0, "1", 1)),
        ("R2", 8, 1, pins2("1", 0, "2", 4)),
        ("D2", 9, 2, pins2("K", 0, "A", 4)),
        ("J11", 11, 5, line(2)),
        # B. key switch. r1 Q2_G, r2 MOTOR_POS, r3 VBAT_S, r4 KEY_N,
        #    r5 (J12 pin 2, not fitted), r6 GND
        ("Q2", 13, 1, TO220), ("E4", 15, 2, PAD), ("E3", 15, 3, PAD),
        ("R3", 17, 1, pins2("2", 0, "1", 2)),
        ("D3", 18, 1, pins2("A", 0, "K", 2)),
        ("C2", 19, 1, pins2("2", 0, "1", 1)),
        ("R4", 20, 1, pins2("1", 0, "2", 3)),
        ("D5", 21, 2, pins2("K", 0, "A", 4)),
        ("J12", 23, 4, line(3)),
        # C. bleeder, rail sense, buck feed. r7 Q3_G, r8 BLEED, r9 GND,
        #    r5 RAIL_ADC, r4 BUCK_IN (right of the KEY_N cut)
        ("C3", 25, 4, pins2("1", 0, "2", 3)), ("Q3", 27, 7, TO220),
        ("R5", 29, 7, pins2("1", 0, "2", 2)),
        ("D4", 30, 7, pins2("K", 0, "A", 2)),
        ("R9", 32, 2, pins2("1", 0, "2", 6)),
        ("R6", 34, 2, pins2("1", 0, "2", 3)),
        ("R7", 35, 5, pins2("1", 0, "2", 1)),
        ("C4", 36, 5, pins2("1", 0, "2", 1)),
        ("E7", 37, 5, PAD), ("E6", 37, 6, PAD),
        ("F2", 39, 3, pins2("1", 0, "2", 1)), ("E5", 40, 4, PAD),
        # D. mast junction: J14 and J15 share rows 8-13 pin for pin;
        #    r14 LED_5V, r15 LED_DIN, r16 LED_5V_FC, r17 LED_DATA_FC
        ("J14", 1, 8, line(8)), ("J15", 3, 8, line(6)),
        ("D6", 5, 14, pins2("K", 0, "A", 2)),
        ("R8", 6, 15, pins2("2", 0, "1", 2)),
        ("E8", 7, 16, PAD), ("E9", 8, 17, PAD),
    ]),
    # Pi Zero footprint (30 × 61 mm): header down the middle, odd pins
    # feed left, even pins right
    "MIB": dict(cols=12, rows=24, parts=[
        ("J32", 5, 2, header40(odd_right=False)),
        # right: r2 5V (pin 2), r3 5V (pin 4), r4 GND (pin 6),
        #        r5 Pi TXD (pin 8), r6 Pi RXD (pin 10)
        ("D10", 7, 2, pins2("K", 0, "A", 2)),
        ("C10", 8, 2, pins2("+", 0, "-", 2)),
        ("C11", 9, 2, pins2("1", 0, "2", 2)),
        ("J31", 11, 2, pins2("1", 0, "2", 2)),
        ("J33", 11, 5, line(3)),
        # left: r2 3V3 (pin 1), r5 DQ (pin 7), r6 GND (pin 9),
        #       r7 GPIO17 (pin 11)
        ("R10", 3, 2, pins2("1", 0, "2", 3)),
        ("R12", 4, 2, pins2("1", 0, "2", 5)),
        ("C12", 2, 6, pins2("2", 0, "1", 1)),
        ("R11", 1, 7, pins2("2", 0, "1", 4)),
        ("J35", 0, 11, line(2)),
        ("J34", 3, 13, line(4)),
    ]),
    "PNL": dict(cols=44, rows=24, parts=_pnl_parts()),
}


@dataclass
class Layout:
    board: str
    cols: int
    rows: int
    pins: dict = field(default_factory=dict)      # (c, r) -> (ref.pin, net)
    bodies: dict = field(default_factory=dict)    # ref -> list of holes
    cuts: list = field(default_factory=list)      # (c, r, kind)
    links: list = field(default_factory=list)     # ((c, r), (c, r), net)
    errors: list = field(default_factory=list)
    segs: dict = field(default_factory=dict)      # r -> [(c0, c1)]


def build(board: str) -> Layout:
    spec = LAYOUT[board]
    L = Layout(board, spec["cols"], spec["rows"])
    pn = DS.pin_net()
    for ref, c0, r0, fp in spec["parts"]:
        holes = []
        for pin, (dc, dr) in fp.items():
            c, r = c0 + dc, r0 + dr
            key = f"{ref}.{pin}"
            net = pn.get(key)
            if net is None:
                net = f"~{key}"               # unused header pin
            if not (0 <= c < L.cols and 0 <= r < L.rows):
                L.errors.append(f"{key} off the board at {(c, r)}")
            if (c, r) in L.pins:
                L.errors.append(f"{key} and {L.pins[(c, r)][0]} share "
                                f"hole {(c, r)}")
            L.pins[(c, r)] = (key, net)
            holes.append((c, r))
        L.bodies[ref] = holes
    # every board pin in the netlist must be placed
    placed = {v[0] for v in L.pins.values()}
    for ref, p in DS.PARTS.items():
        if p.board == board:
            for pin in p.pins:
                k = f"{ref}.{pin}"
                if k in pn and k not in placed:
                    L.errors.append(f"{k} not placed")
    _cut(L)
    _route(L)
    return L


def _cut(L: Layout):
    for r in range(L.rows):
        row = sorted((c, net) for (c, rr), (_k, net) in L.pins.items()
                     if rr == r)
        cuts = []
        for (c1, n1), (c2, n2) in zip(row, row[1:]):
            if n1 == n2:
                continue
            free = [c for c in range(c1 + 1, c2)
                    if (c, r) not in L.pins]
            if free:
                cc = free[len(free) // 2]
                cuts.append((cc, "hole"))
            else:
                cuts.append((c1 + 0.5, "knife"))
        L.cuts += [(c, r, k) for c, k in cuts]
        edges = [-0.5] + [c for c, _ in cuts] + [L.cols - 0.5]
        segs = []
        for a, b in zip(edges, edges[1:]):
            lo = int(a) + 1 if a == int(a) else int(a + 0.5)
            hi = int(b) - 1 if b == int(b) else int(b - 0.5)
            if a < 0:
                lo = 0
            if b >= L.cols - 0.5:
                hi = L.cols - 1
            if lo <= hi:
                segs.append((lo, hi))
        L.segs[r] = segs


def _seg_of(L: Layout, c, r):
    for i, (a, b) in enumerate(L.segs[r]):
        if a <= c <= b:
            return (r, i)
    return None


def _route(L: Layout):
    used = set(L.pins) | {(int(c), r) for c, r, k in L.cuts if k == "hole"}
    seg_net = {}
    for (c, r), (_k, net) in L.pins.items():
        s = _seg_of(L, c, r)
        seg_net.setdefault(s, net)
    by_net = defaultdict(list)
    for s, net in seg_net.items():
        by_net[net].append(s)
    for net, segs in by_net.items():
        if net.startswith("~") or len(segs) < 2:
            continue
        if net in HEAVY:
            L.errors.append(f"heavy net {net} is in {len(segs)} strip "
                            "pieces: it needs one reinforced piece")
        # star from the piece with the most free holes (the hub), each
        # other piece by its nearest free-hole pair; fall back to any
        # piece already joined if the hub runs out of holes
        segs = sorted(segs, key=lambda sg: -len(_free(L, sg, used)))
        joined = [segs[0]]
        for sg in sorted(segs[1:], key=lambda x: len(_free(L, x, used))):
            best = None
            for t in joined:
                for ha in _free(L, sg, used):
                    for hb in _free(L, t, used):
                        d = abs(ha[0] - hb[0]) + abs(ha[1] - hb[1])
                        if best is None or d < best[0]:
                            best = (d, ha, hb)
                if best is not None and t is segs[0]:
                    break
            if best is None:
                L.errors.append(f"{net}: no free hole to link a piece")
                continue
            _, ha, hb = best
            L.links.append((ha, hb, net))
            used |= {ha, hb}
            joined.append(sg)


def _free(L, seg, used):
    r, i = seg
    a, b = L.segs[r][i]
    return [(c, r) for c in range(a, b + 1) if (c, r) not in used]


def verify(L: Layout) -> list[str]:
    """Rebuild connectivity from copper, cuts, links and pins alone."""
    errs = list(L.errors)
    parent = {}

    def f(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def u(a, b):
        parent[f(a)] = f(b)
    for r, segs in L.segs.items():
        for c0, c1 in segs:
            for c in range(c0, c1):
                u((c, r), (c + 1, r))
    for a, b, _n in L.links:
        u(a, b)
    comp_nets = defaultdict(set)
    net_comps = defaultdict(set)
    for (c, r), (_k, net) in L.pins.items():
        comp_nets[f((c, r))].add(net)
        net_comps[net].add(f((c, r)))
    for comp, nets in comp_nets.items():
        if len(nets) > 1:
            errs.append(f"short: {sorted(nets)}")
    for net, comps in net_comps.items():
        if len(comps) > 1:
            errs.append(f"open: {net} in {len(comps)} pieces")
    # the board's view must equal the netlist restricted to the board
    pn = DS.pin_net()
    for (c, r), (k, net) in L.pins.items():
        if not net.startswith("~") and pn.get(k) != net:
            errs.append(f"{k} laid on {net}, netlist says {pn.get(k)}")
    return errs


def stats(L: Layout) -> dict:
    return dict(board=L.board, size=f"{L.cols} × {L.rows} holes "
                f"({L.cols * 2.54:.0f} × {L.rows * 2.54:.0f} mm)",
                parts=len(L.bodies), cuts=len(L.cuts),
                knife=sum(k == "knife" for *_x, k in L.cuts),
                links=len(L.links),
                heavy=sorted({n for _k, n in L.pins.values()} & HEAVY))


def draw(L: Layout, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    s = 0.34
    fig, ax = plt.subplots(figsize=(L.cols * s + 1.2, L.rows * s + 1.0))
    ax.add_patch(Rectangle((-0.6, -0.6), L.cols + 0.2, L.rows + 0.2,
                           color="#e9dcc0", zorder=0))
    heavy_rows = set()
    for (c, r), (_k, net) in L.pins.items():
        if net in HEAVY:
            heavy_rows.add((r, _seg_of(L, c, r)))
    for r, segs in L.segs.items():
        for i, (a, b) in enumerate(segs):
            hv = any(h[1] == (r, i) for h in heavy_rows)
            ax.add_patch(Rectangle((a - 0.42, r - 0.3), b - a + 0.84, 0.6,
                                   color="#c9853e" if hv else "#dca46a",
                                   zorder=1))
            if hv:
                ax.plot([a, b], [r, r], color="#8a8a8a", lw=3.2, zorder=2)
    for c in range(L.cols):
        for r in range(L.rows):
            ax.plot(c, r, "o", ms=1.6, color="#5a4630", zorder=3)
    for c, r, k in L.cuts:
        ax.plot(c, r, marker="x", ms=6, mew=1.6, color="#c0182a", zorder=6)
    for (a, b, net) in L.links:
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#1f5fbf", lw=1.3,
                zorder=5, alpha=0.9)
    for ref, holes in L.bodies.items():
        cs = [h[0] for h in holes]
        rs = [h[1] for h in holes]
        ax.add_patch(Rectangle((min(cs) - 0.3, min(rs) - 0.3),
                               max(cs) - min(cs) + 0.6,
                               max(rs) - min(rs) + 0.6, fill=False,
                               ec="#222", lw=0.9, zorder=7))
        for h in holes:
            ax.plot(*h, "s", ms=3.2, color="#222", zorder=8)
        lab = ref if not ref.startswith("E") else DS.PARTS[ref].pins[
            "1"].label if len(holes) == 1 else ref
        ax.text(min(cs) + 0.1, min(rs) - 0.45, ref if len(lab) > 8 else
                lab, fontsize=5.5, zorder=9, ha="left", va="bottom",
                rotation=0)
    ax.set_xlim(-1, L.cols)
    ax.set_ylim(L.rows, -1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{L.board}: component side. Strips run left-right. "
                 "x = strip cut, blue = wire link, grey = 1.5 mm² "
                 "reinforcement", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def run() -> dict:
    out = {}
    for b in LAYOUT:
        L = build(b)
        out[b] = dict(layout=L, errors=verify(L), stats=stats(L))
    return out


if __name__ == "__main__":
    for b, r in run().items():
        print(b, r["stats"], len(r["errors"]), "errors")
        for e in r["errors"][:20]:
            print("   ", e)
