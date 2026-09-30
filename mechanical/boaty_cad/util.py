"""Shared geometry helpers."""
from __future__ import annotations

import math

import cadquery as cq


def section(x: float, hw: float, zb: float, zt: float, rb: float,
            rt: float) -> cq.Wire:
    """A hull cross-section at station x: a rectangle of half-width hw
    from zb to zt, with bilge radius rb and deck-edge radius rt. Always 9
    edges (it starts mid-bottom), so any two sections loft cleanly."""
    rb = max(0.4, min(rb, hw - 0.4, (zt - zb) / 2 - 0.4))
    rt = max(0.4, min(rt, hw - 0.4, (zt - zb) / 2 - 0.4))
    c = math.cos(math.pi / 4)
    w = (cq.Workplane("YZ", origin=(x, 0, 0))
         .moveTo(0, zb).lineTo(hw - rb, zb)
         .threePointArc((hw - rb + rb * c, zb + rb - rb * c), (hw, zb + rb))
         .lineTo(hw, zt - rt)
         .threePointArc((hw - rt + rt * c, zt - rt + rt * c), (hw - rt, zt))
         .lineTo(-hw + rt, zt)
         .threePointArc((-hw + rt - rt * c, zt - rt + rt * c), (-hw, zt - rt))
         .lineTo(-hw, zb + rb)
         .threePointArc((-hw + rb - rb * c, zb + rb - rb * c), (-hw + rb, zb))
         .close())
    return w.wires().val()


def loft(wires: list[cq.Wire]) -> cq.Solid:
    return cq.Solid.makeLoft(wires, False)


def thread(d_major: float, pitch: float, length: float,
           z0: float = 0.0) -> cq.Solid:
    """External 60° thread ridge on the +z axis from z0 (add it to a core
    of diameter d_major - 1.2·pitch). For an internal thread, cut a bore of
    the minor diameter plus clearance and then cut this with d_major plus
    clearance."""
    h = 0.6 * pitch
    r = d_major / 2 - h
    helix = cq.Wire.makeHelix(pitch, length, r - 0.2,
                              center=cq.Vector(0, 0, z0))
    w = pitch * 0.8
    pts = [(r - 0.2, 0, z0 - w / 2), (r + h, 0, z0 - 0.1),
           (r + h, 0, z0 + 0.1), (r - 0.2, 0, z0 + w / 2)]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(
        [cq.Vector(*p) for p in pts], close=True))
    return (cq.Workplane().add(face)
            .sweep(cq.Workplane().add(helix), isFrenet=True).val())


def threaded_rod(d: float, pitch: float, length: float,
                 z0: float = 0.0) -> cq.Solid:
    core = cq.Solid.makeCylinder(d / 2 - 0.6 * pitch, length,
                                 cq.Vector(0, 0, z0))
    return core.fuse(thread(d, pitch, length - pitch, z0 + pitch / 2)).clean()


def internal_thread_cutter(d: float, pitch: float, length: float,
                           clear: float, z0: float = 0.0) -> cq.Solid:
    """Solid to subtract for a printed internal thread."""
    core = cq.Solid.makeCylinder(d / 2 - 0.6 * pitch + clear, length,
                                 cq.Vector(0, 0, z0))
    return core.fuse(thread(d + 2 * clear, pitch, length, z0)).clean()


def knob(d: float, h: float, n: int = 18) -> cq.Workplane:
    """Knurled knob on the +z axis, edges rounded ≥ 0.6 mm (HUL-D23)."""
    k = cq.Workplane().circle(d / 2).extrude(h).edges().fillet(1.5)
    g = d / 2 + 1.2
    for i in range(n):
        a = 2 * math.pi * i / n
        k = k.cut(cq.Workplane().center(g * math.cos(a), g * math.sin(a))
                  .circle(2.0).extrude(h))
    return k


def rot(shape, axis=(0, 0, 1), deg=0.0, centre=(0, 0, 0)):
    return shape.rotate(cq.Vector(*centre),
                        cq.Vector(*centre) + cq.Vector(*axis), deg)
