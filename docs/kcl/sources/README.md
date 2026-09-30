# Archived sources

Unmodified copies or excerpts of upstream files the Key Component List relies on. The ArduPilot files are from the Rover-4.7.1 release commit (dbe79216), the same commit the simulator is built from and the firmware is flashed from (SDR RID-09). Re-archived in Issue D of the KCL: the release adds `define ALLOW_ARM_NO_COMPASS` to both board files, and has a typo in `motorboat.parm` (which Boaty does not use).

| File | Upstream | Commit |
|---|---|---|
| `ardupilot/SpeedyBeeF405WING_*` | ArduPilot/ardupilot `libraries/AP_HAL_ChibiOS/hwdef/SpeedyBeeF405WING/` | dbe792162d06cab66c3475fd5556bf7a120f119e |
| `ardupilot/MatekF405-TE_hwdef.dat` | ArduPilot/ardupilot `libraries/AP_HAL_ChibiOS/hwdef/MatekF405-TE/hwdef.dat` | dbe792162d06cab66c3475fd5556bf7a120f119e |
| `ardupilot/SITL_JSON_readme.md` | ArduPilot/ardupilot `libraries/SITL/examples/JSON/readme.md` | dbe792162d06cab66c3475fd5556bf7a120f119e |
| `ardupilot/sitl_*.parm` | ArduPilot/ardupilot `Tools/autotest/default_params/` | dbe792162d06cab66c3475fd5556bf7a120f119e |
| `ardupilot/wiki_common-matekf405-te.rst` | ArduPilot/ardupilot_wiki `common/source/docs/common-matekf405-te.rst` | 5365bb696d91a16e6ffb5db2523f0bee0d13c94d |
| `am32_main_c_signal_timeout_excerpt.c` | am32-firmware/AM32 `Src/main.c` lines 1985-2015 and 1355-1372 | 2738df3240baa5bd4295b460cf0c5cfe0bd49d97 |

ArduPilot and AM32 are licensed under GPLv3.
