"""Type-check ratchet for CI (SWE-007, SDR RID-10).

    python3 tools/mypy_ratchet.py            # check
    python3 tools/mypy_ratchet.py --update   # accept the current counts

mypy runs over the boaty package. The safety-critical modules must be
clean. Everywhere else the error count per file may only go down: CI fails
if any file has more errors than in tools/mypy_baseline.json. When a file
improves, --update records the lower count.

Run it in the locked environment (pip install -r requirements.lock), as CI
does: mypy's findings depend on which libraries it can see (pydantic in
particular), so a standalone mypy gives different counts.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "mypy_baseline.json"
MUST_BE_CLEAN = [
    "boaty/mcn/validator.py",      # the only way to make a mission (SAF-004)
    "boaty/mcn/helm_guard.py",     # C7: parameter, fence and GCS checks
    "boaty/mcn/session.py",        # arming, approval, failsafe handling
    "boaty/mcp/events.py",         # IF-04 event vocabulary
    "boaty/mcp/policy.py",         # boat-service command filter (MCP-D19)
]


def counts() -> Counter:
    import importlib.util
    import shutil
    cmd = [sys.executable, "-m", "mypy"] if importlib.util.find_spec("mypy") \
        else [shutil.which("mypy") or "mypy"]
    out = subprocess.run(cmd + ["boaty"], cwd=ROOT, capture_output=True,
                         text=True).stdout
    c: Counter = Counter()
    for line in out.splitlines():
        m = re.match(r"^(boaty/[^:]+):\d+: error:", line)
        if m:
            c[m.group(1)] += 1
    return c


def main() -> int:
    now = counts()
    if "--update" in sys.argv:
        BASELINE.write_text(json.dumps(dict(sorted(now.items())), indent=1)
                            + "\n")
        print(f"baseline: {sum(now.values())} errors in {len(now)} files")
        return 0
    base = json.loads(BASELINE.read_text())
    bad = [f"{f}: {now[f]} errors (must be clean)" for f in MUST_BE_CLEAN
           if now.get(f)]
    bad += [f"{f}: {n} errors (baseline {base.get(f, 0)})"
            for f, n in sorted(now.items())
            if f not in MUST_BE_CLEAN and n > base.get(f, 0)]
    better = [f for f, n in base.items() if now.get(f, 0) < n]
    print(f"mypy: {sum(now.values())} errors (baseline "
          f"{sum(base.values())}); safety modules clean: "
          f"{not any(now.get(f) for f in MUST_BE_CLEAN)}")
    if better:
        print("improved (run --update to lock in):", ", ".join(better))
    for b in bad:
        print("FAIL", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
