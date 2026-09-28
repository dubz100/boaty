# Boaty software

The Python code for Boaty Mk1: the helm interface Mission Control uses, the
simulator that flies the real ArduPilot firmware on a model of our boat, and
the tests that check the system against its requirements.

Slice 1 of 4 (see the simulator plan): autopilot in the loop.

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
params/
  boaty-mk1.parm            vehicle behaviour: loaded on the boat AND in SITL
  boaty-mk1-speedybee.parm  board wiring (hardware only, CR-04)
  sitl.parm                 simulator-only settings
tests/unit/           fast tests of the boat model and bridge (no SITL)
tests/sitl/           scenarios flown on ArduPilot SITL
tools/sitl_report.py  results/sitl_results.json -> results/SITL_REPORT.md
```

## Setup

Python 3.11+, then `pip install pymavlink pytest`.

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
BOATY_SIM_SPEEDUP=5 python3 -m pytest tests/sitl   # ~15 min, needs SITL
python3 tools/sitl_report.py                  # write results/SITL_REPORT.md
```

SITL tests skip themselves if the `ardurover` binary isn't found.
`BOATY_SIM_SPEEDUP` runs the simulation faster than real time. All test
timings are measured in simulated time, so results don't depend on it.
