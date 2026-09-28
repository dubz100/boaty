"""SITL JSON physics bridge (ICD IF-21, proposed DD-19).

ArduPilot SITL started with ``--model JSON`` sends a binary servo packet to UDP
port 9002 every physics frame and waits (lockstep) for a JSON state reply.
This module owns a Boat, advances it one frame per packet and replies.

Packet from SITL (little-endian):
    uint16 magic (18458 for 16 channels, 29569 for 32)
    uint16 frame_rate
    uint32 frame_count
    uint16 pwm[16 or 32]

Reply: one line of JSON with timestamp, imu.gyro, imu.accel_body, position,
velocity, attitude, and battery.voltage/current.

The bridge runs in its own thread so tests can inject faults on
``bridge.boat.faults`` while the autopilot flies.
"""
from __future__ import annotations

import json
import logging
import math
import socket
import struct
import threading
import time

from .boat import Boat

log = logging.getLogger(__name__)

MAGIC_16, MAGIC_32 = 18458, 29569
PWM_MIN, PWM_TRIM, PWM_MAX = 1000, 1500, 2000
MAX_DT = 0.02


def pwm_to_cmd(pwm: int) -> float:
    """Map a reversible throttle output (1000..2000, trim 1500) to -1..1.
    A zero PWM (output disabled, e.g. disarmed) is treated as stop."""
    if pwm <= 0:
        return 0.0
    cmd = (pwm - PWM_TRIM) / (PWM_MAX - PWM_TRIM)
    return max(-1.0, min(1.0, cmd))


class JsonBridge:
    def __init__(self, boat: Boat | None = None, port: int = 9002,
                 left_ch: int = 1, right_ch: int = 4, host: str = "127.0.0.1"):
        self.boat = boat or Boat()
        self.port, self.host = port, host
        # Output channels are 1-based as in SERVOn_FUNCTION (KCL section 7:
        # left = output 1, right = output 4).
        self.left_i, self.right_i = left_ch - 1, right_ch - 1
        self.lock = threading.Lock()
        self.frames = 0
        self.last_frame_count = None
        self.last_pwm: tuple[int, ...] = ()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    # ------------------------------------------------------------------
    def start(self) -> "JsonBridge":
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(0.2)
        self._thread = threading.Thread(target=self._run, name="json-bridge",
                                        daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._sock:
            self._sock.close()

    def wait_for_sitl(self, timeout: float = 30.0) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.frames > 0:
                return True
            time.sleep(0.05)
        return False

    # ------------------------------------------------------------------
    def _run(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(512)
            except socket.timeout:
                continue
            except OSError:
                break
            reply = self.handle(data)
            if reply is not None:
                self._sock.sendto(reply, addr)

    def handle(self, data: bytes) -> bytes | None:
        """Process one servo packet and return the JSON reply (or None)."""
        if len(data) < 8:
            return None
        magic, rate, count = struct.unpack_from("<HHI", data, 0)
        if magic == MAGIC_16:
            n = 16
        elif magic == MAGIC_32:
            n = 32
        else:
            log.warning("bad magic %s", magic)
            return None
        if len(data) < 8 + 2 * n:
            return None
        pwm = struct.unpack_from(f"<{n}H", data, 8)
        with self.lock:
            b = self.boat
            if self.last_frame_count is not None:
                if count < self.last_frame_count:
                    log.info("SITL restarted; resetting boat")
                    b.reset(soc=b.soc, heading_deg=math.degrees(b.psi))
                elif count == self.last_frame_count:
                    # Repeated frame (SITL re-send): reply without stepping.
                    return self._state_json()
            dt = min(MAX_DT, 1.0 / rate) if rate else 0.0025
            b.step(pwm_to_cmd(pwm[self.left_i]), pwm_to_cmd(pwm[self.right_i]),
                   dt)
            self.last_frame_count = count
            self.last_pwm = pwm
            self.frames += 1
            return self._state_json()

    def _state_json(self) -> bytes:
        b = self.boat
        vn, ve, vd = b.velocity_ned()
        state = {
            "timestamp": b.t,
            "imu": {"gyro": [0.0, 0.0, b.r],
                    "accel_body": list(b.accel_body())},
            "position": [b.n, b.e, 0.0],
            "velocity": [vn, ve, vd],
            "attitude": [0.0, 0.0, b.psi],
            "battery": {"voltage": max(b.voltage, 0.0),
                        "current": b.current},
        }
        return ("\n" + json.dumps(state, separators=(",", ":")) + "\n") \
            .encode()

    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        """Thread-safe copy of the truth state, for test assertions."""
        with self.lock:
            b = self.boat
            return dict(t=b.t, n=b.n, e=b.e, heading_deg=math.degrees(b.psi),
                        speed=b.speed(), thrust=list(b.thrust),
                        voltage=b.voltage, current=b.current, soc=b.soc,
                        rail_v=b.rail_voltage())
