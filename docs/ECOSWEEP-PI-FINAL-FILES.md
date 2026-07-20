# EcoSweep Pi — Final Files Reference

A single reference for **all final, complete files** that belong on the Raspberry Pi. Use this when setting up from scratch, updating, or verifying the Pi deployment.

---

## Summary: What Goes Where

| # | Repo Path (PC) | Pi Path | Purpose |
|---|----------------|---------|---------|
| 1 | `hardware/pi/ecosweep_manual_final_patched.py` | `/home/pi/ecosweep_manual_final.py` | Bridge (Bluetooth + Arduino + autonomy) |
| 2 | `hardware/pi/phase2/yolo_fpv_stream_optimized.py` | `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py` | YOLO detection + MJPEG stream |
| 3 | `hardware/pi/camera_stream.py` | `/home/pi/ecosweep-phase1/camera_stream.py` | *Optional* Phase 1: camera-only stream (no YOLO) |
| 4 | `hardware/pi/ecosweep_bridge_minimal.py` | `/home/pi/ecosweep_bridge_minimal.py` | *Optional* Phase 1: minimal bridge (no autonomy) |
| 5 | `hardware/pi/systemd/ecosweep-yolo.service` | `/etc/systemd/system/ecosweep-yolo.service` | systemd: auto-start YOLO stream |
| 6 | `hardware/pi/systemd/ecosweep-bridge.service` | `/etc/systemd/system/ecosweep-bridge.service` | systemd: auto-start bridge |
| 7 | `hardware/pi/systemd/ecosweep-bridge-minimal.service` | `/etc/systemd/system/ecosweep-bridge.service` | *Optional* systemd: minimal bridge |
| 8 | `hardware/pi/ecosweep_start.sh` | `/home/pi/ecosweep_start.sh` | *Optional* manual startup script |
| 9 | `hardware/arduino/EcoSweep_Master/EcoSweep_Master.ino` | Arduino IDE → upload to Arduino | Arduino firmware |

---

## 1. Bridge (Bluetooth + Arduino + Autonomy)

**Repo:** `hardware/pi/ecosweep_manual_final_patched.py`  
**Pi:** `/home/pi/ecosweep_manual_final.py`

**Note:** Copy the *patched* file to the Pi and name it `ecosweep_manual_final.py`.

**Purpose:**
- Bluetooth SPP server (app ↔ Pi)
- Serial bridge to Arduino (USB)
- Autonomy loop: reads `/tmp/ecosweep_detection.json`, sends `M:`, `SA:` commands
- Five-state autonomy: SEARCH → APPROACH_FAR → APPROACH_CLOSE → PICKUP → RECOVER

**Depends on:** YOLO script writing `/tmp/ecosweep_detection.json`

**SCP (from PC):**
```powershell
scp D:\Robot_newcontrol\hardware\pi\ecosweep_manual_final_patched.py pi@YOUR_PI_IP:/home/pi/ecosweep_manual_final.py
```

---

## 2. YOLO FPV Stream

**Repo:** `hardware/pi/phase2/yolo_fpv_stream_optimized.py`  
**Pi:** `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py`

**Purpose:**
- Captures USB webcam frames
- Runs YOLOv8 Nano for garbage detection
- Writes `/tmp/ecosweep_detection.json` (for autonomy)
- Serves MJPEG stream at `http://<PI_IP>:5000/video_feed`

**Dependencies (install on Pi):**
```bash
pip3 install opencv-python-headless flask ultralytics
```

**First run** downloads `yolov8n.pt` (~6MB).

**SCP (from PC):**
```powershell
scp D:\Robot_newcontrol\hardware\pi\phase2\yolo_fpv_stream_optimized.py pi@YOUR_PI_IP:/home/pi/ecosweep-phase2/
```

**Create folder on Pi first:**
```bash
mkdir -p /home/pi/ecosweep-phase2
```

---

## 3. Camera Stream Only (Phase 1 — Optional)

**Repo:** `hardware/pi/camera_stream.py`  
**Pi:** `/home/pi/ecosweep-phase1/camera_stream.py`

**Purpose:** Simple MJPEG stream without YOLO. Use for Phase 1 testing or when YOLO is not needed.

**SCP:**
```powershell
scp D:\Robot_newcontrol\hardware\pi\camera_stream.py pi@YOUR_PI_IP:/home/pi/ecosweep-phase1/
```

---

## 4. Minimal Bridge (Phase 1 — Optional)

**Repo:** `hardware/pi/ecosweep_bridge_minimal.py`  
**Pi:** `/home/pi/ecosweep_bridge_minimal.py`

**Purpose:** Bluetooth + Arduino only, no autonomy. Use for Phase 1 (verify app ↔ robot) before adding YOLO and autonomy.

**SCP:**
```powershell
scp D:\Robot_newcontrol\hardware\pi\ecosweep_bridge_minimal.py pi@YOUR_PI_IP:/home/pi/
```

---

## 5. systemd: YOLO Service

