"""Box sensors read by B6: moisture traces (MCP-D03) and DS18B20 (MCP-D26)."""
from __future__ import annotations

import glob
from dataclasses import dataclass


@dataclass
class SimSensors:
    """Settable stand-ins for simulation and tests."""
    moisture: bool = False
    box_temp_c: float = 30.0

    def read(self) -> tuple[bool, float | None]:
        return self.moisture, self.box_temp_c


class PiSensors:
    """Real sensors on the Pi Zero. Moisture: GPIO input with pull-up, pulled
    low when water bridges the traces. Temperature: DS18B20 on 1-Wire
    (dtoverlay=w1-gpio, GPIO4), read through sysfs."""

    def __init__(self, moisture_gpio: int = 17):
        from gpiozero import Button          # imported only on the Pi
        self._wet = Button(moisture_gpio, pull_up=True)
        paths = glob.glob("/sys/bus/w1/devices/28-*/w1_slave")
        self._w1 = paths[0] if paths else None

    def read(self) -> tuple[bool, float | None]:
        return self._wet.is_pressed, self._temp()

    def _temp(self) -> float | None:
        if not self._w1:
            return None
        try:
            with open(self._w1) as f:
                lines = f.read().splitlines()
        except OSError:
            return None
        if len(lines) < 2 or not lines[0].endswith("YES") or "t=" not in \
                lines[1]:
            return None
        return int(lines[1].split("t=")[1]) / 1000.0
