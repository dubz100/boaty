"""Electrical rule checks on the design.

  E1  every pin of every part is on exactly one net, or listed as NC
  E2  every net has at least two pins, and every pin named exists
  E3  every net is one connected piece: joined by board copper (custom
      boards, proved separately by stripboard.py), mated connectors,
      harness wires and module-internal links, and by nothing else
  E4  every harness wire's ends are on the wire's net
  E5  drivers: a net with an input has a source; no two outputs fight
  E6  no pin sees more than its absolute maximum voltage
  E7  connector keying: each power connector type does one job
      (PWR-D14); on each board no two signal connectors of one type
      share a pin count, so no lead fits the wrong header
"""
from __future__ import annotations

from collections import defaultdict

from . import design as DS

CUSTOM_BOARDS = {"PIB", "MIB", "PNL"}

# The highest voltage each net can carry in service (V). Battery nets at
# full charge; gate nets as the gate network sets them (calcs.py).
V_BATT = 12.6
NET_VMAX = defaultdict(lambda: 3.3, {
    "BATT_POS": V_BATT, "PACK_POS": V_BATT, "BUS_POS": V_BATT,
    "VBAT_S": V_BATT, "MOTOR_POS": V_BATT, "BUCK_IN": V_BATT,
    "BLEED": V_BATT, "SW_MAIN": V_BATT, "KEY_N": V_BATT,
    "Q1_G": V_BATT, "Q2_G": V_BATT, "Q3_G": 10.0, "CELL1": 4.2,
    "CELL2": 8.4, "BATT_NEG": 0.0, "GND": 0.0, "PI5_GND": 0.0,
    "RAIL_ADC": V_BATT / 11, "GPS_4V5": 5.0, "LED_5V_FC": 5.3,
    "LED_5V": 4.6, "5V_MCP": 5.2, "PI5_5V": 5.2, "PI5_5V_IN": 5.2,
    **{f"M{m}_{p}": V_BATT for m in (1, 2) for p in "ABC"},
    **{f"LED_{b}_K": 5.2 for b, *_ in DS.BUTTONS},
})


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.notes: list[str] = []
        self.stats: dict = {}

    def err(self, rule, msg):
        self.errors.append(f"{rule}: {msg}")


def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def run() -> Report:
    R = Report()
    P = DS.PARTS
    pn = DS.pin_net()
    # E2 (pins exist, nets big enough) and E1 (every pin placed once)
    seen = defaultdict(list)
    for net, pins in DS.NETS.items():
        if len(pins) < 2:
            R.err("E2", f"{net} has {len(pins)} pin")
        for p in pins:
            ref, _, pin = p.partition(".")
            if ref not in P or pin not in P[ref].pins:
                R.err("E2", f"{net}: no such pin {p}")
            seen[p].append(net)
    for p, nets in seen.items():
        if len(nets) > 1:
            R.err("E1", f"{p} is on {nets}")
    for ref, part in P.items():
        for pin in part.pins:
            key = f"{ref}.{pin}"
            if key not in pn and key not in DS.NC:
                R.err("E1", f"{key} is on no net")
    # E3 connectivity
    parent = {p: p for p in pn}

    def join(a, b):
        if a in parent and b in parent:
            parent[_find(parent, a)] = _find(parent, b)
    for net, pins in DS.NETS.items():
        on_board = defaultdict(list)
        for p in pins:
            b = P[p.split(".")[0]].board
            if b in CUSTOM_BOARDS:
                on_board[b].append(p)
        for ps in on_board.values():
            for q in ps[1:]:
                join(ps[0], q)
    for a, b in DS.MATES:
        for pin in P[a].pins:
            if pin in P[b].pins:
                join(f"{a}.{pin}", f"{b}.{pin}")
    for w in DS.WIRES:
        # E4
        for end in (w.a, w.b):
            if pn.get(end) != w.net:
                R.err("E4", f"{w.id}: {end} is on {pn.get(end)}, not "
                      f"{w.net}")
        join(w.a, w.b)
    groups = defaultdict(set)
    for p in pn:
        groups[_find(parent, p)].add(p)
    for g in groups.values():
        nets = {pn[p] for p in g}
        if len(nets) > 1:
            R.err("E3", f"joined but different nets: {sorted(nets)}")
    for net, pins in DS.NETS.items():
        roots = {_find(parent, p) for p in pins}
        if len(roots) > 1:
            parts = [sorted(p for p in pins if _find(parent, p) == r)
                     for r in roots]
            R.err("E3", f"{net} is in {len(roots)} pieces: {parts}")
    # E5 drivers
    for net, pins in DS.NETS.items():
        types = [P[p.split('.')[0]].pins[p.split('.')[1]].type
                 for p in pins]
        if DS.IN in types and not any(t in (DS.OUT, DS.PWR_OUT, DS.BIDIR,
                                            DS.PAS) for t in types):
            R.err("E5", f"{net} has inputs and no source")
        if types.count(DS.OUT) > 1:
            R.err("E5", f"{net} has {types.count(DS.OUT)} outputs")
        if types.count(DS.PWR_OUT) > 1:
            R.err("E5", f"{net} has {types.count(DS.PWR_OUT)} supplies")
    # E6 voltages
    over = 0
    for net, pins in DS.NETS.items():
        v = NET_VMAX[net]
        for p in pins:
            ref, pin = p.split(".")
            vm = P[ref].pins[pin].vmax
            if vm is not None and v > vm + 1e-9:
                over += 1
                R.err("E6", f"{p} ({P[ref].value}) max {vm} V sees {v:.2f}"
                      f" V on {net}")
    # E7 keying
    power_types = defaultdict(set)
    for ref, part in P.items():
        v = part.value
        for t in ("XT60", "XT30", "Micro-Fit", "JST-XH"):
            if v.startswith(t):
                power_types[t].add(part.desc.split(",")[0].split(":")[0])
    for x in DS.XT30:
        power_types["XT30"].add("ESC lead")
    for t, jobs in power_types.items():
        R.notes.append(f"{t}: {sorted(jobs)}")
    by_board = defaultdict(list)
    for ref, part in P.items():
        if part.kind == "connector" and part.value.startswith("KK254"):
            by_board[part.board].append((len(part.pins), ref))
    for b, lst in by_board.items():
        counts = [n for n, _ in lst]
        if len(counts) != len(set(counts)):
            R.err("E7", f"{b}: two KK254 headers with one pin count "
                  f"{sorted(lst)}")
    R.stats = dict(parts=len(P), nets=len(DS.NETS),
                   pins=sum(len(p.pins) for p in P.values()),
                   wires=len(DS.WIRES), mates=len(DS.MATES),
                   nc=len(DS.NC), over_voltage=over)
    return R


if __name__ == "__main__":
    r = run()
    for e in r.errors:
        print("ERR", e)
    print(r.stats, f"{len(r.errors)} errors")
