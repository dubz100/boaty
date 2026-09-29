"""C2 panel: four arcade buttons with LEDs (IF-12, MCN-D02, D09, D10).

    GO         GPIO 17  press-and-hold 1.0 +/- 0.1 s
    COME HOME  GPIO 27  acts on press
    STOP       GPIO 22  acts on press, edge to helm.stop() <= 50 ms
    TALK       GPIO 24  hold to talk, release to send
    LEDs       GPIO 5, 6, 13, 19 (lit = does something now)

The panel reports button events to a handler; the session manager (C1)
decides what they mean. SimPanel is driven by tests and the web UI's
on-screen panel; GpioPanel uses gpiozero on the Pi 5.
"""
from __future__ import annotations

import enum
import threading
import time
from typing import Callable

GO_HOLD_S = 1.0
DEBOUNCE_S = 0.03


class Button(enum.Enum):
    GO = "GO"
    COME_HOME = "COME_HOME"
    STOP = "STOP"
    TALK = "TALK"


GPIO = {Button.GO: 17, Button.COME_HOME: 27, Button.STOP: 22,
        Button.TALK: 24}
LED_GPIO = {Button.GO: 5, Button.COME_HOME: 6, Button.STOP: 13,
            Button.TALK: 19}

# Events: "press" (every button, at the edge), "held" (GO after 1.0 s, still
# held), "release" (TALK: send the recording).
Handler = Callable[[Button, str], None]


class SimPanel:
    def __init__(self, handler: Handler, clock=time.monotonic,
                 sleep=time.sleep):
        self.handler, self.clock, self.sleep = handler, clock, sleep
        self.leds: dict[Button, bool] = {b: False for b in Button}
        self.presses: list[tuple[float, Button, str]] = []

    def _emit(self, b: Button, ev: str) -> None:
        self.presses.append((self.clock(), b, ev))
        self.handler(b, ev)

    def press(self, b: Button, hold_s: float = 0.1) -> None:
        """Press, hold for hold_s (in the panel's clock), release."""
        self._emit(b, "press")
        if b is Button.GO and hold_s >= GO_HOLD_S:
            self.sleep(GO_HOLD_S)
            self._emit(b, "held")
            self.sleep(max(0.0, hold_s - GO_HOLD_S))
        else:
            self.sleep(hold_s)
        self._emit(b, "release")

    def set_leds(self, lit: dict[Button, bool]) -> None:
        self.leds.update(lit)


class GpioPanel:                                   # pragma: no cover (Pi only)
    def __init__(self, handler: Handler):
        from gpiozero import LED, Button as GButton
        self.handler = handler
        self.buttons = {}
        for b, pin in GPIO.items():
            g = GButton(pin, pull_up=True, bounce_time=DEBOUNCE_S,
                        hold_time=GO_HOLD_S if b is Button.GO else 10)
            g.when_pressed = lambda b=b: handler(b, "press")
            g.when_released = lambda b=b: handler(b, "release")
            if b is Button.GO:
                g.when_held = lambda b=b: handler(b, "held")
            self.buttons[b] = g
        self.led_out = {b: LED(p) for b, p in LED_GPIO.items()}

    def set_leds(self, lit: dict[Button, bool]) -> None:
        for b, on in lit.items():
            (self.led_out[b].on if on else self.led_out[b].off)()


def spawn(fn, *a) -> threading.Thread:
    t = threading.Thread(target=fn, args=a, daemon=True)
    t.start()
    return t
