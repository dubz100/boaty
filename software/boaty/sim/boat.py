"""Three-degree-of-freedom boat model for Boaty Mk1 (proposed DD-19).

Surge, sway and yaw of a small skid-steer catamaran with two thruster pods,
quadratic hull drag, windage and a 3S Li-ion battery whose sagging voltage
feeds back into the motor rail.

Every number in BoatParams comes from BOATY-KCL-001 section 8, and every one
of them is an estimate until the measurement named there replaces it. The
model is deliberately simple: the purpose is to exercise the autopilot's
modes and failsafes at the right scale (about 4 N of thrust, 1.5 kg, 1.5 m/s),
not to predict handling to the centimetre.

Frames: earth frame is NED (north, east, down) relative to the SITL home.
Body frame is x forward, y starboard, z down. Positive yaw is clockwise seen
from above.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

G = 9.80665
RHO_AIR = 1.225


@dataclass
class BoatParams:
    mass: float = 1.46                # kg, ADD mass budget
    added_mass_surge: float = 0.10    # fraction of mass
    added_mass_sway: float = 0.50
    izz: float = 0.063                # kg m^2, uniform box 0.62 x 0.36 m
    pod_y: float = 0.135              # m, half the hull spacing
    thrust_fwd: float = 2.0           # N per pod at full forward
    thrust_ast: float = 0.75          # N per pod at full astern
    motor_tau: float = 0.10           # s, spin-up time constant
    k_surge: float = 1.62             # N s^2/m^2, quadratic surge drag
    k_sway: float = 16.0              # N s^2/m^2, twin hulls resist sideways
    k_yaw: float = 0.05               # N m s^2, quadratic yaw damping
    lin_surge: float = 0.3            # N s/m, linear terms keep low speeds sane
    lin_sway: float = 3.0
    lin_yaw: float = 0.05             # N m s
    wind_area_front: float = 0.035    # m^2
    wind_area_side: float = 0.06      # m^2
    wind_cd: float = 1.1
    k_power: float = 5.49             # W per N^1.5, set so cruise draws 8 W
    hotel_w: float = 3.1              # W, helm + MCP + beacon + ESC idle
    # Battery: 3S1P Li-ion, acceptance limits (PWR-D20).
    capacity_ah: float = 2.5
    r_pack: float = 0.22              # ohm, cells + BMS + harness
    cells: int = 3
    bms_cutoff_v: float = 2.5         # per cell; BMS opens the pack below


# Generic NMC 18650 open-circuit voltage against state of charge.
_OCV = [(0.00, 3.00), (0.05, 3.30), (0.10, 3.45), (0.20, 3.55), (0.30, 3.62),
        (0.40, 3.68), (0.50, 3.74), (0.60, 3.80), (0.70, 3.87), (0.80, 3.95),
        (0.90, 4.05), (1.00, 4.18)]


def ocv_per_cell(soc: float) -> float:
    soc = min(1.0, max(0.0, soc))
    for (s0, v0), (s1, v1) in zip(_OCV, _OCV[1:]):
        if soc <= s1:
            return v0 + (v1 - v0) * (soc - s0) / (s1 - s0)
    return _OCV[-1][1]


@dataclass
class Faults:
    """Injected faults and environment. Tests set these while SITL runs."""
    thrust_scale: list = field(default_factory=lambda: [1.0, 1.0])
    reverse_motor: list = field(default_factory=lambda: [False, False])
    extra_drag: float = 0.0           # N s^2/m^2 added to surge (weed)
    wind_speed: float = 0.0           # m/s
    wind_from_deg: float = 0.0        # direction the wind comes FROM
    current_n: float = 0.0            # water current, m/s north
    current_e: float = 0.0
    key_in: bool = True               # magnetic arming key (motor rail)
    battery_drain_a: float = 0.0      # extra real load (sags the pack)
    phantom_current_a: float = 0.0    # reported and counted, but no sag:
                                      # fast-forwards capacity use (SC-01)


class Boat:
    """Boat state and integrator. Not thread-safe; the bridge owns it."""

    def __init__(self, params: BoatParams | None = None, soc: float = 1.0,
                 heading_deg: float = 0.0):
        self.p = params or BoatParams()
        self.faults = Faults()
        self.reset(soc=soc, heading_deg=heading_deg)

    def reset(self, soc: float = 1.0, heading_deg: float = 0.0) -> None:
        self.t = 0.0
        self.n = self.e = 0.0                  # m, NED position
        self.psi = math.radians(heading_deg)   # rad
        self.u = self.v = self.r = 0.0         # body velocities
        self.du = self.dv = 0.0                # last body accelerations
        self.thrust = [0.0, 0.0]               # N, left and right pods
        self.soc = soc
        self.used_ah = 0.0
        self.current = 0.0
        self.voltage = self.p.cells * ocv_per_cell(soc)
        self.bms_open = False

    # ------------------------------------------------------------------
    def rail_voltage(self) -> float:
        """Motor rail: battery through the key switch."""
        return self.voltage if (self.faults.key_in and not self.bms_open) \
            else 0.0

    def _thrust_target(self, cmd: float, i: int) -> float:
        cmd = max(-1.0, min(1.0, cmd))
        if self.faults.reverse_motor[i]:
            cmd = -cmd
        full = self.p.thrust_fwd if cmd >= 0 else self.p.thrust_ast
        t = full * cmd * abs(cmd) * self.faults.thrust_scale[i]
        return t if self.rail_voltage() > 0 else 0.0

    def _wind_body(self) -> tuple[float, float]:
        f = self.faults
        if f.wind_speed <= 0:
            return 0.0, 0.0
        # Wind blowing towards (from + 180), earth frame.
        to = math.radians(f.wind_from_deg + 180.0)
        wn, we = f.wind_speed * math.cos(to), f.wind_speed * math.sin(to)
        vn, ve = self.velocity_ned()[:2]
        rn, re = wn - vn, we - ve                  # air relative to boat
        c, s = math.cos(self.psi), math.sin(self.psi)
        rx, ry = c * rn + s * re, -s * rn + c * re
        k = 0.5 * RHO_AIR * self.p.wind_cd
        return (k * self.p.wind_area_front * rx * abs(rx),
                k * self.p.wind_area_side * ry * abs(ry))

    def step(self, cmd_left: float, cmd_right: float, dt: float) -> None:
        p, f = self.p, self.faults
        # Motors: first-order lag towards the commanded thrust.
        a = min(1.0, dt / p.motor_tau)
        for i, cmd in enumerate((cmd_left, cmd_right)):
            self.thrust[i] += a * (self._thrust_target(cmd, i) - self.thrust[i])
        tl, tr = self.thrust

        # Water-relative body velocity.
        c, s = math.cos(self.psi), math.sin(self.psi)
        ur = self.u - (c * f.current_n + s * f.current_e)
        vr = self.v - (-s * f.current_n + c * f.current_e)
        wx, wy = self._wind_body()
        ks = p.k_surge + f.extra_drag
        fx = tl + tr - ks * ur * abs(ur) - p.lin_surge * ur + wx
        fy = -p.k_sway * vr * abs(vr) - p.lin_sway * vr + wy
        nz = p.pod_y * (tl - tr) - p.k_yaw * self.r * abs(self.r) \
            - p.lin_yaw * self.r

        mx = p.mass * (1 + p.added_mass_surge)
        my = p.mass * (1 + p.added_mass_sway)
        # Rigid-body coupling terms for a body-fixed frame.
        self.du = fx / mx + self.v * self.r
        self.dv = fy / my - self.u * self.r
        dr = nz / p.izz
        self.u += self.du * dt
        self.v += self.dv * dt
        self.r += dr * dt
        self.psi = (self.psi + self.r * dt) % (2 * math.pi)
        vn, ve, _ = self.velocity_ned()
        self.n += vn * dt
        self.e += ve * dt
        self.t += dt
        self._battery(dt)

    def _battery(self, dt: float) -> None:
        p = self.p
        if self.bms_open:
            self.current, self.voltage = 0.0, 0.0
            return
        power = p.hotel_w + sum(p.k_power * abs(t) ** 1.5
                                for t in self.thrust)
        ocv = p.cells * ocv_per_cell(self.soc)
        # Solve V = OCV - I R with I = P / V (take the upper root).
        disc = ocv * ocv - 4 * p.r_pack * power
        v = (ocv + math.sqrt(disc)) / 2 if disc > 0 else ocv / 2
        i = power / v + self.faults.battery_drain_a
        v = ocv - i * p.r_pack
        self.current = i + self.faults.phantom_current_a
        self.voltage = v
        self.used_ah += self.current * dt / 3600
        self.soc = max(0.0, 1.0 - self.used_ah / p.capacity_ah)
        if v < p.cells * p.bms_cutoff_v:
            self.bms_open = True

    # ------------------------------------------------------------------
    def velocity_ned(self) -> tuple[float, float, float]:
        c, s = math.cos(self.psi), math.sin(self.psi)
        return (c * self.u - s * self.v, s * self.u + c * self.v, 0.0)

    def accel_body(self) -> tuple[float, float, float]:
        """Specific force an IMU would measure (includes gravity)."""
        return (self.du - self.v * self.r, self.dv + self.u * self.r, -G)

    def speed(self) -> float:
        return math.hypot(self.u, self.v)
