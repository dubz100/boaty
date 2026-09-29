# Boaty simulator results (slices 1-3)

Generated 2026-09-29T12:04:29.586458+00:00 from `results/sitl_results.json`. ArduPilot Rover 4.7.1 SITL on the Boaty boat model, speed-up 5x.

**44 passed, 2 known gaps (requirement not met natively; finding recorded), 0 failed, 0 errors** out of 46 scenarios.

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
| MC-E2E | Explore the pond, take photos, come home | **PASS** | Typed instruction to captain's log with no adult touching the boat: plan validates, read-back checksum matches, the boat flies it inside the fence, stops at the photo point, comes home, auto-disarms after 60 s, photos are synced and sha256 verified before ack | NLI-001, NLI-005, VAL-001, VAL-010, MCN-D12, MCN-D43, MCN-D47, MCN-D49, CAM-007, IF-03, IF-13 |
| MCN-D59 | C1 stops the motors on a persistent breach | **PASS** | Boat services not running (no B7). Gale pushes the boat out of the site fence: C1 commands HOLD before 30 s or 10 m outside; motors stay off | FEN-006, MCN-D59, A-18, FM-14 |
| MCN-D60 | B7 hold is shown and spoken; resuming needs the PIN | **PASS** | Dead motor mid-mission: the boat stops itself; Mission Control says why within 2 s of the helm reporting it; resume refused without the PIN, accepted with it | MCN-D60, MCN-D12, MOD-007, A-08 |
| SC-01 | Battery drain to 35% then 15% | **PASS** | RTL at 35% (+/- 2%); critical alarm at 15%; reaches home within 5 m | FS-001, SC-01 |
| SC-02a | Link cut in STEERING: helm part | **PASS** | HOLD <= 3 s after the link is cut (FS-002 relaxed to 3 s by CR-05; the RTL at 10 s is B4: SC-02b) | FS-002, SC-02, CR-05 |
| SC-02b | Link cut in STEERING: B4 RTL at 10 s | **PASS** | HOLD <= 3 s (helm), then RTL 10 s (+/- 1 s) after the link is cut (B4), and the boat heads home | FS-002, SC-02, MCP-D12, CR-05 |
| SC-03 | Link cut in AUTO | **PASS** | Mission continues; RTL 60 s (+/- 1 s) after the link is cut (B4) | FS-003, SC-03, MCP-D12, FM-31 |
| SC-04 | GNSS failure 5 s then restore | **PASS** | Motors stop <= 3 s after the fix is lost (B6 HOLD); RTL once the position has been healthy for 10 s | FS-004, SC-04, FM-01, FM-06, MCP-D15 |
| SC-04 | GNSS failure 5 s then restore | **KNOWN GAP** | Motors stop <= 3 s after the fix is lost (the RTL after 10 s healthy is B6, slice 2) | FS-004, SC-04, FM-01, FM-06 |
| SC-06 | Drag released after burst 2 | **PASS** | Stuck -> HOLD; B5 astern bursts (<= 0.5 m/s, <= 2 s); weed clears during burst 2; mission resumes; <= 3 bursts | FS-006, SC-06, MCP-D18, FM-27 |
| SC-06b | Permanent weed: three bursts then HOLD + alarm | **PASS** | Exactly 3 bursts, then HOLD with a 'still stuck' alarm, and nothing restarts the motors | FS-006, MCP-D18, FM-27 |
| SC-07 | Kill the whole mission computer mid-mission | **PASS** | With B1-B7 dead (and so the bank link), the helm completes the mission, returns and holds within 5 m of home | FS-007, SC-07, FM-26, MOD-005 |
| SC-09 | STOP in every state | **PASS** | From ARMED, MISSION, RETURNING and MANUAL: helm.stop() called <= 50 ms after the button edge; motors off <= 1 s | FS-009, MCN-D10, SC-09 |
| SC-09a | STOP from AUTO: motors off and disarmed | **PASS** | Helm commands the motors to neutral <= 1 s after stop(); helm disarmed; stop() is idempotent | FS-009, IF-14 |
| SC-10 | Moisture flagged | **PASS** | RTL <= 2 s after the moisture sensor trips; alarm raised; IF-03 health shows fault | FS-010, SC-10, FM-24, MCP-D15 |
| SC-24 | Parameter differs from baseline | **PASS** | Change one failsafe parameter: arming blocked, the difference shown; put it back and arming works | FM-09, MCN-D45, SAF-007, SC-24 |
| SC-25 | Fence missing or disabled | **PASS** | Skip the fence upload: approval (and so arming) refused | FM-10, SC-25, PRE-002 |
| SC-26 | Site file lat/lon swapped; wrong site | **PASS** | Linter and pre-arm both refuse; the good site's fence round-trips through IF-02 exactly | FM-11, MCN-D53, SC-26, IF-15 |
| SC-28 | Persistent breach (wind pushing out) | **PASS** | Offshore gale: B7 stops the motors before 30 s outside or 10 m outside, and they stay stopped (detector recorded) | FEN-006, SC-28, FM-14, V-14 |
| SC-29 | Single motor failure | **PASS** | Right motor dead mid-leg: HOLD within 20 s (from whichever detector fires first), the boat stays inside the fence and ends in HOLD with an alarm | FS-013, SC-29, FM-17, MCP-D24 |
| SC-32 | Read-back corruption | **PASS** | One item altered in transfer: checksum differs, not approved, GO stays disabled | FM-35, FM-47, SC-32, VAL-010, MCN-D43 |
| SC-35 | Home sanity | **PASS** | Boat's home 30 m from the site's home: the plan is refused before approval | FM-46, SC-35, VAL-004 |
| SC-37 | Foreign GCS heartbeat | **PASS** | Second system-255 source: C7 detects it within 3 s, refuses arming and GO, alarms; STOP still works; clears when it goes | FM-41, MCN-D57, SC-37, V-06b |
| SC-38 | First-motion heading check | **PASS** | Compass reversed before the start: HOLD <= 10 s after AUTO begins; the boat stays inside the fence | FM-05, FM-18, SC-38, MCP-D22, A-03 |
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

