"""Build the Mk1 electrical outputs.

    python3 electrical/build_elec.py

Writes
  electrical/results/elec_results.json  checks and calculations (read by
                                        the EDD build; committed)
  docs/edd/figures/*.png                EDD figures (committed)
  electrical/out/                       schematics (PDF/SVG/PNG), KiCad
                                        netlist, wire list, BOM, pin maps,
                                        stripboard layouts, and
                                        Boaty_Mk1_Electrical.zip (not
                                        committed)
"""
from __future__ import annotations

import csv
import datetime
import json
import shutil
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from boaty_elec import calcs, checks, design as DS  # noqa: E402
from boaty_elec import harness, schematics, stripboard  # noqa: E402

OUT = HERE / "out"
RES = HERE / "results"
FIG = HERE.parent / "docs" / "edd" / "figures"
plt.rcParams["font.family"] = "DejaVu Sans"


def commit() -> str:
    return subprocess.run(["git", "-C", str(HERE), "rev-parse", "--short",
                           "HEAD"], capture_output=True,
                          text=True).stdout.strip()


# ---------------------------------------------------------------- netlists
def kicad_netlist(path: Path):
    """KiCad netlist, S-expression format version D (Pcbnew / KiCad
    'Import netlist'). No footprints are assigned: the custom boards are
    stripboard, so this is for cross-checking and future PCB work."""
    def q(s):
        return '"' + str(s).replace('"', "'") + '"'
    lines = ['(export (version "D")',
             f'  (design (source "boaty_elec/design.py") (date '
             f'{q(datetime.date.today().isoformat())}) (tool '
             '"boaty_elec"))', "  (components"]
    for ref, p in DS.PARTS.items():
        lines.append(f"    (comp (ref {q(ref)}) (value {q(p.value)}) "
                     f"(footprint {q(p.pkg)}) (description {q(p.desc)}) "
                     f"(fields (field (name \"MPN\") {q(p.mpn)}) (field "
                     f"(name \"Board\") {q(p.board)})))")
    lines.append("  )")
    lines.append("  (nets")
    for i, (net, pins) in enumerate(DS.NETS.items(), 1):
        nodes = " ".join(f"(node (ref {q(x.split('.')[0])}) (pin "
                         f"{q(x.split('.')[1])}))" for x in pins)
        lines.append(f"    (net (code {q(i)}) (name {q(net)}) {nodes})")
    lines.append("  )")
    lines.append(")")
    path.write_text("\n".join(lines) + "\n")


def csv_out(path: Path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def bom_rows():
    rows = []
    for ref, p in DS.PARTS.items():
        if p.kind == "connector" and p.value == "pad":
            continue
        rows.append([ref, p.value, p.desc, p.board, p.pkg, p.mpn, p.src,
                     f"{p.cost:.2f}", DS.KCL_LINE.get(ref, "new")])
    for ref, desc, qty, each, line, stock in DS.EXTRAS:
        rows.append([ref, f"× {qty}", desc, "-", "-", "-", "EST",
                     f"{qty * each:.2f}", line + (" (stock)" if stock
                                                  else "")])
    return rows


def pinmaps():
    pn = DS.pin_net()
    maps = {}
    for ref in ("U2", "U6", "U50"):
        p = DS.PARTS[ref]
        maps[ref] = [[pin, p.pins[pin].label, pn.get(f"{ref}.{pin}", "nc")]
                     for pin in p.pins]
    return maps


# ---------------------------------------------------------------- figures
def plot_transients(c):
    k = c["key"]
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.2))
    t = [x[0] for x in k["key_in"]["trace"]]
    axs[0].plot(t, [x[1] for x in k["key_in"]["trace"]], color="#2a78d6",
                label="motor rail (V)")
    ax2 = axs[0].twinx()
    ax2.plot(t, [x[2] for x in k["key_in"]["trace"]], color="#eb6834",
             label="Q2 current (A)")
    ax2.set_ylabel("A", fontsize=8, color="#eb6834")
    axs[0].set_title(f"Key in: inrush {k['key_in']['i_peak']:.1f} A, "
                     f"up in {k['key_in']['t_on_ms']:.1f} ms", fontsize=8.5)
    axs[0].set_xlim(0, 12)
    axs[0].set_xlabel("ms", fontsize=8)
    axs[0].set_ylabel("V", fontsize=8, color="#2a78d6")
    for key, colour, lab in (("key_out", "#2a78d6", "with bleeder"),
                             ("key_out_no_bleed", "#aaa", "no bleeder")):
        tr = k[key]["trace"]
        axs[1].plot([x[0] for x in tr], [x[1] for x in tr], color=colour,
                    label=lab)
    axs[1].axhline(0.5, color="#eb6834", lw=0.8, ls="--")
    axs[1].axvline(100, color="#eb6834", lw=0.8, ls=":")
    axs[1].text(102, 6, "IF-06: < 0.5 V\nby 100 ms", fontsize=7,
                color="#eb6834")
    axs[1].set_xlim(0, 300)
    axs[1].set_title(f"Key out: rail < 0.5 V at "
                     f"{k['key_out']['t_off_ms']:.0f} ms", fontsize=8.5)
    axs[1].set_xlabel("ms", fontsize=8)
    axs[1].legend(fontsize=7)
    for ax in (*axs, ax2):
        ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "key_transient.png", dpi=200)
    plt.close(fig)


