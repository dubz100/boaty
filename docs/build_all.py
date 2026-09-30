"""Rebuild every Boaty document in dependency order (SDR RID-08/RID-10).

    python3 docs/build_all.py

Each build runs its own checks (traceability, allocation, FMEA rules, the
VCRM, the baseline register) and stops on the first failure, so this is
also the documentation check CI runs on every push.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

DOCS = Path(__file__).resolve().parent

STEPS = [
    ("common", "baseline.py"),          # the register itself is consistent
    ("concept/src", "figures.py"), ("concept/src", "build_report.py"),
    ("srs/src", "figures.py"), ("srs/src", "build_srs.py"),
    ("add/src", "figures.py"), ("add/src", "build_add.py"),
    ("icd/src", "figures.py"), ("icd/src", "build_icd.py"),
    ("sss/src", "build_sss.py"),
    ("fmea/src", "build_fmea.py"),
    ("ops/src", "build_ops.py"),
    ("kcl/src", "build_kcl.py"),
    ("budgets", "build_power.py"),
    ("sdr/src", "build_sdr.py"),
]


def main() -> int:
    for folder, script in STEPS:
        path = DOCS / folder / script
        t0 = time.time()
        r = subprocess.run([sys.executable, script], cwd=path.parent,
                           capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or [""])[-1][:100]
        print(f"{'ok ' if r.returncode == 0 else 'FAIL'} {folder}/{script} "
              f"({time.time() - t0:.0f} s) {last}")
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-4000:], sep="\n")
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
