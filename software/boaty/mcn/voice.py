"""C4 voice: push-to-talk speech in, phrase set out (IF-12, MCN-D25, D27).

On the Pi 5 both directions run on the device (ADD DD-07): speech-to-text
while TALK is held (audio is never stored or sent), text-to-speech for the
IF-12 phrases. Here are the interfaces, the phrase set, and the stand-ins
the simulator uses. Real engines plug in behind the same two methods.
"""
from __future__ import annotations

import shutil
import subprocess
import threading
from typing import Protocol

PHRASES = {
    "plan_ready": "Ask a grown-up to check it.",
    "start": "Off we go!",
    "photo": "Taking pictures!",
    "come_home": "Coming home!",
    "stop": "Stopping!",
    "failsafe": "I need to come home now.",
    "stuck": "I'm stuck in some weed, trying to wiggle free.",
    "held": "I've stopped. A grown-up needs to check me.",
    "home": "I'm back! Let's look at the pictures.",
    "not_yet": "Not yet!",
    "ask_arm": "Ask a grown-up to arm.",
    "not_now": "Not now.",
    "fence": "I went too far, so I've stopped my motors.",
    "impostor": "Something else is talking to me. A grown-up needs to "
                "check.",
}


class Speaker(Protocol):
    def say(self, text: str) -> None: ...


class Listener(Protocol):
    def start(self) -> None: ...                  # TALK pressed
    def stop(self) -> str: ...                    # TALK released: transcript


class RecordingSpeaker:
    """Simulator speaker: remembers what was said and when."""

    def __init__(self, clock=None):
        self.clock = clock or (lambda: 0.0)
        self.said: list[tuple[float, str]] = []
        self._lock = threading.Lock()

    def say(self, text: str) -> None:
        with self._lock:
            self.said.append((self.clock(), text))

    def texts(self) -> list[str]:
        return [t for _, t in self.said]


class ScriptedListener:
    """Simulator microphone: returns the next queued transcript."""

    def __init__(self, *transcripts: str):
        self.queue = list(transcripts)
        self.listening = False

    def start(self) -> None:
        self.listening = True

    def stop(self) -> str:
        self.listening = False
        return self.queue.pop(0) if self.queue else ""


class EspeakSpeaker:
    """Fallback on-device TTS if espeak-ng is installed (the chosen engine
    is set in ADD DD-07; this keeps the bench usable without it)."""

    def __init__(self, voice: str = "en-gb", speed: int = 150):
        self.exe = shutil.which("espeak-ng") or shutil.which("espeak")
        self.voice, self.speed = voice, speed

    def say(self, text: str) -> None:
        if self.exe:
            subprocess.Popen([self.exe, "-v", self.voice, "-s",
                              str(self.speed), text],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
