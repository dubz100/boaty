# Simulator slice 1: findings

What flying the real ArduPilot Rover 4.7.1 firmware on the Boaty boat model
showed about the design. Evidence for each item is in `SITL_REPORT.md`. These
feed ADD Issue F, ICD Issue E, SSS-HLM Issue D and the SRS.

## Requirements the native autopilot does not meet

| # | Requirement | What the simulator measured | Proposed disposition |
|---|---|---|---|
| S1-01 | FS-002: HOLD <= 2 s after link loss in MANUAL | 3.0 s. Rover's GCS failsafe cannot be faster than FS_GCS_TIMEOUT (min 2 s) + FS_TIMEOUT (min 1 s) | Owner decision: relax FS-002 to 3 s, or have B4 command HOLD at 2 s |
| S1-02 | FS-004: motors stop <= 3 s after GNSS loss | 9.2 s (EKF variance failsafe) | B6 watches the fix and commands HOLD at 3 s (slice 2) |
| S1-03 | FS-005: HOLD within 5 s of being stuck | 4.9 s usually, 15-20 s about 1 run in 3: one noisy GNSS speed sample resets the crash-check counter | Confirms FMEA A-07: B7's filtered second stuck detector (slice 2) |
| S1-04 | FEN-006: stop motors after 30 s / 10 m outside the fence | No native mechanism: 42 m outside after 40 s, still fighting in RTL | B7 (slice 2), as the ADD assumed (V-14 answered) |
| S1-05 | FS-001: reduced speed on critical battery | No native reduction: RTL continues at 1.0 m/s | Mission computer lowers WP_SPEED via GUIDED/params, or the requirement changes (slice 2) |
| S1-06 | V-11: GUIDED stops <= 3 s without targets | 3.9 s (3 s timeout, then decelerating stop) | Accept: B5 bursts are short; about 1 m extra travel |

## Things the design assumed that turned out true

- Fence is enforced in MANUAL. Rover's fence avoidance stopped the boat 2.5 m short of the line (V-02).
- GCS failsafe "continue in AUTO" works (V-03), and only system-255 heartbeats count, so the mission computer can't mask a lost bank link (V-06).
- At the end of RTL the boat station-keeps within 2.2 m in a 4 m/s wind (V-04). ArduPilot stays in RTL, so Mission Control must show "arrived" as HOLD (MOD-005).
- The motor-rail voltage on BATT2 blocks arming with the key out: "Battery 2 below minimum arming voltage" (V-13).
- Battery RTL fires at exactly 35%, the critical alarm follows, and the boat gets home (SC-01).
- The skid-steer boat tracks legs with 0.16 m RMS cross-track error at 1.0 m/s (V-12, NAV-005).

## Risks confirmed (mitigations already planned)

- **Impostor GCS (FM-41):** any system-255 heartbeat keeps the GCS failsafe from firing (V-06b). C7 must refuse to operate when a second 255 appears (SC-37).
- **Fence changes while armed (FEN-007):** ArduPilot accepts them (V-17). Only C7's `NotAllowedWhileArmed` guard enforces FEN-007, so it must stay covered by tests.
- **Single-compass fault (NAV-008):** with the compass rotated 90 degrees the EKF heading stays about 97 degrees wrong with no warning. The boat still completes the mission on GNSS course. Heading-dependent outputs (photo tags, map arrow) would be wrong. B7's heading-vs-course check (A-03, SC-38) is the detector.

## Specification errors found

- **ICD IF-02 manual drive:** Rover reads MANUAL_CONTROL `z` as throttle and `y` as steering, not `x`/`r`.
- **Parameter names (Rover 4.7):** `SYSID_THISMAV`/`SYSID_MYGCS` are now `MAV_SYSID`/`MAV_GCS_SYSID`, and `ARMING_CHECK` is now `ARMING_SKIPCHK`. The GCS failsafe needs `FS_GCS_TIMEOUT` as well as `FS_TIMEOUT`.
- **Baseline additions:**
  - `INITIAL_MODE 4`, `MODE_CH 0` and `RC_OPTIONS 1`: without them the boat armed into MANUAL.
  - `MOT_THST_ASYM 2.67`: the astern/ahead thrust ratio.
  - `CRASH_VEL_MIN` changed from 0.08 to 0.1 to match FS-005.
- **Simulator fidelity:** SITL simulates three compasses. The boat has one, so `sitl.parm` disables the spares. Otherwise single-compass faults are hidden.
