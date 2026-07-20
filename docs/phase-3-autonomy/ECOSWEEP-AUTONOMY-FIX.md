# EcoSweep Autonomy — Fix "Robot Doesn't Move in Auto Mode"

Use this guide when the robot does not move when Autonomous mode is turned ON in the app.

---

## Checklist: Ensure Everything Is Set Up

### 1. Which Bridge Is Running?

Autonomy only works with the **full bridge** (`ecosweep_manual_final.py`). The minimal bridge has no autonomy.

On the Pi:

```bash
# Check which bridge service is enabled
systemctl is-enabled ecosweep-bridge.service ecosweep-bridge-minimal.service 2>/dev/null

# You MUST have:
#   ecosweep-bridge.service: enabled
#   ecosweep-bridge-minimal.service: disabled
```

**Fix:** Use the full bridge:

```bash
sudo systemctl stop ecosweep-bridge-minimal.service
sudo systemctl disable ecosweep-bridge-minimal.service
sudo systemctl enable ecosweep-bridge.service
sudo systemctl start ecosweep-bridge.service
```

### 2. Is the Full Bridge Script on the Pi?

The full bridge with autonomy is `ecosweep_manual_final_patched.py`. It must be copied as `ecosweep_manual_final.py` on the Pi.

On your PC:

```bash
scp D:\Robot_newcontrol\hardware\pi\ecosweep_manual_final_patched.py pi@YOUR_PI_IP:/home/pi/ecosweep_manual_final.py
```

On the Pi, verify:

```bash
head -5 /home/pi/ecosweep_manual_final.py
# Should mention "telemetry parsing, obstacle detection, arm PICKUP"
```

### 3. Is YOLO Running and Writing Detection?

Autonomy reads `/tmp/ecosweep_detection.json` from the YOLO script. If YOLO is not running, the file is missing or stale.

```bash
# YOLO service must be running
sudo systemctl status ecosweep-yolo.service

# Detection file must exist and update
watch -n 0.5 "cat /tmp/ecosweep_detection.json 2>/dev/null || echo 'File not found'"
```

Move the camera toward a bottle/cup. You should see `decision`, `confidence`, `bbox_center_x` change.

### 4. App Connection and Toggle

1. **Connect** the app to the robot via Bluetooth.
2. Open the **Autonomous** tab.
3. Toggle **Autonomous Mode** to **ON** (the switch must be blue/active).

The app sends `MODE:AUTO_ON` to the Pi. Only then does the bridge set `AUTO_MODE = True` and the autonomy loop starts sending `M:` commands.

### 5. Arduino and Ultrasonics

- Arduino must be connected via USB (`/dev/ttyUSB0` or `/dev/ttyACM0`).
- Ultrasonic sensors should report distances. If `front` is always 0 or -1, the robot may think there is an obstacle and stay in STOP.

Check bridge logs:

```bash
sudo journalctl -u ecosweep-bridge.service -f
```

---

## Quick Verification (On Pi)

```bash
# 1. Services
sudo systemctl status ecosweep-bridge.service ecosweep-yolo.service

# 2. Detection file
cat /tmp/ecosweep_detection.json

# 3. Bridge logs (connect app, toggle Auto ON, then check)
sudo journalctl -u ecosweep-bridge.service -n 50 --no-pager
```

---

## Autonomy Behavior Summary

| State     | Condition                          | Action                                  |
|-----------|------------------------------------|-----------------------------------------|
| **IDLE**  | Auto OFF or no connection          | Stays stopped                           |
| **SEARCH**| No garbage detected                | Slow turn (left/right) to find objects  |
| **APPROACH** | Garbage in frame, not centered  | Turn toward target or drive forward     |
| **ALIGN** | Close, fine-tuning                 | Small turns to center                   |
| **PICKUP**| Centered and close (front < 18 cm) | Creep, arm down, grip close, arm up     |
| **STOP**  | Person or obstacle (ultrasonic)    | Stop until clear                        |
| **RECOVER**| Stuck or lost target             | Back up, turn, then SEARCH              |

---

## Tuning (If Robot Moves but Behavior Is Wrong)

Edit `/home/pi/ecosweep_manual_final.py` on the Pi:

| Constant            | Default | Effect                                      |
|---------------------|---------|---------------------------------------------|
| `GARBAGE_MIN_CONF`  | 0.35    | Lower = more detections (more false positives) |
| `SEARCH_SPEED`      | 30      | Speed while turning in SEARCH               |
| `SEARCH_TURN`       | 60      | Turn amount in SEARCH                       |
| `APPROACH_SPEED_FAR`| 70      | Forward speed when object is far            |
| `FRONT_SAFE_CM`     | 15      | Stop if front sensor < this (obstacle)      |
| `FRONT_CLOSE_CM`    | 18      | Close enough to trigger PICKUP              |

After editing: `sudo systemctl restart ecosweep-bridge.service`
