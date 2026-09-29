# Simulator findings (slices 1 and 2)

What flying the real ArduPilot Rover 4.7.1 firmware on the Boaty boat model
showed about the design:

- **Slice 1:** the autopilot on its own.
- **Slice 2:** the boat services B2-B7 on the simulated Pi Zero.

Evidence for each item is in `SITL_REPORT.md`. These findings feed ADD Issue F, ICD Issue E, SSS-HLM Issue D, SSS-MCP Issue C and SRS Issue F.

## Owner decisions

- **CR-05 (FS-002 relaxed to 3 s):** HOLD within 3 s of losing the link in MANUAL, which is the native minimum (FS_GCS_TIMEOUT 2 s + FS_TIMEOUT 1 s). Measured 3.04 s (SC-02a). B4 still commands RTL at 10 s (SC-02b).

## Gaps from slice 1, and how slice 2 closed them

| # | Requirement | Autopilot alone (slice 1) | With the boat services (slice 2) |
|---|---|---|---|
| S1-01 | FS-002 | 3.0 s to HOLD | Requirement relaxed to 3 s (CR-05). B4 RTL at 10 s (SC-02b) |
| S1-02 | FS-004: motors stop <= 3 s after GNSS loss | 9.2 s | **2.5-2.7 s** to motors commanded off (B6 HOLD), then RTL 10.7-10.9 s after the fix returns (SC-04, 7 runs) |
| S1-03 | FS-005: HOLD within 5 s of being stuck | 4.9 s usually, 15-20 s in about 1 run in 3 | Unchanged: the helm's crash check still varies. B7's second stuck detector backs it up at 10 s, and B5 handles the recovery. **FS-005's 5 s is met only most of the time.** |
| S1-04 | FEN-006: motors stop after 30 s or 10 m outside | No native mechanism | B7 stops the motors (SC-28: 7 s and 7.9 m after leaving the fence) |
| S1-05 | FS-001: reduced speed on critical battery | No native reduction | B6 slows RTL to **0.58 m/s** with DO_CHANGE_SPEED (FS-001b) |
| S1-06 | V-11: GUIDED stops <= 3 s | 3.9 s | Accepted: B5 bursts are 2 s, so about 1 m of extra travel |

## Slice 2 results

- **Link watchdog (B4):**
  - AUTO link loss: RTL at 60.0 s (SC-03).
  - MANUAL link loss: HOLD at 3.0 s from the helm, then RTL at about 10 s from B4, and the boat heads home (SC-02b).
- **Weed-shedding (B5):**
  - Weed clears during burst 2: B5 resumes the mission (SC-06).
  - Weed never clears: exactly 3 bursts, then HOLD and a "still stuck" alarm, with the motors off (SC-06b).
- **Health (B6):**
  - Water in the box: RTL after 0.18 s, and IF-03 health reports "fault" (SC-10).
- **Mission computer dies (SC-07):** with B1-B7 killed, which also cuts the bank link, the helm finishes the mission. Its final RTL item brings the boat home, holding 1.3 m off.
- **Navigation monitor (B7):**
  - Reversed compass: HOLD 9.5 s after AUTO starts (SC-38).
  - Dead motor: HOLD at 8.9 s (SC-29).
- **Photos (B2/B3):**
  - A burst of 3 was taken 1 ms after reaching the photo point, plus interval photos every 5 s.
  - Every geotag was within 0.25 m of the true position (B2-01).
  - The IF-03 API passes its contract tests: every endpoint, authentication, errors, EXIF and stale-position nulls.
- **Command filter (MCP-D19, SC-30):** 6,000 random forbidden or out-of-policy commands, from every service in every helm mode, were all refused.

## New findings in slice 2

