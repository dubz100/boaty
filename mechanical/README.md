# Boaty Mk1 mechanical design (CadQuery) — work in progress

Source for BOATY-MDD-001 (draft, not yet issued). `boaty_cad/` holds every
dimension (`params.py`), the part builders (`hull`, `structure`, `mast`,
`pod`), the assembly, mass properties and mesh hydrostatics
(`analysis.py`), a renderer and the compliance checks (`checks.py`,
not yet run end to end). Exports, figures and the MDD PDF are still to do.

Frame: x forward from the stern transom, y to port, z up from the keel.