**Repo:** `hardware/pi/systemd/ecosweep-yolo.service`  
**Pi:** `/etc/systemd/system/ecosweep-yolo.service`

**Purpose:** Auto-start YOLO stream at boot. Waits for `/dev/video0` before starting.

**SCP:**
```powershell
scp D:\Robot_newcontrol\hardware\pi\systemd\ecosweep-yolo.service pi@YOUR_PI_IP:/tmp/
```

**On Pi:**
```bash
sudo cp /tmp/ecosweep-yolo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-yolo
sudo systemctl start ecosweep-yolo
```

---

## 6. systemd: Bridge Service (Full)

**Repo:** `hardware/pi/systemd/ecosweep-bridge.service`  
**Pi:** `/etc/systemd/system/ecosweep-bridge.service`

**Purpose:** Auto-start full bridge at boot. Waits for Arduino and optionally after YOLO.

**SCP:**
```powershell
scp D:\Robot_newcontrol\hardware\pi\systemd\ecosweep-bridge.service pi@YOUR_PI_IP:/tmp/
```

**On Pi:**
```bash
sudo cp /tmp/ecosweep-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-bridge
sudo systemctl start ecosweep-bridge
```

---

## 7. systemd: Bridge Service (Minimal — Optional)

**Repo:** `hardware/pi/systemd/ecosweep-bridge-minimal.service`  
**Pi:** `/etc/systemd/system/ecosweep-bridge.service`

Use this instead of (6) if you only want Phase 1 (no autonomy). It runs `ecosweep_bridge_minimal.py`.

---

## 8. Startup Script (Optional)

**Repo:** `hardware/pi/ecosweep_start.sh`  
**Pi:** `/home/pi/ecosweep_start.sh`

**Purpose:** Manual one-command start. Launches YOLO in background, then bridge in foreground.  
**Note:** Uses `phase2/` and `ecosweep_manual_final.py` — adjust paths if your layout differs (e.g. `ecosweep-phase2/`).

---

## 9. Arduino Firmware

**Repo:** `hardware/arduino/EcoSweep_Master/EcoSweep_Master.ino`  
**Target:** Arduino Mega (via USB)

**Purpose:** Motor control, ultrasonic sensors, servo arm. Upload via Arduino IDE.

---

## Final Recommended Layout on Pi

```
/home/pi/
├── ecosweep_manual_final.py          ← Bridge (copy from ecosweep_manual_final_patched.py)
├── ecosweep-phase2/
│   └── yolo_fpv_stream_optimized.py  ← YOLO + stream
└── (optional) ecosweep-phase1/
    └── camera_stream.py
```

**systemd services** in `/etc/systemd/system/`:
- `ecosweep-yolo.service`
- `ecosweep-bridge.service`

---

## Quick Copy Commands (All at Once)

From **PowerShell on PC** (replace `YOUR_PI_IP`):

```powershell
# Create folders
ssh pi@YOUR_PI_IP "mkdir -p /home/pi/ecosweep-phase2"

# Bridge
scp D:\Robot_newcontrol\hardware\pi\ecosweep_manual_final_patched.py pi@YOUR_PI_IP:/home/pi/ecosweep_manual_final.py

# YOLO
scp D:\Robot_newcontrol\hardware\pi\phase2\yolo_fpv_stream_optimized.py pi@YOUR_PI_IP:/home/pi/ecosweep-phase2/

# systemd
scp D:\Robot_newcontrol\hardware\pi\systemd\ecosweep-yolo.service pi@YOUR_PI_IP:/tmp/
scp D:\Robot_newcontrol\hardware\pi\systemd\ecosweep-bridge.service pi@YOUR_PI_IP:/tmp/
```

**On Pi after SCP:**
```bash
sudo cp /tmp/ecosweep-yolo.service /tmp/ecosweep-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-yolo ecosweep-bridge
sudo systemctl start ecosweep-yolo ecosweep-bridge
```

---

## Files NOT Deployed to Pi (Reference / Legacy)

| Repo Path | Status |
|-----------|--------|
| `hardware/pi/ecosweep_bridge.py` | Legacy; replaced by `ecosweep_manual_final_patched.py` |
| `hardware/pi/phase2/detection_yolo.py` | Reference; YOLO script uses `ultralytics` directly |
| `hardware/pi/phase2/detection.py` | Reference |
| `hardware/pi/phase3/autonomy.py` | Reference; autonomy is integrated in bridge |
| `hardware/pi/phase3/__init__.py` | Package init |
| `hardware/pi/phase2/models/README.md` | Docs only |

---

## Verification Commands

```bash
# Check files exist
ls -la /home/pi/ecosweep_manual_final.py
ls -la /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py

# Check services
sudo systemctl status ecosweep-yolo ecosweep-bridge

# Test stream
curl -I http://localhost:5000/video_feed

# View logs
sudo journalctl -u ecosweep-yolo -f
sudo journalctl -u ecosweep-bridge -f
```

---

*Document version: 1.0 | Covers production Pi deployment | Generated from Robot_newcontrol project*