- **Astern bursts need a different message (ICD IF-04 error).** In GUIDED, Rover turns a negative body-frame velocity into "turn round and drive forwards", so a weed-bound boat would pivot instead of backing out. B5 now uses SET_ATTITUDE_TARGET with thrust -0.5 and zero yaw rate, which Rover maps to straight astern. The filter only allows that form.
- **Thrust curve (baseline change):** with a propeller's thrust ~ throttle^2 and `MOT_THST_EXPO` at its default 0, small steering commands give almost no turning thrust. A 180 degree pivot took 20 s, and the boat sat still for about 10 s after B4's RTL. `MOT_THST_EXPO 1.0` cuts the pivot to 6 s. Re-tune from thrust-stand data (KCL DS-09).
- **GNSS loss detection has two halves.** The helm takes about 1.5 s to report a lost fix. B6's 3 s confirmation (the obvious reading of FS-004) therefore gave 4.6 s, and 1.5 s still straddled the limit (2.99-3.13 s). At 1.0 s it gives 2.5-2.7 s over 7 runs. The trade-off: a genuine 1 s glitch would cause a nuisance HOLD, followed by RTL once the position is healthy again.
- **B7's heading check misfires in a gale.** When wind blows the boat backwards, course and heading are 180 degrees apart, which looks exactly like a reversed compass. B7 then stops the motors, which is the right outcome for FEN-006 but the wrong diagnosis. This happens only far outside the wind limit (15 m/s against ENV-002's 5.4 m/s).
- **A dead motor looks like weed.** The helm's crash check fires first, so B5 tries its astern bursts before giving up with HOLD and an alarm. That is safe, but the alarm says "stuck" rather than "motor fault". Motor RPM telemetry (KCL KF-09) would tell the two apart.
- **B7 stays quiet near the target (new threshold `near_target_m` 5 m).** While station-keeping at home, "progress along the leg" means nothing, and in wind the throttle can pass 50%. Without this, B7 would call "stuck" at home.
- **B5 waits until it sees GUIDED.** The filter checks commands against the helm's reported mode, so B5 must wait for the heartbeat to show GUIDED before sending bursts. Otherwise the first second of each burst is refused.
- **MAVLink 2 from the first packet.** pymavlink otherwise starts on MAVLink 1 and upgrades only after hearing the helm, silently dropping `mission_type` from anything sent earlier. The package now forces MAVLink 2 (IF-02).
- **Spec allocations added in slice 2** (for SSS-MCP Issue C and ICD IF-04):
  - B6 may request HOLD on position loss (FS-004).
  - B6 may send DO_CHANGE_SPEED, but only in RTL and only to reduce speed (FS-001).
  - B7 enforces FEN-006.

## From slice 1 (still valid)

- **Things the design assumed that turned out true:**
  - The fence is enforced in MANUAL: the boat stopped 2.5 m short of the line (V-02).
  - "Continue in AUTO" works (V-03).
  - Only system-255 heartbeats count as the GCS (V-06).
  - The boat station-keeps at home after RTL, within 2.2 m in a 4 m/s wind (V-04).
  - The BATT2 rail sense blocks arming with the key out (V-13).
  - Battery RTL fires at exactly 35% (SC-01).
  - Cross-track error is 0.16 m RMS (V-12).
- **Risks confirmed:**
  - An impostor system-255 heartbeat masks the GCS failsafe (V-06b, needs C7, SC-37).
  - ArduPilot accepts fence changes while armed, so only C7 enforces FEN-007 (V-17).
  - A single-compass fault leaves the EKF heading wrong with no warning (V-16). B7's first-motion check catches the reversed case (SC-38).
- **Specification errors:**
  - ICD IF-02: MANUAL_CONTROL uses `z` (throttle) and `y` (steering).
  - Parameter renames in Rover 4.7: `MAV_SYSID`, `MAV_GCS_SYSID`, `ARMING_SKIPCHK`, and `FS_GCS_TIMEOUT` is needed.
  - Baseline additions: `INITIAL_MODE 4`, `MODE_CH 0`, `RC_OPTIONS 1`, `MOT_THST_ASYM 2.67`.
  - `CRASH_VEL_MIN` changed to 0.1.
  - SITL must run with one compass, like the boat.
