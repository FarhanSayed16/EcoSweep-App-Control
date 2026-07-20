# Phase 3: Manual Changes Reference

Use this document to manually apply all Phase 3 improvements. Each section lists the exact changes to make.

---

## Table of Contents

1. [Bridge Script (`ecosweep_manual_final.py`)](#1-bridge-script-ecosweep_manual_finalpy)
2. [systemd YOLO Service](#2-systemd-yolo-service)
3. [systemd Bridge Service](#3-systemd-bridge-service)
4. [Startup Script (Optional)](#4-startup-script-optional)
5. [Pi Setup Steps](#5-pi-setup-steps)

---

## 1. Bridge Script (`ecosweep_manual_final.py`)

**Location on Pi:** `/home/pi/ecosweep/ecosweep_manual_final.py` (or your bridge path)

### Option A: Replace Entire File

If you prefer to replace the whole file, copy the full content from:

**Repo path:** `hardware/pi/ecosweep_manual_final_patched.py`

Save it as `ecosweep_manual_final.py` on the Pi.
Back up your current file first: `cp ecosweep_manual_final.py ecosweep_manual_final.py.bak`

---

### Option B: Apply Changes Incrementally

If you want to edit your existing file, apply these changes in order:

#### A. Add after `serial_lock = threading.Lock()` (around line 37):

```python
telemetry_lock = Lock()
telemetry = {"front": 999, "left": 999, "right": 999, "updated": 0.0}

DETECTION_FILE = "/tmp/ecosweep_detection.json"
# --- Autonomy tuning ---
APPROACH_SPEED = 100
TURN_SPEED = 80
FRONT_SAFE_CM = 15
FRONT_CLOSE_CM = 25
GARBAGE_MIN_CONF = 0.4
NO_DETECTION_TIMEOUT_S = 2.0
PICKUP_ARM_DOWN_S = 0.5
PICKUP_GRIP_CLOSE_S = 1.5
PICKUP_ARM_UP_S = 0.5
BACKUP_SPEED = -80
BACKUP_DURATION_S = 0.5
```

**Remove** the old `DETECTION_FILE`, `APPROACH_SPEED`, `TURN_SPEED` lines if they exist (they are replaced by the block above).

#### B. Add after `def _write_arduino(cmd):` block (before `def autonomy_loop()`):

```python
def _parse_telemetry(line):
    """Parse DATA:SENSORS:front,left,right and update shared telemetry."""
    if not line or not line.strip().startswith("DATA:SENSORS:"):
        return
    try:
        parts = line.strip().split(":", 2)[2].split(",")
        if len(parts) >= 3:
            f, l, r = int(parts[0]), int(parts[1]), int(parts[2])
            with telemetry_lock:
                telemetry["front"] = f
                telemetry["left"] = l
                telemetry["right"] = r
                telemetry["updated"] = time.time()
    except (ValueError, IndexError):
        pass


def _get_telemetry():
    """Thread-safe copy of telemetry."""
    with telemetry_lock:
        return dict(telemetry)
```

#### C. Replace the entire `def autonomy_loop():` function

Replace your current `autonomy_loop()` with this full implementation:

```python
def autonomy_loop():
    global AUTO_MODE
    state = "SEARCH"
    last_garbage_time = 0.0
    last_no_garbage_time = 0.0
    search_direction = 1

    while True:
        time.sleep(0.1)
        with auto_lock:
            if not AUTO_MODE:
                if state != "IDLE":
                    _write_arduino("M:0,0")
                    state = "IDLE"
                continue

        tel = _get_telemetry()
        front_cm = tel.get("front", 999)

        try:
            with open(DETECTION_FILE, "r") as f:
                det = json.load(f)
        except Exception:
            det = {}

        decision = det.get("decision", "NONE")
        confidence = det.get("confidence", 0.0)
        person_detected = det.get("person_detected", False)
        has_garbage = decision in ("MOVE_LEFT", "MOVE_RIGHT", "CENTERED") and confidence >= GARBAGE_MIN_CONF
        now = time.time()

        # ---- Obstacle: CAMERA (person) OR ULTRASONIC (front too close) ----
        obstacle_camera = person_detected
        obstacle_ultrasonic = front_cm >= 0 and front_cm < FRONT_SAFE_CM
        if obstacle_camera or obstacle_ultrasonic:
            _write_arduino("M:0,0")
            state = "STOP"
            last_no_garbage_time = now
            continue

        if state == "STOP":
            if not obstacle_camera and not obstacle_ultrasonic:
                state = "RECOVER"
            else:
                continue

        # ---- SEARCH ----
        if state == "SEARCH":
            if has_garbage:
                state = "APPROACH"
                last_garbage_time = now
                last_no_garbage_time = 0.0
            else:
                last_no_garbage_time = now if last_no_garbage_time == 0 else last_no_garbage_time
                turn = TURN_SPEED * search_direction
                _write_arduino(f"M:40,{turn}")
                search_direction *= -1
            continue

        # ---- APPROACH ----
        if state == "APPROACH":
            if not has_garbage:
                if last_no_garbage_time == 0:
                    last_no_garbage_time = now
                if now - last_no_garbage_time > NO_DETECTION_TIMEOUT_S:
                    state = "SEARCH"
                    _write_arduino("M:0,0")
                else:
                    _write_arduino("M:0,0")
                continue
            last_garbage_time = now
            last_no_garbage_time = 0.0

            if front_cm >= 0 and front_cm < FRONT_CLOSE_CM and decision == "CENTERED":
                state = "ALIGN"
                _write_arduino("M:0,0")
            elif decision == "MOVE_LEFT":
                _write_arduino(f"M:0,-{TURN_SPEED}")
            elif decision == "MOVE_RIGHT":
                _write_arduino(f"M:0,{TURN_SPEED}")
            elif decision == "CENTERED":
                if front_cm >= 0 and front_cm < FRONT_CLOSE_CM:
                    state = "PICKUP"
                    _write_arduino("M:0,0")
                else:
                    _write_arduino(f"M:{APPROACH_SPEED},0")
            else:
                _write_arduino(f"M:0,{TURN_SPEED * search_direction}")
            continue

        # ---- ALIGN (fine-tune before pickup) ----
        if state == "ALIGN":
            if not has_garbage:
                state = "SEARCH"
                _write_arduino("M:0,0")
                continue
            if decision == "CENTERED":
                state = "PICKUP"
                _write_arduino("M:0,0")
            elif decision == "MOVE_LEFT":
                _write_arduino(f"M:0,-{TURN_SPEED // 2}")
            elif decision == "MOVE_RIGHT":
                _write_arduino(f"M:0,{TURN_SPEED // 2}")
            continue

        # ---- PICKUP: arm sequence ----
        if state == "PICKUP":
            _write_arduino("M:0,0")
            _write_arduino("SA:ARM_DOWN_START")
            time.sleep(PICKUP_ARM_DOWN_S)
            _write_arduino("SA:ARM_DOWN_STOP")
            _write_arduino("SA:GRIP_CLOSE_START")
            time.sleep(PICKUP_GRIP_CLOSE_S)
            _write_arduino("SA:GRIP_CLOSE_STOP")
            _write_arduino("SA:ARM_UP_START")
            time.sleep(PICKUP_ARM_UP_S)
            _write_arduino("SA:ARM_UP_STOP")
            _write_arduino("M:0,0")
            state = "RECOVER"

        # ---- RECOVER: back up, turn, then SEARCH ----
        if state == "RECOVER":
            _write_arduino(f"M:{BACKUP_SPEED},0")
            time.sleep(BACKUP_DURATION_S)
            _write_arduino("M:0,0")
            _write_arduino(f"M:0,{TURN_SPEED * search_direction}")
            time.sleep(0.3)
            _write_arduino("M:0,0")
            state = "SEARCH"
            search_direction *= -1
```

#### D. In the Arduino → App section, add telemetry parsing

Find this block:

```python
                if arduino and arduino.in_waiting > 0:
                    try:
                        resp = arduino.readline().decode(errors="ignore").strip()
                        if resp:
                            client_sock.send((resp + "\n").encode())
                    except Exception:
                        pass
```

Change it to:

```python
                if arduino and arduino.in_waiting > 0:
                    try:
                        resp = arduino.readline().decode(errors="ignore").strip()
                        if resp:
                            _parse_telemetry(resp)
                            client_sock.send((resp + "\n").encode())
                    except Exception:
                        pass
```

(The only change is adding `_parse_telemetry(resp)` before `client_sock.send`.)

---

## 2. systemd YOLO Service

**Create file:** `/home/pi/ecosweep/systemd/ecosweep-yolo.service`

**Full content:**

```ini
[Unit]
Description=EcoSweep YOLO FPV Stream (webcam + detection)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
# Adjust ECOSWEEP_DIR to match your Pi folder (e.g. /home/pi/ecosweep or /home/pi/ecosweep-phase2)
Environment=ECOSWEEP_DIR=/home/pi/ecosweep
# Wait for USB webcam (up to 30 seconds)
ExecStartPre=/bin/bash -c 'for i in $(seq 1 30); do [ -e /dev/video0 ] && break; sleep 1; done'
ExecStart=/usr/bin/python3 ${ECOSWEEP_DIR}/phase2/yolo_fpv_stream_optimized.py
WorkingDirectory=${ECOSWEEP_DIR}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**If using a Python venv:** Change `ExecStart` to use the venv Python, e.g.:

```
ExecStart=/home/pi/yolov8-env/bin/python3 ${ECOSWEEP_DIR}/phase2/yolo_fpv_stream_optimized.py
```

---

## 3. systemd Bridge Service

**Create file:** `/home/pi/ecosweep/systemd/ecosweep-bridge.service`

**Full content:**

```ini
[Unit]
Description=EcoSweep Bridge (Bluetooth + Arduino + Autonomy)
After=network-online.target ecosweep-yolo.service
Wants=network-online.target

[Service]
Type=simple
User=pi
# Adjust ECOSWEEP_DIR to match your Pi folder
Environment=ECOSWEEP_DIR=/home/pi/ecosweep
# Wait for Arduino serial (up to 20 seconds)
ExecStartPre=/bin/bash -c 'for i in $(seq 1 20); do [ -e /dev/ttyUSB0 ] || [ -e /dev/ttyACM0 ] && break; sleep 1; done'
ExecStart=/usr/bin/python3 ${ECOSWEEP_DIR}/ecosweep_manual_final.py
WorkingDirectory=${ECOSWEEP_DIR}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**If using a Python venv:** Change `ExecStart` to use the venv Python, e.g.:

```
ExecStart=/home/pi/yolov8-env/bin/python3 ${ECOSWEEP_DIR}/ecosweep_manual_final.py
```

---

## 4. Startup Script (Optional)

**Create file:** `/home/pi/ecosweep/ecosweep_start.sh`

**Full content:**

```bash
#!/bin/bash
# EcoSweep all-in-one startup script
# Run manually or from rc.local / a single systemd service
# Usage: ./ecosweep_start.sh

ECOSWEEP_DIR="${ECOSWEEP_DIR:-/home/pi/ecosweep}"
cd "$ECOSWEEP_DIR" || exit 1

echo "Waiting for USB webcam..."
for i in $(seq 1 30); do
    [ -e /dev/video0 ] && break
    sleep 1
done
if [ ! -e /dev/video0 ]; then
    echo "WARNING: /dev/video0 not found. YOLO may fail."
fi

echo "Waiting for Arduino..."
for i in $(seq 1 20); do
    [ -e /dev/ttyUSB0 ] || [ -e /dev/ttyACM0 ] && break
    sleep 1
done
if [ ! -e /dev/ttyUSB0 ] && [ ! -e /dev/ttyACM0 ]; then
    echo "ERROR: Arduino not found. Exiting."
    exit 1
fi

echo "Starting YOLO stream in background..."
python3 phase2/yolo_fpv_stream_optimized.py &
YOLO_PID=$!
sleep 5

echo "Starting bridge..."
python3 ecosweep_manual_final.py

# If bridge exits, kill YOLO
kill $YOLO_PID 2>/dev/null
```

**Make executable:** `chmod +x /home/pi/ecosweep/ecosweep_start.sh`

---

## 5. Pi Setup Steps

### 5.1 Create folder structure

```bash
mkdir -p /home/pi/ecosweep/phase2
mkdir -p /home/pi/ecosweep/systemd
```

### 5.2 Copy files

| Source | Destination | Notes |
|--------|-------------|-------|
| `yolo_fpv_stream_optimized.py` | `/home/pi/ecosweep/phase2/` | From repo `hardware/pi/phase2/` |
| `ecosweep_manual_final_patched.py` | `/home/pi/ecosweep/ecosweep_manual_final.py` | Rename to `ecosweep_manual_final.py` |
| `ecosweep-yolo.service` | `/home/pi/ecosweep/systemd/` | Create from Section 2 |
| `ecosweep-bridge.service` | `/home/pi/ecosweep/systemd/` | Create from Section 3 |
| `ecosweep_start.sh` | `/home/pi/ecosweep/` | Create from Section 4 (optional) |

### 5.3 Edit paths in service files

In both `.service` files, change `ECOSWEEP_DIR=/home/pi/ecosweep` to your actual path if different.

### 5.4 Add user to dialout (for serial)

```bash
sudo usermod -a -G dialout pi
```

Log out and back in (or reboot) for this to take effect.

### 5.5 Install systemd services

```bash
sudo cp /home/pi/ecosweep/systemd/ecosweep-yolo.service /etc/systemd/system/
sudo cp /home/pi/ecosweep/systemd/ecosweep-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-yolo.service
sudo systemctl enable ecosweep-bridge.service
```

### 5.6 Start services (or reboot)

```bash
sudo systemctl start ecosweep-yolo.service
sudo systemctl start ecosweep-bridge.service
```

Or reboot:

```bash
sudo reboot
```

### 5.7 Check status

```bash
sudo systemctl status ecosweep-yolo.service
sudo systemctl status ecosweep-bridge.service
```

View logs:

```bash
journalctl -u ecosweep-yolo.service -f
journalctl -u ecosweep-bridge.service -f
```

---

## Tunable Constants (Bridge Script)

In `ecosweep_manual_final.py` you can adjust:

| Constant | Default | Description |
|----------|---------|-------------|
| `FRONT_SAFE_CM` | 15 | Stop when ultrasonic front < this (cm) |
| `FRONT_CLOSE_CM` | 25 | Enter PICKUP when front < this and centered |
| `PICKUP_ARM_DOWN_S` | 0.5 | Arm down duration (seconds) |
| `PICKUP_GRIP_CLOSE_S` | 1.5 | Gripper close duration |
| `PICKUP_ARM_UP_S` | 0.5 | Arm up duration |
| `BACKUP_SPEED` | -80 | Speed when backing up from obstacle |
| `BACKUP_DURATION_S` | 0.5 | How long to back up |
