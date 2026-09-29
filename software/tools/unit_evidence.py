"""Collect the slice-3 evidence that does not need the simulator:
validator branch coverage and case count (VAL-006, MCN-D40), the
property-based run (SC-31), and the unit-suite totals.

    PYTHONPATH=. python tools/unit_evidence.py
Writes results/unit_evidence.json (read by tools/sitl_report.py).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*a):
    return subprocess.run([sys.executable, *a], cwd=ROOT, capture_output=True,
                          text=True)


def main():
    items = {}
    r = run("-m", "coverage", "run", "--branch",
            "--include=boaty/mcn/validator.py", "-m", "pytest", "-q",
            "tests/unit/test_validator.py")
    cases = r.stdout.strip().splitlines()[-1]
    rep = run("-m", "coverage", "json", "-o", "-")
    cov = json.loads(rep.stdout)["totals"]
    items["Validator suite (VAL-006, MCN-D40)"] = {
        "result": cases, "branch_coverage_pct": round(cov["percent_covered"],
                                                      1),
        "branches": cov["num_branches"],
        "missing_branches": cov["missing_branches"]}
    sys.path.insert(0, str(ROOT))
    import tests.unit.test_validator_property as prop
    prop.test_accepted_missions_never_cross_a_boundary()
    items["SC-31 property-based validator check"] = {
        "missions": prop.STATS["accepted"] + prop.STATS["rejected"],
        "accepted": prop.STATS["accepted"],
        "rejected": prop.STATS["rejected"],
        "closest_accepted_route_to_a_boundary_m":
            round(prop.STATS["min_clearance"], 3),
        "criterion": "no accepted route crosses a boundary; >= 2.9 m clear"}
    r = run("-m", "pytest", "-q", "tests/unit")
    items["Unit suite"] = r.stdout.strip().splitlines()[-1]
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "unit_evidence.json").write_text(json.dumps(
        {"generated": datetime.now(timezone.utc).isoformat(),
         "items": items}, indent=1))
    print(json.dumps(items, indent=1))


if __name__ == "__main__":
    main()
