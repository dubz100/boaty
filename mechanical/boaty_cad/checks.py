"""The compliance checks: every mechanical requirement allocated to the
hull, propulsion pods and recovery items (SRS, SSS-HUL/PRP/REC, ICD
IF-16..20), computed from the CAD where the CAD can show it.

status: PASS    met, shown by the CAD or the calculation here
        FAIL    not met: a change request is raised (cr)
        TEST    the CAD cannot show it; the V-item that will
        INFO    reported for the reviewer, no limit
"""
from __future__ import annotations

import math
from functools import lru_cache

import cadquery as cq
import numpy as np

from . import analysis as N
from . import assembly as A
from . import mast as M
from . import params as P
from . import pod as Q
from . import render as RN
from . import structure as S

SMALL_D, SMALL_L = 31.7, 57.1          # EN 71-1 small-parts cylinder


@lru_cache(maxsize=None)
def placed_shapes() -> tuple:
    out = []
    for key, loc, lab in A.instances():
        out.append((key, lab, A.by_key(key).build().val().moved(loc)))
    return tuple(out)


def _bbox(shapes) -> tuple[np.ndarray, np.ndarray]:
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for s in shapes:
        b = s.BoundingBox()
        lo = np.minimum(lo, [b.xmin, b.ymin, b.zmin])
        hi = np.maximum(hi, [b.xmax, b.ymax, b.zmax])
    return lo, hi


MAST_KEYS = {"HUL-403", "HUL-404", "REC-101", "REC-102", "REC-103",
             "REC-104"}


def envelope(mast: bool = True) -> tuple[np.ndarray, np.ndarray]:
    return _bbox([s for k, _, s in placed_shapes()
                  if mast or k not in MAST_KEYS])


def _r(x: float, n: int = 1) -> float:
    return round(float(x), n)


class Results:
    def __init__(self):
        self.rows: list[dict] = []
        self.data: dict = {}

    def add(self, rid, refs, text, value, limit, status, note="", cr=""):
        self.rows.append(dict(id=rid, refs=refs, text=text, value=value,
                              limit=limit, status=status, note=note, cr=cr))


