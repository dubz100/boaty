"""Run the IF-11 evaluation set against the live Claude API.

    PYTHONPATH=. python tools/nli_eval.py [--limit N]

Needs the API key in ~/.config/boaty/anthropic_api_key (mode 0600) or the
file named by BOATY_KEY_FILE. Writes results/nli_eval.json with, per case:
outcome, whether it passed, time to a validated plan (NLI-007), request ID
and token usage. Pass criteria (ICD IF-11): 100 % schema-valid, every
must-decline declined, plan shown <= 20 s.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from boaty.mcn.llm import IntentClient
from boaty.mcn.planning import Planning
from boaty.mcn.site import Site

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    data = json.loads((ROOT / "tests/data/nli_eval.json").read_text())
    site = Site.named(data["site"])
    rows = []
    llm_log = []
    p = Planning(site, IntentClient(log=lambda k, **kw: llm_log.append(kw)))
    for c in data["cases"][: a.limit or None]:
        t0 = time.monotonic()
        now = datetime.now(timezone.utc).isoformat()
        out = p.from_text(c["text"], source="text", now_utc=now)
        dt = time.monotonic() - t0
        if c["expect"] == "plan":
            ops = {s.op for s in []}
            passed = out.ok
        else:
            passed = (not out.ok) and out.attempts[-1:] in (["declined"],
                                                            ["refused"])
        rows.append(dict(id=c["id"], text=c["text"], expect=c["expect"],
                         attempts=out.attempts, ok=out.ok, passed=passed,
                         seconds=round(dt, 2), child=out.child,
                         adult=out.adult,
                         llm=llm_log[-len(out.attempts):] if out.attempts
                         else []))
        print(f"{c['id']} {'PASS' if passed else 'FAIL'} {dt:5.1f}s "
              f"{out.attempts} {out.child[:60]}")
    n = len(rows)
    times = sorted(r["seconds"] for r in rows)
    summary = dict(cases=n, passed=sum(r["passed"] for r in rows),
                   schema_valid=sum("invalid" not in r["attempts"]
                                    for r in rows),
                   p95_s=times[int(0.95 * (n - 1))] if n else None)
    print(summary)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/nli_eval.json").write_text(json.dumps(
        dict(generated=datetime.now(timezone.utc).isoformat(),
             summary=summary, rows=rows), indent=1))


if __name__ == "__main__":
    main()
