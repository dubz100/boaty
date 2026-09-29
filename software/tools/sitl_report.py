"""Turn results/sitl_results.json into results/SITL_REPORT.md.

Run after:  python3 -m pytest tests/sitl
Then:       python3 tools/sitl_report.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
ICON = {"passed": "PASS", "failed": "FAIL", "error": "ERROR",
        "xfail": "KNOWN GAP", "xpass": "PASS (known gap not seen)",
        "skipped": "SKIP", None: "NOT RUN"}


def fmt(v):
    if isinstance(v, dict):
        return "; ".join(f"{k}={fmt(x)}" for k, x in v.items()) or "-"
    if isinstance(v, list):
        return "; ".join(str(x) for x in v) or "-"
    return "-" if v is None else str(v)


def main() -> int:
    data = json.loads((RES / "sitl_results.json").read_text())
    recs = sorted(data["records"], key=lambda r: (r["id"] or "zz"))
    n = {k: sum(1 for r in recs if r["outcome"] == k)
         for k in ("passed", "failed", "error", "xfail", "xpass")}
    out = ["# Boaty simulator results (slices 1-3)", "",
           f"Generated {data['generated']} from `results/sitl_results.json`. "
           f"ArduPilot Rover 4.7.1 SITL on the Boaty boat model, "
           f"speed-up {data['speedup']}x.", "",
           f"**{n['passed'] + n['xpass']} passed, {n['xfail']} known gaps "
           f"(requirement not met natively; finding recorded), "
           f"{n['failed']} failed, {n['error']} errors** out of {len(recs)} "
           "scenarios.", "",
           "| ID | Scenario | Result | Criterion | Refs |",
           "|---|---|---|---|---|"]
    for r in recs:
        out.append(f"| {r['id']} | {r['title']} | **{ICON[r['outcome']]}** "
                   f"| {r['criterion']} | {', '.join(r['refs'])} |")
    out += ["", "## Evidence", ""]
    for r in recs:
        out += [f"### {r['id']}: {r['title']} ({ICON[r['outcome']]})", ""]
        for k, v in r["measured"].items():
            out.append(f"- `{k}`: {fmt(v)}")
        for note in r["notes"]:
            out.append(f"- Note: {note}")
        if r.get("known_finding"):
            out.append(f"- **Known gap:** {r['known_finding']}")
        if r.get("failure"):
            out.append(f"- Failure: `{r['failure'].splitlines()[0][:300]}`")
        out.append("")
    ue = RES / "unit_evidence.json"
    if ue.exists():
        u = json.loads(ue.read_text())
        out += ["## Unit-level evidence (no simulator)", "",
                f"Generated {u['generated']} by `tools/unit_evidence.py`.", ""]
        for k, v in u["items"].items():
            out.append(f"- **{k}**: {fmt(v)}")
        out.append("")
    (RES / "SITL_REPORT.md").write_text("\n".join(out))
    print(f"wrote {RES / 'SITL_REPORT.md'}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
