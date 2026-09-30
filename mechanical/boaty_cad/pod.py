"""PRP-1 thruster pod: saddle block on the IF-17 dovetail with an
integral latch tongue, swept strut, duct with inlet vanes and nacelle,
screwed rear guard, printed prop, and a reference 2205 motor. Hull frame
(y from the hull centreline), boat x and z.

The pod slides onto the transom rail sideways (along y) and the latch
tooth drops into the rail's centre detent, so the same part fits either
hull from either side.
"""
from __future__ import annotations

import math

import cadquery as cq

from . import params as P

AX = P.POD_AXIS_Z
X_AFT, X_FWD = P.DUCT_X
R_IN, R_OUT = P.DUCT_ID / 2, P.DUCT_OD / 2
MOUNT_X = -5.0                 # motor mount face (motor faces aft)
BELL_X = (MOUNT_X - P.MOTOR_L, MOUNT_X)
PROP_X = (BELL_X[0] - 9.0, BELL_X[0] - 1.0)
BLOCK_X = (-15.0, -0.3)
BLOCK_Z = (P.DOVE_Z - 14.0, P.DOVE_Z + 14.0)
BLOCK_Y = P.DOVE_L / 2


def _rail_profile(clear: float) -> cq.Workplane:
    h, w = P.DOVE_H, P.DOVE_W
    base = w - 2 * h / math.tan(math.radians(P.DOVE_ANGLE))
    c = clear
    return (cq.Workplane("XZ").polyline([
        (1.0, P.DOVE_Z - base / 2 - c), (-h - c, P.DOVE_Z - w / 2 - c),
        (-h - c, P.DOVE_Z + w / 2 + c), (1.0, P.DOVE_Z + base / 2 + c)])
        .close())


def body() -> cq.Workplane:
    # saddle block with the female dovetail
    blk = (cq.Workplane().box(BLOCK_X[1] - BLOCK_X[0], 2 * BLOCK_Y,
                              BLOCK_Z[1] - BLOCK_Z[0],
                              centered=(False, True, False))
           .translate((BLOCK_X[0], 0, BLOCK_Z[0]))
           .edges().fillet(1.2))
    blk = blk.cut(_rail_profile(P.DOVE_CLEAR).extrude(BLOCK_Y + 1,
                                                      both=True))
    # latch tongue: U-slot through the back wall, tooth into the detent
    t_back = BLOCK_X[0]
    slot = (cq.Workplane().box(4, 12, 26).translate((t_back + 2, 0,
                                                    P.DOVE_Z - 2))
            .cut(cq.Workplane().box(4, 8, 24).translate(
                (t_back + 2, 0, P.DOVE_Z - 1))))
    blk = blk.cut(slot)
    blk = blk.cut(cq.Workplane().box(3.8, 8, 24).translate(
        (t_back + 4.6, 0, P.DOVE_Z - 1)))            # thin the tongue
    tooth = cq.Workplane().box(2.4, 6, 8).translate(
        (-P.DOVE_H - P.DOVE_CLEAR - 1.0, 0, P.DOVE_Z - 2))
    tab = (cq.Workplane().box(6, 16, 8).translate(
        (t_back - 3, 0, P.DOVE_Z - 11)).edges().fillet(1.5))
    blk = blk.union(tooth).union(tab)
    # swept strut: leading edge swept back STRUT_SWEEP from the vertical
    ztop, zbot = BLOCK_Z[0] + 2, AX + R_OUT - 1.5
    run = (ztop - zbot) * math.tan(math.radians(P.STRUT_SWEEP))
    le_top, chord = -2.0, 10.0
    strut = (cq.Workplane("XZ").polyline([
        (le_top, ztop), (le_top - run, zbot), (le_top - run - chord, zbot),
        (le_top - chord - 2, ztop)]).close().extrude(3.0, both=True)
        .edges("|Y").fillet(1.2))
    # duct with rounded lips, nacelle, three swept inlet vanes
    duct = (cq.Workplane("YZ", origin=(X_AFT, 0, 0)).center(0, AX)
            .circle(R_OUT).circle(R_IN).extrude(X_FWD - X_AFT)
            .faces(">X or <X").edges().fillet(0.9))
    nac = (cq.Workplane("YZ", origin=(MOUNT_X, 0, 0)).center(0, AX)
           .circle(P.NACELLE_D / 2).workplane(offset=X_FWD - MOUNT_X)
           .circle(P.NACELLE_D / 2).loft()
           .union(cq.Workplane("YZ", origin=(X_FWD, 0, 0)).center(0, AX)
                  .circle(P.NACELLE_D / 2).workplane(offset=11)
                  .circle(2.5).loft()))
    vanes = cq.Workplane()
    for i in range(3):
        v = (cq.Workplane().box(9, 1.6, R_IN - P.NACELLE_D / 2 + 1.5)
             .rotate((0, 0, 0), (0, 0, 1), P.VANE_ANGLE)
             .translate((0.5, 0, P.NACELLE_D / 4 + R_IN / 2)))
        vanes = vanes.union(v.rotate((0, 0, 0), (1, 0, 0), 120 * i)
                            .translate((0, 0, AX)))
    pod = blk.union(strut).union(duct).union(nac).union(vanes)
    # motor mount holes (16 mm square M2, wires out of the nacelle top)
    pts = [(8 * sy, AX + 8 * sz) for sy in (1, -1) for sz in (1, -1)]
    pod = pod.cut(cq.Workplane("YZ", origin=(MOUNT_X - 0.1, 0, 0))
                  .pushPoints(pts).circle(1.1).extrude(7))
    # rear guard bosses (2 × M2.5)
    for sy in (1, -1):
        pod = pod.union(cq.Workplane("YZ", origin=(X_AFT, 0, 0))
                        .center(sy * (R_OUT + 2), AX).circle(3.5)
                        .extrude(8))
        pod = pod.cut(cq.Workplane("YZ", origin=(X_AFT - 0.1, 0, 0))
                      .center(sy * (R_OUT + 2), AX).circle(1.05).extrude(7))
    return pod


