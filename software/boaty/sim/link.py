"""Simulated boat-bank radio link (IF-01) as a UDP relay.

SITL's telemetry port sends to the relay's boat side; the relay forwards to
Mission Control on UDP 14550 and relays replies back. Tests cut the link,
drop a fraction of packets or add latency to exercise FS-002/003 and SC-34.
"""
from __future__ import annotations

import heapq
import random
import socket
import threading
import time


class LinkRelay:
    def __init__(self, boat_port: int = 14551, gcs_addr=("127.0.0.1", 14550),
                 host: str = "127.0.0.1", seed: int = 1):
        self.host, self.boat_port, self.gcs_addr = host, boat_port, gcs_addr
        self.up = True
        self.loss = 0.0          # probability of dropping a packet
        self.latency_s = 0.0
        self.rng = random.Random(seed)
        self.boat_addr = None    # learned from SITL's first packet
        self._q: list = []       # (due, seq, sock, data, addr)
        self._seq = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.counts = {"up": 0, "down": 0, "dropped": 0}

    def start(self) -> "LinkRelay":
        # Boat side: SITL sends here.
        self.boat_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.boat_sock.bind((self.host, self.boat_port))
        self.boat_sock.settimeout(0.05)
        # GCS side: an ephemeral port that sends to Mission Control.
        self.gcs_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.gcs_sock.bind((self.host, 0))
        self.gcs_sock.settimeout(0.05)
        self._threads = [
            threading.Thread(target=self._pump, args=(True,), daemon=True),
            threading.Thread(target=self._pump, args=(False,), daemon=True),
            threading.Thread(target=self._deliver, daemon=True)]
        for t in self._threads:
            t.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=1)
        self.boat_sock.close()
        self.gcs_sock.close()

    # Test controls ---------------------------------------------------------
    def cut(self) -> None:
        self.up = False

    def restore(self) -> None:
        self.up, self.loss, self.latency_s = True, 0.0, 0.0

    def degrade(self, loss: float = 0.0, latency_s: float = 0.0) -> None:
        self.loss, self.latency_s = loss, latency_s

    # -----------------------------------------------------------------------
    def _pump(self, from_boat: bool) -> None:
        src = self.boat_sock if from_boat else self.gcs_sock
        while not self._stop.is_set():
            try:
                data, addr = src.recvfrom(65535)
            except (socket.timeout, OSError):
                continue
            if from_boat:
                self.boat_addr = addr
            if not self.up or self.rng.random() < self.loss:
                self.counts["dropped"] += 1
                continue
            if from_boat:
                dst_sock, dst = self.gcs_sock, self.gcs_addr
                self.counts["down"] += 1
            else:
                if self.boat_addr is None:
                    continue
                dst_sock, dst = self.boat_sock, self.boat_addr
                self.counts["up"] += 1
            if self.latency_s <= 0:
                self._send(dst_sock, data, dst)
            else:
                with self._lock:
                    self._seq += 1
                    heapq.heappush(self._q, (time.monotonic() + self.latency_s,
                                             self._seq, dst_sock, data, dst))

    def _deliver(self) -> None:
        while not self._stop.is_set():
            now = time.monotonic()
            with self._lock:
                due = []
                while self._q and self._q[0][0] <= now:
                    due.append(heapq.heappop(self._q))
            for _, _, s, data, dst in due:
                self._send(s, data, dst)
            time.sleep(0.002)

    @staticmethod
    def _send(sock, data, dst) -> None:
        try:
            sock.sendto(data, dst)
        except OSError:
            pass
