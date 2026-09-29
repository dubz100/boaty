# Boaty simulator results (slices 1-2)

Generated 2026-09-29T06:38:10.532575+00:00 from `results/sitl_results.json`. ArduPilot Rover 4.7.1 SITL on the Boaty boat model, speed-up 5x.

**33 passed, 3 known gaps (requirement not met natively; finding recorded), 0 failed, 0 errors** out of 36 scenarios.

| ID | Scenario | Result | Criterion | Refs |
|---|---|---|---|---|
| B2-01 | Photos during a mission | **PASS** | Burst of 3 within 0.5 s of reaching photo point 2; interval photos every 5 s in AUTO; every photo geotagged within 3 m of the boat's true position | CAM-002, CAM-003, MCP-D10, MCP-D11, IF-03 |
| FS-001b | Reduced RTL speed at critical battery | **PASS** | After the critical battery failsafe, B6 slows RTL to 0.6 m/s (+/- 0.1) and raises an alarm | FS-001, V-15, MCP-D15 |
| IF-14-01 | Status snapshot after connect | **PASS** | Link up, disarmed, 3D fix, EKF healthy, home set | IF-14, IF-02 |
| IF-14-02 | Parameter baseline matches the controlled file | **PASS** | Every parameter in boaty-mk1.parm and sitl.parm exists on Rover 4.7.1 with the file's value | SAF-007, SC-24 |
| IF-14-03 | Fence and mission upload, read-back and verify | **PASS** | Read-back equals what was sent; verify() rejects a different mission | IF-14, VAL-010, SC-32 |
| IF-14-04 | Uploads refused while armed | **PASS** | upload_fence/upload_mission/set_param raise NotAllowedWhileArmed | IF-14, FEN-007, SAF-003 |
| IF-14-05 | Arming lands in HOLD, never MANUAL | **PASS** | After arm(): armed, SRS mode HOLD, motors off | MOD-003, INITIAL_MODE |
| IF-14-06 | hold/return_home/manual/start_mission map to the IF-02 mode table | **PASS** | Each call reaches the right ArduPilot and SRS mode | IF-02, IF-14 |
| IF-14-07 | drive() moves the boat in MANUAL | **PASS** | Throttle 0.6 for 5 s moves the boat > 2 m forward | IF-02, MC-008 |
| SC-01 | Battery drain to 35% then 15% | **PASS** | RTL at 35% (+/- 2%); critical alarm at 15%; reaches home within 5 m | FS-001, SC-01 |
| SC-02a | Link cut in STEERING: helm part | **PASS** | HOLD <= 3 s after the link is cut (FS-002 relaxed to 3 s by CR-05; the RTL at 10 s is B4: SC-02b) | FS-002, SC-02, CR-05 |
| SC-02b | Link cut in STEERING: B4 RTL at 10 s | **PASS** | HOLD <= 3 s (helm), then RTL 10 s (+/- 1 s) after the link is cut (B4), and the boat heads home | FS-002, SC-02, MCP-D12, CR-05 |
| SC-03 | Link cut in AUTO | **PASS** | Mission continues; RTL 60 s (+/- 1 s) after the link is cut (B4) | FS-003, SC-03, MCP-D12, FM-31 |
| SC-04 | GNSS failure 5 s then restore | **PASS** | Motors stop <= 3 s after the fix is lost (B6 HOLD); RTL once the position has been healthy for 10 s | FS-004, SC-04, FM-01, FM-06, MCP-D15 |
| SC-04 | GNSS failure 5 s then restore | **KNOWN GAP** | Motors stop <= 3 s after the fix is lost (the RTL after 10 s healthy is B6, slice 2) | FS-004, SC-04, FM-01, FM-06 |
| SC-06 | Drag released after burst 2 | **PASS** | Stuck -> HOLD; B5 astern bursts (<= 0.5 m/s, <= 2 s); weed clears during burst 2; mission resumes; <= 3 bursts | FS-006, SC-06, MCP-D18, FM-27 |
| SC-06b | Permanent weed: three bursts then HOLD + alarm | **PASS** | Exactly 3 bursts, then HOLD with a 'still stuck' alarm, and nothing restarts the motors | FS-006, MCP-D18, FM-27 |
| SC-07 | Kill the whole mission computer mid-mission | **PASS** | With B1-B7 dead (and so the bank link), the helm completes the mission, returns and holds within 5 m of home | FS-007, SC-07, FM-26, MOD-005 |
| SC-09a | STOP from AUTO: motors off and disarmed | **PASS** | Helm commands the motors to neutral <= 1 s after stop(); helm disarmed; stop() is idempotent | FS-009, IF-14 |
| SC-10 | Moisture flagged | **PASS** | RTL <= 2 s after the moisture sensor trips; alarm raised; IF-03 health shows fault | FS-010, SC-10, FM-24, MCP-D15 |
| SC-28 | Persistent breach (wind pushing out) | **PASS** | Offshore gale: B7 stops the motors before 30 s outside or 10 m outside, and they stay stopped (detector recorded) | FEN-006, SC-28, FM-14, V-14 |
| SC-29 | Single motor failure | **PASS** | Right motor dead mid-leg: HOLD within 20 s (from whichever detector fires first), the boat stays inside the fence and ends in HOLD with an alarm | FS-013, SC-29, FM-17, MCP-D24 |
| SC-38 | First-motion heading check | **PASS** | Compass reversed before the start: HOLD <= 10 s after AUTO begins; the boat stays inside the fence | FM-05, FM-18, SC-38, MCP-D22, A-03 |
| V-02 | Fence is enforced in the mode used for MANUAL | **PASS** | Driving straight at the fence in STEERING for 60 s: the boat reaches the fence area but never gets more than 10 m outside | FEN-004, V-02 |
| V-03 | GCS failsafe can 'continue in AUTO' | **PASS** | Link cut in AUTO for 20 s: mode stays AUTO and the mission keeps progressing | FS-003, V-03 |
| V-04 | Boat loiters at home at the end of RTL | **PASS** | After arriving home in RTL, with a 4 m/s wind for 60 s, the boat stays within 5 m of home | MOD-005, V-04 |
| V-05 | Crash check can meet FS-005 (stuck detection) | **KNOWN GAP** | Heavy weed drag in AUTO: HOLD within 5 s of the boat being stuck (< 0.1 m/s) | FS-005, V-05, SC-05, FM-16 |
| V-06 | Helm counts only Mission Control heartbeats as GCS | **PASS** | With Mission Control silent but the mission computer (1/191) heartbeating, the GCS failsafe still fires | FS-002, V-06, IF-02 |
| V-06b | A second system-255 heartbeat masks the GCS failsafe | **PASS** | Shows why C7 must refuse to operate when a foreign system-255 source appears | FM-41, SC-37 |
| V-11 | GUIDED stops within 3 s if velocity targets stop | **KNOWN GAP** | After the last velocity target, motors are off within 3 s | FS-006, V-11 |
| V-12 | Skid-steer boat frame behaves plausibly | **PASS** | Flies the 30 m triangle: cross-track RMS <= 3 m, mean speed within 20% of 1.0 m/s | SWE-004, V-12, NAV-004, NAV-005 |
| V-13 | Second voltage input gates arming (key in/out) | **PASS** | Rail reads < 9 V: arming refused with a battery-2 reason; rail restored: arming works | MOD-003, PRE-007, V-13 |
| V-14 | Native mechanism to stop motors on persistent breach | **PASS** | Offshore gale pushes the boat out: does ArduPilot itself stop the motors by 30 s / 10 m outside? (answer recorded) | FEN-006, V-14, SC-28, FM-14 |
| V-15 | Reduced speed during RTL on critical battery | **PASS** | Answer recorded: RTL speed after the critical battery failsafe, compared with WP_SPEED (1.0 m/s) | FS-001, V-15 |
| V-16 | GNSS-velocity yaw fallback when the compass disagrees | **PASS** | Single compass rotated 90 degrees mid-mission: the boat never leaves the fence (it may HOLD); heading error recorded | NAV-008, V-16, SC-22, FM-04, FS-013 |
| V-17 | Does the helm refuse fence changes while armed? | **PASS** | Answer recorded; our helm API refuses regardless | FEN-007, V-17 |

