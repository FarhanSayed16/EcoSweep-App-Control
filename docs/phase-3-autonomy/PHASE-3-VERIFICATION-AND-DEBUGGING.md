# Phase 3: Verification and Debugging Guide

Use this guide to **confirm Phase 3 is working** and to **track down problems** when something doesn’t behave as expected.

---

## 1. Pre-checks (before testing autonomy)

### 1.1 On the Raspberry Pi

| Check | How to verify |
|-------|----------------|
| **Bridge running** | The control script (e.g. `ecosweep_manual_final.py`) is running and has started without errors. You see "Accepted connection" or similar after the app connects. |
| **Arduino connected** | Bridge reports Arduino found on `/dev/ttyUSB0` or `/dev/ttyACM0`. If not, plug USB and check `ls /dev/tty*`. |
| **YOLO stream running** | `yolo_fpv_stream_optimized.py` is running in another terminal. Stream is reachable at `http://<PI_IP>:5000/video_feed`. |
| **Detection file exists** | Run: `cat /tmp/ecosweep_detection.json` a few times while moving the camera. You should see `decision`, `confidence`, `person_detected` (and optionally `bbox_center_x`, `timestamp`) updating. If the file is missing or stale, YOLO script may have crashed or the path may be wrong. |
| **Serial lock in bridge** | If you use the patched bridge, every Arduino write is behind a single lock. Without it, mixed bytes can cause wrong or no movement. |

### 1.2 In the app

| Check | How to verify |
|-------|----------------|
| **Bluetooth connected** | Dashboard or Manual screen shows "Connected" (no "Please connect to device first"). |
| **Autonomous tab** | You can open the Autonomous tab and see the "Autonomous Mode" toggle. |
| **MODE commands** | When you toggle Autonomous ON, the app sends `MODE:AUTO_ON`; when OFF, `MODE:AUTO_OFF`. (Legacy Device Control screen must send `MODE:AUTO_ON` / `MODE:AUTO_OFF`, not `AUTO_ON` alone.) |
| **Telemetry (optional)** | If the Arduino sends `DATA:SENSORS:...` and `DATA:BATT:...`, the app parses them. On Dashboard you may see battery; on Autonomous screen you can add a small "Robot telemetry" card (front/left/right) to confirm data is reaching the app. |

### 1.3 Arduino

| Check | How to verify |
|-------|----------------|
| **Movement** | In **manual** mode, joystick or Manual screen commands move the robot. If not, fix serial/Bluetooth/wiring first. |
| **Telemetry** | If your sketch sends `DATA:SENSORS:front,left,right` and `DATA:BATT:robot_v,controller_v`, the Pi and app can use them. If Phase 3 logic uses "front close" stop, Arduino must send these. |

---

## 2. Step-by-step verification (Phase 3 behavior)

Do these in order. If a step fails, use Section 3 to debug before continuing.

### Step A: Manual mode still works

1. **Do not** turn on Autonomous mode.
2. Open the **Manual** tab and drive with the joystick (or buttons).
3. **Expected:** Robot moves (forward, back, turn, stop) as before.
4. **If it fails:** The problem is not Phase 3—check Bluetooth, bridge, and Arduino for manual control.

### Step B: Autonomous OFF → robot idle

1. Ensure Autonomous mode is **OFF** in the app.
2. Start the bridge and YOLO stream on the Pi.
3. Connect the app and leave the robot with camera view (e.g. no garbage in frame).
4. **Expected:** Robot does not move on its own.
5. **If it moves:** Either Autonomous was ON, or another process is sending commands. Confirm toggle is OFF and only one bridge is running.

### Step C: Autonomous ON, no garbage → slow search

1. Turn **Autonomous ON** in the app.
2. Point the camera at a blank wall or floor (no bottle/cup/person).
3. **Expected:** Robot slowly rotates (search behavior), e.g. `M:0,60` or similar. It should **not** drive forward fast.
4. **If it doesn’t move:** Check detection file on Pi (`cat /tmp/ecosweep_detection.json`). If `decision` is `NONE` and `confidence` < 0.4, bridge should send a slow turn. Verify bridge autonomy loop is running and reading the file; check for Python errors in the bridge terminal.
5. **If it drives forward:** Detection file may show `CENTERED` with high confidence (e.g. wrong object). Check what YOLO is detecting and adjust `GARBAGE_CLASSES` or camera view.

### Step D: Autonomous ON, garbage in frame → approach

