"""Clocks for the boat services.

On the Pi Zero services run on the system's monotonic clock. In simulation
they run on the physics clock so that every timer (60 s link watchdog, 20 s
divergence, ...) means simulated seconds whatever the speed-up.
"""
from __future__ import annotations

import time
from typing import Callable, Protocol


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(max(0.0, seconds))


class SimClock:
    def __init__(self, sim_time: Callable[[], float], speedup: float = 1.0):
        self._t = sim_time
        self.speedup = max(1.0, speedup)

    def now(self) -> float:
        return self._t()

    def sleep(self, seconds: float) -> None:
        end = self._t() + seconds
        while self._t() < end:
            time.sleep(min(0.01, max(0.001, seconds / self.speedup / 4)))
