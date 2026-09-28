# Boaty simulator results (slice 1)

Generated 2026-09-28T22:24:22.793251+00:00 from `results/sitl_results.json`. ArduPilot Rover 4.7.1 SITL on the Boaty boat model, speed-up 5x.

**21 passed, 3 known gaps (requirement not met natively; finding recorded), 0 failed, 0 errors** out of 24 scenarios.

| ID | Scenario | Result | Criterion | Refs |
|---|---|---|---|---|
| IF-14-01 | Status snapshot after connect | **PASS** | Link up, disarmed, 3D fix, EKF healthy, home set | IF-14, IF-02 |
| IF-14-02 | Parameter baseline matches the controlled file | **PASS** | Every parameter in boaty-mk1.parm and sitl.parm exists on Rover 4.7.1 with the file's value | SAF-007, SC-24 |
| IF-14-03 | Fence and mission upload, read-back and verify | **PASS** | Read-back equals what was sent; verify() rejects a different mission | IF-14, VAL-010, SC-32 |
| IF-14-04 | Uploads refused while armed | **PASS** | upload_fence/upload_mission/set_param raise NotAllowedWhileArmed | IF-14, FEN-007, SAF-003 |
| IF-14-05 | Arming lands in HOLD, never MANUAL | **PASS** | After arm(): armed, SRS mode HOLD, motors off | MOD-003, INITIAL_MODE |
| IF-14-06 | hold/return_home/manual/start_mission map to the IF-02 mode table | **PASS** | Each call reaches the right ArduPilot and SRS mode | IF-02, IF-14 |
| IF-14-07 | drive() moves the boat in MANUAL | **PASS** | Throttle 0.6 for 5 s moves the boat > 2 m forward | IF-02, MC-008 |
| SC-01 | Battery drain to 35% then 15% | **PASS** | RTL at 35% (+/- 2%); critical alarm at 15%; reaches home within 5 m | FS-001, SC-01 |
| SC-02 | Link cut in STEERING | **KNOWN GAP** | HOLD <= 2 s after the link is cut (the RTL at 10 s is B4, slice 2) | FS-002, SC-02 |
| SC-04 | GNSS failure 5 s then restore | **KNOWN GAP** | Motors stop <= 3 s after the fix is lost (the RTL after 10 s healthy is B6, slice 2) | FS-004, SC-04, FM-01, FM-06 |
| SC-09a | STOP from AUTO: motors off and disarmed | **PASS** | Helm commands the motors to neutral <= 1 s after stop(); helm disarmed; stop() is idempotent | FS-009, IF-14 |
| V-02 | Fence is enforced in the mode used for MANUAL | **PASS** | Driving straight at the fence in STEERING for 60 s: the boat reaches the fence area but never gets more than 10 m outside | FEN-004, V-02 |
| V-03 | GCS failsafe can 'continue in AUTO' | **PASS** | Link cut in AUTO for 20 s: mode stays AUTO and the mission keeps progressing | FS-003, V-03 |
| V-04 | Boat loiters at home at the end of RTL | **PASS** | After arriving home in RTL, with a 4 m/s wind for 60 s, the boat stays within 5 m of home | MOD-005, V-04 |
| V-05 | Crash check can meet FS-005 (stuck detection) | **PASS (known gap not seen)** | Heavy weed drag in AUTO: HOLD within 5 s of the boat being stuck (< 0.1 m/s) | FS-005, V-05, SC-05, FM-16 |
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

### IF-14-01: Status snapshot after connect (PASS)

- `mode`: DISARMED
- `fix`: 6
- `sats`: 10
- `battery_v`: 12.48
- `rail_v`: 12.48

### IF-14-02: Parameter baseline matches the controlled file (PASS)

- `parameters_in_baseline`: 57
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

- `moved_m`: 3.033

### SC-01: Battery drain to 35% then 15% (PASS)

- `battery_pct_at_rtl`: 35
- `distance_home_m`: 2.895
- `texts`: Battery 1 is low 10.89V used 1626 mAh; Battery 1 is critical 10.43V used 2125 mAh
- Note: Reduced speed at 15% is not native (see V-15); it belongs to the mission computer in slice 2.

### SC-02: Link cut in STEERING (KNOWN GAP)

- `hold_after_cut_s`: 3.108
- `native_minimum_s`: FS_GCS_TIMEOUT 2 + FS_TIMEOUT 1
- **Known gap:** Finding: native GCS failsafe floor is FS_GCS_TIMEOUT 2 s + FS_TIMEOUT 1 s = ~3 s; FS-002 asks 2 s.
- Failure: `AssertionError: HOLD after 3.1 s: Rover's GCS failsafe cannot be faster than FS_GCS_TIMEOUT (min 2 s) + FS_TIMEOUT (min 1 s)`

### SC-04: GNSS failure 5 s then restore (KNOWN GAP)

