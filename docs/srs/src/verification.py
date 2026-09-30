"""Verification cross-reference matrix (VCRM) inputs besides tests.

Test evidence comes from software/results/vcrm_tests.json (tools/vcrm.py:
unit tests tagged @pytest.mark.verifies, SITL evidence records) and from
the SSS-SIM catalogue results. This file adds the rest:

OTHER  evidence that is not a test: inspection of an artefact, analysis in
       a document. (method, evidence, status)
OPEN   items not yet verifiable, each with the gate by which it must be.
       A requirement may have passing tests and still be open in part.

The SRS build fails if a Must requirement due at the SIM stage has neither
passing evidence nor an OPEN entry (SDR RID-07).
"""

OTHER = {
    "SAF-006": ("Analysis", "BOATY-FMEA-001 Issue F: 60 failure modes, "
                "updated after each simulator slice and the SDR", "Met"),
    "SWE-001": ("Inspection", "software/: CPython 3.11+ only; no "
                "MicroPython parts yet", "Met"),
    "SWE-003": ("Inspection", "boaty/helm/api.py: Mission Control and the "
                "services use only the IF-14 Helm interface", "Met"),
    "SWE-005": ("Inspection", "SSS-SIM catalogue: SC-01 to SC-13 built and "
                "passing; FS-008 by deviation on rig L2", "Met"),
    "LOG-004": ("Inspection", "No code path uploads photos; cloud analysis "
                "is not built (ICD IF-11 data statement)", "Met"),
    "NLI-003": ("Test", "SC-33 live Claude evaluation, 41 cases "
                "(software/results/NLI_EVAL.md)", "Met"),
    "NLI-006": ("Test", "SC-33: every must-decline case declined", "Met"),
    "FEN-002": ("Inspection", "Sites are GeoJSON files in git "
                "(software/sites), linted on load", "Met in part"),
}

OPEN = {
    "FEN-002": ("Drawing fences on the map (fence editor, OBS-06)", "CDR"),
    "MIS-006": ("Mission editing on the map (OBS-06)", "CDR"),
    "MC-005": ("Map tiles offline (MCN-D07); the data behind the map is "
               "tested", "CDR"),
    "MC-014": ("QGroundControl takeover drill (OBS-06)", "TRR"),
    "MC-015": ("Photo-review mode on the panel (OBS-06)", "CDR"),
    "NLI-002": ("Speech-to-text engine on the Pi 5; the TALK flow is "
                "tested with a stand-in", "CDR"),
    "LOG-003": ("Trip replay (MCN-D51); the logs it needs are tested "
                "(SC-12)", "CDR"),
    "LOG-005": ("Home backup (Could)", "ORR"),
    "DET-004": ("Applies only if DET-003 (bird detection) is built", "CDR"),
    "SWE-006": ("Tagged baseline and trial releases (SDR WP5)", "Freeze"),
    "SWE-007": ("CI running tests, ruff and mypy (SDR WP5)", "Freeze"),
    "OPS-012": ("Contingency rehearsal in simulation before the first lake "
                "trial", "ORR"),
}
