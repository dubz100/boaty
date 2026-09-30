"""The documentation baseline register (SDR RID-08).

One place that says which issue of each document is current. Every build
takes its own issue and its parents' issues from here instead of typing
them, so the documents cannot drift apart again. check() fails if a build
declares a different issue from the register, or types a parent issue by
hand in a parents / basis / references field. Mentions of older issues in
revision-history tables are history, and are left alone.

    python3 docs/common/baseline.py     # run the check

The baseline is frozen by an annotated git tag (TAG) once the owner signs
the SDR decision record. After that, any change goes through a numbered
change request, and the register is updated in the same commit.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1]
DATE = "30 September 2026"
TAG = "sdr-baseline-1"
STATUS = f"baselined, {TAG}"
COVER_STATUS = (f"Baselined at the System Design Review (tag {TAG}); "
                "changes only by change request")

# key: (document ID, title, issue)
REGISTER = {
    "CONCEPT": ("-", "Concept Selection Report", "v1.1"),
    "SRS": ("BOATY-SRS-001", "System Requirements Specification", "H"),
    "ADD": ("BOATY-ADD-001", "Architecture Design Document", "H"),
    "ICD": ("BOATY-ICD-001", "Interface Control Document", "H"),
    "SSS-HUL": ("BOATY-SSS-HUL", "Hull and structure", "B"),
    "SSS-PRP": ("BOATY-SSS-PRP", "Propulsion", "C"),
    "SSS-PWR": ("BOATY-SSS-PWR", "Power", "D"),
    "SSS-HLM": ("BOATY-SSS-HLM", "Helm", "F"),
    "SSS-MCP": ("BOATY-SSS-MCP", "Mission computer", "F"),
    "SSS-MCN": ("BOATY-SSS-MCN", "Mission Control", "F"),
    "SSS-REC": ("BOATY-SSS-REC", "Recovery and signalling", "B"),
    "SSS-SIM": ("BOATY-SSS-SIM", "Simulation and test", "G"),
    "FMEA": ("BOATY-FMEA-001", "Design FMEA", "G"),
    "OPS": ("BOATY-OPS-001", "Operations Manual", "E"),
    "KCL": ("BOATY-KCL-001", "Key Component List", "D"),
    "SDR": ("BOATY-SDR-001", "System Design Review", "D"),
}

# Detailed-design documents: registered so builds take their issue from
# here, but not part of the SDR baseline (they are CDR candidates).
DETAIL = {
    "MDD": ("BOATY-MDD-001", "Mechanical Design Description", "A"),
    "EDD": ("BOATY-EDD-001", "Electrical Design Description", "A"),
}
ALL = {**REGISTER, **DETAIL}


def letter(key: str) -> str:
    return ALL[key][2]


def issue(key: str, status: str = STATUS) -> str:
    """The ISSUE line a build prints, e.g. 'Issue H (baseline candidate,
    SDR)'."""
    return f"Issue {letter(key)} ({status})"


def ref(key: str) -> str:
    """Short reference, e.g. 'SRS Issue H'."""
    return f"{key} Issue {letter(key)}"


def full(key: str) -> str:
    """Full reference, e.g. 'BOATY-SRS-001 Issue H'."""
    doc = ALL[key][0]
    return f"{doc} Issue {letter(key)}" if doc != "-" else \
        f"{ALL[key][1]} {letter(key)}"


def refs(*keys: str) -> str:
    return ", ".join(ref(k) for k in keys)


def sss_all() -> str:
    return ", ".join(f"{k[4:]} {letter(k)}" for k in REGISTER
                     if k.startswith("SSS-"))


# ---------------------------------------------------------------- check
BUILDS = {
    "SRS": "srs/src/build_srs.py", "ADD": "add/src/build_add.py",
    "ICD": "icd/src/build_icd.py", "FMEA": "fmea/src/build_fmea.py",
    "OPS": "ops/src/build_ops.py", "KCL": "kcl/src/build_kcl.py",
    "SDR": "sdr/src/build_sdr.py", "MDD": "mdd/src/build_mdd.py",
    "EDD": "edd/src/build_edd.py",
}
# A typed issue letter in a field that names current parents.
TYPED = re.compile(r'(parents=|\["(Basis|Parent|Parents)",|\["\[\d\]",)'
                   r'[^\n]*Issue [A-Z]\b')


def check() -> list[str]:
    probs = []
    for key, path in BUILDS.items():
        src = (DOCS / path).read_text()
        if not re.search(r'^ISSUE = BL?\.issue\("' + re.escape(key) + r'"',
                         src, re.M):
            probs.append(f"{path}: ISSUE is not taken from the register")
    sss = (DOCS / "sss/src/sss_data.py").read_text()
    for key in REGISTER:
        if key.startswith("SSS-") and \
                f'issue=B.issue("{key}")' not in sss:
            probs.append(f"sss_data.py: {key} issue is not taken from the "
                         "register")
    for path in list(BUILDS.values()) + ["sss/src/sss_data.py",
                                         "sss/src/build_sss.py"]:
        for n, line in enumerate((DOCS / path).read_text().splitlines(), 1):
            if TYPED.search(line):
                probs.append(f"{path}:{n}: parent issue typed by hand: "
                             f"{line.strip()[:80]}")
    return probs


if __name__ == "__main__":
    p = check()
    for x in p:
        print("FAIL", x)
    print(f"baseline register: {len(REGISTER)} documents "
          f"(+{len(DETAIL)} detailed design), "
          f"{'consistent' if not p else f'{len(p)} problems'}")
    sys.exit(1 if p else 0)
