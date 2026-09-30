# Boaty

A mini autonomous boat, built by a dad and son.

## Documents

- [`docs/concept/Boaty_Concept_Selection_Report.pdf`](docs/concept/Boaty_Concept_Selection_Report.pdf): concept options, scoring, and the recommended concept (modular GPS catamaran with ArduPilot and a camera "mission brain").

The report is generated from source:

```sh
pip install reportlab matplotlib numpy
cd docs/concept/src
python3 figures.py        # figures -> docs/concept/figures/
python3 build_report.py   # PDF    -> docs/concept/
```

Scores live in `docs/concept/src/scoring.py`. The table, the chart and the sensitivity check all read from it.

- [`docs/srs/Boaty_System_Requirements_Specification.pdf`](docs/srs/Boaty_System_Requirements_Specification.pdf): system requirements specification (BOATY-SRS-001), including the Concept of Operations and Concept of Use.

The SRS is generated the same way. Requirements live in `docs/srs/src/requirements.py`, and `build_srs.py` checks IDs and traceability before rendering. Appendix C is the verification cross-reference matrix (VCRM). It is generated from the tests themselves: unit tests tagged `@pytest.mark.verifies(...)`, SITL evidence records and the SSS-SIM catalogue, collected by `software/tools/vcrm.py` into `software/results/vcrm_tests.json`. Inspection and analysis evidence, and declared open items with their gates, live in `docs/srs/src/verification.py`. The build fails if any evidence is failing, or if a Must requirement due at the simulation stage has no evidence and no declared open item:

```sh
cd docs/srs/src
python3 figures.py && python3 build_srs.py
```

- [`docs/add/Boaty_Architecture_Design_Document.pdf`](docs/add/Boaty_Architecture_Design_Document.pdf): architecture design (BOATY-ADD-001): design-space exploration, selected architecture, interfaces, requirement allocation and budgets. Source in `docs/add/src/` (`architecture.py` holds the data; the build checks every SRS requirement is allocated). Shared PDF styling lives in `docs/common/pdfdoc.py`.

- [`docs/icd/Boaty_Interface_Control_Document.pdf`](docs/icd/Boaty_Interface_Control_Document.pdf): interface control document (BOATY-ICD-001): all 22 interfaces with owners, definitions, timing, error handling, verification, and a register of items still to be confirmed. Interface identities come from the ADD source, so the two can't drift. Build with `cd docs/icd/src && python3 figures.py && python3 build_icd.py`.

- [`docs/sss/`](docs/sss/): subsystem specifications BOATY-SSS-HUL, PRP, PWR, HLM, MCP, MCN, REC and SIM (one PDF each), plus `Boaty_Subsystem_Specifications_Volume.pdf` with all eight. 246 derived requirements, all generated from `docs/sss/src/sss_data.py`. The helm parameter table is generated from `software/params/`, and the SIM test catalogue shows results read from `software/results/sitl_results.json`, so neither can drift from the code. The build fails if any SRS requirement allocated to a subsystem isn't covered, or any trace reference doesn't exist. Build with `cd docs/sss/src && python3 build_sss.py` (needs `pymupdf` for the combined volume).

- [`docs/fmea/Boaty_Design_FMEA.pdf`](docs/fmea/Boaty_Design_FMEA.pdf): design FMEA (BOATY-FMEA-001): 60 failure modes rated for severity, occurrence and detection, with 28 actions and residual risks. Issues D and E add what the simulator found. The build checks that every failure mode of severity ≥ 8 is exercised by a test in the SSS-SIM catalogue. Build with `cd docs/fmea/src && python3 build_fmea.py`.

- [`docs/ops/Boaty_Operations_Manual.pdf`](docs/ops/Boaty_Operations_Manual.pdf): operations manual (BOATY-OPS-001): golden rules, kit lists, 14 procedures, the 18-item pre-launch checklist (the same list Mission Control shows), 12 contingency cards, a printable crew card and a quick reference. The build checks it covers every OPS requirement and procedural FMEA action, and that every reference exists. Build with `cd docs/ops/src && python3 build_ops.py`.

