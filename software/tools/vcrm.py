"""Collect test evidence per SRS requirement for the VCRM (SDR RID-07).

    python3 tools/vcrm.py          # runs the unit tests (~50 s)

Writes results/vcrm_tests.json: one row per test that verifies at least one
requirement, with its outcome.

- Unit tests: run here; requirements from @pytest.mark.verifies(...).
- SITL tests: collected only (they take ~30 min); requirements from their
  verifies markers plus the refs in their evidence records, and the outcome
  from the last full run (results/sitl_results.json).

The SRS build (docs/srs/src/build_srs.py) turns this into the verification
cross-reference matrix and fails if a Must requirement due at the SIM stage
has no passing evidence and no declared open item.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
REQ = re.compile(r"^[A-Z]{2,4}-\d{3}$")


class Collector:
    def __init__(self):
        self.rows: dict[str, dict] = {}

    def pytest_collection_modifyitems(self, items):
        for it in items:
            ids = [i for m in it.iter_markers("verifies") for i in m.args]
            self.rows[it.nodeid] = dict(nodeid=it.nodeid, verifies=ids,
                                        outcome=None)

    def pytest_runtest_logreport(self, report):
        r = self.rows.get(report.nodeid)
        if r is None:
            return
        if report.when == "call" or (report.when == "setup" and
                                     report.outcome != "passed"):
            r["outcome"] = report.outcome


def run(args: list[str]) -> dict[str, dict]:
    c = Collector()
    code = pytest.main(args + ["-q", "-p", "no:cacheprovider"], plugins=[c])
    if code not in (0, 5) and "--collect-only" not in args:
        print(f"pytest exit {code}", file=sys.stderr)
    return c.rows


def main() -> int:
    unit = run([str(ROOT / "tests" / "unit")])
    sitl = run([str(ROOT / "tests" / "sitl"), "--collect-only"])
    res = json.loads((RESULTS / "sitl_results.json").read_text())
    by_node = {r["nodeid"]: r for r in res["records"]}
    rows = []
    for nid, r in unit.items():
        if r["verifies"]:
            rows.append(dict(kind="unit", nodeid=nid, verifies=r["verifies"],
                             outcome=r["outcome"] or "not run"))
    for nid, r in sitl.items():
        rec = by_node.get(nid) or by_node.get(
            nid.replace("software/", "")) or {}
        refs = [x for x in rec.get("refs", []) if REQ.match(x)]
        ids = sorted(set(r["verifies"]) | set(refs))
        if not ids:
            continue
        out = rec.get("outcome") or "not run"
        rows.append(dict(kind="sitl", nodeid=nid, id=rec.get("id"),
                         verifies=ids, outcome=out))
    out = dict(generated=datetime.now(timezone.utc).isoformat(),
               sitl_run=res.get("generated"), rows=rows)
    (RESULTS / "vcrm_tests.json").write_text(json.dumps(out, indent=1))
    n = len({i for r in rows for i in r["verifies"]})
    print(f"wrote results/vcrm_tests.json: {len(rows)} tests covering {n} "
          "requirement IDs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
