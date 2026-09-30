# Simulator findings (slices 1 to 3)

What flying the real ArduPilot Rover 4.7.1 firmware on the Boaty boat model
showed about the design:

- **Slice 1:** the autopilot on its own.
- **Slice 2:** the boat services B2-B7 on the simulated Pi Zero.
- **Slice 3:** Mission Control (C1-C10) on the bank, driving the whole
  system from a typed instruction to the captain's log.

Evidence for each item is in `SITL_REPORT.md`. These findings feed ADD Issue F, ICD Issue E, SSS-HLM Issue D, SSS-MCP Issue C and SRS Issue F.

## Owner decisions

- **CR-05 (FS-002 relaxed to 3 s):** HOLD within 3 s of losing the link in MANUAL, which is the native minimum (FS_GCS_TIMEOUT 2 s + FS_TIMEOUT 1 s). Measured 3.04 s (SC-02a). B4 still commands RTL at 10 s (SC-02b).

## Slice 3 results

- **The whole trip works end to end (MC-E2E).** "Explore the bay and take
  photos of the island, then come home": the Claude reply (a stand-in; see
  below) is planned and validated, uploaded, read back with an equal
  checksum, and flown. The boat stops at the photo point for 3 photos plus
  27 interval photos, comes home, and disarms itself 61 s after arriving
  (MCN-D12). All 30 photos are synced, sha256-checked and only then
  acknowledged, and the captain's log is written. The boat stayed at least
  8.8 m inside the fence and 5.3 m from every no-go zone.
- **STOP (SC-09):** in ARMED, MISSION, RETURNING and MANUAL, the button
  handler reaches helm.stop() in under 1 ms (MCN-D10 allows 50 ms), and
  the outputs are neutral within 0.32 s (FS-009 allows 1 s).
- **Parameter baseline (SC-24):** one changed failsafe parameter blocks
  arming, and the difference is shown by name; restoring it clears the
  block.
- **Fence missing (SC-25) and read-back corruption (SC-32):** the read-back
  comparison refuses approval, so GO stays disabled. Even with the session
  forced into ARMED, C7 refuses GO because the boat's copy was never
  verified.
- **Site file (SC-26):** swapped [lat, lon] and a site 5 km from its
  configured place are both refused by the linter and at pre-arm. The good
  file's fence round-trips through the helm exactly.
- **Home sanity (SC-35):** a boat 30 m from the site's home cannot get a
  plan approved (VAL-004).
- **Foreign ground station (SC-37):** detected 0.7-0.9 s after it appears
  (two runs). GO and arming are refused, an alarm is shown and spoken, and
  STOP still works. It clears 2-3 s after the other source goes (V-06b
  mitigated).
- **Persistent breach with B7 absent (MCN-D59):** a gale pushed the boat
  out of the fence; C1 stopped the motors 10.8-11.2 s later, when it was
  10.2-10.3 m outside, and they stayed off.
- **Boat stops itself (MCN-D60):** with a dead motor, each weed-shedding
  episode is announced once. The final stop is spoken 0.2 s after the
  helm's HOLD, with the reason on the adult's screen. In the last run that
  reason was B5's new "repeatedly stuck" cap (see SC-06 below). Resume is
  refused without the PIN and accepted with it.
- **Validator (VAL-006, MCN-D40, SC-31):**
  - 91 adversarial cases pass, with 100 % branch coverage.
  - Of 400 generated missions, 112 were accepted. An independent geometry
    check found that none of them crosses a boundary; the closest came to
    within 2.999 m.

## New findings in slice 3

- **A validator denial of service (fixed).** A waypoint at 0 N 0 E makes a
  5,800 km leg. Sampling it every metre took 56 s. The validator now checks
  a leg's endpoints against the fence first and only samples legs whose
  ends are inside, so every leg is at most about 200 m. MCN-D39 should say
  so.
- **Parameter download loses values on a busy link (fixed; IF-02/IF-14).**
  With the boat services' traffic on the link, a different handful of the
  1,273 PARAM_VALUE messages went missing on each run. The baseline check
  then saw phantom differences and blocked arming. read_params() now
  re-requests missing indices one by one, as QGroundControl does.
- **The final RTL item runs in AUTO (IF-13 note).** ArduPilot flies a
  mission's NAV_RETURN_TO_LAUNCH item without changing mode, so "the boat
  is coming home" cannot be read from the mode. C1 follows the mission item
  sequence instead. RTL *mode* during a mission now always means a failsafe
  or an adult command.
- **The IF-13 checksum can't be compared with the helm as written.** It
  covers photo counts and item numbers, which the helm does not store. The
  photo counts go to the camera service (IF-03 Session). VAL-010 now
  compares a checksum of what the helm holds: kind, position, hold time
  and speed. The ICD should define that "helm view" as the read-back form.
- **IF-14 needs "motors off, stay armed".** hold() is LOITER (station-
  keeping) and stop() disarms. FEN-006 and MCN-D59 need HOLD with the boat
  still armed, so an adult can bring it back. halt() was added; the ICD
  should add it.
- **Boat-service stops: the reason comes after the mode change.** B5
  switches the helm to HOLD before its "STILL STUCK" text arrives. C1 takes
  the reason from the event text. It also declares a HOLD it can't explain
  after 1 s, so a stop is never silent.
- **Foreign ground station policy (MCN-D57 wording).** "Refuses to command
  the helm" would include STOP. C7 refuses what starts or continues motion
  (arm, GO, upload, manual, drive), but always allows STOP, HOLD and come
  home. Our own heartbeats never come back through the router, so any
  system-255 heartbeat that arrives is foreign.
