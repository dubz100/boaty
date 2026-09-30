"""The facts the SDR report quotes, computed from a copy of the repository.

    python3 snapshot.py <repo root> [out.json]

The review sections (2-7, Appendix A) quote the baseline as it was reviewed
at commit 88b1cd7, so they read review_snapshot.json, made by running this
against a checkout of that commit:

    git worktree add /tmp/sdr-review 88b1cd7
    python3 docs/sdr/src/snapshot.py /tmp/sdr-review \\
        docs/sdr/src/review_snapshot.json

Section 10 (status at the freeze) runs it against the working tree. It runs
as its own process so two versions of the document modules never meet.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


def facts(root: Path) -> dict:
    docs = root / "docs"
    for sub in ("common", "srs/src", "add/src", "sss/src", "fmea/src",
                "kcl/src"):
        sys.path.insert(0, str(docs / sub))
    import fmea_data as F
    import kcl_data as K
    import requirements as R
    import sss_data as SD

    def after(r):
        return F.rpn_after(r) if r[0] in F.POST else F.rpn(r)

    reqs = [dict(id=r["id"], pri=r["pri"], stage=r["stage"],
                 text=re.sub(r"<[^>]+>", "", r["text"]))
            for r in R.all_reqs()]
    derived = sum(len(list(SD.all_derived(SD.SUBSYSTEMS[s])))
                  for s in SD.ORDER)
    bom = K.check()
    res = root / "software" / "results"
    sitl = json.loads((res / "sitl_results.json").read_text())
    nli = json.loads((res / "nli_eval.json").read_text())["summary"]
    parm = "\n".join(p.read_text() for p in
                     (root / "software" / "params").glob("*.parm"))
    try:
        out = subprocess.run([sys.executable, "-m", "pytest",
                              "--collect-only", "-q", "tests/unit"],
                             cwd=root / "software", capture_output=True,
                             text=True, timeout=180).stdout
        m = re.search(r"(\d+) tests? collected", out)
        unit = int(m.group(1)) if m else None
    except (OSError, subprocess.TimeoutExpired):
        unit = None
    return dict(
        commit=subprocess.run(["git", "-C", str(root), "rev-parse",
                               "--short", "HEAD"], capture_output=True,
                              text=True).stdout.strip(),
        reqs=reqs, n_derived=derived,
        tests=[list(t[:5]) + [sorted(t[5])] for t in SD.TESTS],
        results={k: v for k, v in SD.SIM_RESULTS.items()},
        tbds=len(R.TBDS),
        tbds_open=sum("Closed" not in t[1] for t in R.TBDS),
        bom_total=bom["total"], cap=K.CAP, watt=bom["watt"],
        fm_rows=[[r[0], r[5], F.rpn(r), after(r)] for r in F.ROWS],
        fm_actions=len(F.ACTIONS),
        fm_residual=[x[0] for x in F.RESIDUAL],
        sitl_outcomes=dict(Counter(r["outcome"] for r in sitl["records"])),
        sitl_records=len(sitl["records"]),
        sitl_ardupilot=sitl.get("ardupilot_commit"),
        unit_tests=unit, nli=nli,
        has_oa=bool(re.search(r"^OA_TYPE", parm, re.M)),
        has_hdop_gate=bool(re.search(r"^GPS_HDOP_GOOD", parm, re.M)),
        has_ci=(root / ".github" / "workflows").exists(),
        has_power_csv=(docs / "budgets" / "power.csv").exists(),
        has_lock=(root / "software" / "requirements.lock").exists(),
        has_register=(docs / "common" / "baseline.py").exists(),
    )


def load(root: Path) -> dict:
    """facts(root) computed in a separate process."""
    out = subprocess.run([sys.executable, __file__, str(root)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


if __name__ == "__main__":
    f = facts(Path(sys.argv[1]).resolve())
    text = json.dumps(f, indent=1, sort_keys=True)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(text + "\n")
    else:
        print(text)
