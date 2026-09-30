"""Every Mk1 mechanical dimension in one place, traced to what it answers.

Frame (whole boat): x forward from the stern transom, y to port from the
boat centreline, z up from the hull keel line (the flat bottom of the mid
and stern segments). Units mm, g, N. The waterline is not a parameter: the
hydrostatics in analysis.py find it from the computed mass.
"""
from __future__ import annotations

PRINT_MAX = 197.0       # MEC-005 200 mm cube, less 3 mm for skirt/tolerance

# ---------------------------------------------------------------- hull
HULL_Y = 135.0          # hull centreline offset; spacing 270 (HUL-D04)
B = 84.0                # hull beam at the deck (HUL-D01 beam ≤ 360)
D = 90.0                # hull depth, keel to deck (HUL-D07, HUL-D16)
R_BILGE = 18.0          # bottom corner radius
R_DECK = 6.0            # deck edge radius (HUL-D23, rain shedding D13)
T_SHELL = 1.2           # shell wall; HUL-D10 says 1.6: see CR-11
T_END = 2.0             # stem and transom wall
L_STERN, L_MID, L_BOW = 177.0, 196.0, 196.0     # HUL-D02 ≤ 200 each
X_J1 = L_STERN                  # stern/mid joint
X_J2 = L_STERN + L_MID          # mid/bow joint
X_STEM = X_J2 + L_BOW
BOW_KEEL_RISE = 28.0    # keel height at the stem (weed and wave entry)
BOW_FLAT = 30.0         # full section carried this far past the joint
STEM_HALF = 5.0         # half-breadth at the stem (rounded stem)

# IF-16 segment joint
FLANGE_DEPTH = 6.0      # 6 mm flange (IF-16)
FLANGE_WALL = 4.0       # wall thickness over the flange depth
DOWEL_D = 8.0           # 2 × Ø8 dowels, 10 mm engagement (IF-16)
DOWEL_ENG = 10.0
DOWEL_CLEAR = 0.3       # printed hole oversize
DOWEL_POS = [(22.0, 16.0), (-22.0, 16.0)]      # (y, z) in the hull frame
DOWEL_BOSS_D = 15.0
SCREW_D = 12.0          # M12 coarse printed thread (IF-16)
SCREW_P = 1.75
SCREW_CLEAR = 0.45      # internal thread oversize for printing
KNOB_D = 35.0           # Ø35 knurled knob (IF-16)
KNOB_H = 11.0
SCREW_Y = 21.0          # two screws at ± 21 mm: knobs 7 mm apart
SCREW_Z = D + 19.5      # axis above the deck: knob clears the deck
LUG_L = 12.0            # lug length along x
LUG_W = 22.0
NECK_D = 9.0            # captive: the neck turns freely in the threaded lug
THREAD_L = 12.0
NECK_L = 13.0

# Beam pads on the mid segments
BEAM_X = (212.0, 302.0)     # aft and forward crossbeam centres
INSERT_D = 5.6              # M4 heat-set insert hole
INSERT_BOSS_D = 11.0
INSERT_DEPTH = 10.0
BEAM_BOLT_DY = 20.0         # bolts at hull centre ± 20 mm

# REC-D05 tracker pocket (mid segment deck), REC-D04 label recess
POCKET_X = 257.0
POCKET_D = 36.0             # takes a ≤ 35 mm tag
POCKET_DEPTH = 12.0
POCKET_CAP_D = 50.0
LABEL = (70.0, 24.0, 0.6)   # recess on both side faces (both hulls)

# ---------------------------------------------------------------- beams
BEAM_W, BEAM_H, BEAM_T = 20.0, 10.0, 1.5   # 6063 aluminium rectangular tube
BEAM_L = 2 * HULL_Y + 30.0                 # to 15 mm past each hull centre
RAIL_PITCH = 10.0                          # M3 hole grid on top (HUL-2)
RAIL_HOLE = 3.2