def rear_guard() -> cq.Workplane:
    """Outlet guard, 3 mm thick: hub, one ring at r 12.5 and 8 radial
    bars. Largest opening 5.75 mm < 8 mm probe (MEC-010, PRP-D09). Held
    by 2 × M2.5 A2 screws: removing it is an adult, tool action."""
    t = 3.0
    g = (cq.Workplane("YZ").circle(R_OUT).circle(R_IN).extrude(t))
    g = g.union(cq.Workplane("YZ").circle(6.0).extrude(t))
    g = g.union(cq.Workplane("YZ").circle(13.25).circle(11.75).extrude(t))
    for i in range(8):
        a = 360 / 8 * i
        g = g.union(cq.Workplane("YZ").center(0, (R_IN + 5) / 2)
                    .rect(1.5, R_IN - 5).extrude(t)
                    .rotate((0, 0, 0), (1, 0, 0), a))
    for sy in (1, -1):
        g = g.union(cq.Workplane("YZ").center(sy * (R_OUT + 2), 0)
                    .circle(3.5).extrude(t))
        g = g.cut(cq.Workplane("YZ").center(sy * (R_OUT + 2), 0)
                  .circle(1.4).extrude(t))
    g = g.edges("|X").fillet(0.3)
    return g.translate((X_AFT - t, 0, AX))


def guard_openings() -> dict[str, float]:
    """Inscribed-circle size of every opening a probe could enter."""
    bar = 1.5
    # a cell between two bars and two rings admits a circle no larger
    # than the smaller of its radial depth and its narrowest chord
    inner = min(11.75 - 6.0, 2 * math.pi * 6.0 / 8 - bar)
    outer = min(R_IN - 13.25, 2 * math.pi * 13.25 / 8 - bar)
    return {
        "inlet annulus (nacelle to duct)": R_IN - P.NACELLE_D / 2,
        "guard cells, hub to ring": inner,
        "guard cells, ring to duct": outer,
    }


def prop() -> cq.Workplane:
    """Printed 3-blade prop, Ø35, 12 mm hub on the M5 shaft (prop nut).
    Blades skewed back 25° (PRP-D10), pitch angle 28° at 0.7 R."""
    x0, x1 = PROP_X
    hub = (cq.Workplane("YZ", origin=(x0, 0, 0)).circle(P.PROP_HUB / 2)
           .extrude(x1 - x0).faces("<X").edges().fillet(2))
    r0, r1 = P.PROP_HUB / 2 - 0.5, P.PROP_D / 2
    blades = cq.Workplane()
    for i in range(3):
        b = (cq.Workplane("XY").polyline([
            (-4.5, r0), (4.5, r0), (2.0 - 3.5, r1), (-3.5 - 3.5, r1)])
            .close().extrude(1.4).translate((0, 0, -0.7))
            .edges("|Z").fillet(0.5)
            .rotate((0, 0, 0), (0, 1, 0), 28))
        blades = blades.union(b.rotate((0, 0, 0), (1, 0, 0), 120 * i))
    pr = hub.union(blades.translate(((x0 + x1) / 2, 0, 0)))
    pr = pr.cut(cq.Workplane("YZ", origin=(x0 - 1, 0, 0)).circle(2.55)
                .extrude(x1 - x0 + 2))
    return pr.translate((0, 0, AX))


def motor() -> cq.Workplane:
    """2205-class outrunner (KC-04), reference: stator base on the mount
    face, bell and M5 shaft aft."""
    m = (cq.Workplane("YZ", origin=(BELL_X[0], 0, 0)).center(0, AX)
         .circle(P.MOTOR_BELL_D / 2).extrude(P.MOTOR_L))
    shaft = (cq.Workplane("YZ", origin=(PROP_X[0] - 3, 0, 0)).center(0, AX)
             .circle(2.5).extrude(BELL_X[0] - PROP_X[0] + 3))
    return m.union(shaft)
