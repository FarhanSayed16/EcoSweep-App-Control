# EcoSweep Pi — Debug & Verification Guide

Run these commands on your **Raspberry Pi** and paste the output. This will help identify why Bluetooth disconnects, webcam/detection fails, or the app doesn't connect.

---

## Fixes Applied (From Your Debug Output)

| Finding | Fix |
|--------|-----|
| No logs during manual run | Added verbose `_log()` with flush; use `python3 -u` for unbuffered output |
| Reset on every disconnect harms reconnection | Reset Bluetooth only every 5th disconnect |
| Telemetry may overload Bluetooth | Increased throttle to 0.15 s (~6–7 Hz) |
| Output buffered in systemd | Added `Environment=PYTHONUNBUFFERED=1` and `python3 -u` in service |
| Channel 2 in use after stopping service | Switched to **RFCOMM channel 3**; restart Bluetooth before manual run |
| Connects then disconnects after movement | **Keepalive** sends DATA:SENSORS when Arduino silent; **M: throttled** to ~12 Hz to avoid Arduino buffer overflow; **Run as root** for Bluetooth stability |

---

## Section 1: Basic System Info

Run and paste the full output:

```bash
echo "=== PI OS ==="
uname -a
echo ""
echo "=== PYTHON ==="
python3 --version
pip3 list | grep -E "bluetooth|serial|flask|opencv|ultralytics" 2>/dev/null || echo "pip packages not found"
echo ""
echo "=== BLUETOOTH DEVICE ==="
hciconfig -a
echo ""
echo "=== SPP ADVERTISED ==="
sdptool browse local 2>/dev/null | head -40
```

---

## Section 2: Services Status

```bash
echo "=== ECOSWEEP BRIDGE ==="
sudo systemctl status ecosweep-bridge.service
echo ""
echo "=== ECOSWEEP YOLO ==="
sudo systemctl status ecosweep-yolo.service
echo ""
echo "=== BLUETOOTH SERVICE ==="
sudo systemctl status bluetooth
```

---

## Section 3: Bridge Logs (Last 50 lines)

```bash
echo "=== BRIDGE JOURNAL (last 50 lines) ==="
sudo journalctl -u ecosweep-bridge.service -n 50 --no-pager
```

---

## Section 4: YOLO Logs (Last 50 lines)

```bash
echo "=== YOLO JOURNAL (last 50 lines) ==="
sudo journalctl -u ecosweep-yolo.service -n 50 --no-pager
```

---

## Section 5: Camera & Serial Devices

```bash
echo "=== USB DEVICES ==="
lsusb
echo ""
echo "=== VIDEO DEVICES ==="
ls -la /dev/video* 2>/dev/null || echo "No /dev/video* found"
echo ""
echo "=== SERIAL (Arduino) ==="
ls -la /dev/ttyUSB* /dev/ttyACM* /dev/ttyAMA* 2>/dev/null || echo "No Arduino serial ports found"
echo ""
echo "=== VIDEO GROUP ==="
groups pi
id pi
```

---

## Section 6: File Locations & Versions

```bash
echo "=== BRIDGE FILE ==="
ls -la /home/pi/ecosweep_manual_final.py 2>/dev/null || echo "File not found"
head -25 /home/pi/ecosweep_manual_final.py 2>/dev/null | head -25
echo ""
echo "=== YOLO FILE ==="
ls -la /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py 2>/dev/null || echo "File not found"
echo ""
echo "=== DETECTION FILE (YOLO output) ==="
ls -la /tmp/ecosweep_detection.json 2>/dev/null || echo "Detection file not found"
cat /tmp/ecosweep_detection.json 2>/dev/null || echo "Cannot read"
```

---

## Section 7: Live Test (Optional — Run When App Disconnects)

If the app disconnects after a few movements, run this **immediately after** a disconnect to capture bridge logs:

```bash
echo "=== BRIDGE LOGS AFTER DISCONNECT ==="
sudo journalctl -u ecosweep-bridge.service -n 80 --no-pager
```

---

## Section 8: Manual Bridge Run (If Service Fails)

Stop services. **If you get "Address already in use" even after stopping**, restart Bluetooth first:

```bash
sudo systemctl stop ecosweep-bridge.service
sudo systemctl stop ecosweep-yolo.service
sudo systemctl restart bluetooth
sleep 10
echo "Now: 1) Connect from app 2) Move joystick 3) Wait for disconnect 4) Ctrl+C"
sudo python3 -u /home/pi/ecosweep_manual_final.py 2>&1 | tee /tmp/bridge_manual.log
```

Expected output when working: `Serial Port service registered` → `Waiting for Bluetooth connection...` → `Connected. Starting app/arduino threads.` → (after disconnect) `App->Arduino thread stopped.` or `Arduino->App thread stopped.` → `Disconnected (count=1). Cleaning up.`

After it disconnects or you press Ctrl+C, paste:

```bash
cat /tmp/bridge_manual.log
```

---

## Section 9: Bluetooth Pairing / Trust

```bash
echo "=== PAIRED DEVICES ==="
bluetoothctl devices
echo ""
echo "=== TRUSTED DEVICES ==="
bluetoothctl devices Trusted
```

---

## Section 10: One-Liner (All Sections Combined)

If you prefer to run everything at once and save to a file:

```bash
{
  echo "=== SECTION 1: SYSTEM ==="
  uname -a
  python3 --version
  hciconfig -a
  echo ""
  echo "=== SECTION 2: SERVICES ==="
  sudo systemctl status ecosweep-bridge.service
  sudo systemctl status ecosweep-yolo.service
  echo ""
  echo "=== SECTION 3: BRIDGE LOGS ==="
  sudo journalctl -u ecosweep-bridge.service -n 50 --no-pager
  echo ""
  echo "=== SECTION 4: YOLO LOGS ==="
  sudo journalctl -u ecosweep-yolo.service -n 50 --no-pager
  echo ""
  echo "=== SECTION 5: DEVICES ==="
  lsusb
  ls -la /dev/video* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
  groups pi
  echo ""
  echo "=== SECTION 6: FILES ==="
  ls -la /home/pi/ecosweep_manual_final.py /home/pi/ecosweep-phase2/yolo_fpv_stream_optimized.py
  cat /tmp/ecosweep_detection.json 2>/dev/null
  echo ""
  echo "=== SECTION 7: BLUETOOTH ==="
  bluetoothctl devices
} 2>&1 | tee /home/pi/ecosweep_debug_output.txt
echo "Output saved to /home/pi/ecosweep_debug_output.txt"
```

Then copy the file to your PC (e.g. with SCP) or paste its contents:

```bash
cat /home/pi/ecosweep_debug_output.txt
```

---

## What to Send Back

1. Paste the full output from **Section 10** (or Sections 1–9 individually).
2. Describe exactly what happens:
   - Does the app connect at all?
   - How long until it disconnects? (e.g. after 2 joystick movements)
   - Does the webcam stream load in the app?
   - Do you see any detections (e.g. bottle/cup)?
3. If you ran the **manual bridge test** (Section 8), paste the `bridge_manual.log` contents.

---

## Quick Checklist Before Sending

- [ ] Bluetooth paired and trusted (`bluetoothctl trust <MAC>`)
- [ ] Arduino connected via USB before Pi boot
- [ ] USB webcam connected before Pi boot
- [ ] Bridge uses RFCOMM channel 2 (in `ecosweep_manual_final.py`)
- [ ] Latest `ecosweep_manual_final_patched.py` copied to `/home/pi/ecosweep_manual_final.py`