# ---------------------------------------------------------------- box
# Clip-lock food box (IF-18: internal ≥ 180 × 110 × 70). Modelled as a
# generic box; the saddle is sized from BOX_* so a chosen box only changes
# these numbers (TBC-13).
BOX_L, BOX_W, BOX_H = 200.0, 130.0, 86.0   # external, with lid
BOX_LID_H = 14.0
BOX_WALL = 1.6
BOX_X0 = BEAM_X[0] + 38.0  # aft face: 38 mm behind it for glands, cables
TRAY_T = 3.0
TRAY_X = (BEAM_X[0] - 10.0, BEAM_X[0] + 184.0)   # 194 long (MEC-005)
TRAY_WALL_H = 12.0
GLAND_PITCH = 25.0          # 4 × PG7 on the aft face (IF-18)
GLAND_HOLE = 12.7
GLAND_Z = 38.0              # above the box bottom
LATCH_X = BOX_X0 + 100.0
LATCH_FORCE_MIN = 40.0      # HUL-D24

# Camera and hood (HUL-D19/D20)
LENS_Z_ABOVE_BOX = 56.0     # lens centre above the box bottom
WINDOW_D = 30.0
HOOD_OVERHANG = 22.0        # ≥ 15 mm beyond the window (HUL-D19)

# DUPLO deck (IF-20)
STUD_PITCH = 16.0
STUD_NX, STUD_NY = 8, 6     # 128 × 96 mm
STUD_D, STUD_H = 9.4, 4.5   # TBC-14: tune by test print
STUD_BORE = 6.6
PLATE_T = 2.4
PLATE_X0 = BOX_X0 + 58.0   # aft edge of the stud grid
KEY_X = BOX_X0 + 26.0      # key dock over the reed switch (IF-18)

# ---------------------------------------------------------------- mast
MAST_X = BEAM_X[0]
MAST_D, MAST_T = 16.0, 1.0      # IF-19 Ø16 tube
SOCKET_DEPTH = 50.0             # IF-19
SOCKET_OD = 28.0
MAST_BOTTOM_Z = D + BEAM_H + 2.0
MAST_TOP_Z = 423.0              # tube top; masthead to z 455 (MEC-001)
MASTHEAD_H = 32.0               # LED ring 10 + GNSS dome 22
GRIP_D = 22.0
GRIP_Z = D + BEAM_H + 52.0      # grip axis
HANDLE_SPAN = 95.0              # uprights at y = ± 95
COLLAR_Z = 188.0
HOOP_ID = 64.0                  # REC-D06 ≥ 60
HOOP_SECTION = 11.0
STAFF_D = 8.0
STAFF_L = 190.0
STAFF_SOCKET_Z = COLLAR_Z
FLAG = (120.0, 80.0)            # REC-D02 ≥ 120 × 80

# ---------------------------------------------------------------- pod
DOVE_W, DOVE_L, DOVE_H = 20.0, 40.0, 8.0    # IF-17 60°, 20 × 40
DOVE_ANGLE = 60.0
DOVE_Z = 62.0               # rail centre height on the transom
DOVE_CLEAR = 0.3            # IF-17
POD_AXIS_Z = -26.0          # prop axis: duct top 4 mm under the keel
DUCT_ID, DUCT_OD = 38.0, 42.8
DUCT_X = (-42.0, 8.0)       # the duct runs 8 mm under the hull
NACELLE_D = 28.0
PROP_D = 35.0
PROP_HUB = 12.0
MOTOR_BELL_D, MOTOR_L = 27.9, 17.0          # 2205 class (KC-04)
PROBE_D = 8.0               # MEC-010
STRUT_SWEEP = 32.0          # PRP-D10 ≥ 30°
VANE_ANGLE = 45.0           # PRP-D10 inlet bars ≥ 45°

# ---------------------------------------------------------------- materials
RHO = {"PETG": 1.27e-3, "ASA": 1.07e-3, "XPS foam": 0.030e-3,
       "Al 6063": 2.70e-3, "A2": 7.9e-3, "acrylic": 1.19e-3,
       "PP": 0.90e-3, "ripstop": 0.0}         # g/mm³
WALL = 1.2            # 3 perimeters (HUL-D10)
INFILL = 0.25         # solid printed parts: 25% gyroid

# ---------------------------------------------------------------- loads
DESIGN_MASS = 2100.0            # g: boat + 300 g payload (IF-16 load case)
PAYLOAD = 300.0
G = 9.81e-3                     # N per g
SF = 3.0
