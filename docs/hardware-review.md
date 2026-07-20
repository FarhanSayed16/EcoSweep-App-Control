# Hardware Folder & Firmware Review

Review of the `hardware/` folder structure, Arduino sketch, and Raspberry Pi bridge.

---

## 1. Hardware Folder Structure

```
hardware/
├── README.md              # Protocol, gear/sounds, run instructions
├── arduino/
│   └── EcoSweep_Master/
│       └── EcoSweep_Master.ino
└── pi/
    └── ecosweep_bridge.py
```

- **README.md** correctly describes Arduino + Pi roles, gear modes, audio, protocol matrix, and run instructions.
- **Path note**: README says `arduino/EcoSweep_Master.ino`; actual path is `arduino/EcoSweep_Master/EcoSweep_Master.ino` (sketch lives in a folder). Consider updating README for copy-paste accuracy.
- **Optional**: `pi/sounds/` is referenced for WAV files but not committed; that’s fine for optional audio.

---

## 2. Arduino Code Review (`EcoSweep_Master.ino`)

### Strengths

- **Structure**: Clear sections (pins, globals, setup, loop, command handling, telemetry, helpers). Single main loop with non-blocking servo stepping and fixed-interval telemetry (4 Hz).
- **Safety**: Motor watchdog (500 ms command timeout) stops drive if no `M:` command; reduces runaway risk.
- **Protocol**: Handles `M:`, `S:`, `SA:`, `MODE:`, `GEAR:`, `PRESET:`, `PATH:`; echoes MODE/GEAR for app and Pi; sends `DATA:SENSORS`, `DATA:IMU`, `DATA:MQ`, `DATA:BATT`, MODE, GEAR. Format matches app expectations.
- **Gear scaling**: Gear 1/2/3 (0.40 / 0.70 / 1.00) applied to speed/turn before PWM; pivot-in-place when |speed| is small and turn non-zero.
- **Servos**: PCA9685 pulse mapping (150–600), 20 ms step interval for continuous SA movements; angles clamped 0–180.
- **Ultrasonic**: Timeout (30 ms) returns -1 to avoid blocking; distance formula and pin usage are standard.
- **Calibration**: `LEFT_MOTOR_SIGN`, `RIGHT_MOTOR_SIGN`, `TURN_SIGN` allow reversing axes without changing wiring.

### Minor Issues / Gaps

- **Battery**: `DATA:BATT:7.4,11.1` is hardcoded. For real use, add ADC reads (with dividers) or an I2C fuel gauge and send real voltages.
- **PRESET**: Only ACKs; preset names are not interpreted on Arduino. App sends individual `S:id,angle`; acceptable if presets are app-side only.
- **PATH**: Only ACK; no waypoint execution. README already notes this for future autonomous work.
- **Error handling**: Unknown commands get `DATA:LOG:ERR Unknown cmd`; malformed `M:`/`S:` get `Bad M`/`Bad S`. No risk of crash; app ignores these.
- **Compass calibration**: Offsets/scales are magic numbers; in production these should come from a calibration routine or config.

### Verdict

Firmware is readable, safe, and aligned with the app protocol. Main follow-ups: real battery telemetry and (later) PATH execution if autonomous is required.

---

## 3. Raspberry Pi Code Review (`ecosweep_bridge.py`)

### Strengths

- **Roles**: Finds Arduino on `/dev/ttyUSB0`, `/dev/ttyACM0`, or `/dev/ttyAMA0` @ 9600; starts Bluetooth SPP server on RFCOMM 1 and advertises SPP UUID; two threads (app→Arduino, Arduino→app) for full duplex.
- **Protocol**: Forwards all app lines to Arduino except `SOUND:*`, which triggers WAV playback. Intercepts `GEAR:` and `M:` for audio (shift, engine loop, turbo) then forwards to Arduino. Logic matches hardware README.
- **Audio**: Optional; checks `os.path.isfile()` before playing. Engine loop via subprocess (`while true; do aplay ...`); stop_loop() cleans up. Turbo on “quick throttle lift” (speed drop > 80) is a simple heuristic.
- **Cleanup**: `main()` uses try/finally to close client, server, and Arduino; stops engine loop. Daemon threads exit when main thread exits.

### Minor Issues / Gaps

- **Single client**: `server_sock.listen(1)` and single `accept()`; one app at a time. Acceptable for a dedicated controller.
- **Reconnect**: If the app disconnects, the script exits; no automatic re-listen or Arduino re-scan. For headless use, a wrapper (systemd/supervisor + restart) or a small loop (re-accept, reconnect serial) would help.
- **Arduino disconnect**: If USB is unplugged, `arduino_to_app` may raise `SerialException`; thread exits, the other thread may still try to use the socket. Adding a shared “connected” flag and checking it before send/recv would make behavior clearer.
- **Encoding**: `decode(errors="ignore")` avoids crashes on garbage; acceptable for robustness.
- **Python 2**: Script is Python 3 (no print statement issues). README says `python3`; good.

### Verdict

Bridge is clear and does what it’s designed for: SPP server, serial bridge, optional sound. For production, consider reconnection logic and clearer handling of Arduino disconnect.

---

## 4. Summary

| Area | Assessment |
|------|-------------|
| **Hardware folder** | Clear layout; README path to sketch could be updated. |
| **Arduino sketch** | Solid structure, safety, and protocol; add real battery telemetry and optional PATH execution later. |
| **Pi bridge** | Correct SPP + serial + audio behavior; consider reconnection and Arduino-disconnect handling. |
