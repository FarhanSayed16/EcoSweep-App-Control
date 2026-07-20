# EcoSweep Hardware Integration

This folder contains the reference Arduino and Raspberry Pi code used by the EcoSweep app over Bluetooth Classic (SPP), plus exact run instructions.

- Arduino sketch: `arduino/EcoSweep_Master/EcoSweep_Master.ino`
- Raspberry Pi bridge: `pi/ecosweep_bridge.py`
- Optional audio: `pi/sounds/*.wav`

## New Features

### 1) 3-Speed Gear Modes (car-like)
- Command from app: `GEAR:<1|2|3>`
  - Gear 1 → ~40% output (slow)
  - Gear 2 → ~70% output (medium)
  - Gear 3 → 100% output (full)
- Firmware echoes current gear each telemetry cycle:
  - `GEAR:<n>`
- Proportional drive (`M:speed,turn`) is scaled by current gear.

### 2) Fun Engine/Turbo Sounds (on Raspberry Pi)
- The Pi bridge plays sounds when moving and on gear shifts (purely for fun):
  - Looped engine per gear while the robot is moving
  - Shift sound on `GEAR:` change
  - Turbo whoosh when throttle is lifted quickly
- Place WAV files here:
  - `hardware/pi/sounds/engine_idle.wav` (fallback)
  - `hardware/pi/sounds/engine_gear1.wav`
  - `hardware/pi/sounds/engine_gear2.wav`
  - `hardware/pi/sounds/engine_gear3.wav`
  - `hardware/pi/sounds/shift.wav`
  - `hardware/pi/sounds/turbo.wav`
- Audio player used: `aplay` (ALSA). Install: `sudo apt-get install -y alsa-utils`.
- Manual trigger (optional) from the app: `SOUND:TURBO` or `SOUND:SHIFT`

Notes:
- Audio is handled on the Pi (not on the Arduino). The Arduino still receives normal control commands.
- The Pi forwards all commands to Arduino except `SOUND:*`, which Pi consumes to play audio.

## Protocol Compat Matrix (App ⇄ Firmware)

- Commands the app can send:
  - `M:<speed>,<turn>`  ✅ handled on Arduino (scaled by gear)
  - `S:<id>,<angle>`    ✅ handled
  - `SA:<command>`      ✅ handled
  - `MODE:<mode>`       ✅ stored + echoed by Arduino
  - `GEAR:<1|2|3>`      ✅ Arduino scales output; Pi plays shift + engine loop
  - `PRESET:<name>`     ✅ no-op ACK (extend if needed)
  - `PATH:lat,lon;...`  ✅ ACK (extend for autonomous)
  - `SOUND:<SHIFT|TURBO>` ✅ Pi-only manual audio trigger

- Telemetry the app reads:
  - `DATA:SENSORS:<front>,<left>,<right>`  ✅
  - `DATA:BATT:<robot_v>,<controller_v>`   ✅
  - `MODE:<mode>`                           ✅
  - `GEAR:<n>`                              ✅
  - `DATA:IMU:*`, `DATA:MQ:*`              ✅ optional; app ignores if not parsed
  - `DATA:GPS:*`, `DATA:LOG:*`, `DATA:STATS:*` ⛔ optional/not required

## Raspberry Pi – Run Instructions

One-time:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip alsa-utils
sudo usermod -a -G dialout pi
sudo reboot
```

Each run:
```bash
# Ensure SPP profile exists
sudo sdptool add SP
# Run the bridge (binds RFCOMM channel 1 and advertises SPP)
python3 pi/ecosweep_bridge.py
```

## Arduino – Notes
- Board: Arduino Mega
- Libraries: Wire, Adafruit_PWMServoDriver, Adafruit_MPU6050, Adafruit_Sensor, QMC5883LCompass
- Upload `arduino/EcoSweep_Master/EcoSweep_Master.ino`

## Extending Autonomous PATH
- Current: PATH is ACKed only.
- To execute:
  - Parse waypoints, add IMU/compass-based P-controller to steer to waypoint
  - Advance waypoint on proximity threshold

## Troubleshooting
- App can’t connect: ensure Pi binds on RFCOMM 1 and advertises SPP UUID; pair device
- No telemetry: confirm Arduino at 9600 baud, newline-terminated; USB permissions (`dialout` group)
- No audio: verify WAV paths and `aplay` installed; try `aplay <file.wav>` manually
