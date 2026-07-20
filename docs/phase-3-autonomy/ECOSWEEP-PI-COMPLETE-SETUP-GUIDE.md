# EcoSweep Pi — Complete Setup Guide

**Updated.** Use this file to deploy or replace files on the Pi.

> **Files in different locations?** See [ECOSWEEP-PI-FIX-LAYOUT.md](ECOSWEEP-PI-FIX-LAYOUT.md) for your layout (bridge in `/home/pi/`, YOLO in `ecosweep-phase2/`).

---

## Part 1: Files to Replace / Paste on Pi

| PC Path | Pi Path |
|---------|---------|
| `D:\Robot_newcontrol\hardware\pi\ecosweep_manual_final_patched.py` | `/home/pi/ecosweep/ecosweep_manual_final.py` |
| `D:\Robot_newcontrol\hardware\pi\phase2\yolo_fpv_stream_optimized.py` | `/home/pi/ecosweep/phase2/yolo_fpv_stream_optimized.py` |
| `D:\Robot_newcontrol\hardware\pi\systemd\ecosweep-yolo.service` | `/home/pi/ecosweep/systemd/ecosweep-yolo.service` |
| `D:\Robot_newcontrol\hardware\pi\systemd\ecosweep-bridge.service` | `/home/pi/ecosweep/systemd/ecosweep-bridge.service` |

**Included:** Autonomy improvements (proportional steering, speed tiers, arm pickup, obstacle avoidance) and smoother FPV stream (separate capture/YOLO threads).

---

## Part 2: Nano Commands (Create Folders & Open Files)

Run on the Pi:

```bash
mkdir -p /home/pi/ecosweep/phase2
mkdir -p /home/pi/ecosweep/systemd

nano /home/pi/ecosweep/ecosweep_manual_final.py
nano /home/pi/ecosweep/phase2/yolo_fpv_stream_optimized.py
nano /home/pi/ecosweep/systemd/ecosweep-yolo.service
nano /home/pi/ecosweep/systemd/ecosweep-bridge.service
```

For each file: paste the full content, then **Ctrl+O**, **Enter**, **Ctrl+X**.

---

## Part 3: One-Time Setup (If Not Done Yet)

```bash
sudo usermod -a -G dialout pi
sudo usermod -a -G video pi
pip3 install opencv-python-headless flask ultralytics
```

Then log out and back in (or reboot).

---

## Part 4: Install Autostart & Enable Services

```bash
sudo cp /home/pi/ecosweep/systemd/ecosweep-yolo.service /etc/systemd/system/
sudo cp /home/pi/ecosweep/systemd/ecosweep-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-yolo.service ecosweep-bridge.service
sudo systemctl start ecosweep-yolo.service ecosweep-bridge.service
```

---

## Part 5: After Replacing Files — Restart Services

If you already have the setup and only **replaced** the Python files:

```bash
sudo systemctl restart ecosweep-yolo.service
sudo systemctl restart ecosweep-bridge.service
```

---

## Part 6: Verify

```bash
sudo systemctl status ecosweep-yolo.service
sudo systemctl status ecosweep-bridge.service
```

YOLO stream: `http://<PI_IP>:5000/video_feed`

---

## Part 7: Debug (If Issues)

If Bluetooth disconnects, webcam fails, or detection doesn't work:  
**[ECOSWEEP-PI-DEBUG-GUIDE.md](ECOSWEEP-PI-DEBUG-GUIDE.md)** — run diagnostic commands, collect output, and share for diagnosis.
