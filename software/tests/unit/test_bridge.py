"""The JSON bridge speaks ArduPilot's SITL JSON protocol correctly."""
import json
import socket
import struct

import pytest

from boaty.sim.bridge import MAGIC_16, JsonBridge, pwm_to_cmd


def packet(count, pwm, rate=400, magic=MAGIC_16):
    pwm = list(pwm) + [0] * (16 - len(pwm))
    return struct.pack("<HHI16H", magic, rate, count, *pwm)


def test_pwm_mapping():
    assert pwm_to_cmd(1500) == 0
    assert pwm_to_cmd(2000) == 1
    assert pwm_to_cmd(1000) == -1
    assert pwm_to_cmd(0) == 0          # disabled output = stop
    assert pwm_to_cmd(2400) == 1


def test_reply_has_every_mandatory_field():
    br = JsonBridge()
    reply = br.handle(packet(1, [1500] * 4))
    assert reply.startswith(b"\n") and reply.endswith(b"\n")
    s = json.loads(reply)
    for key in ("timestamp", "position", "velocity", "attitude"):
        assert key in s
    assert set(s["imu"]) == {"gyro", "accel_body"}
    assert s["battery"]["voltage"] > 12


def test_channels_one_and_four_drive_the_pods():
    br = JsonBridge()
    for i in range(1, 400):
        br.handle(packet(i, [2000, 1500, 1500, 1500]))   # left only
    assert br.boat.thrust[0] > 1.5 and br.boat.thrust[1] == 0
    assert br.boat.r > 0


def test_repeated_frame_does_not_step():
    br = JsonBridge()
    br.handle(packet(5, [2000, 1500, 1500, 2000]))
    t = br.boat.t
    br.handle(packet(5, [2000, 1500, 1500, 2000]))
    assert br.boat.t == t


def test_frame_count_going_backwards_resets_the_boat():
    br = JsonBridge()
    for i in range(1, 800):
        br.handle(packet(i, [2000, 1500, 1500, 2000]))
    assert br.boat.n > 0.1
    br.handle(packet(1, [1500] * 4))
    assert br.boat.n == pytest.approx(0.0, abs=0.01)


def test_bad_magic_is_ignored():
    assert JsonBridge().handle(packet(1, [1500], magic=1234)) is None


def test_udp_round_trip():
    br = JsonBridge(port=19002).start()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.sendto(packet(1, [1500] * 4), ("127.0.0.1", 19002))
        data, _ = s.recvfrom(4096)
        assert json.loads(data)["timestamp"] > 0
        assert br.wait_for_sitl(timeout=1)
    finally:
        br.stop()