- [`docs/kcl/Boaty_Key_Component_List.pdf`](docs/kcl/Boaty_Key_Component_List.pdf): key component list (BOATY-KCL-001). It covers the parts whose numbers feed the software, the ArduPilot parameters and the simulator. Every value is tagged with its source. The document also includes a cost reconciliation, a supply-sag analysis, the helm pin and parameter allocation, the simulator model parameters and a datasheet register. ArduPilot and AM32 source files it relies on are archived in `docs/kcl/sources/`. Build with `cd docs/kcl/src && python3 build_kcl.py`. Fetch vendor datasheets with `python3 fetch_datasheets.py`, which needs ordinary internet access.

- [`docs/sdr/Boaty_System_Design_Review.pdf`](docs/sdr/Boaty_System_Design_Review.pdf): System Design Review / PDR report (BOATY-SDR-001), gate 1 of 4. It is an independent-style review of the whole documentation baseline. It covers entry criteria, compliance by area, 15 review item discrepancies (9 Major, 6 Minor) plus 7 observations carried to later gates, and the gap-closure plan to freeze. Issue B records the WP1 closures. The recommendation is Conditional GO. Counts are computed from the same source data as the other documents, so rebuilding after fixes updates the picture. Build with `python3 docs/sdr/src/build_sdr.py`.

- [`docs/budgets/power.csv`](docs/budgets/power.csv): the boat's power budget (SSS-PWR PWR-D17). It is generated from the ADD loads and the parameter baseline by `docs/budgets/build_power.py`, which checks the 40 min endurance with 30% margin.

### Rebuilding and the baseline register

`python3 docs/build_all.py` rebuilds every document in dependency order. Each build runs its own checks: traceability, allocation, FMEA rules, the VCRM, the power budget, and the baseline register. It stops on the first failure. `docs/common/baseline.py` is the register: the current issue of every document. Builds take their own issue and their parents' issues from it, and the check fails if any parent issue is typed by hand. The documentation is frozen with the annotated tag `sdr-baseline-1` once the owner signs the SDR decision record. After that, changes go through numbered change requests.

### Continuous integration

`.github/workflows/ci.yml` runs on every push:

- `ruff`
- the mypy ratchet (`software/tools/mypy_ratchet.py`): the safety-critical modules must be type-clean, and no other file may get worse than `software/tools/mypy_baseline.json`
- the unit tests
- `docs/build_all.py`

Dependencies are pinned in `software/requirements.lock`. The SITL scenarios run locally, because they take about 35 min and need an ArduPilot build. Their evidence file records the ArduPilot commit used, pinned to Rover-4.7.1 `dbe79216`.

## Software

- [`software/`](software/): the Python code and the simulator. ArduPilot Rover 4.7.1 SITL flies a model of the boat, the real mission-computer services run on a simulated Pi Zero, and Mission Control drives it all as it will on the Pi 5. See [`software/README.md`](software/README.md). Results are in [`software/results/`](software/results/): `FINDINGS.md` summarises what the simulator showed, and `SITL_REPORT.md` gives the evidence for every scenario.

## Document issues (30 September 2026): SDR baseline candidate

The authoritative list is `docs/common/baseline.py`:

- SRS H
- ADD H
- ICD H
- SSS: HUL B, PRP C, PWR D, HLM F, MCP F, MCN F, REC B, SIM G
- FMEA G
- Operations manual E
- KCL D
- SDR C

These issues carry:

- CR-04: the SpeedyBee flight controller.
- CR-05: FS-002 relaxed to 3 s.
- Everything simulator slices 1 to 3 established.
- The System Design Review's WP1 owner decisions:
  - CR-06: NLI-003 and MOD-005 reworded to match the verified design.
  - CR-07: wildlife is photographed only from outside a 15 m nest stand-off, which the site checker enforces. "Duck patrol" is now "Duck watch". The breeding-season rule is deferred to the site visit (TBD-09).
  - CR-08: the £185 cap covers the boat, Mission Control and charging kit. The antenna pole kit, spares and consumables sit in a separate field-kit budget.
- SDR WP2 to WP4:
  - RTL now plans round exclusion zones.
  - Mission Control checks HDOP before arming.
  - The failsafe scenarios SC-11, SC-12, SC-13 and SC-20 are built, and B6 now holds on a GNSS position jump.
  - The boat-service event vocabulary is in one module, with the ICD IF-04 table generated from it.
  - The ICD has a data statement for what is sent to Claude.
  - The web UI's security assumption is recorded.
  - The SRS carries a generated VCRM.
