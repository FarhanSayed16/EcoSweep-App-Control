# Bluetooth Protocol

App and robot communicate over **Bluetooth Classic SPP** with newline-terminated text messages.

## Outgoing (App → Robot)

| Command | Format | Example | Notes |
|---------|--------|---------|--------|
| Movement | `M:<speed>,<turn>` | `M:200,-90` | speed, turn in [-255, 255] |
| Servo angle | `S:<id>,<angle>` | `S:1,120` | id 0–4, angle 0–180° |
| Servo action | `SA:<command>` | `SA:ARM_UP_START` | Continuous movement |
| Mode | `MODE:<mode>` | `MODE:AUTO_ON` | AUTO_ON / AUTO_OFF etc. |
| Preset | `PRESET:<name>` | `PRESET:pickup` | Recall saved preset |
| Gear | `GEAR:<1\|2\|3>` | `GEAR:2` | 1=~40%, 2=~70%, 3=100% |
| Path | `PATH:<lat>,<lon>;...` | `PATH:19.0,72.8;19.1,72.9` | Waypoints for mission |
| Person | `PERSON:ADD:<name>` | `PERSON:ADD:John` | Add for recognition |
| Sound | `SOUND:TURBO` or `SOUND:SHIFT` | — | Pi-only; plays WAV |

## Incoming (Robot → App)

| Type | Format | Example |
|------|--------|---------|
| Sensors | `DATA:SENSORS:<front>,<left>,<right>` | `DATA:SENSORS:45,30,60` |
| Battery | `DATA:BATT:<robot_v>,<controller_v>` | `DATA:BATT:12.5,3.7` |
| GPS | `DATA:GPS:<lat>,<lon>` | `DATA:GPS:19.0760,72.8777` |
| Log | `DATA:LOG:<message>` | `DATA:LOG:Voice cmd 'FORWARD'` |
| Speech | `DATA:SPEAK:<text>` | `DATA:SPEAK:My name is EcoSweep.` |
| Stats | `DATA:STATS:<value>` | `DATA:STATS:5` |
| Mode | `MODE:<mode>` | `MODE:AUTO_ON` |
| Gear | `GEAR:<n>` | `GEAR:2` |

All lines are sent with a trailing newline (`\n`). Malformed lines are ignored by the app to avoid crashes.
