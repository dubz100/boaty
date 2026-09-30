"""HUL-1: the six hull segments (three part designs, each used on both
hulls: the segments are symmetric about their own centreline), the joint
dowels and the thumb-screws that close each joint (IF-16).

Construction: a thin PETG shell, open at every joint face, filled flush
with two-part closed-cell PU foam poured through the open end and trimmed.
The foam is the core of a sandwich: the shell is a skin, and the joint
flange, dowel bosses and screw lugs are the only thick printed features.

Each builder returns (part, foam) in the hull frame: boat x, y from the
hull centreline, z from the keel.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import params as P
from .util import (internal_thread_cutter, knob, loft, section,
                   threaded_rod)


# ---------------------------------------------------------------- lines
def bow_station(x: float) -> tuple[float, float]:
    """(half-breadth, keel height) of the bow at station x."""
    s = (x - P.X_J2 - P.BOW_FLAT) / (P.L_BOW - P.BOW_FLAT)
    s = min(max(s, 0.0), 1.0)
    hw = P.STEM_HALF + (P.B / 2 - P.STEM_HALF) * (1 - s ** 2.2) ** 0.55
    zb = P.BOW_KEEL_RISE * s ** 1.7
    return hw, zb


def _sec(x: float, off: float, hw: float | None = None,
         zb: float = 0.0) -> cq.Wire:
    hw = P.B / 2 if hw is None else hw
    return section(x, hw - off, zb + off, P.D - off, P.R_BILGE - off,
                   P.R_DECK - off)


def _prism(x0: float, x1: float, off: float) -> cq.Solid:
    return loft([_sec(x0, off), _sec(x1, off)])


def _bow_loft(x0: float, x1: float, off: float, n: int = 9) -> cq.Solid:
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
    xs = sorted(set([x0, P.X_J2 + P.BOW_FLAT] + xs))
    xs = [x for x in xs if x0 <= x <= x1]
    wires = []
    for x in xs:
        hw, zb = bow_station(x)
        wires.append(_sec(x, off, hw, zb))
    return loft(wires)


# ---------------------------------------------------------------- features
def _dowel_bosses(xj: float, into: int) -> cq.Workplane:
    """Solid bosses behind the dowel positions, webbed to the bottom.
    into = +1 if the segment lies forward of the joint."""
    L = P.DOWEL_ENG + 6
    x0 = xj if into > 0 else xj - L
    out = cq.Workplane()
    for y, z in P.DOWEL_POS:
        c = cq.Workplane("YZ", origin=(x0, 0, 0)).center(y, z).circle(
            P.DOWEL_BOSS_D / 2).extrude(L)
        web = cq.Workplane().box(L, P.DOWEL_BOSS_D, z, centered=(
            False, True, False)).translate((x0, y, 0))
        out = out.union(c).union(web)
    return out


def _dowel_holes(xj: float, into: int) -> cq.Workplane:
    d = P.DOWEL_D + P.DOWEL_CLEAR
    L = P.DOWEL_ENG + 1
    x0 = xj if into > 0 else xj - L
    out = cq.Workplane()
    for y, z in P.DOWEL_POS:
        out = out.union(cq.Workplane("YZ", origin=(x0, 0, 0)).center(y, z)
                        .circle(d / 2).extrude(L))
    return out


def _lug(xj: float, into: int, y: float) -> cq.Workplane:
    """A screw lug on the deck, one face flush with the joint face."""
    x0 = xj if into > 0 else xj - P.LUG_L
    h = P.SCREW_Z + 9 - P.D + 1
    lug = (cq.Workplane().box(P.LUG_L, P.LUG_W, h, centered=(False, True,
                                                            False))
           .translate((x0, y, P.D - 1))
           .edges("|X").fillet(3).edges("not |X").chamfer(0.8))
    return lug


def _lug_thread(xj: float, into: int, y: float) -> cq.Solid:
    cut = internal_thread_cutter(P.SCREW_D, P.SCREW_P, P.LUG_L + 2,
                                 P.SCREW_CLEAR, -1)
    cut = cut.rotate(cq.Vector(), cq.Vector(0, 1, 0), 90)   # along +x
    x0 = xj if into > 0 else xj - P.LUG_L
    return cut.translate(cq.Vector(x0, y, P.SCREW_Z))


def _joint(part: cq.Workplane, xj: float, into: int, threaded_lugs: bool,
           dowels_fitted: bool) -> cq.Workplane:
    part = part.union(_chunk(_dowel_bosses(xj, into)))
    for y in (P.SCREW_Y, -P.SCREW_Y):
        part = part.union(_chunk(_lug(xj, into, y)))
    for y in (P.SCREW_Y, -P.SCREW_Y):
        part = part.cut(cq.Workplane().add(_lug_thread(xj, into, y)))
    if not dowels_fitted:
        part = part.cut(_dowel_holes(xj, into))
    else:
        # the dowels are bonded in this side; model the bonding sockets
        part = part.cut(_dowel_holes(xj, into))
    return part


def _flange_cavity(x0: float, x1: float) -> cq.Solid:
    """Inner cavity over a flange: the wall is FLANGE_WALL thick here."""
    return _prism(x0, x1, P.FLANGE_WALL)


def _beam_bosses(yc: float = 0.0) -> tuple[cq.Workplane, cq.Workplane]:
    """M4 heat-set insert bosses under each beam end (mid segment)."""
    boss = cq.Workplane()
    holes = cq.Workplane()
    for bx in P.BEAM_X:
        for dy in (P.BEAM_BOLT_DY, -P.BEAM_BOLT_DY):
            boss = boss.union(cq.Workplane().center(bx, dy)
                              .circle(P.INSERT_BOSS_D / 2)
                              .extrude(P.INSERT_DEPTH + 3)
                              .translate((0, 0, P.D - P.INSERT_DEPTH - 3)))
            holes = holes.union(cq.Workplane().center(bx, dy)
                                .circle(P.INSERT_D / 2)
                                .extrude(P.INSERT_DEPTH + 1)
                                .translate((0, 0, P.D - P.INSERT_DEPTH)))
    return boss, holes


# ---------------------------------------------------------------- segments
CHUNKY: list = []      # solid printed features, weighed with infill


def _chunk(w: cq.Workplane) -> cq.Workplane:
    CHUNKY.append(w)
    return w


def _foam(cavity: cq.Workplane, part: cq.Workplane) -> cq.Workplane:
    """The foam core: the shell's inner space less every printed feature
    that reaches into it (flange, bosses, lugs), trimmed flush with the
    joint faces."""
    return cavity.cut(part).clean()


def mid_segment() -> tuple[cq.Workplane, cq.Workplane]:
    x0, x1 = P.X_J1, P.X_J2
    outer = cq.Workplane().add(_prism(x0, x1, 0))
    cav = (cq.Workplane().add(_prism(x0 + P.FLANGE_DEPTH - 0.01,
                                     x1 - P.FLANGE_DEPTH + 0.01, P.T_SHELL))
           .union(cq.Workplane().add(_flange_cavity(x0 - 1, x0 +
                                                    P.FLANGE_DEPTH)))
           .union(cq.Workplane().add(_flange_cavity(x1 - P.FLANGE_DEPTH,
                                                    x1 + 1))))
    part = outer.cut(cav)
    boss, holes = _beam_bosses()
    pocket_boss = (cq.Workplane().center(P.POCKET_X, 0)
                   .circle(P.POCKET_D / 2 + 3).extrude(P.POCKET_DEPTH + 2)
                   .translate((0, 0, P.D - P.POCKET_DEPTH - 2)))
    part = part.union(_chunk(boss.intersect(outer))).union(
        _chunk(pocket_boss))
    part = part.cut(holes)
    # tracker pocket (REC-D05): sealed by a cap on an O-ring, 3 × M3
    part = part.cut(cq.Workplane().center(P.POCKET_X, 0)
                    .circle(P.POCKET_D / 2).extrude(P.POCKET_DEPTH)
                    .translate((0, 0, P.D - P.POCKET_DEPTH)))
    for i in range(3):
        a = math.radians(90 + 120 * i)
        part = part.cut(cq.Workplane().center(
            P.POCKET_X + 21 * math.cos(a), 21 * math.sin(a))
            .circle(1.25).extrude(8).translate((0, 0, P.D - 8)))
    # label recesses (REC-D04), both sides so one part serves both hulls
    lx, lz, ld = P.LABEL
    for s in (1, -1):
        part = part.cut(cq.Workplane().box(lx, ld * 2, lz)
                        .translate(((x0 + x1) / 2 - 10, s * P.B / 2,
                                    P.D * 0.62)))
    part = _joint(part, x0, +1, threaded_lugs=True, dowels_fitted=True)
    part = _joint(part, x1, -1, threaded_lugs=True, dowels_fitted=True)
    foam = _foam(cq.Workplane().add(_prism(x0, x1, P.T_SHELL)), part)
    return part.clean(), foam


def stern_segment() -> tuple[cq.Workplane, cq.Workplane]:
    x0, x1 = 0.0, P.X_J1
    outer = cq.Workplane().add(_prism(x0, x1, 0))
    cav = (cq.Workplane().add(_prism(x0 + P.T_END, x1 - P.FLANGE_DEPTH +
                                     0.01, P.T_SHELL))
           .union(cq.Workplane().add(_flange_cavity(x1 - P.FLANGE_DEPTH,
                                                    x1 + 1))))
    part = outer.cut(cav)
    # transom backing block behind the dovetail rail (foam backs the rest)
    back = (cq.Workplane().box(12, P.DOVE_L + 16, P.DOVE_W + 16)
            .translate((P.T_END + 6, 0, P.DOVE_Z)))
    part = part.union(_chunk(back.intersect(outer)))
    part = part.union(_chunk(dovetail_rail()))
    # cable clips for the motor lead on the inboard deck edge (both sides)
    for s in (1, -1):
        for cx in (60.0, 140.0):
            clip = (cq.Workplane("XZ", origin=(0, s * (P.B / 2 - 9), 0))
                    .center(cx, P.D + 4).rect(10, 9).extrude(5, both=True)
                    .cut(cq.Workplane("XZ", origin=(0, s * (P.B / 2 - 9), 0))
                         .center(cx, P.D + 3.5).circle(3.2).extrude(
                             10, both=True))
                    .cut(cq.Workplane().box(10, 2.5, 5).translate(
                        (cx, s * (P.B / 2 - 9), P.D + 7.5))))
            part = part.union(clip)
    part = _joint(part, x1, -1, threaded_lugs=False, dowels_fitted=False)
    foam = _foam(cq.Workplane().add(_prism(x0 + P.T_END, x1, P.T_SHELL)),
                 part)
    return part.clean(), foam


def bow_segment() -> tuple[cq.Workplane, cq.Workplane]:
    x0, x1 = P.X_J2, P.X_STEM
    outer = cq.Workplane().add(_bow_loft(x0, x1, 0))
    cav = (cq.Workplane().add(_bow_loft(x0 + P.FLANGE_DEPTH - 0.01,
                                        x1 - P.T_END, P.T_SHELL))
           .union(cq.Workplane().add(_flange_cavity(x0 - 1, x0 +
                                                    P.FLANGE_DEPTH))))
    part = outer.cut(cav)
    part = _joint(part, x0, +1, threaded_lugs=False, dowels_fitted=False)
    foam = _foam(cq.Workplane().add(_bow_loft(x0, x1 - P.T_END,
                                              P.T_SHELL)), part)
    return part.clean(), foam


def outer_hull() -> cq.Workplane:
    """One hull's outer envelope (for hydrostatics)."""
    return (cq.Workplane().add(_prism(0, P.X_J2, 0))
            .union(cq.Workplane().add(_bow_loft(P.X_J2, P.X_STEM, 0))))