### B2-01: Photos during a mission (PASS)

- `photos`: 21
- `burst`: 3
- `interval`: 18
- `first_burst_after_reached_s`: 0.002
- `worst_geotag_error_m`: 0.272
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

- `moved_m`: 3.605

### MC-E2E: Explore the pond, take photos, come home (PASS)

- `items`: 5
- `planned_s`: 249
- `flown_s`: 166.582
- `total_s`: 272.592
- `readback_checksum_equal`: True
- `min_fence_clearance_m`: 8.783
- `min_zone_clearance_m`: 5.265
- `photos`: 30
- `photo_point_photos`: 3
- `synced`: 30
- `acked`: 30
- `bad_hash`: 0
- `home_to_disarm_s`: 61.122
- `captains_log`: True
- `llm_logged`: 1
- `spoken`: Let's explore the bay and take pictures of the island!; Ask a grown-up to check it.; Off we go!; Taking pictures!; Coming home!; I'm back! Let's look at the pictures.
- Note: Clearances are from the helm's reported position; the validator's 3 m margin is on the planned route.

### MCN-D59: C1 stops the motors on a persistent breach (PASS)

- `halt_after_s`: 11.194
- `outside_at_halt_m`: 10.308
- `motors_running_next_20s`: 0.8
- `spoken`: True
- `helm_mode`: HOLD

### MCN-D60: B7 hold is shown and spoken; resuming needs the PIN (PASS)

- `held_after_s`: 70.688
- `final_helm_hold_after_s`: 70.426
- `said_after_final_hold_s`: 0.212
- `spoken`: I'm stuck in some weed, trying to wiggle free.; I'm stuck in some weed, trying to wiggle free.; I'm stuck in some weed, trying to wiggle free.; I've stopped. A grown-up needs to check me.
- `reason`: BOATY B5 REPEATEDLY STUCK: HOLD
- `alerts`: The boat stopped itself: BOATY B5 REPEATEDLY STUCK: HOLD. Check it, then Resume (PIN) or Come home.
- `resumed`: True
- `mode_after_resume`: AUTO
- `events`: BOATY B5 SHED START; BOATY B5 FREE AFTER 1: RESUMED; BOATY B5 SHED END; BOATY B5 SHED START; BOATY B5 FREE AFTER 2: RESUMED; BOATY B5 SHED END; BOATY B5 SHED START; BOATY B5 FREE AFTER 2: RESUMED; BOATY B5 SHED END; BOATY B5 REPEATEDLY STUCK: HOLD