1. Put a **bottle or cup** in view of the camera.
2. Keep Autonomous **ON**.
3. **Expected:** Robot turns toward the object (MOVE_LEFT / MOVE_RIGHT), then moves forward when centered (CENTERED).
4. **If it doesn’t turn:** Check detection file: `decision` should be MOVE_LEFT or MOVE_RIGHT when object is off-center. Confirm YOLO script is running and writing the file. Check bridge for errors.
5. **If it doesn’t move forward when centered:** Detection should show CENTERED; bridge should send `M:APPROACH_SPEED,0`. Verify logic in bridge autonomy loop and that serial writes use the lock.

### Step E: Person in frame → stop (safety)

1. With Autonomous **ON**, show a **person** to the camera (or a clear "person" detection).
2. **Expected:** Robot stops (e.g. `M:0,0`) and stays stopped.
3. **If it doesn’t stop:** Detection file should show `person_detected: true`. Verify bridge checks `person_detected` and sends stop; confirm YOLO script sets `person_detected` from person class.

### Step F: Toggle OFF → manual control again

1. Turn **Autonomous OFF** in the app.
2. **Expected:** Robot stops if it was moving. Joystick on Manual tab works again.
3. **If joystick still doesn’t work:** App may be blocking manual commands when it thinks mode is still AUTO. Confirm app sends `MODE:AUTO_OFF` and updates its internal mode; check bridge sets AUTO_MODE = False so it forwards manual commands.

---

## 3. Common failures and fixes

| Symptom | What to check | Fix |
|--------|----------------|-----|
| **Robot doesn’t move in auto** | Detection file present and updating? Bridge reading it? | Ensure YOLO script is running and writes to `/tmp/ecosweep_detection.json`. Run bridge from correct working directory. Check file permissions. |
| **Robot moves in wrong direction** | Left/right decision vs actual camera view | Check `bbox_center_x` vs frame center in detection file. Adjust `CENTER_MARGIN_PX` in YOLO script or turn direction in bridge (e.g. swap sign of turn). |
| **Robot doesn’t stop for person** | `person_detected` in detection file? Bridge logic? | Ensure YOLO script sets `person_detected` when person class is detected. In bridge, ensure autonomy loop checks `person_detected` and sends `M:0,0`. |
| **Mixed or wrong commands** | Two threads writing to Arduino without lock | Use a single lock for all `arduino.write(...)` in the bridge (see PHASE-3-PRODUCTION-INTEGRATION.md). Use the patched script or add `serial_lock` and `_write_arduino()`. |
| **App toggle doesn’t change behavior** | Wrong command format | App must send `MODE:AUTO_ON` and `MODE:AUTO_OFF` (with `MODE:` prefix). Fix any screen that sends only `AUTO_ON` / `AUTO_OFF`. |
| **No telemetry in app** | Arduino not sending DATA lines? Bridge not forwarding? | Confirm Arduino sends `DATA:SENSORS:...` and `DATA:BATT:...`. Confirm bridge forwards all Arduino lines to the app. Check app parses these (BluetoothService). |
| **YOLO stream or detection file stale** | YOLO script crashed or camera busy | Restart `yolo_fpv_stream_optimized.py`. Ensure no other process is using the camera. Check Pi CPU/memory (e.g. `htop`). |

---

## 4. Debugging on the Pi

- **Bridge logs:** Run the bridge in a terminal (not only as a service) so you see print output. Add temporary prints in the autonomy loop (e.g. decision, confidence, person_detected) if needed.
- **Detection file:** `watch -n 0.5 cat /tmp/ecosweep_detection.json` to see updates every 0.5 s.
- **Serial traffic (advanced):** If you have a serial sniffer or a second port, you can log bytes sent to the Arduino to confirm commands are correct and not interleaved.

---

## 5. App-side improvements (done in this project)

- **Manual screen:** When Autonomous mode is ON, a banner at the top says: *"Autonomous mode is ON. Joystick disabled. Turn off in Autonomous tab to drive manually."* So you know why the joystick doesn’t move the robot.
- **Autonomous screen:** A **"Robot telemetry"** card shows front / left / right distances (cm) and *"Updated just now"* (or *"Xs ago"*). If it shows *"No sensor data from robot yet"* or values stay —, the Arduino/Pi is not sending `DATA:SENSORS:...` or the app isn’t receiving it—useful for debugging.
- **BluetoothService:** Tracks `lastSensorUpdate` when `DATA:SENSORS` is parsed, so the app can show how fresh the telemetry is.
- **Device Control (legacy):** Fixed to send `MODE:AUTO_ON` and `MODE:AUTO_OFF` (with `MODE:` prefix) so the Pi bridge receives the correct protocol.

Use this guide whenever you change Phase 3 code or add new features to avoid regressions and to isolate issues quickly.