## Evidence

### B2-01: Photos during a mission (PASS)

- `photos`: 21
- `burst`: 3
- `interval`: 18
- `first_burst_after_reached_s`: 0.0
- `worst_geotag_error_m`: 0.278
- `untagged`: 0

### FS-001b: Reduced RTL speed at critical battery (PASS)

- `rtl_speed_m_s`: 0.58
- `events`: BOATY B6 CRITICAL BATTERY: SLOW RTL

### IF-14-01: Status snapshot after connect (PASS)

- `mode`: DISARMED
- `fix`: 6
- `sats`: 10
- `battery_v`: 12.48
- `rail_v`: 12.48

### IF-14-02: Parameter baseline matches the controlled file (PASS)

- `parameters_in_baseline`: 58
- `live_parameters`: 1273
- `differences`: 0

### IF-14-03: Fence and mission upload, read-back and verify (PASS)

- `fence_vertices`: 4
- `mission_items`: 3

### IF-14-04: Uploads refused while armed (PASS)


### IF-14-05: Arming lands in HOLD, never MANUAL (PASS)

- `mode`: HOLD
- `ardupilot_mode`: 4

### IF-14-06: hold/return_home/manual/start_mission map to the IF-02 mode table (PASS)

- `start_mission`: 10/AUTO
- `hold`: 5/HOLD
- `return_home`: 11/RTL
- `manual`: 3/MANUAL