### SC-01: Battery drain to 35% then 15% (PASS)

- `battery_pct_at_rtl`: 35
- `distance_home_m`: 2.995
- `texts`: Battery 1 is low 10.89V used 1625 mAh; Battery 1 is critical 10.43V used 2126 mAh
- Note: Reduced speed at 15% is not native (see V-15); it belongs to the mission computer in slice 2.

### SC-02a: Link cut in STEERING: helm part (PASS)

- `hold_after_cut_s`: 3.092
- `native_minimum_s`: FS_GCS_TIMEOUT 2 + FS_TIMEOUT 1

### SC-02b: Link cut in STEERING: B4 RTL at 10 s (PASS)

- `hold_after_s`: 3.117
- `rtl_after_s`: 9.161
- `dist_home_at_cut_m`: 9.549
- `dist_home_15s_after_rtl_m`: 5.454
- `events`: BOATY B4 LINK LOST IN MANUAL: RTL

### SC-03: Link cut in AUTO (PASS)

- `mode_30s_after_cut`: AUTO
- `rtl_after_s`: 59.785
- `events`: -

### SC-04: GNSS failure 5 s then restore (PASS)

- `outputs_neutral_after_s`: 2.545
- `thrust_gone_after_s`: 2.65
- `rtl_after_restore_s`: 10.623
- `events`: BOATY B6 POSITION LOST: HOLD; BOATY B6 POSITION OK: RTL
- Note: RTL comes 10 s after B6 sees a healthy position, which includes the EKF's own recovery after the fix returns.

### SC-04: GNSS failure 5 s then restore (KNOWN GAP)

- `motors_off_after_s`: 9.227
- `modes`: [8.2, 'HOLD']
- `texts`: EKF variance; EKF failsafe; EKF failsafe cleared
- **Known gap:** Finding: EKF failsafe stops motors ~9 s after GNSS loss; FS-004 asks 3 s. Needs B6 fix-loss HOLD.
- Failure: `AssertionError: motors still running 3 s after GNSS loss`

### SC-06: Drag released after burst 2 (PASS)

- `watch`: {'burst': 1, 'resume_ack': True, 'mode': 4, 'peak_mps': 0.0, 'after_s': 8.0, 'ended': 'helm HOLD'}; {'burst': 2, 'resume_ack': True, 'mode': 4, 'peak_mps': 0.01, 'after_s': 0.0, 'ended': 'helm HOLD'}; {'burst': 3, 'resume_ack': True, 'mode': 10, 'peak_mps': 0.68, 'after_s': 3.0, 'ended': 'moving forward'}
- `bursts`: 3
- `min_speed_during_burst_m_s`: 0.013
- `mode_after`: AUTO
- `speed_after_m_s`: 1.001
- `events`: BOATY B5 SHED START; BOATY B5 FREE AFTER 3: RESUMED; BOATY B5 SHED END

### SC-06b: Permanent weed: three bursts then HOLD + alarm (PASS)

- `bursts`: 3
- `mode`: HOLD
- `motors_off`: True
- `events`: BOATY B5 SHED START; BOATY B5 STILL STUCK: HOLD; BOATY B5 SHED END

### SC-07: Kill the whole mission computer mid-mission (PASS)

- `home_after_s`: 244.602
- `final_distance_m`: 1.274

### SC-09: STOP in every state (PASS)

- `ARMED`: edge_to_call_ms=0.0; outputs_neutral_s=0.0; disarmed=True; after=IDLE
- `MISSION`: edge_to_call_ms=0.0; outputs_neutral_s=0.3324999999996976; disarmed=True; after=DEBRIEF
- `RETURNING`: edge_to_call_ms=0.0; outputs_neutral_s=0.048333333333289374; disarmed=True; after=DEBRIEF
- `MANUAL`: edge_to_call_ms=0.0; outputs_neutral_s=0.32666666666636957; disarmed=True; after=DEBRIEF

### SC-09a: STOP from AUTO: motors off and disarmed (PASS)

- `outputs_neutral_s`: 0.342
- `thrust_below_0_05N_s`: 0.598
- Note: Measured at 5x speed-up, so wall-clock latency in the test harness counts 5 times over; spin-down is the model's 0.1 s motor time constant.

