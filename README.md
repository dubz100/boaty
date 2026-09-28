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