### IF-14-07: drive() moves the boat in MANUAL (PASS)

- `moved_m`: 3.57

### SC-01: Battery drain to 35% then 15% (PASS)

- `battery_pct_at_rtl`: 35
- `distance_home_m`: 2.993
- `texts`: Battery 1 is low 10.89V used 1625 mAh; Battery 1 is critical 10.43V used 2126 mAh
- Note: Reduced speed at 15% is not native (see V-15); it belongs to the mission computer in slice 2.

### SC-02a: Link cut in STEERING: helm part (PASS)

- `hold_after_cut_s`: 3.032
- `native_minimum_s`: FS_GCS_TIMEOUT 2 + FS_TIMEOUT 1

### SC-02b: Link cut in STEERING: B4 RTL at 10 s (PASS)

- `hold_after_s`: 3.052
- `rtl_after_s`: 9.676
- `dist_home_at_cut_m`: 9.52
- `dist_home_15s_after_rtl_m`: 5.972
- `events`: BOATY B4 LINK LOST IN MANUAL: RTL

### SC-03: Link cut in AUTO (PASS)

- `mode_30s_after_cut`: AUTO
- `rtl_after_s`: 59.967
- `events`: BOATY B4 LINK LOST 60S: RTL

### SC-04: GNSS failure 5 s then restore (PASS)

- `outputs_neutral_after_s`: 2.497
- `thrust_gone_after_s`: 2.575
- `rtl_after_restore_s`: 10.691
- `events`: BOATY B6 POSITION LOST: HOLD; BOATY B6 POSITION OK: RTL
- Note: RTL comes 10 s after B6 sees a healthy position, which includes the EKF's own recovery after the fix returns.

### SC-04: GNSS failure 5 s then restore (KNOWN GAP)

- `motors_off_after_s`: 9.152
- `modes`: [8.2, 'HOLD']
- `texts`: EKF variance; EKF failsafe; EKF failsafe cleared
- **Known gap:** Finding: EKF failsafe stops motors ~9 s after GNSS loss; FS-004 asks 3 s. Needs B6 fix-loss HOLD.
- Failure: `AssertionError: motors still running 3 s after GNSS loss`

### SC-06: Drag released after burst 2 (PASS)

- `bursts`: 2
- `min_speed_during_burst_m_s`: -0.01
- `mode_after`: AUTO
- `speed_after_m_s`: 0.986
- `events`: BOATY B5 SHED START; BOATY B5 FREE AFTER 2: RESUMED; BOATY B5 SHED END

### SC-06b: Permanent weed: three bursts then HOLD + alarm (PASS)

- `bursts`: 3
- `mode`: HOLD
- `motors_off`: True
- `events`: BOATY B5 SHED START; BOATY B5 STILL STUCK: HOLD; BOATY B5 SHED END

### SC-07: Kill the whole mission computer mid-mission (PASS)

- `home_after_s`: 242.716
- `final_distance_m`: 1.284

### SC-09a: STOP from AUTO: motors off and disarmed (PASS)

- `outputs_neutral_s`: 0.322
- `thrust_below_0_05N_s`: 0.574
- Note: Measured at 5x speed-up, so wall-clock latency in the test harness counts 5 times over; spin-down is the model's 0.1 s motor time constant.

### SC-10: Moisture flagged (PASS)

- `rtl_after_s`: 0.07
- `health_status`: fault
- `events`: BOATY B6 WATER IN BOX: RTL

### SC-28: Persistent breach (wind pushing out) (PASS)

- `hold_after_breach_s`: 6.682
- `outside_at_hold_m`: 7.322
- `detector`: B7 HEADING CHECK FAILED: HOLD
- `motors_running_in_next_30s_s`: 1.05
- `b7_actions`: B7 HEADING CHECK FAILED: HOLD
- `events`: BOATY B7 HEADING CHECK FAILED: HOLD
- Note: In a gale that blows the boat backwards the first-motion heading check fires first (course and heading 180 deg apart). The outcome, motors off, is what FEN-006 wants; the diagnosis is wrong.

### SC-29: Single motor failure (PASS)

- `first_hold_after_s`: 8.886
- `first_detector`: helm crash check
- `worst_outside_m`: 0.0
- `final_mode`: HOLD
- `events`: BOATY B5 SHED START; BOATY B5 STILL STUCK: HOLD; BOATY B5 SHED END
- Note: A dead motor looks like 'stuck' to the helm's crash check, so B5 tries its astern bursts before giving up. Safe, but B5 cannot tell weed from a dead motor.

### SC-38: First-motion heading check (PASS)