- `motors_off_after_s`: 9.026
- `modes`: [8.0, 'HOLD']
- `texts`: EKF variance; EKF failsafe; EKF failsafe cleared
- **Known gap:** Finding: EKF failsafe stops motors ~9 s after GNSS loss; FS-004 asks 3 s. Needs B6 fix-loss HOLD.
- Failure: `AssertionError: motors still running 3 s after GNSS loss`

### SC-09a: STOP from AUTO: motors off and disarmed (PASS)

- `outputs_neutral_s`: 0.057
- `thrust_below_0_05N_s`: 0.355
- Note: Measured at 5x speed-up, so wall-clock latency in the test harness counts 5 times over; spin-down is the model's 0.1 s motor time constant.

### V-02: Fence is enforced in the mode used for MANUAL (PASS)

- `max_north_m`: 22.478
- `fence_line_north_m`: 25.0
- `worst_outside_m`: 0.0
- `fence_action`: none needed
- `texts`: -
- Note: Rover's fence avoidance (AVOID_*) holds the boat short of the fence line in MANUAL, so the breach action is a second layer.

### V-03: GCS failsafe can 'continue in AUTO' (PASS)

- `modes_during_cut`: AUTO (unchanged)
- `progress_m`: 19.734
- `failsafe_texts`: GCS Failsafe; Failsafe - Continuing Auto Mode

### V-04: Boat loiters at home at the end of RTL (PASS)

- `max_drift_m`: 2.182
- `mode_at_end`: RTL
- Note: ArduPilot stays in RTL and station-keeps for boats; Mission Control must show 'arrived' as HOLD (MOD-005).

### V-05: Crash check can meet FS-005 (stuck detection) (PASS (known gap not seen))

- `stuck_after_weed_s`: 0.032
- `hold_after_stuck_s`: 4.897
- `crash_text`: Crash: Going to HOLD
- **Known gap:** Finding: native crash check resets on any noisy GNSS speed sample; stuck-to-HOLD varies 4.9-20 s. Needs B7 second stuck detector (A-07).
- Failure: `None`

### V-06: Helm counts only Mission Control heartbeats as GCS (PASS)

- `failsafe_after_s`: 2.779

### V-06b: A second system-255 heartbeat masks the GCS failsafe (PASS)

- `failsafe_fired`: False
- Note: Expected: the failsafe does NOT fire, because ArduPilot accepts any system-255 heartbeat. Mitigation is FM-41 / SC-37 in Mission Control (slice 3).

### V-11: GUIDED stops within 3 s if velocity targets stop (KNOWN GAP)

- `speed_before_m_s`: 0.999
- `motors_off_after_s`: 3.905
- Note: Rover 4.7.1 mode_guided.cpp: 3 s timeout, then a decelerating stop (ATC_DECEL_MAX).
- **Known gap:** Finding: GUIDED times out after 3 s then decelerates; motors off ~3.9 s.
- Failure: `assert (53.278333333293 is not None and (53.278333333293 - 49.37333333329655) <= 3.0)`

### V-12: Skid-steer boat frame behaves plausibly (PASS)

- `cross_track_rms_m`: 0.157
- `cross_track_max_m`: 0.341
- `mean_speed_m_s`: 1.008
- `samples`: 296

### V-13: Second voltage input gates arming (key in/out) (PASS)

- `rail_v_key_out`: 1.235
- `refusal`: Arm: Battery 2 below minimum arming voltage
- `armed_with_key_in`: True
- Note: SITL cannot switch its second analogue input off, so key out is emulated by scaling BATT2_VOLT_MULT; the real switch is tested on L2 (L2-13).

### V-14: Native mechanism to stop motors on persistent breach (PASS)

- `outside_after_40s_m`: 42.542
- `motors_running`: True
- `mode`: RTL
- Note: Answer: NO native stop - ArduPilot keeps fighting in RTL. FEN-006 must be met by B7/B-services (slice 2).

### V-15: Reduced speed during RTL on critical battery (PASS)

- `rtl_speed_after_critical_m_s`: 1.0
- `distance_home_m`: 42.163
- `mode`: RTL
- `texts`: Battery 1 is low 10.89V used 1625 mAh; Battery 1 is critical 10.21V used 2125 mAh
- Note: Answer: NO native speed reduction: FS-001's reduced speed at 15% must come from the mission computer (slice 2).

### V-16: GNSS-velocity yaw fallback when the compass disagrees (PASS)

- `sim_mag1_orient`: 2.0
- `worst_outside_m`: 0.0
- `worst_heading_error_deg`: 100.512
- `heading_error_last_20s_deg`: 97.108
- `mission_seq_at_end`: 3
- `mission_total`: 3
- `texts`: -
- `mode_at_end`: AUTO
- Note: Finding: with its only compass rotated, the EKF heading stays wrong (no GSF yaw reset, no message), yet the boat still tracks its mission on GNSS course. Heading-dependent outputs (photo tags, map arrow) would be wrong; B7's heading-vs-course check (A-03, SC-38) is what catches it.

### V-17: Does the helm refuse fence changes while armed? (PASS)

- `ardupilot_native`: accepted
- Note: FEN-007 is enforced by C7 (NotAllowedWhileArmed) whatever ArduPilot does.
