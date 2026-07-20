# Phase 3: Auto-Start on Raspberry Pi (Headless)

This guide explains how to run EcoSweep automatically when the Pi boots (e.g. when powered by battery, no monitor).

> **See also:** [ECOSWEEP-PI-COMPLETE-SETUP-GUIDE.md](ECOSWEEP-PI-COMPLETE-SETUP-GUIDE.md) — Complete file list, webcam autostart fix, and step-by-step verification.

---

## Prerequisites

- Raspberry Pi with Raspberry Pi OS
- USB webcam connected
- Arduino connected via USB
- Scripts deployed to the Pi (see **Deploy Files** below)

---

## Option 1: systemd Services (Recommended)

Two services: YOLO stream first, then bridge.

### Step 1: Deploy files to the Pi

On your Pi, create a project folder and copy the scripts. Example:

```bash
# On the Pi (or copy from your PC via SCP)
mkdir -p /home/pi/ecosweep/phase2
mkdir -p /home/pi/ecosweep/systemd
```

Copy these files (adjust paths if your layout differs):

| Source (on PC) | Destination (on Pi) |
|----------------|---------------------|
| `hardware/pi/phase2/yolo_fpv_stream_optimized.py` | `/home/pi/ecosweep/phase2/` |
| `hardware/pi/ecosweep_manual_final_patched.py` | `/home/pi/ecosweep/ecosweep_manual_final.py` |
| `hardware/pi/systemd/ecosweep-yolo.service` | `/home/pi/ecosweep/systemd/` |
| `hardware/pi/systemd/ecosweep-bridge.service` | `/home/pi/ecosweep/systemd/` |

**Important:** Rename `ecosweep_manual_final_patched.py` to `ecosweep_manual_final.py` on the Pi.

### Step 2: Adjust paths in the service files

Edit both service files and set `ECOSWEEP_DIR` to your actual folder:

```bash
nano /home/pi/ecosweep/systemd/ecosweep-yolo.service
```

Change:
```
Environment=ECOSWEEP_DIR=/home/pi/ecosweep
```
to your path if different (e.g. `/home/pi/ecosweep-phase2`).

Do the same for `ecosweep-bridge.service`.

### Step 3: Install and enable services

```bash
sudo cp /home/pi/ecosweep/systemd/ecosweep-yolo.service /etc/systemd/system/
sudo cp /home/pi/ecosweep/systemd/ecosweep-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-yolo.service
sudo systemctl enable ecosweep-bridge.service
```

### Step 4: Start services (or reboot)

```bash
sudo systemctl start ecosweep-yolo.service
sudo systemctl start ecosweep-bridge.service
```

Or reboot:
```bash
sudo reboot
```

### Step 5: Check status

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

## Option 2: Single startup script

Use `ecosweep_start.sh` if you prefer one script instead of systemd.

### Step 1: Deploy and make executable

```bash
# Copy ecosweep_start.sh to /home/pi/ecosweep/
chmod +x /home/pi/ecosweep/ecosweep_start.sh
```

### Step 2: Run at boot via rc.local

```bash
sudo nano /etc/rc.local
```

Add before `exit 0`:
```bash
su - pi -c "cd /home/pi/ecosweep && ./ecosweep_start.sh" &
```

Or use a systemd service that runs the script:

```ini
[Unit]
Description=EcoSweep All-in-One
After=network-online.target

[Service]
Type=simple
User=pi
Environment=ECOSWEEP_DIR=/home/pi/ecosweep
ExecStart=/home/pi/ecosweep/ecosweep_start.sh
WorkingDirectory=/home/pi/ecosweep
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Python environment

If you use a virtual environment (e.g. `yolov8-env`) for YOLO:

1. **systemd:** Change `ExecStart` to use the venv Python:
   ```
   ExecStart=/home/pi/yolov8-env/bin/python3 ${ECOSWEEP_DIR}/phase2/yolo_fpv_stream_optimized.py
   ```

2. **ecosweep_start.sh:** Change `python3` to the venv path:
   ```bash
   /home/pi/yolov8-env/bin/python3 phase2/yolo_fpv_stream_optimized.py &
   /home/pi/yolov8-env/bin/python3 ecosweep_manual_final.py
   ```

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| YOLO fails to start | `ls /dev/video0` — webcam present? `journalctl -u ecosweep-yolo.service` |
| Bridge fails | `ls /dev/ttyUSB0 /dev/ttyACM0` — Arduino present? Add `pi` to `dialout`: `sudo usermod -a -G dialout pi` |
| No detection file | YOLO must run first. Check YOLO service is up. `cat /tmp/ecosweep_detection.json` |
| Bluetooth not discoverable | Bridge resets Bluetooth on start. Wait ~10 s after boot before connecting from app. |

---

## Summary of steps on the Pi

1. Create `/home/pi/ecosweep/` and copy scripts (YOLO, bridge, systemd files).
2. Rename `ecosweep_manual_final_patched.py` → `ecosweep_manual_final.py`.
3. Edit service files: set `ECOSWEEP_DIR` to your path.
4. Install: `sudo cp .../systemd/*.service /etc/systemd/system/`
5. Enable: `sudo systemctl enable ecosweep-yolo ecosweep-bridge`
6. Reboot or `sudo systemctl start ecosweep-yolo ecosweep-bridge`.