def plot_sag(c):
    hr = c["harness"]
    ws = [40 + 2 * i for i in range(26)]
    v_esc = [calcs.sag(w, r_up=hr["r_up"], r_down=hr["r_down"])["v_esc"]
             for w in ws]
    v_ideal = [calcs.sag(w)["v_esc"] for w in ws]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.plot(ws, v_esc, color="#2a78d6", lw=1.8, label="with this harness")
    ax.plot(ws, v_ideal, color="#aaa", ls="--", label="no harness (SDR "
            "analysis)")
    ax.axhline(7.5, color="#eb6834", lw=0.9)
    ax.text(41, 7.53, "PWR-D22 7.5 V", fontsize=7, color="#eb6834")
    ax.axhline(7.2, color="#c0182a", lw=0.9, ls=":")
    ax.text(41, 7.23, "AM32 minimum 7.2 V", fontsize=7, color="#c0182a")
    for w in (60, 70):
        ax.axvline(w, color="#666", lw=0.6, ls=":")
    ax.set_xlabel("BATT_WATT_MAX (W)", fontsize=8)
    ax.set_ylabel("ESC input (V)", fontsize=8)
    ax.set_title("Rail at the ESCs at the critical battery (9.6 V "
                 "resting, 0.22 Ω pack)", fontsize=8.5)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "sag.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    for d in (OUT, RES, FIG):
        d.mkdir(parents=True, exist_ok=True)
    sch = OUT / "schematics"
    sch.mkdir(exist_ok=True)
    made = schematics.build(str(sch))
    # one PDF of all sheets
    import pymupdf
    book = pymupdf.open()
    for _sid, _t, stem in made:
        book.insert_pdf(pymupdf.open(f"{stem}.pdf"))
    book.save(str(OUT / "Boaty_Mk1_Schematics.pdf"))
    for sid, _t, stem in made:
        shutil.copy(f"{stem}.png", FIG / f"{sid}.png")
    c = calcs.run()
    chk = checks.run(c)
    # boards
    bdir = OUT / "stripboard"
    bdir.mkdir(exist_ok=True)
    for b in stripboard.LAYOUT:
        L = stripboard.build(b)
        stripboard.draw(L, bdir / f"{b}_layout.png")
        shutil.copy(bdir / f"{b}_layout.png", FIG / f"{b}_layout.png")
        csv_out(bdir / f"{b}_cuts.csv", ["column", "row", "kind"],
                [[f"{x:g}", r, k] for x, r, k in L.cuts])
        csv_out(bdir / f"{b}_links.csv", ["from (col,row)", "to (col,row)",
                                          "net"],
                [[f"{a}", f"{bb}", n] for a, bb, n in L.links])
        csv_out(bdir / f"{b}_placement.csv", ["hole (col,row)", "pin",
                                              "net"],
                [[f"{k}", v[0], v[1]] for k, v in sorted(L.pins.items())])
    harness.draw_box(FIG / "box_layout.png")
    harness.draw_interconnect(FIG / "interconnect.png")
    shutil.copy(FIG / "box_layout.png", OUT / "box_layout.png")
    shutil.copy(FIG / "interconnect.png", OUT / "interconnect.png")
    plot_transients(c)
    plot_sag(c)
    # data files
    kicad_netlist(OUT / "boaty_mk1.net")
    csv_out(OUT / "netlist.csv", ["net", "pin", "part value", "board"],
            [[n, p, DS.PARTS[p.split('.')[0]].value,
              DS.PARTS[p.split('.')[0]].board]
             for n, ps in DS.NETS.items() for p in ps])
    harness.write_wirelist(OUT / "wirelist.csv")
    csv_out(OUT / "bom_electrical.csv", ["ref", "value", "description",
                                         "board", "package", "part / MPN",
                                         "source", "£ (est)", "KCL line"],
            bom_rows())
    for ref, rows in pinmaps().items():
        csv_out(OUT / f"pinmap_{ref}.csv", ["pin", "function", "net"],
                rows)
    # results
    trace_free = {k: {a: b for a, b in v.items() if a != "trace"}
                  if isinstance(v, dict) else v
                  for k, v in c["key"].items()}
    res = dict(commit=commit(), rows=chk["rows"], erc=chk["erc"],
               boards=chk["boards"], box=chk["box"], cost={
                   k: v for k, v in chk["cost"].items() if k != "lines"},
               cost_lines=chk["cost"]["lines"],
               calcs={k: v for k, v in c.items() if k not in ("key",
                                                               "wires")},
               key=trace_free, wires=c["wires"],
               sheets=[(s, t) for s, t, _ in made],
               parts=[dict(ref=r, value=p.value, desc=p.desc, board=p.board,
                           mpn=p.mpn, src=p.src, cost=p.cost)
                      for r, p in DS.PARTS.items()],
               extras=DS.EXTRAS, glands=DS.GLANDS,
               pinmaps=pinmaps())
    (RES / "elec_results.json").write_text(
        json.dumps(res, indent=1, default=float) + "\n")
    shutil.copy(RES / "elec_results.json", OUT / "elec_results.json")
    # source and zip
    src = OUT / "source"
    if src.exists():
        shutil.rmtree(src)
    shutil.copytree(HERE / "boaty_elec", src / "boaty_elec",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(HERE / "build_elec.py", src)
    (OUT / "README.txt").write_text(README.format(commit=commit()))
    z = OUT / "Boaty_Mk1_Electrical.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(OUT.rglob("*")):
            if f.is_file() and f != z:
                zf.write(f, f"Boaty_Mk1_Electrical/{f.relative_to(OUT)}")
    n = {s: sum(r["status"] == s for r in chk["rows"])
         for s in ("PASS", "FAIL", "TEST")}
    print(f"zip {z} {z.stat().st_size / 1e6:.1f} MB; checks {n}")


README = """Boaty Mk1 electrical design (BOATY-EDD-001 draft)
Built from commit {commit}. Everything here is generated from
source/boaty_elec/design.py by build_elec.py.

Boaty_Mk1_Schematics.pdf   all six sheets (S1-S6); also per sheet in
                           schematics/ as PDF, SVG and PNG
boaty_mk1.net              netlist, KiCad S-expression format (import into
                           Pcbnew or KiCad's netlist viewer; no footprints)
netlist.csv                every net and pin
wirelist.csv               the harness: every wire with gauge, length,
                           colour, route and cable
bom_electrical.csv         every electrical part, with the KCL BOM line it
                           belongs to ("new" = added by this design)
pinmap_U2.csv, _U6, _U50   flight controller, Pi Zero and Pi 5 pin use
stripboard/                layouts for PIB, MIB and PNL (component side,
                           strips left-right) with cut, link and placement
                           lists; each is proved against the netlist
box_layout.png             what goes where in the electronics box
interconnect.png           boards, modules and cables
elec_results.json          the checks and calculations behind the EDD
"""

if __name__ == "__main__":
    main()