def dovetail_rail() -> cq.Workplane:
    """IF-17 male rail on the transom: 60°, 20 mm high at the face, 40 mm
    long along y, with a centre detent pocket for the pod latch."""
    h, w = P.DOVE_H, P.DOVE_W
    base = w - 2 * h / math.tan(math.radians(P.DOVE_ANGLE))
    rail = (cq.Workplane("XZ").polyline([(0.5, P.DOVE_Z - base / 2),
                                         (-h, P.DOVE_Z - w / 2),
                                         (-h, P.DOVE_Z + w / 2),
                                         (0.5, P.DOVE_Z + base / 2)]).close()
            .extrude(P.DOVE_L / 2, both=True))
    rail = rail.edges("|Y").fillet(0.8)
    detent = cq.Workplane().box(3.0, 7, 9).translate((-h + 1.2, 0,
                                                       P.DOVE_Z))
    return rail.cut(detent)


# ---------------------------------------------------------------- hardware
def thumb_screw() -> cq.Workplane:
    """IF-16 captive thumb-screw: Ø35 knob, Ø9 neck that turns freely in
    the threaded lug once through it, M12 × 1.75 printed thread. Along +z;
    the knob is at z < 0."""
    k = knob(P.KNOB_D, P.KNOB_H).translate((0, 0, -P.KNOB_H))
    k = k.cut(cq.Workplane().circle(13).circle(7).extrude(6)
              .translate((0, 0, -P.KNOB_H)))         # cored underside
    neck = cq.Workplane().circle(P.NECK_D / 2).extrude(P.NECK_L)
    rod = cq.Workplane().add(threaded_rod(P.SCREW_D, P.SCREW_P, P.THREAD_L,
                                          P.NECK_L))
    tip = (cq.Workplane().circle(P.SCREW_D / 2 - 1.2).extrude(1.0)
           .translate((0, 0, P.NECK_L + P.THREAD_L)))
    return k.union(neck).union(rod).union(tip)


