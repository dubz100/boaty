"""Build BOATY-SDR-001: System Design Review (SDR / PDR) report.

The review is written as an independent assessment of the system
documentation baseline. The counts it quotes are computed from the
same source data the other documents are built from, so re-running
the build after gaps are closed updates the compliance picture.

Run:  python3 docs/sdr/src/build_sdr.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parents[1]
ROOT = DOCS.parent
for sub in ("common", "srs/src", "add/src", "sss/src", "fmea/src",
            "kcl/src"):
    sys.path.insert(0, str(DOCS / sub))

import fmea_data as F  # noqa: E402
import kcl_data as K  # noqa: E402
import requirements as R  # noqa: E402
import sss_data as SD  # noqa: E402
from pdfdoc import (ORANGE, ORANGE_T, GREEN_T, BLUE_T, H1, H2, P, Doc,  # noqa
                    PageBreak, Spacer, bullets, callout, colors,
                    control_and_contents, cover, mm, table)

OUT = HERE.parent / "Boaty_System_Design_Review.pdf"
DOC_ID = "BOATY-SDR-001"
ISSUE = "Issue B (review report, RID log updated)"
DATE = "30 September 2026"

# RID closures recorded after the review: RID -> (status, evidence).
CLOSURES = {
    "RID-04": ("Closed", "CR-07 (SRS G OPS-005; SSS-MCN E MCN-D65; ICD G "
               "IF-15; FMEA F FM-44; OPS D). Season rule carried as "
               "TBD-09 to ORR."),
    "RID-06": ("Closed", "CR-06 (SRS G NLI-003, MOD-005, mode table; ADD G "
               "DD-23)."),
    "RID-01": ("Closed", "WP2: OA_TYPE 2 + AVOID_BEHAVE 0, FENCE_MARGIN 2 "
               "(params); SC-27 passes calm and in wind; FM-13 re-rated, "
               "FM-59 added (FMEA F); HLM-D19 (SSS-HLM E); ADD G DD-26."),
    "RID-11": ("Closed", "WP2: Rover has no GPS_HDOP_GOOD, so the HDOP ≤ 1.5 "
               "gate is in Mission Control (MCN-D15, unit test); HLM-D09 "
               "re-allocated (SSS-HLM E)."),
    "RID-12": ("Partly", "CR-08 cap scope and price rule (SRS G CON-001; "
               "ADD G DD-25; KCL C). power.csv open (WP5)."),
}
AMBER_T = colors.HexColor("#fff6dc")

# ---------------------------------------------------------------- facts
REQS = list(R.all_reqs())
REQ = {r["id"]: r for r in REQS}
DERIVED = {ss: list(SD.all_derived(SD.SUBSYSTEMS[ss])) for ss in SD.ORDER}
N_DER = sum(len(v) for v in DERIVED.values())
RES = SD.SIM_RESULTS
SIM_TESTS = [t for t in SD.TESTS if t[1] == "SIM"]
NOT_BUILT = [t for t in SIM_TESTS if t[0] not in RES]
PASSED = [t for t in SIM_TESTS if RES.get(t[0], "").startswith("Pass")]
TRACED = {x for t in SD.TESTS for x in t[5]}
SIM_STAGE = [r for r in REQS if r["stage"] == "SIM"]
SIM_UNNAMED = [r for r in SIM_STAGE if r["id"] not in TRACED]
SIM_UNNAMED_M = [r for r in SIM_UNNAMED if r["pri"] == "M"]
TBD_OPEN = [t for t in R.TBDS if "Closed" not in t[1]]
BOM = K.check()


def after(r):
    return F.rpn_after(r) if r[0] in F.POST else F.rpn(r)


HI_BEFORE = [r for r in F.ROWS if F.rpn(r) >= 100]
HI_AFTER = [r for r in F.ROWS if after(r) >= 100]
RESIDUAL_IDS = {x[0] for x in F.RESIDUAL}
SEV9 = [r for r in F.ROWS if r[5] >= 9]

SITL = json.loads((ROOT / "software/results/sitl_results.json").read_text())
SITL_OUT = Counter(r["outcome"] for r in SITL["records"])
UNIT = json.loads((ROOT / "software/results/unit_evidence.json").read_text())
NLI = json.loads((ROOT / "software/results/nli_eval.json").read_text())
NLI_S = NLI["summary"]
PARM = "\n".join(p.read_text() for p in (ROOT / "software/params")
                 .glob("*.parm"))
HAS_OA = bool(re.search(r"^OA_TYPE", PARM, re.M))
HAS_HDOP = bool(re.search(r"^GPS_HDOP_GOOD", PARM, re.M))
HAS_CI = (ROOT / ".github" / "workflows").exists()
HAS_POWER_CSV = (DOCS / "budgets" / "power.csv").exists()


def unit_total():
    """Unit tests collected (pytest --collect-only), else the count at
    the reviewed commit."""
    import subprocess
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "tests/unit"], cwd=ROOT / "software", capture_output=True,
            text=True, timeout=120).stdout
        m = re.search(r"(\d+) tests? collected", out)
        return int(m.group(1)) if m else 295
    except (OSError, subprocess.TimeoutExpired):
        return 295


# ---------------------------------------------------------------- RIDs
# (id, severity, area, title, documents, finding + evidence,
#  recommendation, closure evidence)
MAJ, MIN, OBS = "Major", "Minor", "Obs."
RIDS = [
    ("RID-01", MAJ, "Safety", "RTL is not fence-aware (NAV-007, HLM-D19)",
     "SRS NAV-007; SSS-HLM HLM-D19; FMEA FM-13; KCL; software/params",
     "NAV-007 (Must) needs RTL to reach home without entering an "
     "exclusion zone. HLM-D19 allocates this to 'fence-aware path "
     "planning' in the helm. The parameter baseline has "
     + ("an OA_TYPE entry" if HAS_OA else "<b>no OA_* parameters</b>")
     + ", so a failsafe or adult RTL steers a straight line home and "
     "can cross the island exclusion. FM-13 (S8) is rated D3 on the "
     "strength of this control and of SC-27, which is not built. This "
     "is the one gap where the design, as configured, does not meet a "
     "Must safety requirement.",
     "Configure ArduPilot object avoidance with the Dijkstra planner "
     "around fences (OA_TYPE = 2 and its margins) in the baseline. "
     "Build SC-27 (breach on the far side of the island, then RTL) and "
     "SITL-verify a clean path. If SITL shows it is unreliable with this "
     "hull, change NAV-007 instead: put it in the site rules that no "
     "exclusion may lie between home and any mission area (a site-linter "
     "check). Then re-rate FM-13.",
     "Parameter file diff, SC-27 pass record, FM-13 re-rated"),
    ("RID-02", MAJ, "Verification", "SWE-005 not met: FS-011, 012 and 013 "
     "have no automated scenario",
     "SRS SWE-005, FS-008/011/012/013; SSS-SIM catalogue",
     "SWE-005 (Must, SIM stage) requires an automated simulation "
     "scenario for every failsafe FS-001 to FS-013. The catalogue lists "
     "SC-11 (GNSS loss during battery RTL), SC-12 (log and announce "
     "audit) and SC-13 (single-fault sweep), but none is built. SC-08 "
     "(FS-008, helm signal loss to the ESCs) is also not built. The SSS "
     "moves it to rig L2, but the SRS still asks for a simulation. "
     "FS-013 (no single failure leaves the fence under power) is the "
     "system's top safety claim and has no automated evidence.",
     "Build SC-11, SC-12 and SC-13 in the existing SITL harness. SC-13 "
     "can be a parametrised sweep over the SC-01 to SC-05 fault "
     "injectors × mission phase. For FS-008, either write an SRS "
     "deviation (verified on rig L2 by test, as SITL cannot model the "
     "ESC input) or build a SITL analogue (servo output frozen or "
     "zeroed).",
     "Three pass records in sitl_results.json; SRS deviation or SC-08 "
     "record"),
    ("RID-03", MAJ, "Safety", "Residual risk above threshold with no "
     "disposition (FM-02)",
     "FMEA FM-02, residual-risk register, SSS-SIM SC-20",
     f"{len(HI_BEFORE)} failure modes met the RPN ≥ 100 rule before "
     f"actions and {len(HI_AFTER)} still do after them: "
     + ", ".join(f"{r[0]} ({after(r)})" for r in HI_AFTER) + ". "
     "FM-43 (swimmer near the boat) is formally accepted in the "
     "residual-risk register. FM-02 (GNSS position jump near the fence, "
     "S9) is neither accepted nor closed. Its post-action rating waits "
     "on SC-20, which is not built.",
     "Build SC-20 (20-50 m jump for 2 s near the fence) and re-rate "
     "FM-02 on the result. If the rating stays ≥ 100, the owner must "
     "accept it in the residual-risk register with its rationale (e.g. "
     "EKF glitch rejection plus a 100 m fence set back from the shore).",
     "SC-20 record; FM-02 re-rated or residual entry signed"),
    ("RID-04", MAJ, "Safety / stakeholder", "Photographing ducks conflicts "
     "with OPS-005 wildlife rule",
     "SRS OPS-005, STK-06; site file; planner templates; FMEA FM-44; NLI "
     "evaluation set",
     "The mission statement is 'explore the pond, take pictures of "
     "ducks'. OPS-005 (Must) says 'no mission shall aim to approach or "
     "follow wildlife' and makes known nesting areas exclusions. The "
     "stand-in site has a <i>duck house</i> that is both a 2 m "
     "exclusion and a photo landmark with a 6 m keep-out. The live "
     "evaluation planned visits to it. The 'Duck patrol' template makes "
     "wildlife stops a product feature. A floating duck house is a "
     "likely nesting site in the breeding season (roughly March to "
     "July). Disturbing nesting birds can be an offence. FM-44 "
     "(nesting area approached, O2) looks understated when the system "
     "is designed to go there.",
     "Owner decision, recorded as a CR. (1) Reword OPS-005 so the "
     "system may photograph wildlife from a set stand-off but never "
     "chase it. (2) Set a nesting stand-off that the site linter "
     "enforces (suggest ≥ 15 m exclusion radius around nest structures, "
     "not a 6 m landmark keep-out). (3) Add a seasonal flag to site "
     "features, so landmarks are unavailable in the breeding season. "
     "(4) Rename or constrain 'Duck patrol'. (5) Re-rate FM-44 and add "
     "the rule to the operations manual and the NLI declines.",
     "CR approved; site schema and linter change; FM-44 re-rated"),
    ("RID-05", MAJ, "Interfaces", "Event vocabulary is an uncontrolled "
     "interface",
     "ICD IF-04; SSS-MCN MCN-D60; SSS-MCP B4-B7; software",
     "The boat services tell Mission Control what they are doing through "
     "STATUSTEXT messages starting 'BOATY '. MCN-D60 (spoken reasons for "
     "a HOLD) parses the text of these messages. IF-04 mentions only the "
     "prefix. The actual vocabulary (e.g. the new B5 episodes, "
     "'REPEATEDLY STUCK: HOLD', 'NO CONTROL') exists only in code. A "
     "wording change on the boat would silently break a verified "
     "requirement on shore.",
     "Define the event vocabulary once in code (one module of constants "
     "used by B4-B7 and C-side parsing). Generate an IF-04 table from "
     "it in the ICD build. Add a unit test that every event the "
     "services can emit is known to the parser. Add the B5 episode cap "
     "and its parameters to IF-04.",
     "ICD IF-04 table; shared constants module; unit test"),
    ("RID-06", MAJ, "Requirements", "Two requirements contradict the "
     "agreed design",
     "SRS NLI-003, MOD-005; ICD IF-11; ADD",
     "<b>NLI-003</b> requires the Claude request to include 'fence, "
     "exclusion zones, home …'. IF-11 deliberately sends named places "
     "and a trip-time guide, not geometry (data minimisation; Claude "
     "never sees coordinates, and the validator owns geometry). "
     "<b>MOD-005</b> says a finished AUTO mission 'shall enter RTL'. "
     "In the design, the last mission item is a return-to-launch that "
     "runs in AUTO. The mode reported stays AUTO until HOLD. Both "
     "designs are better than the requirement text, but a frozen "
     "baseline cannot hold requirements known to be false.",
     "Raise CR-06 to amend both. NLI-003: 'the request shall include "
     "the site's named places, the mission schema and the time and "
     "energy limits, and shall not include coordinates'. MOD-005: 'the "
     "boat shall return home (RTL behaviour, in AUTO or RTL mode) and "
     "then HOLD'. Update the MOD table and ICD IF-11 wording to match.",
     "SRS issue with CR-06"),
    ("RID-07", MAJ, "Verification", "No requirement-level verification "
     "matrix (VCRM)",
     "SRS; SSS; SSS-SIM catalogue; software/results",
     f"The SRS has {len(REQS)} requirements. {len(SIM_STAGE)} are due "
     f"for verification at the SIM stage. {len(SIM_UNNAMED)} of those "
     f"({len(SIM_UNNAMED_M)} Must) are not named in the trace of any "
     "catalogue test. Many are in fact verified by unit tests or by "
     "SSS-derived requirements, but nothing shows it requirement by "
     "requirement. The reviewer could not confirm SIM-stage compliance "
     "for these without reading test code. This is the main exit "
     "criterion of a PDR, and it is the document that CDR and TRR will "
     "need.",
     "Generate a VCRM from source: SRS requirement → SSS derived "
     "requirement(s) → test IDs (catalogue and pytest node IDs) → "
     "latest result. Tag pytest tests with the requirement IDs they "
     "verify (a marker) so the matrix is built, not typed. The build "
     "should fail if a Must SIM-stage requirement has neither evidence "
     "nor a named future test. Appendix A lists the gaps to start from.",
     "VCRM appendix or document; build check"),
    ("RID-08", MAJ, "Configuration", "Document set is not a consistent "
     "baseline",
     "All documents",
     "The documents cross-reference issues and facts that have since "
     "moved on. Examples found:<br/>"
     "• ICD PDF not rebuilt after the source change (shows parent ADD "
     "Issue E). References [1] still cite SRS D, ADD D and FMEA B. IF-11 "
     "says 'tool use' and 'keyring' (the design uses structured output "
     "and a 0600 key file). IF-21 says '106 passing'. The IF-15 example "
     "site is 'milton-todds-pit'. IF-15 lacks the backstop-radius "
     "rule. IF-02 lacks PARAM_REQUEST_READ re-requests.<br/>"
     "• ADD cites SRS D. Its drivers and cost table say £160/£150, and "
     "§2.1 says '£100 target'. §4.6 still says 'to confirm'. §4.8 says "
     "'tool use'. The decision log lacks CR-04 and CR-05. It says "
     "'ICD (next)'.<br/>"
     "• SRS: STK-05 still £100; the use story still has a key switch; "
     "the FS table caption says TBD-08; 'Next: ADD'.<br/>"
     "• SSS applicable documents are hard-coded to SRS D, ADD C and ICD "
     "B. HUL and REC are at Issue A with stale parents.<br/>"
     "• FMEA and KCL status/basis lines name superseded issues.",
     "Create one baseline register in code (docs/common/baseline.py: "
     "document → issue → date). Have every build read its parents and "
     "references from it rather than from literals, and add a check "
     "that fails on a mismatch. Fix the listed text, then rebuild every "
     "PDF in one commit.",
     "Baseline register; all PDFs rebuilt; check passes"),
    ("RID-09", MAJ, "Configuration", "Software baseline is not "
     "identifiable",
     "SRS SWE-006; SSS-SIM SIM-D12; KCL; software/README",
     "There are no git tags. There is no dependency lock file, so the "
     "SIM evidence cannot be reproduced exactly. The KCL archives "
     "ArduPilot sources at commit a11f7351, but the simulator is built "
     "from the Rover-4.7.1 branch (dbe79216). The evidence was "
     "therefore produced with a different ArduPilot commit from the one "
     "the documents cite.",
     "Pin ArduPilot to one commit everywhere (KCL, README, build "
     "script) and re-archive the sources if needed. Add a lock file "
     "(pip-tools or uv). At freeze, create an annotated tag "
     "(e.g. <i>sdr-baseline-1</i>) that covers the documents, the "
     "parameters and the software, and record it in the baseline "
     "register.",
     "Lock file; single commit ID; tag"),
    ("RID-10", MIN, "Configuration", "No CI, lint or type checking",
     "SRS SWE-007 (Should); SSS-SIM SIM-D11; MCN-D33",
     "No CI workflow exists" + ("" if not HAS_CI else " (found)") +
     ". There is no ruff or mypy configuration. Unit tests and the "
     "secret-scan test run only when someone remembers.",
     "Add a GitHub Actions workflow running ruff, mypy (on the boaty "
     "package) and the unit tests (SITL stays manual). Add a docs job "
     "that runs every build script's checks.",
     "Green workflow on the baseline tag"),
    ("RID-11", MIN, "Safety", "HDOP arming gate not configured",
     "SRS PRE-001; SSS-HLM HLM-D09; software/params",
     "HLM-D09 says arming needs HDOP ≤ 1.5, and allocates this to the "
     "helm. GPS_HDOP_GOOD is "
     + ("present" if HAS_HDOP else "<b>not in the parameter baseline</b>")
     + ", so ArduPilot's default (2.3) applies.",
     "Add GPS_HDOP_GOOD = 150 to the baseline. Add a parameter "
     "read-back unit check.", "Parameter diff"),
    ("RID-12", MIN, "Budgets", "Power budget file missing; cost margin "
     "thin",
     "SSS-PWR PWR-D17; KCL cost reconciliation",
     "PWR-D17 names docs/budgets/power.csv, which "
     + ("exists." if HAS_POWER_CSV else "does not exist.") +
     " The power analysis lives only in the KCL. The BOM is "
     f"£{BOM['total']} against the £{K.CAP} cap (margin "
     f"£{K.CAP - BOM['total']}, {100 * (K.CAP - BOM['total']) / K.CAP:.0f}%) "
     "on estimated prices. The conditional antenna pole kit (£8, only "
     "if V-08 needs it) would breach it.",
     "Either create power.csv from the KCL data (generated) or re-point "
     "PWR-D17 at the KCL section. Record an owner decision on what "
     "sits inside the cap (pole kit, spares), and state a price-margin "
     "policy for CDR (e.g. prices confirmed from vendors before "
     "ordering).",
     "File or SSS change; owner decision recorded"),
    ("RID-13", MIN, "Safety", "FMEA rule text and the build check "
     "disagree; missing failure mode",
     "FMEA §2.2 and fmea_data.check()",
     "The rules say action is required for every S ≥ 9 row 'whatever O "
     "and D are', but the check lets a direct test (D ≤ 3) stand in for "
     "an action. SC-09 showed that re-arming mid-lake resets home to "
     "the re-arm point. VAL-004 catches it, but there is no failure "
     "mode for it.",
     "Align the rule text with the check (state the D ≤ 3 exemption). "
     "Add an FM for 'home reset by re-arm away from the launch point' "
     "with VAL-004 and SC-09 as controls.",
     "FMEA issue"),
    ("RID-14", MIN, "Privacy", "Child's voice transcripts go to a cloud "
     "service without a stated policy",
     "ICD IF-11; OPS manual; SRS NLI-008",
     "Transcribed instructions from a 4-year-old are sent to the Claude "
     "API and logged locally. No document says what is sent, how long "
     "local logs are kept, or who may read them.",
     "Add a short data statement to the ICD (IF-11 payload is text "
     "only, with no audio, names or location) and to the operations "
     "manual (log retention, how to delete).",
     "ICD and OPS text"),
    ("RID-15", MIN, "Security", "Web UI security assumptions not "
     "recorded",
     "ADD; ICD IF-09/IF-10; SSS-MCN",
     "The web UI is plain HTTP. The panel and instruction endpoints "
     "rely on the closed Wi-Fi network, not on authentication (the "
     "adult PIN protects approval only). This is a reasonable choice "
     "for Mk1, but it is not written down as an assumption, and "
     "nothing requires WPA2 or a non-default passphrase.",
     "Add the assumption to the ADD and a derived MCN requirement: "
     "WPA2/3 with a unique passphrase, the AP not bridged to the "
     "tethered internet for inbound traffic.", "ADD / SSS text"),
    # Observations: carried to a named later gate
    ("OBS-01", OBS, "Operations", "Site and permission open (TBD-02, "
     "TBD-03)", "SRS TBD register; site file",
     "The site file is a stand-in built from public mapping. The real "
     "lake, launch point and home bay, and the Trust's permission, are "
     "open.",
     "Carry. Gate: ORR (before the first lake trial). The site linter "
     "already blocks an unsurveyed site from use.", "Site survey; "
     "permission email"),
    ("OBS-02", OBS, "Verification", "Hardware verification items open",
     "SSS-SIM V-01, V-07 to V-10; KCL",
     "The rig and bench checks that close key assumptions (fence-aware "
     "RTL on hardware, ESC stop on signal loss, thrust, sag) are "
     "planned, but they need hardware.",
     "Carry. Gate: CDR for the test plans, TRR for the results.",
     "Rig reports"),
    ("OBS-03", OBS, "Interfaces", "ICD TBC items open",
     "ICD TBC-06, 08, 11-14",
     "These need hardware or vendor data (pinouts, timings).",
     "Carry. Gate: CDR.", "ICD issue at CDR"),
    ("OBS-04", OBS, "Budgets", "Performance numbers are estimates",
     "KCL; SSS-PRP, PWR",
     "Thrust, power draw, endurance and salvaged-cell capacity are "
     "estimates. Several datasheets are not yet fetched. The simulator "
     "boat model is tuned to these estimates, not measured data.",
     "Carry. Gate: CDR (datasheets fetched, bench thrust and current "
     "measured, SITL model re-tuned to them).",
     "Bench data; model update"),
    ("OBS-05", OBS, "Performance", "Planning latency not measured on the "
     "real link",
     "SRS NLI-007; NLI evaluation",
     f"The live evaluation met NLI-007 (p95 {NLI_S['p95_s']:.1f} s) "
     "from a cloud container, not over a phone's 4G tether.",
     "Carry. Gate: TRR (repeat SC-33 on the tethered Pi 5).",
     "SC-33 re-run record"),
    ("OBS-06", OBS, "Scope", "Features not yet implemented",
     "SSS-MCN (MCN-D07, D51 and others)",
     "Still to build: speech engines (STT and TTS), the fence editor, "
     "replay (MCN-D51), map tiles (MCN-D07), a waterfowl finder, "
     "RSSI and latency logging, and the QGroundControl takeover drill. "
     "These are specified, which is what PDR needs.",
     "Carry. Gate: CDR (an implementation plan per item); TRR (built "
     "and verified).", "CDR plan"),
    ("OBS-07", OBS, "Verification", "Remaining FMEA scenarios not built",
     "SSS-SIM SC-21 to SC-23, SC-34, SC-36, SC-39",
     "These scenarios cover frozen GNSS, compass offset, helm restart, "
     "link degradation, interrupted upload and overstated capacity. "
     "Their FMEA detection ratings assume the tests will exist.",
     "Carry. Gate: TRR. None is needed to freeze the system design.",
     "Pass records"),
]


# ---------------------------------------------------------------- build
def sev_style(rows):
    st = []
    for i, r in enumerate(rows[1:], start=1):
        c = {"Major": ORANGE_T, "Minor": AMBER_T}.get(r[1], BLUE_T)
        st.append(("BACKGROUND", (1, i), (1, i), c))
    return st


def build():
    maj = [r for r in RIDS if r[1] == MAJ]
    mino = [r for r in RIDS if r[1] == MIN]
    obs = [r for r in RIDS if r[1] == OBS]
    fs_reqs = [r for r in REQS if r["id"].startswith("FS-")]
    fs_named = [r for r in fs_reqs if r["id"] in TRACED]

    st = cover("System Design Review", "Independent SDR / PDR assessment "
               "of the Boaty Mk1 system documentation baseline, with "
               "findings, recommendations and the plan to freeze",
               [["Document", DOC_ID], ["Issue", ISSUE], ["Date", DATE],
                ["Review type", "System Design Review / Preliminary "
                 "Design Review (gate 1 of 4: SDR, CDR, TRR, ORR)"],
                ["Recommendation", "<b>Conditional GO</b>: freeze after "
                 f"closing {len(maj)} Major and {len(mino)} Minor RIDs"],
                ["Findings", f"{len(maj)} Major, {len(mino)} Minor, "
                 f"{len(obs)} Observations carried to a named gate"]])
    st += control_and_contents(
        [["A", DATE, "First issue: review of the documentation baseline "
          "as at commit 88b1cd7.", "Claude (as reviewer)"],
         ["B", DATE, "WP1 owner decisions recorded (CR-06, CR-07, CR-08): "
          "RID log updated. RID-12 corrected: the pole kit that breaches "
          "the cap is the antenna pole, not a recovery pole. WP2 closes "
          "RID-01 and RID-11.", "Claude, owner decisions"]],
        "How to use this report: section 2 gives the decision. Section 6 "
        "lists every review item discrepancy (RID) with its evidence and "
        "recommended closure. Section 8 is the plan to freeze. Close a "
        "RID by recording the closure evidence in the RID log (section "
        "8.3); the freeze happens when every Major and Minor RID is "
        "closed or dispositioned by the owner.")

    # 1
    st += [H1("1. Purpose, scope and reviewer statement"),
           P("This is the first of the four project gates agreed with the "
             "owner. SDR/PDR asks one question: <i>is the system design, "
             "as documented, complete, consistent and credible enough to "
             "freeze and start detailed design?</i> Detailed design here "
             "means hardware drawings, the build, and the remaining "
             "software. The gate comes before any Mk1 hardware is bought, "
             "so evidence is analysis, inspection and simulation."),
           H2("1.1 Scope"),
           *bullets([
               "All controlled documents in docs/ as built at commit "
               "88b1cd7 (list in section 3).",
               "The parameter baseline (software/params) and the site "
               "file, as configuration items that the documents claim.",
               f"The verification evidence in software/results: SITL "
               f"records ({sum(SITL_OUT.values())}), unit evidence, and "
               f"the live Claude evaluation ({NLI_S['cases']} cases).",
               "Out of scope: detailed code review (that belongs to CDR), "
               "hardware (none exists) and the lake site (not surveyed).",
           ]),
           H2("1.2 Method"),
           *bullets([
               "Read every document end to end against the SRS as the "
               "top-level contract.",
               "Cross-checked each document's stated parents, issues and "
               "facts against the others (configuration consistency).",
               "Traced Must requirements into the design (ADD allocation, "
               "SSS derived requirements), and on into verification "
               "(catalogue, results), using the source data rather than "
               "the rendered PDFs, so the counts here are exact.",
               "Checked the claims the documents make about configuration "
               "(parameters, site, tests) against the repository itself.",
               "Graded findings as Major, Minor or Observation (section "
               "6.1).",
           ]),
           H2("1.3 Independence statement"),
           callout("The owner asked for an independent review. The "
                   "reviewer is the same assistant that drafted most of "
                   "these documents, which is not true independence. To "
                   "offset this, the review worked from the source data "
                   "and the repository rather than the prose. It looked "
                   "first for where the documents contradict the code. "
                   "<b>Recommendation:</b> the owner, as a practising "
                   "engineer, should personally read the Major RIDs and "
                   "the safety sections (FMEA, failsafes) before signing "
                   "the freeze. A second person (another engineer, or "
                   "another AI session given only the documents) would "
                   "strengthen it further.", ORANGE, ORANGE_T),
           PageBreak()]

    # 2 decision
    st += [H1("2. Summary and recommended decision"),
           callout(f"<b>Recommendation: Conditional GO.</b> The "
                   "architecture is sound, well reasoned and unusually "
                   "well evidenced for this stage. "
                   f"{len(PASSED)} of {len(SIM_TESTS)} catalogued "
                   "simulator scenarios already pass on the real software. "
                   "But the documentation is <b>not yet a baseline that "
                   "can be frozen</b>. One Must safety requirement is not "
                   "met as configured (RTL crossing an exclusion). The "
                   "failsafe verification the SRS demands is incomplete. "
                   "Two requirements contradict the design. The wildlife "
                   "rule conflicts with the product goal. And the "
                   "documents disagree with each other about which issues "
                   "they depend on. Close the "
                   f"{len(maj)} Major and {len(mino)} Minor RIDs, rebuild "
                   "and tag, then freeze.", colors.HexColor("#1e8a55"),
                   GREEN_T),
           Spacer(1, 3 * mm),
           H2("2.1 What is good"),
           *bullets([
               "<b>Safety architecture.</b> Every safety function (fence, "
               "failsafes, RTL, STOP) sits in the flight controller. "
               "Python and Claude can only propose. The validator is the "
               "only way to create a mission the helm will accept, and "
               "this is enforced in code, not just stated.",
               "<b>Documents built from data.</b> Requirements, "
               "allocation, parameters and test results are generated "
               "from one source. Builds fail on untraced requirements, "
               "unknown references and a BOM over the cap. That is better "
               "configuration discipline than many funded projects "
               "manage.",
               f"<b>Evidence ahead of phase.</b> {SITL_OUT.get('passed', 0)} "
               f"SITL records pass. There are {unit_total()} unit tests, "
               "and property-based validator fuzzing. The live Claude "
               f"evaluation got {NLI_S['passed']}/{NLI_S['cases']} "
               f"with every must-decline case declined "
               f"({NLI_S['must_decline_declined']}). The simulator has "
               "already found and fixed real design faults (SC-06, the "
               "parameter read-back, short-trip planning). They are "
               "fed back into the FMEA.",
               "<b>Operations taken seriously.</b> The operations manual, "
               "crew card and checklist are traced to the FMEA's "
               "procedural actions. The same checklist drives Mission "
               "Control.",
           ]),
           H2("2.2 What must change before freeze"),
           table([["RID", "Issue", "Closure in one line"]] +
                 [[r[0], r[3], r[6].split(". ")[0] + "."] for r in maj],
                 [16, 62, 92]),
           PageBreak()]

    # 3 documents
    docs_rows = [["Document", "ID", "Issue", "Reviewer's note"],
                 ["Concept Selection Report", "-", "v1.1",
                  "Superseded in detail by the SRS and ADD; kept as the "
                  "rationale record. No action."],
                 ["System Requirements Spec.", "BOATY-SRS-001", "F",
                  f"{len(REQS)} requirements. Stale text (RID-08); two "
                  "contradictions (RID-06); OPS-005 (RID-04)."],
                 ["Architecture Design Doc.", "BOATY-ADD-001", "F",
                  "Sound; stale drivers, cost and references (RID-08); "
                  "security assumption missing (RID-15)."],
                 ["Interface Control Doc.", "BOATY-ICD-001", "F (PDF "
                  "stale)", "22 interfaces. PDF not rebuilt; IF-04 "
                  "vocabulary (RID-05); IF-11 text (RID-06, RID-14)."],
                 ["Subsystem specs (8)", "BOATY-SSS-*", "A-E",
                  f"{N_DER} derived requirements. HUL and REC Issue A with "
                  "stale parents; hard-coded references (RID-08)."],
                 ["Design FMEA", "BOATY-FMEA-001", "E",
                  f"{len(F.ROWS)} failure modes, {len(F.ACTIONS)} actions. "
                  "FM-02 (RID-03), FM-13 (RID-01), FM-44 (RID-04), rules "
                  "(RID-13)."],
                 ["Operations Manual", "BOATY-OPS-001", "C",
                  "Good. Needs the wildlife and data statements (RID-04, "
                  "RID-14)."],
                 ["Key Component List", "BOATY-KCL-001", "B",
                  f"BOM £{BOM['total']} of £{K.CAP}. ArduPilot commit "
                  "mismatch (RID-09); basis stale (RID-08)."],
                 ["Software and results", "software/", "commit 88b1cd7",
                  "Not a document, but the documents cite it. No tag, no "
                  "lock, no CI (RID-09, RID-10)."]]
    st += [H1("3. Documents reviewed"),
           table(docs_rows, [36, 30, 20, 84]),
           P("Not provided and not needed at this gate: detailed drawings, "
             "the wiring diagram, the software design description and the "
             "test procedures. They are CDR deliverables (section 8.4).",
             "small")]

    # 4 entry criteria
    ec = [["#", "Entry criterion", "Status", "Evidence / RID"],
          ["E1", "Stakeholder needs and ConOps agreed", "Met",
           "SRS §1-2; STK-01 to STK-08, with owner decisions logged."],
          ["E2", "System requirements complete, with priority, method and "
           "stage", "Met with RIDs", f"{len(REQS)} requirements; "
           f"{len(TBD_OPEN)} of {len(R.TBDS)} TBDs open (site-dependent). "
           "RID-04, RID-06."],
          ["E3", "Architecture selected with trade studies", "Met",
           "ADD design-space exploration, weighted candidates and "
           "sensitivity."],
          ["E4", "Every requirement allocated to a subsystem", "Met",
           "The ADD and SSS builds fail on unallocated requirements."],
          ["E5", "Interfaces identified and defined", "Partly met",
           "22 interfaces defined; event vocabulary uncontrolled "
           "(RID-05); TBCs open (OBS-03)."],
          ["E6", "Subsystem requirements derived and traced", "Met",
           f"{N_DER} derived requirements; trace checked by the build."],
          ["E7", "Budgets (cost, mass, power) with margins", "Partly met",
           f"Cost £{BOM['total']}/£{K.CAP}; power.csv missing (RID-12); "
           "the numbers are estimates (OBS-04)."],
          ["E8", "Hazards and failure modes analysed; high risks actioned",
           "Partly met", f"{len(F.ROWS)} FMs; FM-02 has no disposition "
           "(RID-03); FM-13 relies on an unconfigured control (RID-01)."],
          ["E9", "Verification approach defined per requirement", "Partly "
           "met", "Method and stage on every requirement, but no VCRM "
           "(RID-07)."],
          ["E10", "Risky technology de-risked", "Met",
           "ArduPilot SITL and the live LLM evaluation already run on the "
           "real software."],
          ["E11", "Documents under configuration control", "Not met",
           "Cross-references inconsistent; no tags (RID-08, RID-09)."]]
    ec_style = []
    for i, r in enumerate(ec[1:], start=1):
        c = (GREEN_T if r[2] == "Met" else ORANGE_T if r[2] == "Not met"
             else AMBER_T)
        ec_style.append(("BACKGROUND", (2, i), (2, i), c))
    st += [H1("4. Entry criteria assessment"),
           table(ec, [10, 62, 22, 76], style_extra=ec_style),
           PageBreak()]

    # 5 compliance
    pri = Counter(r["pri"] for r in REQS)
    stage = Counter(r["stage"] for r in REQS)
    st += [H1("5. Compliance assessment"),
           H2("5.1 Requirements"),
           P(f"The SRS holds {len(REQS)} requirements: {pri['M']} Must, "
             f"{pri['S']} Should and {pri['C']} Could. Each has a "
             "verification method, a stage and a trace to a stakeholder "
             "need, and the build rejects any that do not. By stage: "
             + ", ".join(f"{k} {v}" for k, v in stage.most_common()) +
             ". The requirements are mostly singular, testable and "
             "free of design. The exceptions are those in RID-06, and "
             "HLM-D19 which names a mechanism."),
           P(f"TBDs: {len(R.TBDS) - len(TBD_OPEN)} of {len(R.TBDS)} "
             "closed. The two open ones (TBD-02 site and TBD-03 "
             "permission) don't affect the system design. They are "
             "carried to ORR (OBS-01)."),
           H2("5.2 Architecture and allocation"),
           P("The allocation is complete by construction. The division of "
             "authority is the design's strongest feature: the flight "
             "controller alone is safety authority, Python can only "
             "request HOLD, and Claude can only propose. It is enforced "
             "in the code in three ways: ValidatedMission can only be "
             "created by the validator, GuardedHelm refuses motion "
             "commands while a foreign GCS is present, and parameter "
             "read-back is checked against the baseline. The accepted "
             "common-cause risk (fence and failsafes in one flight "
             "controller) is stated honestly in the FMEA residual "
             "register, with a Mk2 path (SAF-005)."),
           H2("5.3 Interfaces"),
           P("The ICD defines all 22 interfaces from the ADD register, "
             "with owners, timing and error handling. The weakness is "
             "what sits <i>inside</i> an interface. The STATUSTEXT "
             "vocabulary (RID-05) and the IF-11 payload (RID-06, RID-14) "
             "are defined by code rather than by the ICD."),
           H2("5.4 Verification status by stage")]
    vs = [["Stage", "SRS reqs", "Catalogue tests", "Status at SDR"],
          ["SIM", str(stage["SIM"]), str(len(SIM_TESTS)),
           f"{len(PASSED)} pass, {len(NOT_BUILT)} not built "
           f"({', '.join(t[0] for t in NOT_BUILT)}). No failures."],
          ["BENCH", str(stage["BENCH"]),
           str(sum(1 for t in SD.TESTS if t[1] == "BENCH")),
           "Planned; needs hardware (CDR/TRR)."],
          ["Rigs L1-L3", "-", str(sum(1 for t in SD.TESTS
                                      if t[1] in ("L1", "L2", "L3"))),
           "Planned; needs hardware."],
          ["POOL", str(stage["POOL"]),
           str(sum(1 for t in SD.TESTS if t[1] == "POOL")),
           "Planned (TRR)."],
          ["LAKE", str(stage["LAKE"]), "-", "Planned (ORR onwards)."]]
    st += [table(vs, [22, 20, 26, 102]),
           P(f"SITL run: {SITL_OUT.get('passed', 0)} passed, "
             f"{SITL_OUT.get('xfail', 0)} known gaps (expected failures "
             f"for later slices), {SITL_OUT.get('xpass', 0)} known gap "
             "not seen. Live NLI evaluation: "
             f"{NLI_S['passed']}/{NLI_S['cases']}, p95 "
             f"{NLI_S['p95_s']:.1f} s. Failsafes: {len(fs_named)} of "
             f"{len(fs_reqs)} FS requirements are named by a catalogue "
             "test, but only those with a built scenario count for "
             "SWE-005 (RID-02).", "small"),
           H2("5.5 Safety and risk"),
           P(f"The FMEA has {len(F.ROWS)} failure modes. {len(SEV9)} are "
             f"at severity ≥ 9, and all of those have a test. "
             f"{len(HI_BEFORE)} met the RPN ≥ 100 rule before actions and "
             f"{len(HI_AFTER)} after "
             f"({', '.join(r[0] for r in HI_AFTER)}). "
             f"{len(F.RESIDUAL)} residual risks are formally accepted "
             f"({', '.join(x[0] for x in F.RESIDUAL)}). The FMEA is "
             "strengthened by simulator findings (FM-49 to FM-58). Its "
             "weaknesses are the unconfigured RTL control (RID-01), the "
             "open FM-02 (RID-03), the wildlife rating (RID-04) and one "
             "missing mode (RID-13)."),
           H2("5.6 Budgets"),
           table([["Budget", "Value", "Limit / margin", "Assessment"],
                  ["Cost (BOM)", f"£{BOM['total']}", f"£{K.CAP} cap; "
                   f"£{K.CAP - BOM['total']} margin", "Compliant but thin; "
                   "estimated prices (RID-12)."],
                  ["Power", f"{BOM['watt']} W limit", "PWR-D17 ≥ 30% "
                   "margin", "Analysis in KCL; budget file missing "
                   "(RID-12)."],
                  ["Mass / buoyancy", "SSS-HUL", "Reserve buoyancy",
                   "Estimated; CDR to confirm with a weighed build."],
                  ["API cost", f"${NLI_S.get('cost_usd', 0.31):.2f} per "
                   f"{NLI_S['cases']} plans", "Pennies per trip",
                   "Compliant."]],
                 [28, 30, 38, 74]),
           H2("5.7 Configuration management"),
           P("Generating documents from source is excellent practice. But "
             "each document hard-codes its parents' issue letters, so "
             "they drift (RID-08). The software has no tags, lock file or "
             "CI (RID-09, RID-10). A freeze needs one identifier that "
             "names a consistent set: documents, parameters, site and "
             "code."),
           PageBreak()]

    # 6 RIDs
    st += [H1("6. Review item discrepancies"),
           H2("6.1 Severity definitions"),
           table([["Severity", "Meaning", "Before freeze?"],
                  ["Major", "The baseline fails a Must requirement, is "
                   "internally contradictory, or cannot be identified. "
                   "Would mislead detailed design.", "Close"],
                  ["Minor", "A gap or error that is local and cheap to "
                   "fix, and that does not change the architecture.",
                   "Close or owner disposition"],
                  ["Obs.", "Expected to be open at this phase. Carried to "
                   "the named gate.", "Carry"]],
                 [20, 120, 30],
                 style_extra=[("BACKGROUND", (0, 1), (0, 1), ORANGE_T),
                              ("BACKGROUND", (0, 2), (0, 2), AMBER_T),
                              ("BACKGROUND", (0, 3), (0, 3), BLUE_T)]),
           H2("6.2 RID summary")]
    summ = [["RID", "Sev.", "Area", "Title"]] + \
        [[r[0], r[1], r[2], r[3]] for r in RIDS]
    st += [table(summ, [16, 14, 30, 110], style_extra=sev_style(summ)),
           PageBreak(), H2("6.3 RID detail")]
    for r in RIDS:
        rows = [[f"<b>{r[0]}</b>", r[1], f"<b>{r[3]}</b>"],
                ["Area", r[2], f"Documents: {r[4]}"],
                ["Finding", r[5], ""],
                ["Recommend", r[6], ""],
                ["Close with", r[7], ""]]
        c = {"Major": ORANGE_T, "Minor": AMBER_T}.get(r[1], BLUE_T)
        st += [table(rows, [20, 26, 124], header=False, style_extra=[
            ("BACKGROUND", (0, 0), (-1, 0), c),
            ("SPAN", (1, 2), (2, 2)), ("SPAN", (1, 3), (2, 3)),
            ("SPAN", (1, 4), (2, 4))]), Spacer(1, 3 * mm)]
    st.append(PageBreak())

    # 7 open items carried
    st += [H1("7. Items carried to later gates"),
           P("These are expected at SDR and do not block the freeze. Each "
             "has a gate by which it must close."),
           table([["Item", "Gate", "What closes it"]] +
                 [[f"{r[0]} {r[3]}", r[6].split("Gate: ")[-1]
                   if "Gate:" in r[6] else r[6], r[7]] for r in obs],
                 [70, 60, 40]),
           PageBreak()]

    # 8 plan
    st += [H1("8. Gap-closure plan and freeze"),
           H2("8.1 Work packages"),
           P("The RIDs group naturally into five packages. They are "
             "ordered so that the requirement changes (which need owner "
             "decisions) start first, and the rebuild and tag come last."),
           table([["WP", "Content", "RIDs", "Owner input"],
                  ["WP1 Decisions", "CR-06: NLI-003 and MOD-005 wording; "
                   "wildlife stand-off, season and OPS-005 rewording; "
                   "cost-cap scope (pole kit); FM-02 acceptance if needed",
                   "04, 06, 12, 03", "Yes: approve the CR"],
                  ["WP2 Safety config", "OA_TYPE Dijkstra's fence "
                   "avoidance; GPS_HDOP_GOOD; parameter checks",
                   "01, 11", "No"],
                  ["WP3 Scenarios", "SC-27, SC-11, SC-12, SC-13, SC-20 "
                   "(+ SC-08 or a deviation); FMEA re-rating; new FM",
                   "01, 02, 03, 13", "Deviation for SC-08 if chosen"],
                  ["WP4 Interfaces & VCRM", "Event vocabulary module and "
                   "IF-04 table; IF-11 data statement; VCRM generated "
                   "from pytest markers; security assumption",
                   "05, 07, 14, 15", "No"],
                  ["WP5 Baseline", "Baseline register; fix stale text; "
                   "power.csv; ArduPilot pin; lock file; CI; rebuild all "
                   "PDFs; tag", "08, 09, 10, 12", "Sign the freeze"]],
                 [28, 82, 26, 34]),
           H2("8.2 Freeze (SDR exit) criteria"),
           *bullets([
               "Every Major and Minor RID is closed with its evidence, or "
               "dispositioned by the owner in writing.",
               "All document builds pass their checks, including the new "
               "baseline-consistency check and the VCRM check.",
               "Full SITL and unit suites pass on the tagged commit, with "
               "no new known gaps.",
               "Tag <i>sdr-baseline-1</i> created. From then on, any "
               "change to a frozen document goes through a numbered CR "
               "with impact noted on the other documents.",
               "The owner signs the decision record (section 9).",
           ]),
           H2("8.3 RID log"),
           table([["RID", "Sev.", "Status", "Closed by (commit / CR)",
                   "Date"]] +
                 [[r[0], r[1],
                   CLOSURES.get(r[0], ("Open" if r[1] != OBS else "Carried",
                                       ""))[0],
                   CLOSURES.get(r[0], ("", ""))[1],
                   DATE if r[0] in CLOSURES else ""]
                  for r in RIDS],
                 [16, 14, 16, 100, 24]),
           H2("8.4 What CDR will expect"),
           *bullets([
               "Hull and pod drawings with weighed-mass and buoyancy "
               "estimates; electronics box layout; wiring diagram.",
               "Software design description for the remaining features "
               "(OBS-06), and code review of the safety-relevant paths.",
               "Datasheets fetched; bench thrust and current measured; the "
               "SITL boat model re-tuned (OBS-04).",
               "Rig and bench test procedures (L1-L3, BENCH) with pass "
               "criteria traced through the VCRM.",
               "Confirmed prices and an order list within the cap.",
           ]),
           PageBreak()]

    # 9 decision record
    st += [H1("9. Decision record"),
           table([["Item", "Entry"],
                  ["Review", "System Design Review / PDR, gate 1"],
                  ["Baseline reviewed", "commit 88b1cd7"],
                  ["Reviewer recommendation", "Conditional GO: close "
                   f"{len(maj)} Major and {len(mino)} Minor RIDs, then "
                   "freeze and tag"],
                  ["Owner decision", "☐ GO   ☐ Conditional GO   ☐ NO-GO"],
                  ["Conditions / notes", "<br/><br/>"],
                  ["Signed (owner)", "<br/>"],
                  ["Date", ""]], [50, 120]),
           PageBreak()]

    # Appendix A
    rows = [["Requirement", "Pri.", "Text (abridged)"]]
    for r in SIM_UNNAMED_M:
        txt = re.sub(r"<[^>]+>", "", r["text"])
        rows.append([r["id"], r["pri"], txt[:150] +
                     ("…" if len(txt) > 150 else "")])
    st += [H1("Appendix A. SIM-stage Must requirements without a "
              "named test"),
           P(f"{len(SIM_UNNAMED_M)} Must requirements due at the SIM stage "
             "are not named in the trace of any catalogue test. Many "
             "are verified by unit tests or by derived-requirement tests; "
             "the VCRM (RID-07) should show which, and add tests for the "
             "rest.", "small"),
           table(rows, [22, 10, 138])]

    doc = Doc(OUT, DOC_ID, "System Design Review", ISSUE)
    doc.multiBuild(st)
    return len(maj), len(mino), len(obs)


if __name__ == "__main__":
    print(build(), "->", OUT)