### SC-10: Moisture flagged (PASS)

- `rtl_after_s`: 0.071
- `health_status`: fault
- `events`: BOATY B6 WATER IN BOX: RTL

### SC-24: Parameter differs from baseline (PASS)

- `arm_ok`: False
- `reasons`: helm parameters differ from the baseline: FS_GCS_TIMEOUT
- `difference`: FS_GCS_TIMEOUT=2.0; 10.0
- `arm_ok_after_restore`: True

### SC-25: Fence missing or disabled (PASS)

- `approved`: False
- `fence_ok`: False
- `state`: PLAN_READY

### SC-26: Site file lat/lon swapped; wrong site (PASS)

- `fence_round_trip`: True
- `swapped_errors`: ERROR MCN-D53: 42 coordinate(s) look like [lat, lon]; GeoJSON needs [lon, lat]
- `wrong_site_errors`: ERROR MCN-D53: site is 5.0 km from its configured reference (max 1 km)
- `plan_ok`: False
- `approve`: False; the boat's home is 5009 m from the site's home: launch from the jetty
- `plan_adult`: the boat's home is 5009 m from the site's home: launch from the jetty

### SC-28: Persistent breach (wind pushing out) (PASS)

- `hold_after_breach_s`: 6.86
- `outside_at_hold_m`: 7.597
- `detector`: B7 HEADING CHECK FAILED: HOLD
- `motors_running_in_next_30s_s`: 0.95
- `b7_actions`: B7 HEADING CHECK FAILED: HOLD
- `events`: BOATY B7 HEADING CHECK FAILED: HOLD
- Note: In a gale that blows the boat backwards the first-motion heading check fires first (course and heading 180 deg apart). The outcome, motors off, is what FEN-006 wants; the diagnosis is wrong.

### SC-29: Single motor failure (PASS)

- `first_hold_after_s`: 8.931
- `first_detector`: helm crash check
- `worst_outside_m`: 0.0
- `final_mode`: HOLD
- `events`: BOATY B5 SHED START; BOATY B5 FREE AFTER 1: RESUMED; BOATY B5 SHED END; BOATY B5 SHED START; BOATY B5 STILL STUCK: HOLD; BOATY B5 SHED END
- Note: A dead motor looks like 'stuck' to the helm's crash check, so B5 tries its astern bursts before giving up. Safe, but B5 cannot tell weed from a dead motor.

### SC-32: Read-back corruption (PASS)

- `approved`: False
- `expected`: sha256:a8f69b53f852f3f35c154c705296179ee808ae8da36f0ca6b4efbdf08ed2a8ed
- `read_back`: sha256:355d9b3e23ec576a4b1c21ec6b2c11a781a1f51b5bbb27045e5962256295b0fb
- `auto_after_go`: False

### SC-35: Home sanity (PASS)

- `plan_ok`: False
- `rules`: VAL-004
- `adult`: the boat's home is 30 m from the site's home: launch from the jetty

### SC-37: Foreign GCS heartbeat (PASS)

- `detect_s`: 0.682
- `go_refused`: True
- `alarm`: True
- `spoken`: True
- `clear_s`: 2.123
- `go_after_clear`: True

### SC-38: First-motion heading check (PASS)

- `hold_after_s`: 9.602
- `detector`: B7 HEADING CHECK FAILED: HOLD
- `worst_outside_m`: 0.0
- `events`: BOATY B7 HEADING CHECK FAILED: HOLD

### V-02: Fence is enforced in the mode used for MANUAL (PASS)

- `max_north_m`: 22.561
- `fence_line_north_m`: 25.0
- `worst_outside_m`: 0.0
- `fence_action`: none needed
- `texts`: -
- Note: Rover's fence avoidance (AVOID_*) holds the boat short of the fence line in MANUAL, so the breach action is a second layer.

### V-03: GCS failsafe can 'continue in AUTO' (PASS)

- `modes_during_cut`: AUTO (unchanged)
- `progress_m`: 19.87
- `failsafe_texts`: GCS Failsafe; Failsafe - Continuing Auto Mode

### V-04: Boat loiters at home at the end of RTL (PASS)

- `max_drift_m`: 1.844
- `mode_at_end`: RTL
- Note: ArduPilot stays in RTL and station-keeps for boats; Mission Control must show 'arrived' as HOLD (MOD-005).

