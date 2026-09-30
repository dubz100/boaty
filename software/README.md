# Boaty software

The Python code for Boaty Mk1: the helm interface Mission Control uses, the
simulator that flies the real ArduPilot firmware on a model of our boat, and
the tests that check the system against its requirements.

Slices 1 to 3 of 4: autopilot in the loop, the boat services on the
simulated Pi Zero, and Mission Control (the Pi 5 on the bank).

```
boaty/
  helm/api.py         IF-14 Helm protocol, data types, events, errors
  helm/ardupilot.py   ArduPilotHelm: IF-14 over MAVLink 2 (IF-02), pymavlink
  helm/params.py      read and compare .parm files (SAF-007 baseline)
  sim/boat.py         3-DOF boat + battery model (KCL section 8 parameters)
  sim/bridge.py       ArduPilot SITL JSON physics bridge (IF-21, DD-19)
  sim/link.py         simulated radio link: cut, loss, latency (IF-01)
  sim/sitl.py         start/stop physics + SITL + link as one "boat"
  sim/companion.py    listener on the companion port (IF-04) for tests
  sim/router.py       stand-in for B1 (mavlink-router) in simulation
  mcp/policy.py       IF-04 command filter, default-deny (MCP-D19)
  mcp/client.py       the filtered MAVLink client every service uses
  mcp/view.py         the services' view of the helm (telemetry)
  mcp/services.py     B4 link watchdog, B5 weed-shedding, B6 health,
                      B7 navigation monitor, and the host that runs them
  mcp/camera.py       B2 camera, photo store, EXIF geotags, thumbnails
  mcp/photo_api.py    B3 photo and health HTTP API (IF-03)
  mcp/sensors.py      moisture and DS18B20 (Pi) or settable stand-ins (sim)
  mcp/clock.py        system clock on the Pi, physics clock in simulation
  mcn/models.py       IF-13 Intent, Mission, ValidationResult (pydantic),
                      canonical checksum, Mission -> helm items
  mcn/geo.py          local metres geometry (pure)
  mcn/site.py         C9 site file (IF-15) and linter (MCN-D53)
  mcn/validator.py    C6 validator (VAL-001..007): pure, deterministic
  mcn/planner.py      C5 geometry: lanes, photo stops, laps, detours,
                      estimates, templates
  mcn/llm.py          IF-11 Claude API client (structured output, fallbacks)
  mcn/planning.py     instruction -> Claude -> planner -> validator, retry,
                      templates
  mcn/helm_guard.py   C7: ValidatedMission-only upload, read-back checksum,
                      parameter baseline, foreign-GCS lockout
  mcn/session.py      C1 session state machine, buttons, checklist, alarms
  mcn/panel.py        C2 panel: GPIO on the Pi, emulation in simulation
  mcn/pin.py          adult PIN (hash only, 10 min unlock, lockout)
  mcn/voice.py        C4 phrase set, speaker and microphone interfaces
  mcn/photos.py       C8 photo sync (sha256 before ack), captain's log
  mcn/web.py          C3 web UI on port 8000, WebSocket push
  mcn/log.py          C10 JSON-lines session log
  mcn/app.py          run it: python -m boaty.mcn.app --sim
params/
  boaty-mk1.parm            vehicle behaviour: loaded on the boat AND in SITL
  boaty-mk1-speedybee.parm  board wiring (hardware only, CR-04)
  sitl.parm                 simulator-only settings
  boat-services.json        B4-B7 thresholds (MCP-D27), controlled like params
sites/                site files (IF-15); tools/make_site.py draws Milton's
tests/unit/           fast tests (no SITL): model, services, validator
                      (91 adversarial cases + property test), planner,
                      Claude client, session, web UI
tests/sitl/           scenarios flown on ArduPilot SITL
tests/data/nli_eval.json  41-instruction evaluation set for the Claude API
tools/sitl_report.py  results/sitl_results.json -> results/SITL_REPORT.md
tools/unit_evidence.py    validator coverage and property-test evidence
tools/nli_eval.py     run the evaluation set against the live Claude API
                      (results/NLI_EVAL.md)
```

## Setup

Python 3.11+, then `pip install -e ".[test]"` (pymavlink, Pillow,
anthropic, pydantic; pytest, hypothesis, coverage).

Build ArduPilot Rover SITL once (about 5 minutes on 4 cores). This is the
same firmware release the helm will run:

```sh
git clone --depth 1 --branch Rover-4.7.1 https://github.com/ArduPilot/ardupilot.git
cd ardupilot && git submodule update --init --recursive --depth 1
pip install pexpect future "empy==3.3.4"
./waf configure --board sitl && ./waf rover
export ARDUPILOT_HOME=$PWD
```

## Run

```sh
cd software
python3 -m pytest tests/unit                  # seconds, no SITL needed
BOATY_SIM_SPEEDUP=5 python3 -m pytest tests/sitl   # ~25 min, needs SITL
PYTHONPATH=. python3 tools/unit_evidence.py   # coverage + property test
python3 tools/sitl_report.py                  # write results/SITL_REPORT.md
```

To try Mission Control in a browser against the simulator:

```sh
PYTHONPATH=. python -m boaty.mcn.app --sim --speedup 2
# open http://localhost:8000 ; the session PIN is printed once
```

For natural-language planning, put an Anthropic API key in
`~/.config/boaty/anthropic_api_key` with mode 0600 (never in the
repository, MCN-D33). Without it, Mission Control offers the templates.
The request uses `claude-opus-5-5` with structured outputs and the
server-side refusal fallback (`fallbacks: "default"`). Then
`PYTHONPATH=. python tools/nli_eval.py` runs the 41-case evaluation (last run: 41/41, p95 7 s, $0.31).

SITL tests skip themselves if the `ardurover` binary isn't found.
`BOATY_SIM_SPEEDUP` runs the simulation faster than real time. All test
timings are measured in simulated time, so results don't depend on it.
