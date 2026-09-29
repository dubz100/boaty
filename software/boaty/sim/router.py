"""Stand-in for B1 (mavlink-router on the Pi Zero) in simulation.

On the boat, mavlink-router (ICD IF-04 configuration) joins three endpoints:

    helm             the flight controller's UART (here: SITL serial0 -> UDP)
    missioncontrol   UDP client to the bank, over the radio (IF-01)
    local            UDP server on 127.0.0.1:14560 for services B2-B7

Every packet from one endpoint goes to all the others, and a local client
also hears the other local clients. That is enough for our traffic: one
helm, one GCS, a handful of services. The real boat runs mavlink-router
itself; this class only reproduces its topology so the simulator fails the
same way the boat does. Killing it (stop()) is "the Pi Zero crashed": the
bank link goes with it, as it would on the boat.
"""
from __future__ import annotations

import select
import socket
import threading


class Router:
    def __init__(self, helm_port: int = 14570, local_port: int = 14560,
                 mc_addr=("127.0.0.1", 14551), host: str = "127.0.0.1"):
        self.host = host
        self.helm_port, self.local_port, self.mc_addr = (helm_port,
                                                          local_port, mc_addr)
        self.helm_addr = None
        self.local_clients: set = set()
        self.counts = {"helm": 0, "mc": 0, "local": 0}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "Router":
        self.helm = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.helm.bind((self.host, self.helm_port))
        self.local = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.local.bind((self.host, self.local_port))
        self.mc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.mc.bind((self.host, 0))
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="b1-router",
                                        daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        for s in (self.helm, self.local, self.mc):
            s.close()

    @property
    def running(self) -> bool:
        return self._thread is not None

    def _send(self, sock, data, addr) -> None:
        try:
            sock.sendto(data, addr)
        except OSError:
            pass

    def _run(self) -> None:
        socks = [self.helm, self.local, self.mc]
        while not self._stop.is_set():
            try:
                ready, _, _ = select.select(socks, [], [], 0.1)
            except (OSError, ValueError):
                break
            for s in ready:
                try:
                    data, addr = s.recvfrom(65535)
                except OSError:
                    continue
                if s is self.helm:
                    self.helm_addr = addr
                    self.counts["helm"] += 1
                    self._send(self.mc, data, self.mc_addr)
                    for c in list(self.local_clients):
                        self._send(self.local, data, c)
                elif s is self.mc:
                    self.counts["mc"] += 1
                    if self.helm_addr:
                        self._send(self.helm, data, self.helm_addr)
                    for c in list(self.local_clients):
                        self._send(self.local, data, c)
                else:
                    self.local_clients.add(addr)
                    self.counts["local"] += 1
                    if self.helm_addr:
                        self._send(self.helm, data, self.helm_addr)
                    self._send(self.mc, data, self.mc_addr)
                    for c in list(self.local_clients):
                        if c != addr:
                            self._send(self.local, data, c)
