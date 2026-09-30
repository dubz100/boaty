"""Write docs/budgets/power.csv, the boat's power budget (SSS-PWR PWR-D17).

    python3 docs/budgets/build_power.py

Loads come from the ADD (architecture.POWER_BOAT), the pack capacity from
the helm parameter baseline (BATT_CAPACITY, which is also the salvaged-cell
acceptance limit, PWR-D20). The build fails if the endurance at the cruise
load misses 40 min (PWR-009) with 30% margin (PWR-D17), or if usable energy
misses PWR-D18.
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
sys.path.insert(0, str(DOCS / "add" / "src"))
import architecture as A  # noqa: E402

PARM = DOCS.parent / "software" / "params" / "boaty-mk1.parm"
OUT = HERE / "power.csv"

CELLS, V_CELL, USABLE = 3, 3.6, 0.80
NEED_MIN, MARGIN, NEED_WH = 40.0, 0.30, 20.0   # PWR-009, PWR-D17, PWR-D18


def batt_capacity_ah() -> float:
    m = re.search(r"^BATT_CAPACITY\s+(\d+)", PARM.read_text(), re.M)
    return int(m.group(1)) / 1000


def budget() -> dict:
    loads = list(A.POWER_BOAT)
    total = sum(w for _, w in loads)
    ah = batt_capacity_ah()
    wh = CELLS * V_CELL * ah * USABLE
    minutes = wh / total * 60
    return dict(loads=loads, total_w=total, capacity_ah=ah, usable_wh=wh,
                endurance_min=minutes, margin=minutes / NEED_MIN - 1,
                before_rtl_min=minutes * 0.65)


def main() -> int:
    b = budget()
    rows = [["item", "watts", "source"]]
    rows += [[n, f"{w:.1f}", "ADD 7.2 (estimate; motors from the boat "
              "model, tests/unit/test_boat.py)"] for n, w in b["loads"]]
    rows += [["TOTAL at cruise (1.0 m/s)", f"{b['total_w']:.1f}", ""],
             ["pack capacity (Ah)", f"{b['capacity_ah']:.2f}",
              "BATT_CAPACITY = cell acceptance limit (PWR-D20)"],
             ["usable energy (Wh)", f"{b['usable_wh']:.1f}",
              f"{CELLS}S x {V_CELL} V x capacity x {USABLE:.0%}"],
             ["endurance at cruise (min)", f"{b['endurance_min']:.0f}",
              f"needs >= {NEED_MIN:.0f} (PWR-009)"],
             ["margin at 40 min", f"{b['margin']:.0%}",
              f"needs >= {MARGIN:.0%} (PWR-D17)"],
             ["cruise time before the 35% RTL (min)",
              f"{b['before_rtl_min']:.0f}", "FS-001; missions are <= 20 min "
              "(MIS-003)"]]
    with OUT.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    assert b["usable_wh"] >= NEED_WH, f"usable {b['usable_wh']:.1f} Wh " \
        f"< {NEED_WH} Wh (PWR-D18)"
    assert b["margin"] >= MARGIN, f"margin {b['margin']:.0%} < 30% (PWR-D17)"
    print(f"wrote {OUT.relative_to(DOCS.parent)}: {b['total_w']:.1f} W, "
          f"{b['usable_wh']:.1f} Wh, {b['endurance_min']:.0f} min "
          f"(margin {b['margin']:.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