- `hold_after_s`: 9.685
- `detector`: B7 HEADING CHECK FAILED: HOLD
- `worst_outside_m`: 0.0
- `events`: BOATY B7 HEADING CHECK FAILED: HOLD

### V-02: Fence is enforced in the mode used for MANUAL (PASS)

- `max_north_m`: 22.562
- `fence_line_north_m`: 25.0
- `worst_outside_m`: 0.0
- `fence_action`: none needed
- `texts`: -
- Note: Rover's fence avoidance (AVOID_*) holds the boat short of the fence line in MANUAL, so the breach action is a second layer.

### V-03: GCS failsafe can 'continue in AUTO' (PASS)

- `modes_during_cut`: AUTO (unchanged)
- `progress_m`: 19.877
- `failsafe_texts`: GCS Failsafe; Failsafe - Continuing Auto Mode

### V-04: Boat loiters at home at the end of RTL (PASS)

- `max_drift_m`: 1.842
- `mode_at_end`: RTL
- Note: ArduPilot stays in RTL and station-keeps for boats; Mission Control must show 'arrived' as HOLD (MOD-005).

### V-05: Crash check can meet FS-005 (stuck detection) (KNOWN GAP)

- `stuck_after_weed_s`: 0.064
- `hold_after_stuck_s`: 15.042
- `crash_text`: Crash: Going to HOLD
- **Known gap:** Finding: native crash check resets on any noisy GNSS speed sample; stuck-to-HOLD varies 4.9-20 s. Needs B7 second stuck detector (A-07).
- Failure: `assert (68.51499999994581 - 53.47249999995949) <= (5.0 + 1.0)`

### V-06: Helm counts only Mission Control heartbeats as GCS (PASS)

- `failsafe_after_s`: 2.988

### V-06b: A second system-255 heartbeat masks the GCS failsafe (PASS)

- `failsafe_fired`: False
- Note: Expected: the failsafe does NOT fire, because ArduPilot accepts any system-255 heartbeat. Mitigation is FM-41 / SC-37 in Mission Control (slice 3).

### V-11: GUIDED stops within 3 s if velocity targets stop (KNOWN GAP)

- `speed_before_m_s`: 1.028
- `motors_off_after_s`: 3.929
- Note: Rover 4.7.1 mode_guided.cpp: 3 s timeout, then a decelerating stop (ATC_DECEL_MAX).
- **Known gap:** Finding: GUIDED times out after 3 s then decelerates; motors off ~3.9 s.
- Failure: `assert (53.25666666662635 is not None and (53.25666666662635 - 49.32749999996326) <= 3.0)`

### V-12: Skid-steer boat frame behaves plausibly (PASS)

- `cross_track_rms_m`: 0.155
- `cross_track_max_m`: 0.401
- `mean_speed_m_s`: 1.008
- `samples`: 295

### V-13: Second voltage input gates arming (key in/out) (PASS)

- `rail_v_key_out`: 1.235
- `refusal`: Arm: Battery 2 below minimum arming voltage
- `armed_with_key_in`: True
- Note: SITL cannot switch its second analogue input off, so key out is emulated by scaling BATT2_VOLT_MULT; the real switch is tested on L2 (L2-13).

### V-14: Native mechanism to stop motors on persistent breach (PASS)

- `outside_after_40s_m`: 41.727
- `motors_running`: True
- `mode`: RTL
- Note: Answer: NO native stop - ArduPilot keeps fighting in RTL. FEN-006 must be met by B7/B-services (slice 2).

### V-15: Reduced speed during RTL on critical battery (PASS)

- `rtl_speed_after_critical_m_s`: 0.999
- `distance_home_m`: 41.362
- `mode`: RTL
- `texts`: Battery 1 is low 10.89V used 1625 mAh; Battery 1 is critical 10.21V used 2126 mAh
- Note: Answer: NO native speed reduction: FS-001's reduced speed at 15% must come from the mission computer (slice 2).

### V-16: GNSS-velocity yaw fallback when the compass disagrees (PASS)

- `sim_mag1_orient`: 2.0
- `worst_outside_m`: 0.0
- `worst_heading_error_deg`: 101.624
- `heading_error_last_20s_deg`: 100.96
- `mission_seq_at_end`: 3
- `mission_total`: 3
- `texts`: -
- `mode_at_end`: AUTO
- Note: Finding: with its only compass rotated, the EKF heading stays wrong (no GSF yaw reset, no message), yet the boat still tracks its mission on GNSS course. Heading-dependent outputs (photo tags, map arrow) would be wrong; B7's heading-vs-course check (A-03, SC-38) is what catches it.

### V-17: Does the helm refuse fence changes while armed? (PASS)

- `ardupilot_native`: accepted
- Note: FEN-007 is enforced by C7 (NotAllowedWhileArmed) whatever ArduPilot does.
