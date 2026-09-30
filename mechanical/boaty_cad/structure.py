"""HUL-2..5: crossbeams, electronics box (bought, modelled for fit), saddle
tray with over-centre latches, camera hood and window, DUPLO deck plate,
arming key and key dock. All in the boat frame."""
from __future__ import annotations

import math

import cadquery as cq

from . import params as P

Z_BEAM = P.D                      # beams sit on the hull decks
Z_TRAY = P.D + P.BEAM_H           # tray underside
Z_BOX = Z_TRAY + P.TRAY_T         # box underside
Z_LID = Z_BOX + P.BOX_H           # box lid top
BOX_X1 = P.BOX_X0 + P.BOX_L
LENS_Z = Z_BOX + P.LENS_Z_ABOVE_BOX


# ---------------------------------------------------------------- beams
def crossbeam(x: float) -> cq.Workplane:
    """20 × 10 × 1.5 mm aluminium tube with the M3 rail grid (two rows,
    10 mm pitch) and the M4 holes to the mid segments' inserts."""
    L = P.BEAM_L
    b = (cq.Workplane().box(P.BEAM_W, L, P.BEAM_H)
         .faces("+Y or -Y").shell(-P.BEAM_T)
         .translate((x, 0, Z_BEAM + P.BEAM_H / 2)))
    n = int((L - 20) // P.RAIL_PITCH) + 1
    ys = [-(n - 1) * P.RAIL_PITCH / 2 + i * P.RAIL_PITCH for i in range(n)]
    for dx in (-5.0, 5.0):
        pts = [(x + dx, y) for y in ys
               if all(abs(abs(y) - (P.HULL_Y + s * P.BEAM_BOLT_DY)) > 6
                      for s in (1, -1))]
        b = b.cut(cq.Workplane().pushPoints(pts).circle(P.RAIL_HOLE / 2)
                  .extrude(3).translate((0, 0, Z_BEAM + P.BEAM_H - 2)))
    bolts = [(x, s * (P.HULL_Y + d * P.BEAM_BOLT_DY)) for s in (1, -1)
             for d in (1, -1)]
    return b.cut(cq.Workplane().pushPoints(bolts).circle(2.2)
                 .extrude(P.BEAM_H + 2).translate((0, 0, Z_BEAM - 1)))


def beam_cap() -> cq.Workplane:
    """Printed end cap, pushed into each beam end (rounded, HUL-D23)."""
    cap = (cq.Workplane().box(P.BEAM_W + 1, 6, P.BEAM_H + 1)
           .edges().fillet(2.5))
    plug = cq.Workplane().box(P.BEAM_W - 2 * P.BEAM_T - 0.3, 10,
                              P.BEAM_H - 2 * P.BEAM_T - 0.3).translate(
        (0, -7.9, 0))
    return cap.union(plug)


# ---------------------------------------------------------------- box
def box_body() -> cq.Workplane:
    """Clip-lock box body (bought; IF-18), with the modifications: 4 × PG7
    holes in the aft face, window hole in the front face."""
    h = P.BOX_H - P.BOX_LID_H
    body = (cq.Workplane().box(P.BOX_L, P.BOX_W, h, centered=(False, True,
                                                            False))
            .edges("|Z").fillet(10).faces(">Z").shell(-P.BOX_WALL)
            .translate((P.BOX_X0, 0, Z_BOX)))
    ys = [(i - 1.5) * P.GLAND_PITCH for i in range(4)]
    body = body.cut(cq.Workplane("YZ", origin=(P.BOX_X0 - 1, 0, 0))
                    .pushPoints([(y, Z_BOX + P.GLAND_Z) for y in ys])
                    .circle(P.GLAND_HOLE / 2).extrude(P.BOX_WALL + 2))
    body = body.cut(cq.Workplane("YZ", origin=(BOX_X1 - P.BOX_WALL - 1, 0,
                                               0))
                    .center(0, LENS_Z).circle(P.WINDOW_D / 2)
                    .extrude(P.BOX_WALL + 2))
    return body


def box_lid() -> cq.Workplane:
    lid = (cq.Workplane().box(P.BOX_L, P.BOX_W, P.BOX_LID_H,
                              centered=(False, True, False))
           .edges("|Z").fillet(10).faces("<Z").shell(-P.BOX_WALL)
           .edges(">Z").fillet(3)
           .translate((P.BOX_X0, 0, Z_LID - P.BOX_LID_H)))
    # the box's own four clips (two per long side)
    for x in (P.BOX_X0 + 45, BOX_X1 - 45):
        for s in (1, -1):
            lid = lid.union(cq.Workplane().box(40, 3, 22).translate(
                (x, s * (P.BOX_W / 2 + 1.5), Z_LID - P.BOX_LID_H - 4)))
    return lid


def gland(y: float) -> cq.Workplane:
    """PG7 cable gland, nylon, on the aft face (reference)."""
    g = (cq.Workplane("YZ", origin=(P.BOX_X0 - 1, 0, 0))
         .center(y, Z_BOX + P.GLAND_Z).polygon(6, 17.3).extrude(-6)
         .union(cq.Workplane("YZ", origin=(P.BOX_X0 - 7, 0, 0))
                .center(y, Z_BOX + P.GLAND_Z).circle(7.5).extrude(-11)))
    return g


# ---------------------------------------------------------------- tray
TRAY_HW = P.BOX_W / 2 + 0.8 + 3.0       # 0.8 mm clearance, 3 mm walls


def tray() -> cq.Workplane:
    """HUL-3 saddle: a 4 mm plate across both beams, side walls that
    locate the box, an aft stop, a cable slot behind the box, bolted
    through the beams' M3 grid; pivot bosses for the two latches."""
    x0, x1 = P.TRAY_X
    t = (cq.Workplane().box(x1 - x0, 2 * TRAY_HW, P.TRAY_T,
                            centered=(False, True, False))
         .edges("|Z").fillet(6).translate((x0, 0, Z_TRAY)))
    for s in (1, -1):
        wall = cq.Workplane().box(x1 - P.BOX_X0 + 2, 3.0, P.TRAY_WALL_H,
                                  centered=(False, True, False)).translate(
            (P.BOX_X0 - 2, s * (TRAY_HW - 1.5), Z_BOX))
        t = t.union(wall.edges(">Z").fillet(1.2))
    stop = cq.Workplane().box(3, 2 * TRAY_HW, P.TRAY_WALL_H,
                              centered=(False, True, False)).translate(
        (P.BOX_X0 - 3.8, 0, Z_BOX))
    t = t.union(stop.edges(">Z").fillet(1.2))
    # lightening windows between the beams and under the box
    for cx, lx in (((P.BEAM_X[0] + P.BEAM_X[1]) / 2, 62.0),
                   (P.BOX_X0 + 108.0, 72.0)):
        t = t.cut(cq.Workplane().box(lx, 2 * TRAY_HW - 30, 10)
                  .edges("|Z").fillet(8).translate((cx, 0, Z_TRAY)))
    # cable slot behind the box (glands exit aft, leads drop through)
    t = t.cut(cq.Workplane().box(18, 90, 10).edges("|Z").fillet(6)
              .translate((P.BOX_X0 - 16, 0, Z_TRAY)))
    # M3 bolts into the beam grid: 2 per beam
    pts = [(bx + dx, s * 45.0) for bx in P.BEAM_X for dx in (-5.0,)
           for s in (1, -1)]
    t = t.cut(cq.Workplane().pushPoints(pts).circle(1.7).extrude(10)
              .translate((0, 0, Z_TRAY - 1)))
    # latch pivot bosses
    for s in (1, -1):
        boss = (cq.Workplane("XZ", origin=(0, s * (TRAY_HW + 3), 0))
                .center(P.LATCH_X, Z_BOX + 6).circle(5).extrude(3, both=True)
                .union(cq.Workplane().box(14, 6, 10).translate(
                    (P.LATCH_X, s * (TRAY_HW + 3), Z_BOX + 1))))
        boss = boss.cut(cq.Workplane("XZ", origin=(0, s * (TRAY_HW + 3), 0))
                        .center(P.LATCH_X, Z_BOX + 6).circle(1.6)
                        .extrude(5, both=True))
        t = t.union(boss)
    return t


def latch(side: int) -> cq.Workplane:
    """Over-centre latch lever: pivots on the tray boss (M3 stainless pin),
    hooks the keeper on the box side. The toggle passes centre by 2 mm
    and the lever has a flexure detent sized to need ≥ 40 N at the tab
    (HUL-D24), checked on the bench. Closed position shown."""
    y = side * (TRAY_HW + 8.5)
    lever = (cq.Workplane("XZ", origin=(0, y, 0))
             .center(P.LATCH_X, Z_BOX + 30).rect(14, 56).extrude(2.5,
                                                                 both=True)
             .edges("|Y").fillet(3))
    hook = (cq.Workplane().box(14, 8, 4).translate(
        (P.LATCH_X, y - side * 3.0, Z_BOX + 56)))
    tab = (cq.Workplane().box(20, 3, 12).translate(
        (P.LATCH_X, y + side * 3.5, Z_BOX + 48)).edges().fillet(1.2))
    eye = (cq.Workplane("XZ", origin=(0, y, 0)).center(P.LATCH_X, Z_BOX + 6)
           .circle(5).extrude(2.5, both=True))
    lv = lever.union(hook).union(tab).union(eye)
    return lv.cut(cq.Workplane("XZ", origin=(0, y, 0))
                  .center(P.LATCH_X, Z_BOX + 6).circle(1.65)
                  .extrude(4, both=True))


def keeper(side: int) -> cq.Workplane:
    """Printed keeper bonded to the box side (sealant-free: no hole)."""
    y = side * (P.BOX_W / 2 + 2.0)
    k = cq.Workplane().box(18, 4, 8).translate((P.LATCH_X, y, Z_BOX + 50))
    return k.edges("|Y").fillet(1.5)


# ---------------------------------------------------------------- camera
def camera_hood() -> cq.Workplane:
    """HUL-5 spray hood: bonded to the box front around the window, open
    at the front and bottom so a cloth reaches the window (HUL-D19)."""
    w, h, t, L = 56.0, 46.0, 2.0, P.HOOD_OVERHANG + 3
    outer = cq.Workplane().box(L, w, h, centered=(False, True, True))
    inner = cq.Workplane().box(L + 2, w - 2 * t, h - t,
                               centered=(False, True, True)).translate(
        (-1, 0, -t / 2 - 0.01))
    hood = outer.cut(inner).cut(cq.Workplane().box(L + 2, w - 2 * t, 10)
                                .translate((L / 2, 0, -h / 2)))
    flange = (cq.Workplane().box(2, w + 12, h + 8,
                                 centered=(False, True, True))
              .cut(cq.Workplane().box(4, P.WINDOW_D + 12, P.WINDOW_D + 12,
                                      centered=(False, True, True))
                   .translate((-1, 0, 0))))
    hood = hood.union(flange).edges("|X").fillet(0.8)
    return hood.translate((BOX_X1, 0, LENS_Z + h / 2 - 22))


def window() -> cq.Workplane:
    """2 mm acrylic disc bonded over the window hole (bought/cut)."""
    return (cq.Workplane("YZ", origin=(BOX_X1, 0, 0)).center(0, LENS_Z)
            .circle(P.WINDOW_D / 2 + 5).extrude(2))


def camera() -> cq.Workplane:
    """OV5647 module (KC-11), reference, inside behind the window."""
    board = cq.Workplane().box(9, 25, 24).translate(
        (BOX_X1 - P.BOX_WALL - 8, 0, LENS_Z - 2.5))
    lens = (cq.Workplane("YZ", origin=(BOX_X1 - P.BOX_WALL - 4, 0, 0))
            .center(0, LENS_Z).circle(4).extrude(3.5))
    return board.union(lens)


# ---------------------------------------------------------------- DUPLO
def duplo_plate() -> cq.Workplane:
    """IF-20 plate: 6 × 8 studs at 16 mm pitch, bored through so rain
    drains (HUL-D13), clips over the lid's long edges (≤ 20 N, HUL-D25).
    Rests on the lid; lifted off for box access."""
    gx = P.STUD_NX * P.STUD_PITCH
    gy = P.STUD_NY * P.STUD_PITCH
    bx0, bx1 = P.PLATE_X0 - 6, P.PLATE_X0 + gx + 6
    base = (cq.Workplane().box(bx1 - bx0, gy + 8, P.PLATE_T,
                               centered=(False, True, False))
            .edges("|Z").fillet(8).edges(">Z").fillet(1.0)
            .translate((bx0, 0, Z_LID)))
    pts = [(P.PLATE_X0 + P.STUD_PITCH * (i + 0.5),
            -gy / 2 + P.STUD_PITCH * (j + 0.5))
           for i in range(P.STUD_NX) for j in range(P.STUD_NY)]
    studs = (cq.Workplane().pushPoints(pts).circle(P.STUD_D / 2)
             .extrude(P.STUD_H).translate((0, 0, Z_LID + P.PLATE_T))
             .edges(">Z").chamfer(0.6))
    plate = base.union(studs)
    plate = plate.cut(cq.Workplane().pushPoints(pts).circle(P.STUD_BORE / 2)
                      .extrude(P.PLATE_T + P.STUD_H + 2).translate(
                          (0, 0, Z_LID - 1)))
    # side clips over the lid edge (snap lip 0.8 mm)
    for s in (1, -1):
        for cx in (bx0 + 25, bx1 - 25):
            aw = (P.BOX_W - gy) / 2 + 3
            arm = cq.Workplane().box(24, aw, P.PLATE_T).translate(
                (cx, s * (gy / 2 + aw / 2), Z_LID + P.PLATE_T / 2))
            plate = plate.union(arm)
            clip = (cq.Workplane().box(24, 2.4, 12).translate(
                (cx, s * (P.BOX_W / 2 + 1.2 + 0.2), Z_LID - 6 + P.PLATE_T
                 / 2))
                .union(cq.Workplane().box(24, 1.6, 1.6).translate(
                    (cx, s * (P.BOX_W / 2 - 0.6), Z_LID - 11))))
            plate = plate.union(clip.edges("|X").fillet(0.6))
    return plate


def key_dock() -> cq.Workplane:
    """IF-18 key dock: a cup bonded to the lid over the reed switch, with
    'KEY' raised on its floor."""
    cup = (cq.Workplane().box(46, 42, 5).edges("|Z").fillet(6)
           .translate((P.KEY_X, 0, Z_LID + 2.5)))
    cup = cup.cut(cq.Workplane().box(41, 37, 5).edges("|Z").fillet(4)
                  .translate((P.KEY_X, 0, Z_LID + 3.5)))
    txt = (cq.Workplane().text("KEY", 8, 0.6, halign="center",
                               valign="center")
           .rotate((0, 0, 0), (0, 0, 1), 90)
           .translate((P.KEY_X - 12, 0, Z_LID + 1.0)))
    return cup.union(txt)


def arming_key() -> cq.Workplane:
    """Magnet key (KC-07): 40 × 36 × 9 fob, Ø20 × 3 magnet bonded in,
    lanyard hole. 36 mm minimum width: not a small part (CHD-001)."""
    fob = (cq.Workplane().box(40, 36, 9).edges("|Z").fillet(8)
           .edges().fillet(1.0))
    fob = fob.cut(cq.Workplane().circle(10.1).extrude(3.2).translate(
        (0, 0, -4.5)))
    fob = fob.cut(cq.Workplane().center(14, 0).slot2D(10, 5, 90)
                  .extrude(12).translate((0, 0, -6)))
    return fob.translate((P.KEY_X, 0, Z_LID + 1.5 + 4.5))


def electronics() -> dict[str, tuple[float, float, float, float, tuple]]:
    """Box contents for the mass properties: name -> (mass g, x, y, z,
    size). Masses from ADD A.MASS / KCL; the battery sits low and aft to
    bring the centre of gravity to the handle (HUL-D21)."""
    zb = Z_BOX + P.BOX_WALL
    x0 = P.BOX_X0 + P.BOX_WALL
    return {
        "Battery 3S 18650 + BMS": (160.0, x0 + 40, 0, zb + 10,
                                   (66, 57, 20)),
        "Flight controller + PDB": (25.0, x0 + 110, 25, zb + 8,
                                    (52, 32, 12)),
        "Pi Zero 2 W + SD": (22.0, x0 + 120, -30, zb + 30, (65, 30, 6)),
        "ESCs (2)": (30.0, x0 + 80, 30, zb + 30, (30, 25, 12)),
        "Power module, buck, key switch": (30.0, x0 + 90, -25, zb + 8,
                                           (40, 25, 12)),
        "Wiring and connectors": (60.0, x0 + 60, 0, zb + 25, (120, 90, 30)),
    }
