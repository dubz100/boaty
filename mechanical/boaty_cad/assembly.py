"""The Mk1 assembly: every part design once (CATALOGUE) and every
placement of it (instances()). Boat frame throughout (see params).

kind:  printed  printed here (STL + STEP exported, weighed from CAD)
       stock    cut or drilled from stock (STEP exported, weighed from CAD)
       bought   bought item modelled for fit (weighed from the catalogue
                mass where one is given)
       ref      reference model of a KCL component (weighed from KCL/ADD)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

import cadquery as cq

from . import hull as H
from . import mast as M
from . import params as P
from . import pod as Q
from . import structure as S


@dataclass
class Part:
    key: str
    name: str
    kind: str
    material: str
    build: Callable[[], cq.Workplane]
    qty: int
    frame: str = "boat"          # "boat" or "hull" (y from hull centreline)
    mass: float | None = None    # catalogue mass, g, if not weighed
    child: bool = False          # handled by the child (CHD-001, HUL-D22)
    colour: str = "grey"
    note: str = ""
    refs: tuple[str, ...] = ()
    foam: Callable[[], cq.Workplane] | None = None
    chunky: Callable[[], list] | None = None
    places: list = field(default_factory=list)


@lru_cache(maxsize=None)
def _seg(kind: str):
    return H.build(kind)


def _hull_part(kind: str):
    return lambda: _seg(kind)[0]


HV = "hivis"        # fluorescent orange (REC-D01)

CATALOGUE: list[Part] = [
    Part("HUL-101", "Bow segment", "printed", "ASA", _hull_part("bow"), 2,
         "hull", child=True, colour=HV, refs=("HUL-D02", "IF-16"),
         foam=lambda: _seg("bow")[1], chunky=lambda: _seg("bow")[2]),
    Part("HUL-102", "Mid segment", "printed", "ASA", _hull_part("mid"), 2,
         "hull", child=True, colour=HV, refs=("HUL-D02", "REC-D04/D05"),
         foam=lambda: _seg("mid")[1], chunky=lambda: _seg("mid")[2]),
    Part("HUL-103", "Stern segment", "printed", "ASA", _hull_part("stern"),
         2, "hull", child=True, colour=HV, refs=("HUL-D02", "IF-17"),
         foam=lambda: _seg("stern")[1], chunky=lambda: _seg("stern")[2]),
    Part("HUL-104", "Joint thumb-screw M12", "printed", "PETG",
         H.thumb_screw, 8, "hull", child=True, colour="yellow",
         refs=("IF-16", "HUL-D22")),
    Part("HUL-105", "Joint dowel Ø8 × 20 (bonded)", "printed", "PETG",
         H.dowel, 8, "hull", refs=("IF-16",)),
    Part("HUL-106", "Tracker pocket cap", "printed", "PETG", H.pocket_cap,
         2, "hull", refs=("REC-D05",)),
    Part("HUL-201", "Crossbeam 20 × 10 × 1.5 Al tube, 300 long", "stock",
         "Al 6063", lambda: S.crossbeam(0.0), 2, colour="alu",
         refs=("HUL-2",)),
    Part("HUL-202", "Beam end cap (bonded)", "printed", "PETG", S.beam_cap,
         4, colour="black", refs=("HUL-D23",)),
    Part("HUL-301", "Electronics box body (clip-lock, modified)", "bought",
         "PP", S.box_body, 1, mass=95.0, colour="clear", refs=("IF-18",)),
    Part("HUL-302", "Electronics box lid", "bought", "PP", S.box_lid, 1,
         mass=40.0, colour="clear", refs=("IF-18",)),
    Part("HUL-303", "Saddle tray", "printed", "PETG", S.tray, 1,
         colour="grey", refs=("IF-18", "HUL-D16")),
    Part("HUL-304", "Over-centre latch", "printed", "PETG",
         lambda: S.latch(1), 2, colour="black", refs=("HUL-D24",)),
    Part("HUL-305", "Latch keeper (bonded to box)", "printed", "PETG",
         lambda: S.keeper(1), 2, colour="black", refs=("HUL-D24",)),
    Part("HUL-306", "PG7 cable gland", "bought", "PA", lambda: S.gland(0),
         4, mass=4.0, colour="black", refs=("IF-18", "MEC-012")),
    Part("HUL-307", "Key dock (bonded to lid)", "printed", "PETG",
         S.key_dock, 1, colour=HV, refs=("IF-18",)),
    Part("HUL-308", "Arming key fob (magnet bonded in)", "printed", "PETG",
         S.arming_key, 1, mass=None, colour="red",
         refs=("IF-18", "CHD-003")),
    Part("HUL-401", "DUPLO deck plate", "printed", "PETG", S.duplo_plate,
         1, child=True, colour="green", refs=("IF-20", "MEC-009")),
    Part("HUL-402", "Mast step and carry handle", "printed", "PETG",
         M.step_and_handle, 1, colour=HV, refs=("IF-19", "HUL-D21")),
    Part("HUL-403", "Mast tube Ø16 × 1 Al, 311 long", "stock", "Al 6063",
         M.mast_tube, 1, colour="alu", refs=("IF-19",)),
    Part("HUL-404", "Mast thumb-screw M8 (captive)", "printed", "PETG",
         M.mast_screw, 1, colour="yellow", refs=("IF-19",)),
    Part("HUL-501", "Camera hood", "printed", "PETG", S.camera_hood, 1,
         colour=HV, refs=("HUL-D19",)),
    Part("HUL-502", "Camera window, 2 mm acrylic", "stock", "acrylic",
         S.window, 1, colour="clear", refs=("HUL-D19",)),
    Part("REC-101", "Collar and recovery hoop", "printed", "PETG",
         M.collar_hoop, 1, colour=HV, refs=("REC-D06", "REC-005")),
    Part("REC-102", "Flag staff with ball cap", "printed", "PETG",
         M.flag_staff, 1, child=True, colour="yellow",
         refs=("REC-D02", "REC-D08")),
    Part("REC-103", "Flag, fluorescent ripstop 120 × 80", "bought",
         "ripstop", M.flag, 1, mass=3.0, colour=HV, refs=("REC-D02",)),
    Part("REC-104", "Masthead: GNSS dome and LED diffuser", "printed",
         "PETG", M.masthead, 1, colour="white", refs=("IF-19", "REC-D03")),
    Part("PRP-101", "Thruster pod body", "printed", "PETG", Q.body, 2,
         "hull", child=True, colour="black", refs=("IF-17", "PRP-D09/10")),
    Part("PRP-102", "Rear guard", "printed", "PETG", Q.rear_guard, 2,
         "hull", colour="black", refs=("MEC-010", "PRP-D09")),
    Part("PRP-103", "Propeller Ø35, 3 blades", "printed", "PETG", Q.prop, 2,
         "hull", colour="yellow", refs=("PRP-D10",)),
    Part("KC-04", "Motor 2205 (reference)", "ref", "-", Q.motor, 2, "hull",
         mass=28.0, colour="alu", refs=("KC-04",)),
    Part("KC-11", "Camera OV5647 (reference)", "ref", "-", S.camera, 1,
         mass=8.0, colour="black", refs=("KC-11",)),
]


def by_key(key: str) -> Part:
    return next(p for p in CATALOGUE if p.key == key)


def instances() -> list[tuple[str, cq.Location, str]]:
    """(part key, location, instance label) for every part in the boat."""
    out = []
    loc0 = cq.Location()
    for p in CATALOGUE:
        if p.frame == "hull":
            n_side = p.qty // 2
            for side, lab in ((1, "P"), (-1, "S")):
                for i in range(n_side):
                    out.append((p.key, _hull_loc(p.key, side, i),
                                f"{p.key}-{lab}{i + 1}"))
        else:
            for i in range(p.qty):
                out.append((p.key, _boat_loc(p.key, i), f"{p.key}-{i + 1}"))
    return [(k, loc if loc is not None else loc0, lab)
            for k, loc, lab in out]


def _hull_loc(key: str, side: int, i: int) -> cq.Location:
    y = side * P.HULL_Y
    if key == "HUL-104":        # thumb-screws: 2 per joint, knob outward
        xj = (P.X_J1, P.X_J2)[i // 2]
        sy = (P.SCREW_Y, -P.SCREW_Y)[i % 2]
        # screw built along +z, knob at z<0; engaged: neck in lug A
        if xj == P.X_J1:        # knob aft, points +x
            x = xj - P.LUG_L - 0.5
            return cq.Location(cq.Vector(x, y + sy, P.SCREW_Z),
                               cq.Vector(0, 1, 0), 90)
        x = xj + P.LUG_L + 0.5
        return cq.Location(cq.Vector(x, y + sy, P.SCREW_Z),
                           cq.Vector(0, 1, 0), -90)
    if key == "HUL-105":        # dowels bonded into the end segments
        xj = (P.X_J1, P.X_J2)[i // 2]
        dy, dz = P.DOWEL_POS[i % 2]
        return cq.Location(cq.Vector(xj - P.DOWEL_ENG, y + dy, dz),
                           cq.Vector(0, 1, 0), 90)
    if key == "HUL-106":
        return cq.Location(cq.Vector(P.POCKET_X, y, P.D))
    return cq.Location(cq.Vector(0, y, 0))


def _boat_loc(key: str, i: int) -> cq.Location | None:
    if key == "HUL-201":
        return cq.Location(cq.Vector(P.BEAM_X[i], 0, 0))
    if key == "HUL-202":
        bx = P.BEAM_X[i // 2]
        s = (1, -1)[i % 2]
        y = s * (P.BEAM_L / 2 + 3)
        return cq.Location(cq.Vector(bx, y, P.D + P.BEAM_H / 2),
                           cq.Vector(0, 0, 1), 0 if s > 0 else 180)
    if key in ("HUL-304", "HUL-305"):
        return None if i == 0 else cq.Location(
            cq.Vector(2 * P.LATCH_X, 0, 0), cq.Vector(0, 0, 1), 180)
    if key == "HUL-306":
        return cq.Location(cq.Vector(0, (i - 1.5) * P.GLAND_PITCH, 0))
    return None


def placed(key: str, loc: cq.Location) -> cq.Workplane:
    return by_key(key).build().val().moved(loc)


def assembly() -> cq.Assembly:
    colours = {HV: (1.0, 0.35, 0.0), "yellow": (1.0, 0.85, 0.1),
               "grey": (0.55, 0.57, 0.6), "alu": (0.78, 0.8, 0.82),
               "black": (0.12, 0.12, 0.12), "clear": (0.8, 0.9, 1.0, 0.45),
               "green": (0.2, 0.65, 0.25), "white": (0.95, 0.95, 0.95),
               "red": (0.85, 0.1, 0.1)}
    a = cq.Assembly(name="boaty_mk1")
    for key, loc, lab in instances():
        p = by_key(key)
        a.add(p.build(), name=lab, loc=loc,
              color=cq.Color(*colours[p.colour]))
    return a
