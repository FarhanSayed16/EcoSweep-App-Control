# EcoSweep Pi — Fix Layout & Verify

Your Pi has files in different folders. This guide helps you verify what exists and set things up correctly.

> **Too many folders?** See [ECOSWEEP-PI-CLEANUP.md](ECOSWEEP-PI-CLEANUP.md) to archive old files and clean up.

---

## Step 1: Verify What You Have on the Pi

Run these on the Pi (SSH or terminal):

```bash
# Check bridge file
ls -la /home/pi/ecosweep_manual_final.py

# Check YOLO file
ls -la /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py

# List all ecosweep-related folders in home
ls -la /home/pi/ | grep -E "ecosweep|ecosweep"

# Find all ecosweep files
find /home/pi -name "*ecosweep*" -o -name "yolo_fpv*" 2>/dev/null
```

---

## Step 2: Your Actual Layout (What You Said)

| File | Your Path |
|------|-----------|
| Bridge | `/home/pi/ecosweep_manual_final.py` |
| YOLO | `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py` |
| systemd | Does not exist yet |

---

## Step 3: Option A — Keep Your Layout (Recommended)

Use your existing paths. Create systemd services that point to them.

### 3.1 Create systemd folder

```bash
mkdir -p /home/pi/ecosweep-phase2/systemd
```

### 3.2 Create YOLO service file

```bash
nano /home/pi/ecosweep-phase2/systemd/ecosweep-yolo.service
```

Paste this (paths match your layout):

```ini
[Unit]
Description=EcoSweep YOLO FPV Stream (webcam + detection)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
ExecStartPre=/bin/bash -c 'for i in $(seq 1 60); do [ -e /dev/video0 ] && break; sleep 1; done; sleep 5'
ExecStart=/usr/bin/python3 /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py
WorkingDirectory=/home/pi/ecosweep-phase2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Save: Ctrl+O, Enter, Ctrl+X.

### 3.3 Create Bridge service file

```bash
nano /home/pi/ecosweep-phase2/systemd/ecosweep-bridge.service
```

Paste this:

```ini
[Unit]
Description=EcoSweep Bridge (Bluetooth + Arduino + Autonomy)
After=network-online.target ecosweep-yolo.service
Wants=network-online.target

[Service]
Type=simple
User=pi
ExecStartPre=/bin/bash -c 'for i in $(seq 1 30); do [ -e /dev/ttyUSB0 ] || [ -e /dev/ttyACM0 ] && break; sleep 1; done'
ExecStart=/usr/bin/python3 /home/pi/ecosweep_manual_final.py
WorkingDirectory=/home/pi
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Save: Ctrl+O, Enter, Ctrl+X.

### 3.4 Install and enable services

```bash
sudo cp /home/pi/ecosweep-phase2/systemd/ecosweep-yolo.service /etc/systemd/system/
sudo cp /home/pi/ecosweep-phase2/systemd/ecosweep-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-yolo.service ecosweep-bridge.service
sudo systemctl start ecosweep-yolo.service ecosweep-bridge.service
```

---

## Step 4: Where to Put Updated Files from PC

| Copy from PC | Paste to Pi |
|--------------|-------------|
| `hardware/pi/ecosweep_manual_final_patched.py` | `/home/pi/ecosweep_manual_final.py` |
| `hardware/pi/phase2/yolo_fpv_stream_optimized.py` | `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py` |

Replace the contents of those two files (via nano, SCP, or USB) with the latest versions from your PC.

---

## Step 5: Nano Commands for Your Layout

```bash
nano /home/pi/ecosweep_manual_final.py
nano /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py
```

Open each, paste the full content from your PC, then Ctrl+O, Enter, Ctrl+X.

---

## Step 6: Restart After Replacing Files

```bash
sudo systemctl restart ecosweep-yolo.service
sudo systemctl restart ecosweep-bridge.service
```

---

## Step 7: Verify It Works

```bash
sudo systemctl status ecosweep-yolo.service
sudo systemctl status ecosweep-bridge.service
```

Both should show `active (running)`.

YOLO stream: `http://<PI_IP>:5000/video_feed`

---

## Option B — Consolidate Into One Folder (If You Prefer)

If you want everything under `/home/pi/ecosweep/`:

```bash
mkdir -p /home/pi/ecosweep/phase2
mv /home/pi/ecosweep_manual_final.py /home/pi/ecosweep/
mv /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py /home/pi/ecosweep/phase2/
```

Then use the standard service files from `ECOSWEEP-PI-COMPLETE-SETUP-GUIDE.md` with `ECOSWEEP_DIR=/home/pi/ecosweep`.

---

## Summary

| What | Where |
|------|-------|
| Bridge | `/home/pi/ecosweep_manual_final.py` |
| YOLO | `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py` |
| Service files | `/home/pi/ecosweep-phase2/systemd/` (create them) |
