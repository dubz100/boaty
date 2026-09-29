"""IF-04 / MCP-D19 command filter, including the SC-30 fuzz test."""
import random

import pytest

import boaty  # noqa: F401  (MAVLink 2 before pymavlink loads)
from pymavlink import mavutil

from boaty.mcp.policy import (ASTERN_MASK, AUTO, GUIDED, HOLD, RTL, Filter)

mavutil.set_dialect("ardupilotmega")
mav = mavutil.mavlink
M = mavutil.mavlink.MAVLink(None, srcSystem=1, srcComponent=191)
CUSTOM = mav.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED


def set_mode(mode):
    return M.command_long_encode(1, 1, mav.MAV_CMD_DO_SET_MODE, 0, CUSTOM,
                                 mode, 0, 0, 0, 0, 0)


def astern(thrust, rate=0.0, mask=ASTERN_MASK):
    return M.set_attitude_target_encode(0, 1, 1, mask, [1, 0, 0, 0], 0, 0,
                                        rate, thrust)


@pytest.mark.parametrize("svc,mode,ok", [
    ("B4", RTL, True), ("B4", HOLD, False), ("B4", AUTO, False),
    ("B6", RTL, True), ("B6", HOLD, True), ("B6", GUIDED, False),
    ("B7", HOLD, True), ("B7", RTL, False), ("B7", AUTO, False),
    ("B5", GUIDED, True), ("B5", HOLD, True), ("B5", AUTO, False),
    ("B2", HOLD, False), ("B3", RTL, False),
    ("B7", 0, False), ("B7", 3, False),            # MANUAL, STEERING
])
def test_mode_changes_per_service(svc, mode, ok):
    assert Filter(svc).check(set_mode(mode))[0] is ok


def test_b5_may_resume_only_the_mode_it_interrupted():
    f = Filter("B5")
    assert not f.check(set_mode(AUTO))[0]
    f.grant_resume(AUTO)
    assert f.check(set_mode(AUTO))[0]
    assert not f.check(set_mode(RTL))[0]
    f.grant_resume(3)                                # STEERING: refused
    assert not f.check(set_mode(3))[0]
    f.grant_resume(None)
    assert not f.check(set_mode(AUTO))[0]


def test_astern_bursts():
    f = Filter("B5")
    assert f.check(astern(-0.5), GUIDED)[0]
    assert f.check(astern(-0.2), GUIDED)[0]
    assert not f.check(astern(-0.5), AUTO)[0]        # only in GUIDED
    assert not f.check(astern(-0.8), GUIDED)[0]      # too fast
    assert not f.check(astern(0.5), GUIDED)[0]       # ahead
    assert not f.check(astern(-0.5, rate=0.3), GUIDED)[0]   # turning
    assert not f.check(astern(-0.5, mask=0), GUIDED)[0]     # attitude used
    assert not Filter("B7").check(astern(-0.5), GUIDED)[0]


def test_velocity_targets_are_forbidden():
    """A negative body velocity makes Rover turn round, not reverse."""
    msg = M.set_position_target_local_ned_encode(
        0, 1, 1, mav.MAV_FRAME_BODY_NED, 0b0000110111000111, 0, 0, 0, -0.5,
        0, 0, 0, 0, 0, 0, 0)
    assert not Filter("B5").check(msg, GUIDED)[0]


def test_change_speed_only_b6_only_in_rtl_only_down():
    cs = lambda v: M.command_long_encode(  # noqa: E731
        1, 1, mav.MAV_CMD_DO_CHANGE_SPEED, 0, 1, v, -1, 0, 0, 0, 0)
    assert Filter("B6").check(cs(0.6), RTL)[0]
    assert not Filter("B6").check(cs(0.6), AUTO)[0]
    assert not Filter("B6").check(cs(2.0), RTL)[0]
    assert not Filter("B4").check(cs(0.6), RTL)[0]


FORBIDDEN_BUILDERS = [
    lambda: M.command_long_encode(1, 1, mav.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                                  1, 0, 0, 0, 0, 0, 0),
    lambda: M.command_long_encode(1, 1, mav.MAV_CMD_COMPONENT_ARM_DISARM, 0,
                                  0, 21196, 0, 0, 0, 0, 0),
    lambda: M.param_set_encode(1, 1, b"FENCE_ENABLE", 0,
                               mav.MAV_PARAM_TYPE_REAL32),
    lambda: M.mission_count_encode(1, 1, 3, 0),
    lambda: M.mission_count_encode(1, 1, 3, 1),
    lambda: M.mission_item_int_encode(1, 1, 0, 0, 16, 0, 1, 0, 0, 0, 0, 0,
                                      0, 0, 0),
    lambda: M.mission_clear_all_encode(1, 1, 0),
    lambda: M.mission_clear_all_encode(1, 1, 1),
    lambda: M.manual_control_encode(1, 0, 0, 1000, 0, 0),
    lambda: M.rc_channels_override_encode(1, 1, *([1900] * 8)),
    lambda: M.command_long_encode(1, 1, mav.MAV_CMD_DO_FENCE_ENABLE, 0, 0,
                                  0, 0, 0, 0, 0, 0),
    lambda: M.command_long_encode(1, 1, mav.MAV_CMD_MISSION_START, 0, 0, 0,
                                  0, 0, 0, 0, 0),
    lambda: M.command_long_encode(1, 1, mav.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0,
                                  0, 0, 0, 0, 0, 0, 0),
    lambda: M.command_long_encode(1, 1, mav.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
                                  0, 1, 0, 0, 0, 0, 0, 0),
    lambda: M.set_mode_encode(1, CUSTOM, AUTO),
]


def test_sc30_command_fuzz():
    """SC-30: random forbidden commands from every service, in every helm
    mode, are all refused."""
    rng = random.Random(30)
    for _ in range(3000):
        svc = rng.choice(["B2", "B3", "B4", "B5", "B6", "B7"])
        mode = rng.choice([None, 0, 3, HOLD, 5, AUTO, RTL, GUIDED])
        msg = rng.choice(FORBIDDEN_BUILDERS)()
        f = Filter(svc)
        if rng.random() < 0.3:
            f.grant_resume(rng.choice([AUTO, RTL]))
        ok, why = f.check(msg, mode)
        assert not ok, (svc, mode, msg.get_type(), why)
    # And random mode numbers: only each service's own list gets through.
    allowed = {"B4": {RTL}, "B5": {GUIDED, HOLD}, "B6": {RTL, HOLD},
               "B7": {HOLD}, "B2": set(), "B3": set()}
    for _ in range(3000):
        svc = rng.choice(list(allowed))
        mode = rng.randrange(0, 30)
        assert Filter(svc).check(set_mode(mode))[0] is (mode in allowed[svc])
