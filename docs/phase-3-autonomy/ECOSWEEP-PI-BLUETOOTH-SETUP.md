# EcoSweep Pi — Bluetooth SPP Setup

If the app shows "useable service is not available" or cannot connect, complete these steps on the Pi.

---

## Step 1: Install Bluetooth Packages

```bash
sudo apt-get update
sudo apt-get install -y pi-bluetooth bluez python3-bluez
```

---

## Step 2: Add Pi User to Bluetooth Group

```bash
sudo usermod -a -G bluetooth pi
```

Log out and back in (or reboot) for this to take effect.

---

## Step 3: Enable SPP (Serial Port Profile) Before Bridge Starts

Run once manually, or add to a startup script:

```bash
sudo sdptool add SP
sudo hciconfig hci0 piscan
```

---

## Step 4: Pair the Phone and Trust (Important)

1. On the **phone**: Open Settings → Bluetooth → turn on.
2. On the **Pi**: run `bluetoothctl`, then:
   ```
   power on
   discoverable on
   pairable on
   ```
3. On the **phone**: Scan for devices, find "raspberrypi" (or your Pi name), tap to pair. Enter PIN if asked (often 1234 or 0000).
4. After pairing, on the **Pi** in bluetoothctl:
   ```
   devices
   trust XX:XX:XX:XX:XX:XX
   ```
   Replace with your phone's MAC address from the `devices` list. **Trust** lets the phone reconnect without asking every time.
5. Type `quit` to exit bluetoothctl.

---

## Step 5: Update Bridge Script

The bridge must advertise the SPP service so the phone can connect. The updated `ecosweep_manual_final_patched.py` includes `bluetooth.advertise_service()`. Copy the latest version to the Pi:

- From PC: `hardware/pi/ecosweep_manual_final_patched.py`
- To Pi: `/home/pi/ecosweep_manual_final.py`

---

## Step 6: Restart Bridge Service

```bash
sudo systemctl restart ecosweep-bridge.service
```

**Important**: Only one process can use the Bluetooth RFCOMM port at a time. If you run the bridge **manually** for debugging, first stop the service:

```bash
sudo systemctl stop ecosweep-bridge.service
sudo python3 /home/pi/ecosweep_manual_final.py
```

When done debugging, start the service again: `sudo systemctl start ecosweep-bridge.service`

---

## Step 7: Wait Before Connecting

After the Pi boots or after restarting the bridge, wait **~15–20 seconds** before opening the app and connecting. Bluetooth needs time to advertise the SPP service.

---

## Troubleshooting

| Issue | Try |
|-------|-----|
| "Service not available" | Ensure bridge has `advertise_service()` and SPP UUID. Run `sudo sdptool add SP` on Pi. |
| Phone doesn't see Pi | `sudo hciconfig hci0 piscan` on Pi. Check Bluetooth is on. |
| Pairing fails | Unpair on both devices, then pair again. Try PIN 1234 or 0000. |
| Connects then instantly disconnects | Bridge now uses two threads (app↔Arduino, Arduino↔app) so telemetry streams continuously. Update to latest `ecosweep_manual_final_patched.py`. Ensure Arduino is connected. Run `trust [PHONE_MAC]` in bluetoothctl. |
| **"Address already in use" (Errno 98)** | (1) Stop the service: `sudo systemctl stop ecosweep-bridge.service`. (2) The bridge uses RFCOMM **channel 2** (channel 1 is often held by bluetoothd). Update to latest `ecosweep_manual_final_patched.py`. (3) If still failing, restart Bluetooth and try: `sudo systemctl restart bluetooth` then wait 10 sec before running the script. |
| **Disconnects after a few movements** | Bridge throttles telemetry to ~10 Hz to avoid Bluetooth overload. Update to latest `ecosweep_manual_final_patched.py`. After disconnect, wait 2–3 sec before reconnecting. |
| **Nothing detected / webcam poor** | Ensure YOLO service runs: `sudo systemctl status ecosweep-yolo.service`. If "Cannot open camera", plug USB webcam before boot or run `ls /dev/video*` to verify device. Detection needs objects in GARBAGE_CLASSES (bottle, cup, etc.). |

---

## Verify SPP is Advertised

On the Pi:

```bash
sdptool browse local
```

Look for "Serial Port" in the output. If it's missing, run `sudo sdptool add SP` and restart the bridge.
