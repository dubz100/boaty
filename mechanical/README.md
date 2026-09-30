# Boaty Mk1 mechanical design (CadQuery)

The detailed mechanical design behind BOATY-MDD-001, the Mechanical Design
Description (`docs/mdd/`). Draft for the CDR.

    pip install cadquery          # 2.8, with its OCP kernel
    python3 mechanical/build_cad.py

`build_cad.py` runs the compliance checks, exports every part and the
assembly, renders the MDD figures and packs `out/Boaty_Mk1_CAD.zip`
(about 6 minutes). Then `python3 docs/mdd/src/build_mdd.py` builds the PDF
from the committed results, without CadQuery.

| Module | What it holds |
|---|---|
| `boaty_cad/params.py` | every dimension, with the requirement it answers |
| `hull.py` | the three segment designs, joint hardware |
| `structure.py` | beams, box, tray, latches, hood, DUPLO deck, key |
| `mast.py` | step and handle, tube, collar and hoop, flag, masthead |
| `pod.py` | thruster pod, guard, prop, reference motor |
| `assembly.py` | the part catalogue and every placement |
| `analysis.py` | mass properties, mesh hydrostatics and stability |
| `checks.py` | the compliance matrix |
| `render.py` | the z-buffer renderer for the figures |

Committed outputs: `results/mech_results.json` and `docs/mdd/figures/`.
`out/` is build output and is not committed.

Frame: x forward from the stern transom, y to port, z up from the keel
line; mm and g.