- **ArduPilot moves home to wherever the boat is armed.** After a
  mid-lake STOP, re-arming out there would make the lake the new home.
  VAL-004 refuses to plan in that case ("launch from the jetty"), which is
  what OPS wants. The checklist should say it too.
- **Planner limits are real.** Exploring the whole pond at medium or
  thorough coverage exceeds 20 min. The planner refuses, and the retry
  asks Claude for something shorter. The 1.2 x estimate was conservative:
  planned 249 s, and the RTL item began at 167 s.
- **"Duck patrol" spreads its photo stops over the whole pond**, not just
  the chosen area (photo_stops with near = null). This is safe and
  validated, but it may not be what the owner expects. It is a candidate
  template change.
- **Claude API contract (IF-11 updates):**
  - Model: the ICD names `claude-opus-5`. The code uses `claude-opus-5-5`,
    the current model.
  - Structured outputs can't carry numeric ranges or string lengths. The
    schema therefore puts them in descriptions, and pydantic re-checks
    them.
  - Retries: the ICD's "retry once" and MCN-D29's "at most 2" are both met
    by one retry, with the problem passed back as data.
  - Refusals: the request opts into server-side fallbacks
    (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). A
    refusal that survives the fallback offers the templates.

## Live Claude evaluation (IF-11, SC-33)

- 39 instructions (41 after the trip-length fix below) were run against
  the live API (`claude-opus-5-5`),
  each through the real planning flow: Claude, then the planner, then the
  validator. Details are in `NLI_EVAL.md`.
  - **All 39 passed.** Every reply was schema-valid, and no retries or
    refusals were needed.
  - **All 14 must-declines were declined.** These covered chasing ducks
    and geese, other lakes, leaving the fence, racing, and injected fake
    "system" and tag text. Each was declined in child-friendly words with
    a real alternative ("...but we can sail over to the island").
  - **The 5 other adversarial cases were safe.** A raw-coordinate JSON
    request was declined. "Twenty times, a hundred photos" was clamped to
    the schema limits: three stops, 38 photos.
- **Time to a validated plan:** median 4.0 s, 95th percentile 8.0 s,
  maximum 12.0 s. These were measured from a cloud host, not a phone on
  4G, so NLI-007's 20 s on 4G still needs a lake-side check.
- **Cost:** $0.23 for the run, about 0.6 p per plan. The system prompt is
  cached (1,938 tokens), so later requests read it at the cache rate.
- **Fixed: the model couldn't judge trip length.**
  - **Symptom:** "Just a short trip please, he's getting tired" gave a
    10.4-minute plan, longer than the 8-minute "adventure". The site
    context had names, sizes and directions, but nothing about time.
  - **Fix (prompt `intent-1.1`):** the planner now works out
    `trip_minutes` for each area (explore light/medium/thorough, lap) and
    each landmark visit, as a whole trip from home and back, and adds it
    to the context. The prompt says a short, quick or tired-child trip
    should be about 5 minutes.
  - **Check:** three short-trip phrasings, each with a 5.5-minute limit,
    gave 4.2, 4.2 and 1.6 minutes.
  - **Full rerun: 41 of 41** (the 39 cases plus two new short-trip ones).
    All 14 must-declines were declined; 95th percentile 6.9 s; $0.31.
  - **Side effect:** the model now plans landmark visits more often. For
    "Look for ducks" and "Take lots of pictures" it visits landmarks to
    take photos, which is reasonable, so those two cases now accept
    "visit" as well.

## SC-06 intermittency: root cause found and fixed

- **Symptom:** "Weed clears during burst 2" failed now and then in the
  full suite. B5 did its bursts and then reported "still stuck" with the
  weed gone.
- **Diagnosis:** a log of each post-resume watch (resume ACK, peak
  speed, time, why it ended) showed the problem. B5's "free" test used
  ground-speed *magnitude*. The astern burst leaves the boat drifting
  backwards at up to 0.4 m/s, and that drift counted as moving. So the
  outcome depended on how much drift was left when B5 sampled.
- **What made it worse:** lowering the threshold let a boat with a dead
  motor be "freed" 10 times in a row without ever stopping (MCN-D60).
- **Fix (MCP-D34, FMEA FM-58 / A-29):**
  - "Free" now means *forward* speed, along the heading, above 0.2 m/s
    held for 1 s within 8 s. A freed boat reached 0.72-0.76 m/s forward
    2.5-3 s after resuming; a stuck one peaked at 0.04 m/s.
  - More than 3 episodes in 2 minutes stops the boat with a "repeatedly
    stuck" alarm.
  - A GUIDED switch that fails is retried once, then reported as "no
    control", not as "still stuck".
- **Test fix:** the test also released the weed at the *end* of burst 2,
  not during it. It now releases half-way through.

## Not yet verified (needs hardware or more build)

- **Not built yet in slice 3:**
  - speech engines (C4 has the interfaces, stand-ins and an espeak
    fallback)
  - map tiles and the fence editor (MCN-D19)
  - helm log download and replay (MCN-D51)
  - the waterfowl finder (MCN-D48)
  - home-network sync (MCN-D52)
  - RSSI and latency logging (MCN-D21, D46)
  - QGroundControl takeover (MCN-D24)
- **Hardware only:** the GPIO panel code (MCN-D02, D09) needs the Pi 5.

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
