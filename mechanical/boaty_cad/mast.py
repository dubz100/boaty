"""HUL-4 and REC: mast step and carry handle, mast tube, collar with the
recovery hoop and flag-staff socket, flag staff, masthead (GNSS dome and
LED ring), and the mast's captive thumb-screw. Boat frame."""
from __future__ import annotations

import cadquery as cq

from . import params as P
from .util import internal_thread_cutter, knob, threaded_rod

Z0 = P.D + P.BEAM_H                   # top of the aft beam
X = P.MAST_X
SOCKET_TOP = Z0 + P.SOCKET_DEPTH + 5
UPRIGHT_Y = 88.0
M8 = (8.0, 1.25)
SCREW_Z = Z0 + 30.0


def step_and_handle() -> cq.Workplane:
    """One printed part (188 mm across: MEC-005). A saddle over the aft
    beam, bolted with 4 × M3 through the beam; the IF-19 socket (50 mm
    deep) at the centre; a Ø22 grip bar either side of the socket, 41 mm
    finger clearance, within ± 50 mm of the centre of gravity (HUL-D21)."""
    base = cq.Workplane()
    for y in (0.0, UPRIGHT_Y, -UPRIGHT_Y):
        base = base.union(cq.Workplane().box(P.BEAM_W + 8, 20, 4,
                                             centered=(True, True, False))
                          .edges("|Z").fillet(3.0).translate((X, y, Z0)))
    cheeks = cq.Workplane()
    for dx in (-(P.BEAM_W / 2 + 2), P.BEAM_W / 2 + 2):
        for y in (0.0, UPRIGHT_Y, -UPRIGHT_Y):
            cheeks = cheeks.union(cq.Workplane().box(4, 16, 8).translate(
                (X + dx, y, Z0 - 4)))
    tower = (cq.Workplane().circle(P.SOCKET_OD / 2)
             .extrude(SOCKET_TOP - Z0).translate((X, 0, Z0)))
    boss = (cq.Workplane("YZ", origin=(X - P.SOCKET_OD / 2 + 2, 0, 0))
            .center(0, SCREW_Z).circle(8).extrude(-8))
    grip = (cq.Workplane("XZ", origin=(0, UPRIGHT_Y + 6, 0))
            .center(X, P.GRIP_Z).circle(P.GRIP_D / 2)
            .extrude(2 * UPRIGHT_Y + 12))
    ups = cq.Workplane()
    for s in (1, -1):
        ups = ups.union(cq.Workplane().box(P.BEAM_W + 4, 12,
                                           P.GRIP_Z - Z0 + 2)
                        .edges("|Z").fillet(2.0)
                        .translate((X, s * UPRIGHT_Y,
                                    Z0 + (P.GRIP_Z - Z0 + 2) / 2)))
    part = base.union(cheeks).union(tower).union(boss).union(grip).union(
        ups)
    bore = (cq.Workplane().circle(P.MAST_D / 2 + 0.25)
            .extrude(P.SOCKET_DEPTH + 10).translate((X, 0, Z0 + 2)))
    part = part.cut(bore)
    thr = internal_thread_cutter(M8[0], M8[1], 20, 0.4, 0).rotate(
        cq.Vector(), cq.Vector(0, 1, 0), -90).translate(
        cq.Vector(X - 2, 0, SCREW_Z))
    part = part.cut(cq.Workplane().add(thr))
    for y in (0.0, UPRIGHT_Y):
        for s in (1, -1):
            if y == 0.0 and s < 0:
                continue
            part = part.cut(cq.Workplane().center(X - 5, s * (y or 22))
                            .circle(1.7).extrude(12).translate(
                                (0, 0, Z0 - 1)))
    # cable exit: the GNSS/LED lead leaves the tube bottom through here
    part = part.cut(cq.Workplane().box(10, 7, 12).translate(
        (X + P.SOCKET_OD / 2 - 3, 0, Z0 + 8)))
    return part


def mast_screw() -> cq.Workplane:
    """Captive M8 thumb-screw, Ø24 knob, radial into the socket."""
    k = knob(24, 8, 14).translate((0, 0, -8))
    neck = cq.Workplane().circle(3.2).extrude(9)
    rod = cq.Workplane().add(threaded_rod(M8[0], M8[1], 8, 9))
    s = k.union(neck).union(rod)
    return (s.rotate((0, 0, 0), (0, 1, 0), 90)
            .translate((X - P.SOCKET_OD / 2 - 14, 0, SCREW_Z)))


