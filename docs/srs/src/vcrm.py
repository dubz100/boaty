"""Build the verification cross-reference matrix (VCRM) from its sources.

Sources: requirements.py (what and when), software/results/vcrm_tests.json
(tagged unit tests and SITL evidence records, with outcomes), the SSS-SIM
catalogue results, and verification.py (other evidence and open items).
Used by the SRS build (appendix and check) and the SDR report.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
for p in (DOCS / "add" / "src", DOCS / "sss" / "src", HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import requirements as REQ  # noqa: E402
import verification as V  # noqa: E402

TESTS_JSON = DOCS.parent / "software" / "results" / "vcrm_tests.json"


def _catalogue():
    """Catalogue test ID -> (result, traced IDs), SIM tests only."""
    import sss_data as SD
    return {t[0]: (SD.SIM_RESULTS.get(t[0]), set(t[5])) for t in SD.TESTS
            if t[1] == "SIM"}


def build() -> list[dict]:
    tests = json.loads(TESTS_JSON.read_text())["rows"] \
        if TESTS_JSON.exists() else []
    cat = _catalogue()
    out = []
    for r in REQ.all_reqs():
        rid = r["id"]
        unit = [t for t in tests if t["kind"] == "unit"
                and rid in t["verifies"]]
        sitl = [t for t in tests if t["kind"] == "sitl"
                and rid in t["verifies"]]
        cats = sorted(c for c, (res, tr) in cat.items() if rid in tr)
        ev, ok, bad = [], False, []
        if unit:
            n_pass = sum(t["outcome"] == "passed" for t in unit)
            ev.append(f"{n_pass}/{len(unit)} unit tests")
            ok |= n_pass > 0
            bad += [t["nodeid"] for t in unit if t["outcome"] == "failed"]
        if sitl:
            ids = sorted({t.get("id") or t["nodeid"].split("::")[-1]
                          for t in sitl})
            passed = [t for t in sitl if t["outcome"] in ("passed", "xpass")]
            ev.append("SITL " + ", ".join(ids))
            ok |= bool(passed)
            bad += [t["nodeid"] for t in sitl if t["outcome"] == "failed"]
        cat_pass = [c for c in cats if (cat[c][0] or "").startswith("Pass")]
        if cats:
            ev.append("catalogue " + ", ".join(cats))
            ok |= bool(cat_pass)
        if rid in V.OTHER:
            m, what, st = V.OTHER[rid]
            ev.append(f"{m}: {what}")
            ok |= st == "Met"
        op = V.OPEN.get(rid)
        if bad:
            status = "FAIL"
        elif ok and op:
            status = f"Partly; open to {op[1]}"
        elif ok and r["stage"] != "SIM":
            status = f"Sim evidence; confirm at {r['stage']}"
        elif ok:
            status = "Verified"
        elif op:
            status = f"Open to {op[1]}"
        elif r["stage"] != "SIM":
            status = f"Planned ({r['stage']})"
        else:
            status = "GAP"
        out.append(dict(id=rid, pri=r["pri"], ver=r["ver"], stage=r["stage"],
                        evidence=ev, open=op[0] if op else None,
                        status=status, failing=bad))
    return out


def check(rows: list[dict]) -> list[str]:
    """Problems that must stop the build: failing evidence anywhere, and
    Must requirements due at SIM with neither evidence nor an open item."""
    probs = [f"{r['id']}: failing {r['failing']}" for r in rows
             if r["status"] == "FAIL"]
    probs += [f"{r['id']}: Must, SIM stage, no evidence and not declared "
              "open" for r in rows if r["status"] == "GAP"
              and r["pri"] == "M"]
    return probs
