"""Mass properties, hydrostatics, stability and the compliance checks.

Mass: printed parts are weighed as a slicer would print them: a part
thinner than twice the wall is solid; for the chunky features (lugs,
bosses, blocks) the outer WALL is solid and the core is at INFILL.
Hydrostatics: the underwater part of the hull solids is cut by a water
plane at the solved sinkage, trim and heel (fresh water, 1.000 g/cm³).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq
import numpy as np

from . import assembly as A
from . import mast as M
from . import params as P
from . import pod as Q
from . import structure as S

RHO_W = 1.0e-3            # g/mm³, fresh water


def printed_volume(solid: cq.Shape) -> float:
    v, a = solid.Volume(), solid.Area()
    shell = min(v, a * P.WALL)
    return shell + max(0.0, v - shell) * P.INFILL


@dataclass
class Item:
    name: str
    key: str
    mass: float                 # g, one instance
    cg: tuple[float, float, float]
    group: str
    basis: str


def _part_mass(p: A.Part) -> tuple[float, str, cq.Vector]:
    """(mass of one, basis, centroid in the part's own frame)."""
    shape = p.build().val()
    c = shape.Center()
    if p.mass is not None:
        return p.mass, "catalogue", c
    rho = P.RHO[p.material]
    if p.kind == "printed":
        if p.chunky is not None:
            chunks = [w.val() for w in p.chunky()]
            v_ch = sum(ch.Volume() for ch in chunks)
            vp = shape.Volume() - v_ch + sum(printed_volume(ch)
                                             for ch in chunks)
        else:
            vp = printed_volume(shape)
        m = vp * rho
        basis = f"CAD, printed {vp / 1000:.1f} cm³"
    else:
        m = shape.Volume() * rho
        basis = f"CAD {shape.Volume() / 1000:.1f} cm³"
    if p.foam is not None:
        vf = p.foam().val().Volume()
        m += vf * P.RHO["XPS foam"]
        basis += f" + foam {vf / 1e6:.2f} L"
    return m, basis, c


GROUPS = {"HUL-1": "Hull segments, foam, joints", "HUL-2": "Crossbeams",
          "HUL-3": "Box, tray, latches, glands", "HUL-4": "Deck, mast step, "
          "handle, tube", "HUL-5": "Camera hood and window",
          "REC": "Recovery: hoop, flag, masthead", "PRP": "Thruster pods",
          "KC-04": "Thruster pods", "KC-11": "Electronics (box contents)"}


def _group(key: str) -> str:
    for k, g in GROUPS.items():
        if key.startswith(k):
            return g
    return "Other"


# Items with no CAD geometry: catalogue masses (ADD A.MASS, KCL) and where
# they sit. GNSS and beacon in the masthead; stainless fasteners spread.
EXTRA = [
    ("GNSS + compass board, LED ring, mast cable", 25.0,
     (P.MAST_X, 0.0, P.MAST_TOP_Z + 8), "Recovery: hoop, flag, masthead"),
    ("Stainless fasteners, inserts, pins (count in MDD)", 50.0,
     (300.0, 0.0, P.D + 5), "Fasteners"),
    ("Magnet (arming key) Ø20 × 3", 7.0, (P.KEY_X, 0.0, S.Z_LID + 3),
     "Box, tray, latches, glands"),
    ("Labels, hi-vis tape, O-rings, sealant", 15.0, (300.0, 0.0, P.D),
     "Recovery: hoop, flag, masthead"),
    ("Pod connectors (2 pairs) and motor leads", 30.0, (120.0, 0.0, P.D + 5),
     "Thruster pods"),
]


def mass_items() -> list[Item]:
    items: list[Item] = []
    cache: dict[str, tuple[float, str, cq.Vector]] = {}
    for key, loc, lab in A.instances():
        p = A.by_key(key)
        if key not in cache:
            cache[key] = _part_mass(p)
        m, basis, c = cache[key]
        moved = cq.Vertex.makeVertex(c.x, c.y, c.z).moved(loc).Center()
        items.append(Item(p.name, lab, m, (moved.x, moved.y, moved.z),
                          _group(key), basis))
    for name, (m, x, y, z, _size) in S.electronics().items():
        items.append(Item(name, "KCL", m, (x, y, z),
                          "Electronics (box contents)", "ADD A.MASS"))
    for name, m, xyz, grp in EXTRA:
        items.append(Item(name, "est", m, xyz, grp, "estimate"))
    return items


def totals(items: list[Item]) -> tuple[float, np.ndarray]:
    m = sum(i.mass for i in items)
    cg = sum(np.array(i.cg) * i.mass for i in items) / m
    return m, cg


# ---------------------------------------------------------------- hydro
def displacement_solid() -> "Mesh":
    """Both hulls' outer envelopes plus the pods' material (the duct
    floods), as one compound."""
    from . import hull as H
    hull = H.outer_hull().val()
    pod = Q.body().val().fuse(Q.motor().val())
    shapes = []
    for s in (1, -1):
        shapes.append(hull.moved(cq.Location(cq.Vector(0, s * P.HULL_Y, 0))))
        shapes.append(pod.moved(cq.Location(cq.Vector(0, s * P.HULL_Y, 0))))
    return Mesh(cq.Compound.makeCompound(shapes))


def _water_normal(heel: float, trim: float) -> np.ndarray:
    """Unit normal of the water plane in the boat frame (pointing up).
    heel > 0: port side down; trim > 0: bow up."""
    h, t = math.radians(heel), math.radians(trim)
    n = np.array([math.sin(t), -math.sin(h) * math.cos(t),
                  math.cos(h) * math.cos(t)])
    return n / np.linalg.norm(n)


class Mesh:
    """A closed triangle mesh of the displacement body. Volumes below a
    plane come from signed tetrahedra to a point on the plane: the cap
    faces then add nothing, so clipping the triangles is enough."""

    def __init__(self, body: cq.Shape, tol: float = 0.15):
        tris = []
        for sol in body.Solids():
            vs, ts = sol.tessellate(tol, 0.1)
            v = np.array([x.toTuple() for x in vs])
            t = np.array(ts)
            tris.append(v[t])
        self.tri = np.concatenate(tris)          # (n, 3, 3)
        self.volume = self._vol(self.tri, np.zeros(3))[0]

    @staticmethod
    def _vol(tri: np.ndarray, p: np.ndarray) -> tuple[float, np.ndarray]:
        a, b, c = tri[:, 0] - p, tri[:, 1] - p, tri[:, 2] - p
        v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
        cen = (a + b + c) / 4.0 + p
        V = v.sum()
        return V, (cen * v[:, None]).sum(0) / V if V else np.zeros(3)

    def below(self, p: np.ndarray, n: np.ndarray) -> tuple[float,
                                                            np.ndarray]:
        d = np.einsum("ijk,k->ij", self.tri - p, n)      # (n, 3)
        nb = (d < 0).sum(1)
        keep = [self.tri[nb == 3]]
        for tri, dd in zip(self.tri[(nb == 1) | (nb == 2)],
                           d[(nb == 1) | (nb == 2)]):
            poly = []
            for i in range(3):
                j = (i + 1) % 3
                if dd[i] < 0:
                    poly.append(tri[i])
                if (dd[i] < 0) != (dd[j] < 0):
                    t = dd[i] / (dd[i] - dd[j])
                    poly.append(tri[i] + t * (tri[j] - tri[i]))
            for k in range(1, len(poly) - 1):
                keep.append(np.array([[poly[0], poly[k], poly[k + 1]]]))
        allt = np.concatenate(keep)
        return self._vol(allt, p)


def submerged(body: "Mesh", z0: float, heel: float, trim: float,
              xref: float) -> tuple[float, np.ndarray]:
    """Volume and centroid below the water plane through (xref, 0, z0)
    with the given heel and trim."""
    n = _water_normal(heel, trim)
    return body.below(np.array([xref, 0.0, z0]), n)


@dataclass
class Float:
    mass: float
    z0: float           # water plane height at xref (keel frame)
    trim: float
    heel: float
    cb: np.ndarray
    gz: float           # righting arm, mm (positive rights the boat)
    xref: float

    def draft_at(self, x: float) -> float:
        """Water plane height above the keel line at station x."""
        return self.z0 + math.tan(math.radians(self.trim)) * -(x -
                                                                 self.xref)


def equilibrium(body, mass: float, cg: np.ndarray, heel: float = 0.0,
                trim0: float = 0.0, z00: float = 30.0) -> Float:
    """Sinkage and trim so that buoyancy = weight and the trim moment is
    zero, at a fixed heel."""
    V = mass / RHO_W
    xref = float(cg[0])

    def resid(z0, trim):
        vol, cb = submerged(body, z0, heel, trim, xref)
        n = _water_normal(heel, trim)
        # moment arm along the boat's x in the water frame: (CB-CG)
        # projected on the horizontal fore-aft direction
        fwd = np.array([math.cos(math.radians(trim)), 0,
                        -math.sin(math.radians(trim))])
        fwd = fwd - n * np.dot(fwd, n)
        fwd /= np.linalg.norm(fwd)
        return vol - V, float(np.dot(cb - cg, fwd)), cb

    z0, trim = z00, trim0
    for _ in range(20):
        r1, r2, cb = resid(z0, trim)
        if abs(r1) < V * 2e-4 and abs(r2) < 0.05:
            break
        dz, dt = 0.3, 0.05
        a1, a2, _ = resid(z0 + dz, trim)
        b1, b2, _ = resid(z0, trim + dt)
        J = np.array([[(a1 - r1) / dz, (b1 - r1) / dt],
                      [(a2 - r2) / dz, (b2 - r2) / dt]])
        step = np.linalg.solve(J, -np.array([r1, r2]))
        step = np.clip(step, [-15, -3], [15, 3])
        z0, trim = z0 + step[0], trim + step[1]
    n = _water_normal(heel, trim)
    # transverse horizontal direction in the water frame
    fwd = np.array([math.cos(math.radians(trim)), 0,
                    -math.sin(math.radians(trim))])
    lat = np.cross(n, fwd)
    lat /= np.linalg.norm(lat)
    # heel > 0 puts port down; the righting moment pushes it back:
    # GZ > 0 when the CB is further to port (down side) than the CG
    gz = float(np.dot(cb - cg, lat))
    return Float(mass, z0, trim, heel, cb, gz, xref)


def heel_balance(body, mass: float, cg: np.ndarray, lo: float = 0.0,
                 hi: float = 12.0) -> Float:
    """Static heel with an off-centre CG: the heel where GZ = 0."""
    f_lo = equilibrium(body, mass, cg, lo)
    f_hi = equilibrium(body, mass, cg, hi, f_lo.trim, f_lo.z0)
    for _ in range(12):
        if f_hi.gz * f_lo.gz > 0:
            break
        mid = (f_lo.heel + f_hi.heel) / 2
        f_m = equilibrium(body, mass, cg, mid, f_lo.trim, f_lo.z0)
        if f_m.gz * f_lo.gz > 0:
            f_lo = f_m
        else:
            f_hi = f_m
        if f_hi.heel - f_lo.heel < 0.05:
            break
    return f_lo if abs(f_lo.gz) < abs(f_hi.gz) else f_hi


def mast_off_top() -> float:
    return max(S.Z_LID + P.PLATE_T + P.STUD_H, M.SOCKET_TOP,
               P.GRIP_Z + P.GRIP_D / 2, S.Z_LID + 1.5 + 9)


def pod_bottom() -> float:
    return P.POD_AXIS_Z - P.DUCT_OD / 2
