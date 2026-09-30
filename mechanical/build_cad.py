"""Build the Mk1 mechanical outputs.

    python3 mechanical/build_cad.py            # everything
    python3 mechanical/build_cad.py --no-figs  # checks, results and CAD only

Writes
  mechanical/results/mech_results.json   the checks, mass and hydrostatics
                                         (read by the MDD build; committed)
  docs/mdd/figures/*.png                 MDD figures (committed)
  mechanical/out/                        STEP/STL per part, assembly STEP
                                         and GLB, and Boaty_Mk1_CAD.zip
                                         (build output, not committed)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cadquery as cq  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from boaty_cad import assembly as A  # noqa: E402
from boaty_cad import checks as C  # noqa: E402
from boaty_cad import params as P  # noqa: E402
from boaty_cad import render as RN  # noqa: E402

OUT = HERE / "out"
RES = HERE / "results"
FIG = HERE.parent / "docs" / "mdd" / "figures"
plt.rcParams["font.family"] = "DejaVu Sans"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40]


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ---------------------------------------------------------------- exports
def export_parts() -> list[dict]:
    rows = []
    pdir = OUT / "parts"
    pdir.mkdir(parents=True, exist_ok=True)
    for p in A.CATALOGUE:
        shape = p.build().val()
        b = shape.BoundingBox()
        at0 = shape.moved(cq.Location(cq.Vector(-b.xmin, -b.ymin,
                                                -b.zmin)))
        stem = f"{p.key}_{slug(p.name)}"
        cq.exporters.export(cq.Workplane().add(at0),
                            str(pdir / f"{stem}.step"))
        files = [f"parts/{stem}.step"]
        if p.kind == "printed":
            cq.exporters.export(cq.Workplane().add(at0),
                                str(pdir / f"{stem}.stl"),
                                tolerance=0.05, angularTolerance=0.1)
            files.append(f"parts/{stem}.stl")
        rows.append(dict(key=p.key, name=p.name, kind=p.kind,
                         material=p.material, qty=p.qty, child=p.child,
                         refs=list(p.refs), files=files,
                         size=[round(b.xlen, 1), round(b.ylen, 1),
                               round(b.zlen, 1)]))
    return rows


def export_assembly():
    adir = OUT / "assembly"
    adir.mkdir(parents=True, exist_ok=True)
    a = A.assembly()
    a.save(str(adir / "boaty_mk1_assembly.step"))
    a.save(str(adir / "boaty_mk1_assembly.glb"))


def make_zip(parts: list[dict]):
    z = OUT / "Boaty_Mk1_CAD.zip"
    src = OUT / "source"
    if src.exists():
        shutil.rmtree(src)
    shutil.copytree(HERE / "boaty_cad", src / "boaty_cad",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(HERE / "build_cad.py", src)
    shutil.copy(RES / "mech_results.json", OUT / "mech_results.json")
    lines = ["Boaty Mk1 mechanical CAD (BOATY-MDD-001 draft)",
             f"Built from commit {commit()} with CadQuery {cq.__version__}.",
             "",
             "Frame: x forward from the stern transom, y to port, z up from "
             "the keel line. mm.",
             "assembly/  the whole boat as STEP (colours, one body per part "
             "instance) and GLB",
             "parts/     every part design, moved to the origin: STEP for "
             "all, STL for printed parts",
             "source/    the CadQuery source (python3 build_cad.py rebuilds "
             "everything)",
             "mech_results.json  mass, hydrostatics and the compliance "
             "checks",
             "", "Part list (qty is for the whole boat):"]
    for r in parts:
        lines.append(f"  {r['key']:8s} x{r['qty']:<2d} {r['kind']:8s} "
                     f"{r['material']:8s} {r['name']}")
    (OUT / "README.txt").write_text("\n".join(lines) + "\n")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(OUT.rglob("*")):
            if f.is_file() and f != z:
                zf.write(f, f"Boaty_Mk1_CAD/{f.relative_to(OUT)}")
    log("zip", z, f"{z.stat().st_size / 1e6:.1f} MB")


def commit() -> str:
    return subprocess.run(["git", "-C", str(HERE), "rev-parse", "--short",
                           "HEAD"], capture_output=True,
                          text=True).stdout.strip()


# ---------------------------------------------------------------- figures
def _meshes(explode: dict | None = None, tol: float = 0.6,
            skip: set | None = None):
    out = []
    for key, lab, shape in C.placed_shapes():
        if skip and key in skip:
            continue
        s = shape
        if explode:
            d = explode.get(key) or explode.get(lab)
            if d is not None:
                s = s.moved(cq.Location(cq.Vector(*d)))
        out.append((RN.mesh(s, tol), A.by_key(key).colour))
    return out


def _save(img, path, dpi=200):
    plt.imsave(path, np.clip(img, 0, 1))


def figures(res: dict):
    FIG.mkdir(parents=True, exist_ok=True)
    parts = _meshes()
    log("render iso")
    _save(RN.render(parts, -58, 24, px=0.55), FIG / "iso.png")
    _save(RN.render(parts, 125, 28, px=0.55), FIG / "iso_aft.png")
    # side elevation with the design and light waterlines
    log("render side")
    meta: dict = {}
    img = RN.render(parts, -90, 0, px=0.5, meta=meta)
    fig, ax = plt.subplots(figsize=(img.shape[1] / 150, img.shape[0] / 150),
                           dpi=150)
    ax.imshow(np.clip(img, 0, 1))
    for lab, c in (("design", "#2a78d6"), ("light", "#7fb1ea")):
        f = res["data"][f"float_{lab}"]
        x0, x1 = -60.0, P.X_STEM + 20
        z = lambda x: f["sinkage"] - np.tan(np.radians(f["trim"])) * (  # noqa
            x - f["xref"])
        a = RN.to_px(meta, (x0, -400, z(x0)))
        b = RN.to_px(meta, (x1, -400, z(x1)))
        ax.plot([a[0], b[0]], [a[1], b[1]], color=c, lw=1.4,
                ls="-" if lab == "design" else "--")
        ax.text(b[0] + 4, b[1], f"{lab} WL", color=c, fontsize=7,
                va="center")
    ax.axis("off")
    fig.savefig(FIG / "side.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    log("render top/front")
    _save(RN.render(parts, 0, 90, px=0.5), FIG / "top.png")
    _save(RN.render(parts, 0, 0, px=0.5), FIG / "front.png")
    # exploded
    log("render exploded")
    ex = {"HUL-101": (70, 0, 0), "HUL-103": (-70, 0, 0),
          "PRP-101": (-150, 0, 0), "PRP-102": (-175, 0, 0),
          "PRP-103": (-162, 0, 0), "KC-04": (-150, 0, 0),
          "HUL-201": (0, 0, 45), "HUL-202": (0, 0, 45),
          "HUL-303": (0, 0, 80), "HUL-304": (0, 0, 80),
          "HUL-301": (0, 0, 120), "HUL-305": (0, 0, 120),
          "HUL-306": (0, 0, 120), "HUL-501": (0, 0, 120),
          "HUL-502": (0, 0, 120), "KC-11": (0, 0, 120),
          "HUL-302": (0, 0, 165), "HUL-307": (0, 0, 165),
          "HUL-401": (0, 0, 205), "HUL-308": (0, 0, 225),
          "HUL-402": (0, 0, 45), "HUL-403": (0, 0, 120),
          "HUL-404": (0, 0, 45), "REC-101": (0, 0, 150),
          "REC-102": (0, 0, 170), "REC-103": (0, 0, 170),
          "REC-104": (0, 0, 160), "HUL-106": (0, 0, 30)}
    # screws and dowels travel with their end segments
    for key, loc, lab in A.instances():
        if key in ("HUL-104", "HUL-105"):
            x = loc.toTuple()[0][0]
            ex[lab] = (70, 0, 0) if x > P.X_J1 + 20 else (-70, 0, 0)
    _save(RN.render(_meshes(ex), -58, 24, px=0.6), FIG / "exploded.png")
    # hull segment section (cut at the hull centreline, foam shown)
    log("render section")
    sec_parts = []
    cutter = cq.Solid.makeBox(1000, 400, 400, cq.Vector(-100, -400, -100))
    for p in A.CATALOGUE[:3]:
        s = p.build().val().cut(cutter)
        sec_parts.append((RN.mesh(s, 0.3), p.colour))
        sec_parts.append((RN.mesh(p.foam().val().cut(cutter), 0.5), "foam"))
    for key in ("PRP-101", "PRP-102", "PRP-103", "KC-04"):
        s = A.by_key(key).build().val().cut(cutter)
        sec_parts.append((RN.mesh(s, 0.3), A.by_key(key).colour))
    for key, loc, lab in A.instances():
        if key in ("HUL-104", "HUL-105") and lab.endswith(("P1", "P3")):
            s = A.by_key(key).build().val().moved(loc).moved(
                cq.Location(cq.Vector(0, -P.HULL_Y, 0)))
            sec_parts.append((RN.mesh(s, 0.3), A.by_key(key).colour))
    _save(RN.render(sec_parts, -90, 12, px=0.35), FIG / "hull_section.png")
    part_sheets()
    plots(res)


def part_sheets():
    log("part sheets")
    ps = A.CATALOGUE
    per = 12
    for n in range(0, len(ps), per):
        chunk = ps[n:n + per]
        fig, axs = plt.subplots(3, 4, figsize=(10, 7.6))
        for ax in axs.flat:
            ax.axis("off")
        for ax, p in zip(axs.flat, chunk):
            s = p.build().val()
            img = RN.render([(RN.mesh(s, 0.25), p.colour)], -55, 28,
                            px=max(0.08, max(s.BoundingBox().xlen,
                                             s.BoundingBox().ylen,
                                             s.BoundingBox().zlen) / 260))
            ax.imshow(np.clip(img, 0, 1))
            ax.set_title(f"{p.key}  ×{p.qty}\n{p.name[:34]}", fontsize=7.2)
        fig.tight_layout()
        fig.savefig(FIG / f"parts_{n // per + 1}.png", dpi=170)
        plt.close(fig)


def plots(res: dict):
    d = res["data"]
    gz = np.array(d["gz"])
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.plot(gz[:, 0], gz[:, 1], color="#2a78d6", lw=1.8)
    ax.axhline(0, color="#999", lw=0.6)
    ax.axvline(d["heel_edge"], color="#eb6834", lw=1, ls="--")
    ax.text(d["heel_edge"] + 1, gz[:, 1].max() * 0.1,
            f"300 g at the deck edge: {d['heel_edge']:.1f}°", fontsize=7,
            color="#eb6834")
    ax.axvline(d["wave_slope"], color="#888", lw=0.8, ls=":")
    ax.text(d["wave_slope"] + 1, gz[:, 1].max() * 0.9,
            f"100 mm wave slope ≈ {d['wave_slope']:.0f}°", fontsize=7,
            color="#666")
    ax.set_xlabel("heel (°)")
    ax.set_ylabel("righting arm GZ (mm)")
    ax.set_title(f"Righting arm at design mass ({d['float_design']['mass']:.0f}"
                 " g)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "gz.png", dpi=200)
    plt.close(fig)
    g = sorted(d["mass_groups"].items(), key=lambda kv: kv[1])
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.barh([k for k, _ in g], [v for _, v in g], color="#2a78d6")
    for i, (_, v) in enumerate(g):
        ax.text(v + 8, i, f"{v:.0f} g", va="center", fontsize=7)
    ax.set_xlabel("g")
    ax.set_title(f"Mass by group: {d['mass']:.0f} g against 1800 g",
                 fontsize=9)
    ax.tick_params(labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "mass.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    figs = "--no-figs" not in sys.argv
    t0 = time.time()
    log("checks")
    R = C.run()
    RES.mkdir(exist_ok=True)
    params = {k: getattr(P, k) for k in dir(P) if k.isupper() and
              isinstance(getattr(P, k), (int, float, tuple, list))}
    res = dict(commit=commit(), cadquery=cq.__version__,
               rows=R.rows, data=R.data, params=params)
    log("export parts")
    res["parts"] = export_parts()
    (RES / "mech_results.json").write_text(
        json.dumps(res, indent=1, default=float) + "\n")
    log("export assembly")
    export_assembly()
    if figs:
        figures(res)
    make_zip(res["parts"])
    n = {s: sum(r["status"] == s for r in R.rows)
         for s in ("PASS", "FAIL", "TEST")}
    log(f"done in {time.time() - t0:.0f} s: {n}")


if __name__ == "__main__":
    main()
