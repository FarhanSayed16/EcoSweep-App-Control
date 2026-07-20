# EcoSweep Pi — Start From Scratch

A clean, incremental plan. Complete each phase and **verify it works** before moving to the next.

---

## Overview

| Phase | Goal | When to proceed |
|-------|------|-----------------|
| **0** | Clean Pi, install basics | Before anything |
| **1** | Minimal Bluetooth bridge (app ↔ Arduino) | When app connects and motors move |
| **2** | Add YOLO + camera stream | When Phase 1 is stable |
| **3** | Add autonomy | When Phase 2 works |

---

# Phase 0: Clean and Prepare

## 0.1 Stop and remove old setup

On the Pi:

```bash
sudo systemctl stop ecosweep-bridge.service ecosweep-yolo.service 2>/dev/null
sudo systemctl disable ecosweep-bridge.service ecosweep-yolo.service 2>/dev/null
sudo rm -f /etc/systemd/system/ecosweep-*.service
sudo systemctl daemon-reload
```

## 0.2 Install packages

```bash
sudo apt-get update
sudo apt-get install -y pi-bluetooth bluez python3-bluez python3-serial
pip3 install pyserial
```

## 0.3 Add user to groups

```bash
sudo usermod -a -G bluetooth,dialout,video pi
```

Then **log out and log back in** (or reboot).

## 0.4 Physical setup

- [ ] Arduino connected via USB to Pi
- [ ] USB webcam connected (for Phase 2)
- [ ] Pi powered, SSH or monitor available

## 0.5 Verify devices

```bash
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
ls -la /dev/video0 2>/dev/null
```

You should see `/dev/ttyUSB0` or `/dev/ttyACM0` (Arduino) and `/dev/video0` (camera).

---

# Phase 1: Minimal Bluetooth Bridge

**Goal:** App connects, joystick moves the robot, connection stays stable.

## 1.1 Create folder and copy bridge

On your **PC**, copy this file to the Pi:

| PC path | Pi path |
|---------|---------|
| `hardware/pi/ecosweep_bridge_minimal.py` | `/home/pi/ecosweep_bridge_minimal.py` |

Using SCP (from PC, replace `YOUR_PI_IP` with your Pi’s address):

```bash
scp D:\Robot_newcontrol\hardware\pi\ecosweep_bridge_minimal.py YOUR_PI_IP:/home/pi/
```

Or create the file with nano on the Pi:

```bash
nano /home/pi/ecosweep_bridge_minimal.py
```

Paste the full contents of `ecosweep_bridge_minimal.py`, then Ctrl+O, Enter, Ctrl+X.

## 1.2 Pair phone (one-time)

On the Pi:

```bash
bluetoothctl
```

In bluetoothctl:

```
power on
discoverable on
pairable on
```

On the **phone**: Settings → Bluetooth → scan → pair with `raspberrypi` (PIN often 1234 or 0000).

Back in bluetoothctl:

```
devices
trust XX:XX:XX:XX:XX:XX
quit
```

Replace `XX:XX:XX:XX:XX:XX` with your phone’s MAC address from `devices`.

## 1.3 Run bridge manually

```bash
sudo systemctl restart bluetooth
sleep 8
sudo python3 -u /home/pi/ecosweep_bridge_minimal.py
```

Expected output:

```
EcoSweep Minimal Bridge starting...
Arduino OK: /dev/ttyUSB0
Waiting for Bluetooth connection...
```

## 1.4 Connect from app

1. Open the EcoSweep app on the phone.
2. Connect to the Pi.
3. You should see: `Connected.`
4. Move the joystick. The robot should move.
5. Leave it connected for at least 30 seconds.

**Verify:**
- [ ] App shows connected
- [ ] Joystick moves the robot
- [ ] Connection does not drop after 30 seconds

If it disconnects, check the terminal for error messages.

## 1.5 Install as service (optional, after manual test works)

**Option A** — Copy from PC:

```bash
scp hardware/pi/systemd/ecosweep-bridge-minimal.service pi@YOUR_PI_IP:/tmp/
# On Pi:
sudo cp /tmp/ecosweep-bridge-minimal.service /etc/systemd/system/ecosweep-bridge.service
```

**Option B** — Create manually:

```bash
sudo nano /etc/systemd/system/ecosweep-bridge.service
```

Paste:

```ini
[Unit]
Description=EcoSweep Bluetooth Bridge
After=bluetooth.target
Wants=bluetooth.target

[Service]
Type=simple
User=root
Environment=PYTHONUNBUFFERED=1
ExecStartPre=/bin/bash -c 'for i in $(seq 1 30); do [ -e /dev/ttyUSB0 ] || [ -e /dev/ttyACM0 ] && break; sleep 1; done'
ExecStart=/usr/bin/python3 -u /home/pi/ecosweep_bridge_minimal.py
WorkingDirectory=/home/pi
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-bridge.service
sudo systemctl start ecosweep-bridge.service
sudo systemctl status ecosweep-bridge.service
```