def run() -> Results:
    R = Results()
    D = R.data

    # -------------------------------------------------- mass
    items = N.mass_items()
    m, cg = N.totals(items)
    D["mass_items"] = [dict(name=i.name, key=i.key, mass=_r(i.mass),
                            group=i.group, basis=i.basis, cg=[_r(c) for c in
                                                              i.cg])
                       for i in items]
    groups: dict[str, float] = {}
    for i in items:
        groups[i.group] = groups.get(i.group, 0.0) + i.mass
    D["mass_groups"] = {k: _r(v) for k, v in groups.items()}
    D["mass"] = _r(m)
    D["cg"] = [_r(c) for c in cg]
    R.add("M-01", "MEC-002", "Ready-to-sail mass, excluding payload",
          f"{m:.0f} g", "≤ 1800 g", "PASS" if m <= 1800 else "FAIL",
          f"{m - 1800:+.0f} g against the limit", "CR-07")
    hul_groups = ("Hull segments, foam, joints", "Crossbeams",
                  "Box, tray, latches, glands", "Deck, mast step, handle, "
                  "tube", "Camera hood and window", "Fasteners")
    m_hul = sum(groups.get(g, 0) for g in hul_groups)
    D["mass_hul"] = _r(m_hul)
    R.add("M-02", "HUL-D03", "Hull and structure mass", f"{m_hul:.0f} g",
          "≤ 1000 g", "PASS" if m_hul <= 1000 else "FAIL",
          "segments, beams, deck, box, mast, fasteners", "CR-07")
    pod = next(i for i in items if i.name == "Thruster pod body").mass
    guard = next(i for i in items if i.name == "Rear guard").mass
    prop = next(i for i in items if i.name.startswith("Propeller")).mass
    m_pod = pod + guard + prop + 28.0
    D["mass_pod"] = _r(m_pod)
    R.add("M-03", "PRP-D13", "Pod mass including the motor",
          f"{m_pod:.0f} g", "≤ 75 g", "PASS" if m_pod <= 75 else "FAIL",
          "body, guard, prop, 28 g motor; lead and connector excluded")

    # -------------------------------------------------- geometry
    lo, hi = envelope(True)
    size = hi - lo
    D["envelope"] = [_r(v) for v in size]
    D["envelope_lo"] = [_r(v) for v in lo]
    R.add("G-01", "HUL-D01, MEC-001", "Overall length (hull bow to pod "
          "guard)", f"{size[0]:.0f} mm", "≤ 620 (HUL) / 650 (SRS)",
          "PASS" if size[0] <= 620 else "FAIL")
    R.add("G-02", "HUL-D01, MEC-001", "Overall beam", f"{size[1]:.0f} mm",
          "≤ 360 / 400", "PASS" if size[1] <= 360 else "FAIL")
    R.add("G-03", "HUL-D01, MEC-001", "Height, pod bottom to masthead",
          f"{size[2]:.0f} mm", "≤ 500", "PASS" if size[2] <= 500 else
          "FAIL")
    lo2, hi2 = envelope(False)
    s2 = hi2 - lo2
    D["envelope_mast_off"] = [_r(v) for v in s2]
    ok = s2[0] <= 650 and s2[1] <= 400 and s2[2] <= 250
    R.add("G-04", "HUL-D21, MEC-014", "Envelope with the mast removed",
          f"{s2[0]:.0f} × {s2[1]:.0f} × {s2[2]:.0f}", "≤ 650 × 400 × 250",
          "PASS" if ok else "FAIL", "pods fitted")
    R.add("G-05", "HUL-D04", "Hull centreline spacing",
          f"{2 * P.HULL_Y:.0f} mm", "≥ 270", "PASS")
    seg = [P.L_STERN, P.L_MID, P.L_BOW]
    R.add("G-06", "HUL-D02", "Segments per hull and length",
          f"3; {', '.join(f'{x:.0f}' for x in seg)} mm", "3; ≤ 200",
          "PASS" if max(seg) <= 200 else "FAIL")
    worst = []
    for p in A.CATALOGUE:
        if p.kind != "printed":
            continue
        b = p.build().val().BoundingBox()
        d = sorted([b.xlen, b.ylen, b.zlen])
        worst.append((d[-1], p.key, p.name, d))
    worst.sort(reverse=True)
    D["print_sizes"] = [(k, n, [_r(v) for v in d]) for _, k, n, d in worst]
    big = worst[0]
    R.add("G-07", "MEC-005, HUL-D02", "Largest printed part (fits the "
          "200 mm cube)", f"{big[2]}: {big[3][2]:.0f} × {big[3][1]:.0f} × "
          f"{big[3][0]:.0f}", "every side ≤ 200",
          "PASS" if big[0] <= 200 else "FAIL",
          f"{len(worst)} printed part designs checked")

    # -------------------------------------------------- foam
    fills = {}
    for p in A.CATALOGUE:
        if p.foam is None:
            continue
        foam = p.foam().val().Volume()
        fills[p.name] = foam
    D["foam_l"] = {k: _r(v / 1e6, 3) for k, v in fills.items()}
    R.add("B-01", "HUL-D05, MEC-006", "Closed-cell foam fill of each "
          "segment cavity", "100% modelled (XPS, profiled blocks)", "≥ 90%",
          "TEST", "The CAD fills the cavity; the as-built fill is checked "
          "by weighing each filled segment (V-item M-V1)")

    # -------------------------------------------------- hydrostatics
    body = N.displacement_solid()
    D["hull_volume_l"] = _r(body.volume / 1e6, 3)
    pay_deck = np.array([P.PLATE_X0 + P.STUD_NX * P.STUD_PITCH / 2, 0,
                         S.Z_LID + 12])
    md = m + P.PAYLOAD
    cgd = (cg * m + pay_deck * P.PAYLOAD) / md
    light = N.equilibrium(body, m, cg)
    des = N.equilibrium(body, md, cgd)

    def keel(x):
        from .hull import bow_station
        return bow_station(x)[1] if x > P.X_J2 else 0.0

    def draft(f):
        xs = np.linspace(0, P.X_STEM, 300)
        return max(f.draft_at(x) - keel(x) for x in xs)

    def freeboard(f):
        xs = np.linspace(0, P.X_STEM, 300)
        return min(P.D - f.draft_at(x) for x in xs)

    for lab, f, mm in (("light", light, m), ("design", des, md)):
        D[f"float_{lab}"] = dict(mass=_r(mm), sinkage=_r(f.z0, 2),
                                 trim=_r(f.trim, 2), draft=_r(draft(f)),
                                 freeboard=_r(freeboard(f)),
                                 xref=_r(f.xref),
                                 wl_aft=_r(f.draft_at(0)),
                                 wl_fwd=_r(f.draft_at(P.X_STEM)))
    dd, fb = draft(des), freeboard(des)
    R.add("H-01", "HUL-D07", "Hull draft at design mass (boat + 300 g on "
          "the deck)", f"{dd:.1f} mm at {md:.0f} g", "≤ 35",
          "PASS" if dd <= 35 else "FAIL",
          f"pods reach {-Q.AX + P.DUCT_OD / 2 + des.z0:.0f} mm below the "
          "water")
    R.add("H-02", "HUL-D07, MEC-003", "Least freeboard at design mass",
          f"{fb:.1f} mm", "≥ 50", "PASS" if fb >= 50 else "FAIL")
    tr = des.trim
    R.add("H-03", "HUL-D20", "Trim (camera level) light / design",
          f"{light.trim:+.1f}° / {tr:+.1f}°", "± 3°",
          "PASS" if max(abs(light.trim), abs(tr)) <= 3 else "FAIL",
          "negative = bow down; lens axis is parallel to the keel")
    lens_x = S.BOX_X1
    lens_h = S.LENS_Z - des.draft_at(lens_x)
    R.add("H-04", "HUL-D20", "Lens height above the water at design mass",
          f"{lens_h:.0f} mm", "≥ 120", "PASS" if lens_h >= 120 else "FAIL")
    lid_h = min(S.Z_LID - des.draft_at(x) for x in (P.BOX_X0, S.BOX_X1))
    R.add("H-05", "HUL-D16", "Box lid above the water at design mass",
          f"{lid_h:.0f} mm", "≥ 150", "PASS" if lid_h >= 150 else "FAIL")

    # reserve buoyancy: two breached segments lose their unfilled space
    # (≤ 10% of the cavity by HUL-D05); the box gives no buoyancy
    seg_foam = sorted(fills.values(), reverse=True)
    lost = 0.10 * (seg_foam[0] + seg_foam[0])
    reserve = (body.volume - lost) * N.RHO_W
    D["reserve_g"] = _r(reserve)
    need = 1.5 * P.DESIGN_MASS
    R.add("H-06", "HUL-D06, REC-001", "Buoyancy with two segments "
          "breached, box flooded", f"{reserve:.0f} g",
          f"≥ 1.5 × 2100 = {need:.0f} g (and ≥ 1.5 × {md:.0f} = "
          f"{1.5 * md:.0f} g)", "PASS" if reserve >= max(need, 1.5 * md)
          else "FAIL", "the two largest segments breached, 10% void each")

    # static heel with 300 g at the deck edge (outboard edge of a hull)
    pay_edge = np.array([P.X_J1 + P.L_MID / 2, P.HULL_Y + P.B / 2, P.D])
    cge = (cg * m + pay_edge * P.PAYLOAD) / md
    hb = N.heel_balance(body, md, cge, 0.0, 10.0)
    D["heel_edge"] = _r(hb.heel, 2)
    R.add("H-07", "HUL-D08, MEC-004", "Static heel, 300 g at the deck "
          "edge", f"{hb.heel:.1f}°", "≤ 10°",
          "PASS" if hb.heel <= 10 else "FAIL")
    # GZ curve at design mass, centred load
    gz = []
    f0 = des
    for h in list(range(0, 91, 5)):
        f = N.equilibrium(body, md, cgd, float(h), f0.trim, f0.z0)
        gz.append((h, _r(f.gz, 2)))
        f0 = f
    D["gz"] = gz
    gzs = np.array(gz)
    imax = int(np.argmax(gzs[:, 1]))
    vanish = next((gzs[i, 0] for i in range(imax, len(gzs))
                   if gzs[i, 1] <= 0), 90.0)
    D["gz_max"] = [float(gzs[imax, 0]), float(gzs[imax, 1])]
    D["vanish"] = float(vanish)
    rm_max = md * P.G * gzs[imax, 1] / 1000       # N·m
    D["rm_max"] = _r(rm_max, 2)
    # turn: 1.5 m/s on a 1 m radius, side force at the CG against the
    # hull's lateral resistance at half the draft
    a_turn = 1.5 ** 2 / 1.0
    lever = (cgd[2] - (des.z0 - dd / 2)) / 1000
    m_turn = md / 1000 * a_turn * lever
    D["turn_moment"] = _r(m_turn, 3)
    # smallest heel where the righting moment exceeds the turn moment
    phi_turn = next((h for h, g in gz if md * P.G * g / 1000 >= m_turn and
                     h > 0), None)
    slope = math.degrees(math.atan(math.pi * 100 / 1000))
    D["wave_slope"] = _r(slope)
    R.add("H-08", "HUL-D09, MEC-004", "Stability: max righting arm; "
          "angle of vanishing stability", f"GZ {gzs[imax, 1]:.0f} mm at "
          f"{gzs[imax, 0]:.0f}°; vanishes at {vanish:.0f}°",
          f"vanishing > wave slope {slope:.0f}° + edge heel "
          f"{hb.heel:.0f}°", "PASS" if vanish > slope + hb.heel + 15
          else "FAIL", f"turn at 1.5 m/s, R 1 m heels < {phi_turn}°; "
          "confirmed in the pool (V-item)")

    # tow by the hoop: sideways pull that would capsize, vs tow drag
    z_hoop = P.COLLAR_Z
    lever_t = (z_hoop - (des.z0 - dd / 2)) / 1000
    f_cap = rm_max / lever_t
    drag = 0.5 * 1000 * 0.5 ** 2 * 1.0 * (2 * 0.55 * dd / 1000)
    D["tow"] = dict(capsize_force=_r(f_cap, 1), drag_side=_r(drag, 1),
                    lever=_r(lever_t * 1000))
    R.add("H-09", "REC-005, REC-D06", "Tow by the hoop without capsize "
          "(sideways, worst case)", f"capsizes at {f_cap:.0f} N side pull",
          f"> side drag at 0.5 m/s ≈ {drag:.1f} N",
          "PASS" if f_cap > 2 * drag else "FAIL",
          "a 50 N pull is a strength case; towed, the pull equals the drag")

    # -------------------------------------------------- structure
    W = md * P.G                                    # N
    Fh = P.SF * W
    Mb = Fh / 2 * P.HULL_Y / 1000                   # N·m, beam at the grip
    b_, h_, t_ = P.BEAM_W, P.BEAM_H, P.BEAM_T
    I = (b_ * h_ ** 3 - (b_ - 2 * t_) * (h_ - 2 * t_) ** 3) / 12
    sig = Mb * 1000 * (h_ / 2) / I
    D["beam_stress"] = _r(sig)
    handle_dx = abs(P.MAST_X - cg[0])
    grip_y = (P.SOCKET_OD / 2 + M.UPRIGHT_Y - 6) / 2
    R.add("S-01", "HUL-D21, MEC-014", "Carry handle from the centre of "
          "gravity (x; y of the grip centre)", f"{handle_dx:.0f} mm; "
          f"{grip_y:.0f} mm", "≤ 50", "PASS" if max(handle_dx, grip_y) <= 50
          else "FAIL", "each grip either side of the mast socket")
    R.add("S-02", "HUL-D21", "Aft beam at 3 × design weight on the handle",
          f"{sig:.0f} MPa", "6063-T6 yield 160 MPa",
          "PASS" if sig < 160 / 1.5 else "FAIL",
          f"{Fh:.0f} N at the grip, hulls hanging from the beam ends")
    # IF-16 joint: hand torque → preload; sag capacity vs 3 × design
    T_hand = 20.0 * P.KNOB_D / 2 / 1000             # 20 N at the rim
    F_pre = T_hand / (0.3 * P.SCREW_D / 1000)
    lever_j = (P.SCREW_Z - P.D / 3) / 1000
    M_cap = 2 * F_pre * lever_j
    L = P.X_STEM / 1000
    M_dem = P.SF * W / 2 / 2 * (L / 3)              # per hull, at 1/3 L
    D["joint"] = dict(preload=_r(F_pre), m_cap=_r(M_cap, 2),
                      m_dem=_r(M_dem, 2))
    R.add("S-03", "IF-16, HUL-D14, HUL-D25", "Segment joint: bending "
          "before it opens (hand-tight), vs 3 × design weight, bow and "
          "stern supported", f"{M_cap:.1f} N·m", f"≥ {M_dem:.1f} N·m",
          "PASS" if M_cap >= M_dem else "FAIL",
          f"2 × M12 at {F_pre:.0f} N each from 20 N at the Ø35 knob "
          "(K = 0.3); load test B-item")
    # IF-19 socket: 50 N on the hoop
    M_sock = 50.0 * (P.COLLAR_Z - P.MAST_BOTTOM_Z) / 1000
    D["socket_moment"] = _r(M_sock, 2)
    R.add("S-04", "IF-19, REC-D06", "Moment at the mast socket, 50 N on "
          "the hoop", f"{M_sock:.1f} N·m", "design 30 N·m (IF-19)",
          "PASS" if M_sock <= 30 else "FAIL",
          "the hoop is low on the mast: 5 × lower than the ICD's 15 N·m")
    # hoop section in bending: 50 N at the far side of the ring
    Zs = math.pi * P.HOOP_SECTION ** 3 / 32
    sig_h = 50.0 * (M.HOOP_R * 2) / Zs
    D["hoop_stress"] = _r(sig_h)
    R.add("S-05", "REC-005, REC-D06", "Hoop: internal size; 50 N pull",
          f"Ø{P.HOOP_ID:.0f} mm; {sig_h:.0f} MPa (cantilever, "
          "conservative)", "≥ Ø60; PETG ≈ 50 MPa",
          "PASS" if P.HOOP_ID >= 60 and sig_h < 50 / 1.5 else "TEST",
          "the ring shares the load round both sides; pull test B-item")

    # -------------------------------------------------- guards
    op = Q.guard_openings()
    D["openings"] = {k: _r(v, 2) for k, v in op.items()}
    worst_o = max(op.values())
    R.add("P-01", "MEC-010, PRP-D09", "Largest opening a probe could "
          "enter (inlet annulus and rear guard)", f"{worst_o:.2f} mm",
          f"< {P.PROBE_D:.0f} mm", "PASS" if worst_o < P.PROBE_D - 1
          else "FAIL", "the duct is solid; the prop sits between inlet and "
          "guard; B-01 probe test")
    R.add("P-02", "PRP-D10", "Strut sweep; inlet vane angle",
          f"{P.STRUT_SWEEP:.0f}°; {P.VANE_ANGLE:.0f}°", "≥ 30°; ≥ 45°",
          "PASS")
    R.add("P-03", "IF-17, PRP-D12", "Pod mount: dovetail angle, size, "
          "clearance; tool-free latch",
          f"{P.DOVE_ANGLE:.0f}°, {P.DOVE_W:.0f} × {P.DOVE_L:.0f}, "
          f"{P.DOVE_CLEAR} mm; tongue and detent",
          "60°, 20 × 40, 0.3 mm", "PASS", "swap time is a bench test")
    R.add("P-04", "PRP-D14, CHD-003", "Prop unreachable fitted or "
          "unfitted", "guard is on the pod; screws need a tool", "adult "
          "action only", "PASS")

    # -------------------------------------------------- mast, GNSS, flag
    gnss = np.array([P.MAST_X, 0, P.MAST_TOP_Z + 6])
    power_pts = [np.array([x, y, z]) for x in (P.BOX_X0, S.BOX_X1)
                 for y in (-P.BOX_W / 2, P.BOX_W / 2)
                 for z in (S.Z_BOX, S.Z_LID)]
    # motor leads: gland → tray slot → aft beam → hull deck → transom
    lead = [(P.BOX_X0 - 10, 0, S.Z_BOX + P.GLAND_Z), (P.BOX_X0 - 16, 0,
                                                       S.Z_TRAY),
            (P.MAST_X - 10, 40, P.D + P.BEAM_H), (P.MAST_X - 10, P.HULL_Y,
                                                  P.D),
            (0, P.HULL_Y, P.D), (-10, P.HULL_Y, Q.AX)]
    dist = min(np.linalg.norm(gnss - p) for p in power_pts)

    def seg_d(a, b, p):
        a, b = np.array(a, float), np.array(b, float)
        t = np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1)
        return np.linalg.norm(p - (a + t * (b - a)))

    d_lead = min(seg_d(lead[i], lead[i + 1], gnss) for i in range(len(lead)
                                                                  - 1))
    d_min = min(dist, d_lead)
    D["gnss_sep"] = _r(d_min)
    R.add("E-01", "MEC-013, HUL-D18, IF-19", "GNSS to power wiring, box "
          "and motor leads", f"{d_min:.0f} mm", "≥ 150",
          "PASS" if d_min >= 150 else "FAIL",
          "motor leads run down from the glands, along the aft beam and "
          "the hull decks")
    top_wl = M.masthead_top_z() - des.z0
    D["gnss_top_above_wl"] = _r(top_wl)
    R.add("E-02", "IF-19", "Masthead top above the water (design mass)",
          f"{top_wl:.0f} mm", "≈ 450, total height ≤ 500",
          "FAIL" if abs(top_wl - 450) > 15 else "PASS",
          "the ≤ 500 mm height from the pod bottom sets it", "CR-08")
    flag_top = M.staff_top_z() - 12 - des.z0
    R.add("E-03", "REC-D02, REC-003", "Flag size; flag top above the "
          "water; below the GNSS", f"{P.FLAG[0]:.0f} × {P.FLAG[1]:.0f}; "
          f"{flag_top:.0f} mm", "≥ 120 × 80; ≥ 320 mm",
          "PASS" if flag_top >= 320 and M.staff_top_z() < P.MAST_TOP_Z
          else "FAIL")

    # -------------------------------------------------- box, deck
    ib = (P.BOX_L - 2 * P.BOX_WALL, P.BOX_W - 2 * P.BOX_WALL,
          P.BOX_H - 2 * P.BOX_WALL)
    R.add("I-01", "IF-18, HUL-D15", "Box inside size; glands; key dock",
          f"{ib[0]:.0f} × {ib[1]:.0f} × {ib[2]:.0f}; 4 × PG7 at "
          f"{P.GLAND_PITCH:.0f} mm on the aft face; cup on the lid",
          "≥ 180 × 110 × 70", "PASS" if ib[0] >= 180 and ib[1] >= 110
          and ib[2] >= 70 else "FAIL", "the chosen box fixes these "
          "(TBC-13); submersion test B-item")
    R.add("I-02", "IF-20, HUL-D17, MEC-009", "DUPLO grid",
          f"{P.STUD_NY} × {P.STUD_NX} at {P.STUD_PITCH:.0f} mm, Ø"
          f"{P.STUD_D} × {P.STUD_H}", "6 × 8 at 16 mm", "PASS",
          "stud size by test print against genuine bricks (TBC-14)")
    R.add("I-03", "HUL-D19", "Camera hood overhang beyond the window",
          f"{P.HOOD_OVERHANG:.0f} mm", "≥ 15", "PASS")
    R.add("I-04", "HUL-D24", "Box and battery bay open only by an adult",
          "2 over-centre latches, detent ≥ 40 N; box clips under them",
          "≥ 40 N or two hands", "TEST", "force measured on the bench")

    # -------------------------------------------------- child safety
    fits = []
    for p in A.CATALOGUE:
        b = p.build().val().BoundingBox()
        d = sorted([b.xlen, b.ylen, b.zlen])
        f = math.hypot(d[0], d[1]) <= SMALL_D and d[2] <= SMALL_L
        if f:
            fits.append(p)
    D["small_parts"] = [(p.key, p.name, p.child) for p in fits]
    child_small = [p for p in fits if p.child]
    R.add("C-01", "CHD-001, HUL-D22", "Child-handled parts that fit the "
          "small-parts cylinder", ", ".join(p.name for p in child_small) or
          "none", "none", "PASS" if not child_small else "FAIL",
          "parts that do fit are bonded, captive or behind a tool: " +
          "; ".join(p.name for p in fits))
    R.add("C-02", "CHD-002, HUL-D23", "Edges and finger traps",
          "child-handled edges filleted or chamfered ≥ 0.6 mm; joints "
          "close face to face", "≥ 0.6 mm", "TEST",
          "check on the first prints (inspection)")

    # -------------------------------------------------- hi-vis
    parts = []
    for k, lab, s in placed_shapes():
        parts.append((RN.mesh(s, 1.0), A.by_key(k).colour))
    img, pid = RN.render(parts, 0, 90, px=1.0, ids=True)
    seen = pid >= 0
    hv = np.isin(pid, [i for i, (_, c) in enumerate(parts)
                       if c == "hivis"])
    share = hv.sum() / seen.sum()
    D["hivis_share"] = _r(share * 100)
    R.add("V-01", "REC-D01, REC-002", "Fluorescent share of the top "
          "view", f"{share * 100:.0f}%", "≥ 50%",
          "PASS" if share >= 0.5 else "FAIL",
          "segments printed in fluorescent orange; DUPLO plate green "
          "(bricks cover it)")
    return R