def dowel() -> cq.Workplane:
    """Ø8 × 20 printed dowel, bonded 10 mm into the end segment's joint
    face (so it is never a loose part), lead-in chamfer."""
    return (cq.Workplane().circle(P.DOWEL_D / 2).extrude(2 * P.DOWEL_ENG)
            .faces(">Z").chamfer(1.2).faces("<Z").chamfer(0.5))


def pocket_cap() -> cq.Workplane:
    c = (cq.Workplane().circle(P.POCKET_CAP_D / 2).extrude(3)
         .edges(">Z").fillet(1.2))
    c = c.cut(cq.Workplane().circle(P.POCKET_D / 2 + 1.2).circle(
        P.POCKET_D / 2).extrude(0.8))      # O-ring groove (Ø1 cord)
    for i in range(3):
        a = math.radians(90 + 120 * i)
        c = c.cut(cq.Workplane().center(21 * math.cos(a), 21 * math.sin(a))
                  .circle(1.7).extrude(3))
    return c


def build(kind: str) -> tuple[cq.Workplane, cq.Workplane, list]:
    """(part, foam core, chunky printed features) for 'bow', 'mid' or
    'stern'."""
    CHUNKY.clear()
    part, foam = {"bow": bow_segment, "mid": mid_segment,
                  "stern": stern_segment}[kind]()
    return part, foam, list(CHUNKY)