---

# Phase 2: Add YOLO and Camera Stream

**Prerequisite:** Phase 1 done. Bridge runs (manual or service). USB webcam connected.

Bridge and YOLO run as **separate processes** — no conflict. Bridge uses Bluetooth; YOLO uses camera + port 5000.

---

## 2.1 Copy YOLO script to Pi

| PC path | Pi path |
|---------|---------|
| `hardware/pi/phase2/yolo_fpv_stream_optimized.py` | `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py` |

On Pi:

```bash
mkdir -p /home/pi/ecosweep-phase2
```

From PC (replace `YOUR_PI_IP`):

```bash
scp D:\Robot_newcontrol\hardware\pi\phase2\yolo_fpv_stream_optimized.py pi@YOUR_PI_IP:/home/pi/ecosweep-phase2/
```

Or use nano on Pi and paste the file contents.

---

## 2.2 Install YOLO dependencies

```bash
pip3 install opencv-python-headless flask ultralytics
```

First run may download `yolov8n.pt` (~6MB).

---

## 2.3 Run YOLO manually (verify first)

**In a new terminal/SSH session** (bridge keeps running in the other):

```bash
python3 /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py
```

On your PC or phone browser: `http://YOUR_PI_IP:5000/video_feed`

**Verify:**
- [ ] Video stream loads
- [ ] Detection boxes on bottle, cup, etc.
- [ ] Bridge still connected to app in the other terminal

Press Ctrl+C to stop YOLO when done testing.

---

## 2.4 Install YOLO as a service (auto-start)

```bash
sudo nano /etc/systemd/system/ecosweep-yolo.service
```

Paste:

```ini
[Unit]
Description=EcoSweep YOLO Stream
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
ExecStartPre=/bin/bash -c 'for i in $(seq 1 60); do [ -e /dev/video0 ] && break; sleep 1; done; sleep 3'
ExecStart=/usr/bin/python3 -u /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py
WorkingDirectory=/home/pi/ecosweep-phase2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-yolo.service
sudo systemctl start ecosweep-yolo.service
sudo systemctl status ecosweep-yolo.service
```

---

## 2.5 Run bridge and YOLO together

- **Bridge:** `sudo python3 -u /home/pi/ecosweep_bridge_minimal.py` (manual) or `sudo systemctl start ecosweep-bridge.service` (if installed).
- **YOLO:** `sudo systemctl start ecosweep-yolo.service`.

Both can run at the same time. App connects via bridge; camera stream via `http://PI_IP:5000/video_feed`.

---

# Phase 3: Add Autonomy

**Proceed only when Phase 2 works.**

Replace the minimal bridge with the full bridge that includes autonomy:

| PC path | Pi path |
|---------|---------|
| `hardware/pi/ecosweep_manual_final_patched.py` | `/home/pi/ecosweep_manual_final.py` |

Update the bridge service to use the full script:

```bash
sudo nano /etc/systemd/system/ecosweep-bridge.service
```

Change `ExecStart` to:

```
ExecStart=/usr/bin/python3 -u /home/pi/ecosweep_manual_final.py
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ecosweep-bridge.service
```

---

# File Reference

## Files to copy (PC → Pi)

| Phase | PC file | Pi path |
|-------|---------|---------|
| 1 | `hardware/pi/ecosweep_bridge_minimal.py` | `/home/pi/ecosweep_bridge_minimal.py` |
| 2 | `hardware/pi/phase2/yolo_fpv_stream_optimized.py` | `/home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py` |
| 3 | `hardware/pi/ecosweep_manual_final_patched.py` | `/home/pi/ecosweep_manual_final.py` |

## Service files

Created directly on Pi in `/etc/systemd/system/` (see Phase 1.5 and 2.4).

---

# Troubleshooting

| Issue | Action |
|-------|--------|
| "Address already in use" | `sudo systemctl restart bluetooth` then wait 10 s |
| App won't connect | Run `trust [PHONE_MAC]` in bluetoothctl; unpair/repair on phone |
| Arduino not found | Check USB cable; `ls /dev/ttyUSB*` |
| Camera not found | `ls /dev/video*`; ensure `pi` in `video` group |
| Bridge crashes | Run manually: `sudo python3 -u /home/pi/ecosweep_bridge_minimal.py` and watch output |

---

# Quick Start (After Full Setup)

```bash
sudo systemctl start ecosweep-bridge.service
sudo systemctl start ecosweep-yolo.service
```

Wait ~20 seconds, then connect from the app.