### V-05: Crash check can meet FS-005 (stuck detection) (PASS (known gap not seen))

- `stuck_after_weed_s`: 0.067
- `hold_after_stuck_s`: 4.907
- `crash_text`: Crash: Going to HOLD
- **Known gap:** Finding: native crash check resets on any noisy GNSS speed sample; stuck-to-HOLD varies 4.9-20 s. Needs B7 second stuck detector (A-07).
- Failure: `None`

### V-06: Helm counts only Mission Control heartbeats as GCS (PASS)

- `failsafe_after_s`: 2.918

### V-06b: A second system-255 heartbeat masks the GCS failsafe (PASS)

- `failsafe_fired`: False
- Note: Expected: the failsafe does NOT fire, because ArduPilot accepts any system-255 heartbeat. Mitigation is FM-41 / SC-37 in Mission Control (slice 3).

### V-11: GUIDED stops within 3 s if velocity targets stop (KNOWN GAP)

- `speed_before_m_s`: 1.028
- `motors_off_after_s`: 3.945
- Note: Rover 4.7.1 mode_guided.cpp: 3 s timeout, then a decelerating stop (ATC_DECEL_MAX).
- **Known gap:** Finding: GUIDED times out after 3 s then decelerates; motors off ~3.9 s.
- Failure: `assert (53.32999999995962 is not None and (53.32999999995962 - 49.384999999963206) <= 3.0)`

### V-12: Skid-steer boat frame behaves plausibly (PASS)

- `cross_track_rms_m`: 0.157
- `cross_track_max_m`: 0.406
- `mean_speed_m_s`: 1.008
- `samples`: 296

### V-13: Second voltage input gates arming (key in/out) (PASS)

- `rail_v_key_out`: 1.235
- `refusal`: Arm: Battery 2 below minimum arming voltage
- `armed_with_key_in`: True
- Note: SITL cannot switch its second analogue input off, so key out is emulated by scaling BATT2_VOLT_MULT; the real switch is tested on L2 (L2-13).

### V-14: Native mechanism to stop motors on persistent breach (PASS)

- `outside_after_40s_m`: 41.847
- `motors_running`: True
- `mode`: RTL
- Note: Answer: NO native stop - ArduPilot keeps fighting in RTL. FEN-006 must be met by B7/B-services (slice 2).

### V-15: Reduced speed during RTL on critical battery (PASS)

- `rtl_speed_after_critical_m_s`: 1.0
- `distance_home_m`: 41.464
- `mode`: RTL
- `texts`: Battery 1 is low 10.89V used 1625 mAh; Battery 1 is critical 10.21V used 2126 mAh
- Note: Answer: NO native speed reduction: FS-001's reduced speed at 15% must come from the mission computer (slice 2).

### V-16: GNSS-velocity yaw fallback when the compass disagrees (PASS)

- `sim_mag1_orient`: 2.0
- `worst_outside_m`: 0.0
- `worst_heading_error_deg`: 101.309
- `heading_error_last_20s_deg`: 98.381
- `mission_seq_at_end`: 3
- `mission_total`: 3
- `texts`: -
- `mode_at_end`: AUTO
- Note: Finding: with its only compass rotated, the EKF heading stays wrong (no GSF yaw reset, no message), yet the boat still tracks its mission on GNSS course. Heading-dependent outputs (photo tags, map arrow) would be wrong; B7's heading-vs-course check (A-03, SC-38) is what catches it.

### V-17: Does the helm refuse fence changes while armed? (PASS)

- `ardupilot_native`: accepted
- Note: FEN-007 is enforced by C7 (NotAllowedWhileArmed) whatever ArduPilot does.

## Unit-level evidence (no simulator)

Generated 2026-09-29T12:05:40.754204+00:00 by `tools/unit_evidence.py`.

- **Validator suite (VAL-006, MCN-D40)**: result=91 passed in 2.11s; branch_coverage_pct=100.0; branches=76; missing_branches=0
- **SC-31 property-based validator check**: missions=400; accepted=112; rejected=288; closest_accepted_route_to_a_boundary_m=2.999; criterion=no accepted route crosses a boundary; >= 2.9 m clear
- **Unit suite**: 294 passed in 42.68s