def mast_tube() -> cq.Workplane:
    L = P.MAST_TOP_Z - P.MAST_BOTTOM_Z
    return (cq.Workplane().circle(P.MAST_D / 2).circle(P.MAST_D / 2 -
                                                       P.MAST_T)
            .extrude(L).translate((X, 0, P.MAST_BOTTOM_Z)))


HOOP_R = P.HOOP_ID / 2 + P.HOOP_SECTION / 2


def collar_hoop() -> cq.Workplane:
    """REC-D06: collar pinned to the tube by one M4 A4 cross-bolt, the
    Ø64 internal hoop behind the mast (horizontal, so a pole hook drops
    in from above), and the flag-staff socket on the port side. Round
    11 mm hoop section: no edge under 0.6 mm (REC-D08)."""
    z = P.COLLAR_Z
    col = (cq.Workplane().circle(13).extrude(24).translate((X, 0, z - 12)))
    hoop = (cq.Workplane().circle(HOOP_R + P.HOOP_SECTION / 2)
            .circle(HOOP_R - P.HOOP_SECTION / 2).extrude(P.HOOP_SECTION)
            .edges().fillet(P.HOOP_SECTION / 2 - 0.3)
            .translate((X - 13 - HOOP_R + 2, 0, z - P.HOOP_SECTION / 2)))
    web = cq.Workplane().box(12, 10, 16).translate((X - 14, 0, z))
    sock = (cq.Workplane().circle(7.5).extrude(28)
            .translate((X, 20, z - 14)))
    part = col.union(hoop).union(web).union(sock)
    part = part.cut(cq.Workplane().circle(P.MAST_D / 2 + 0.2).extrude(30)
                    .translate((X, 0, z - 15)))
    # M4 A4 cross-bolt through collar and a drilled tube: the hoop cannot
    # slip or turn on the mast (adult, tool)
    part = part.cut(cq.Workplane("XZ", origin=(0, 14, 0)).center(X, z)
                    .circle(2.2).extrude(28))
    part = part.cut(cq.Workplane().circle(P.STAFF_D / 2 + 0.25).extrude(
        24).translate((X, 20, z - 10)))
    return part


def flag_staff() -> cq.Workplane:
    """Ø8 printed staff with a Ø16 ball cap (REC-D08), 190 long."""
    z0 = P.COLLAR_Z - 10
    rod = cq.Workplane().circle(P.STAFF_D / 2).extrude(P.STAFF_L - 8)
    cap = cq.Workplane().sphere(8).translate((0, 0, P.STAFF_L - 8))
    return rod.union(cap).translate((X, 20, z0))


def staff_top_z() -> float:
    return P.COLLAR_Z - 10 + P.STAFF_L


def flag() -> cq.Workplane:
    """Fluorescent ripstop flag (REC-D02), 120 × 80, flying aft."""
    w, h = P.FLAG
    zt = staff_top_z() - 12
    return (cq.Workplane("XZ", origin=(0, 20, 0))
            .center(X - 4 - w / 2, zt - h / 2).rect(w, h).extrude(0.3))


def masthead() -> cq.Workplane:
    """Sleeve over the tube top, WS2812 ring under a translucent diffuser
    (REC-D03), GNSS/compass dome on top (IF-19)."""
    z0 = P.MAST_TOP_Z - 10
    sleeve = (cq.Workplane().circle(11).extrude(10)
              .translate((X, 0, z0)))
    ring = (cq.Workplane().circle(22).circle(11).extrude(10)
            .edges().fillet(1.5).translate((X, 0, z0)))
    dome = (cq.Workplane().circle(25).extrude(P.MASTHEAD_H - 10)
            .edges(">Z").fillet(8).edges("<Z").fillet(1)
            .translate((X, 0, z0 + 10)))
    # hollow: the GNSS board sits inside on the ring (1.6 mm walls)
    dome = dome.cut(cq.Workplane().circle(23.4)
                    .extrude(P.MASTHEAD_H - 10 - 1.6)
                    .edges(">Z").fillet(6).translate((X, 0, z0 + 10)))
    part = sleeve.union(ring).union(dome)
    return part.cut(cq.Workplane().circle(P.MAST_D / 2 + 0.2).extrude(10)
                    .translate((X, 0, z0 - 0.01)))


def masthead_top_z() -> float:
    return P.MAST_TOP_Z - 10 + P.MASTHEAD_H
