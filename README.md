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

The SRS is generated the same way. Requirements live in `docs/srs/src/requirements.py`, and `build_srs.py` checks IDs and traceability before rendering:

```sh
cd docs/srs/src
python3 figures.py && python3 build_srs.py
```

- [`docs/add/Boaty_Architecture_Design_Document.pdf`](docs/add/Boaty_Architecture_Design_Document.pdf): architecture design (BOATY-ADD-001): design-space exploration, selected architecture, interfaces, requirement allocation and budgets. Source in `docs/add/src/` (`architecture.py` holds the data; the build checks every SRS requirement is allocated). Shared PDF styling lives in `docs/common/pdfdoc.py`.

- [`docs/icd/Boaty_Interface_Control_Document.pdf`](docs/icd/Boaty_Interface_Control_Document.pdf): interface control document (BOATY-ICD-001): all 22 interfaces with owners, definitions, timing, error handling, verification, and a register of items still to be confirmed. Interface identities come from the ADD source, so the two can't drift. Build with `cd docs/icd/src && python3 figures.py && python3 build_icd.py`.

- [`docs/sss/`](docs/sss/): subsystem specifications BOATY-SSS-HUL, PRP, PWR, HLM, MCP, MCN, REC and SIM (one PDF each), plus `Boaty_Subsystem_Specifications_Volume.pdf` with all eight. 243 derived requirements, all generated from `docs/sss/src/sss_data.py`. The helm parameter table is generated from `software/params/`, and the SIM test catalogue shows results read from `software/results/sitl_results.json`, so neither can drift from the code. The build fails if any SRS requirement allocated to a subsystem isn't covered, or any trace reference doesn't exist. Build with `cd docs/sss/src && python3 build_sss.py` (needs `pymupdf` for the combined volume).

- [`docs/fmea/Boaty_Design_FMEA.pdf`](docs/fmea/Boaty_Design_FMEA.pdf): design FMEA (BOATY-FMEA-001): 58 failure modes rated for severity, occurrence and detection, with 28 actions and residual risks. Issues D and E add what the simulator found. The build checks that every failure mode of severity ≥ 8 is exercised by a test in the SSS-SIM catalogue. Build with `cd docs/fmea/src && python3 build_fmea.py`.

- [`docs/ops/Boaty_Operations_Manual.pdf`](docs/ops/Boaty_Operations_Manual.pdf): operations manual (BOATY-OPS-001): golden rules, kit lists, 14 procedures, the 18-item pre-launch checklist (the same list Mission Control shows), 12 contingency cards, a printable crew card and a quick reference. The build checks it covers every OPS requirement and procedural FMEA action, and that every reference exists. Build with `cd docs/ops/src && python3 build_ops.py`.

- [`docs/kcl/Boaty_Key_Component_List.pdf`](docs/kcl/Boaty_Key_Component_List.pdf): key component list (BOATY-KCL-001). It covers the parts whose numbers feed the software, the ArduPilot parameters and the simulator. Every value is tagged with its source. The document also includes a cost reconciliation, a supply-sag analysis, the helm pin and parameter allocation, the simulator model parameters and a datasheet register. ArduPilot and AM32 source files it relies on are archived in `docs/kcl/sources/`. Build with `cd docs/kcl/src && python3 build_kcl.py`. Fetch vendor datasheets with `python3 fetch_datasheets.py`, which needs ordinary internet access.

## Software

- [`software/`](software/): the Python code and the simulator. ArduPilot Rover 4.7.1 SITL flies a model of the boat, the real mission-computer services run on a simulated Pi Zero, and Mission Control drives it all as it will on the Pi 5. See [`software/README.md`](software/README.md). Results are in [`software/results/`](software/results/): `FINDINGS.md` summarises what the simulator showed, and `SITL_REPORT.md` gives the evidence for every scenario.

## Document issues (29 September 2026)

- SRS F
- ADD F
- ICD F
- SSS: HLM D, MCP D, MCN D, PWR C, PRP B, SIM E (the others are unchanged)
- FMEA E
- Operations manual C
- KCL B

These issues carry:

- CR-04: the SpeedyBee flight controller.
- CR-05: FS-002 relaxed to 3 s.
- Everything simulator slices 1 to 3 established.
