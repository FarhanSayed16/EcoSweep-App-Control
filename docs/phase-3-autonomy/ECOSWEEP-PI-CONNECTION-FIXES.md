# EcoSweep Pi — Connection & Disconnect Fixes

Root causes identified and fixes applied.

---

## Root Causes

| Issue | Cause |
|-------|-------|
| **App connects then disconnects** | (1) No data to app when Arduino disconnected → Bluetooth stack may close idle connection. (2) Rapid M: commands flood Arduino serial buffer (64 bytes) → overflow/corruption. |
| **App not reconnecting** | Aggressive Bluetooth reset on disconnect; channel conflict (1 and 2 often held by system). |
| **Inconsistent behavior** | Bridge ran as `pi`; some Bluetooth operations need root for stability. |

---

## Fixes Applied

### 1. Keepalive (Bridge → App)
- When Arduino sends nothing for 1.5 s, bridge sends `DATA:SENSORS:999,999,999` to the app.
- Keeps the connection active when Arduino is disconnected or idle.
- App still parses this as sensor data.

### 2. M: Command Throttling (Bridge → Arduino)
- M: commands limited to ~12 Hz (every 80 ms).
- Avoids Arduino serial buffer overflow when joystick sends many commands.
- Other commands (GEAR, MODE, SA:) still forwarded immediately.

### 3. Run Bridge as Root
- Systemd service uses `User=root` instead of `User=pi`.
- Improves Bluetooth SPP reliability.

### 4. Arduino Status Logging
- Logs whether Arduino is connected at startup.
- Easier to see if telemetry is disabled.

### 5. Reset Without Sudo When Root
- `reset_bluetooth_adapter()` skips `sudo` when already running as root.

---

## Deploy Steps

1. Copy updated files to Pi:
   - `ecosweep_manual_final_patched.py` → `/home/pi/ecosweep_manual_final.py`
   - `ecosweep-bridge.service` → `/etc/systemd/system/`

2. Copy service and reload:
   ```bash
   sudo cp /home/pi/ecosweep-phase2/systemd/ecosweep-bridge.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl restart ecosweep-bridge.service
   ```

3. Full reset (if connection issues remain):
   ```bash
   sudo systemctl restart bluetooth
   sleep 10
   sudo systemctl restart ecosweep-bridge.service
   ```
   On the phone: Forget/Unpair the Pi, then pair again and run `trust [PHONE_MAC]` in bluetoothctl.

---

## Verify

```bash
sudo journalctl -u ecosweep-bridge.service -f
```

Expected lines:
- `Arduino connected on /dev/ttyUSB0` (or NOT connected)
- `Serial Port service registered`
- `Waiting for Bluetooth connection...`
- `Connected. Starting app/arduino threads.`
- On disconnect: `App->Arduino thread stopped.` or `Arduino->App thread stopped.`
