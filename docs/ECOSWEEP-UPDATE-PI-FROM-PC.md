# Update EcoSweep on Raspberry Pi from Your PC

Quick guide to push the updated bridge script from your computer to the Pi and restart the service.

---

## 1. One-Line SCP (Recommended)

From **PowerShell** or **Command Prompt** on your PC:

```powershell
scp D:\Robot_newcontrol\hardware\pi\ecosweep_manual_final_patched.py pi@YOUR_PI_IP:/home/pi/ecosweep_manual_final.py
```

Replace `YOUR_PI_IP` with your Pi's IP (e.g. `10.148.140.158`).

**Example:**
```powershell
scp D:\Robot_newcontrol\hardware\pi\ecosweep_manual_final_patched.py pi@10.148.140.158:/home/pi/ecosweep_manual_final.py
```

---

## 2. Restart the Bridge Service

After copying, SSH into the Pi and restart the bridge:

```bash
ssh pi@YOUR_PI_IP
sudo systemctl restart ecosweep-bridge
```

Or in one command from PC (PowerShell):

```powershell
ssh pi@10.148.140.158 "sudo systemctl restart ecosweep-bridge"
```

---

## 3. Full Copy + Restart (One Script)

From **PowerShell** on your PC:

```powershell
$PI_IP = "10.148.140.158"   # <-- Change this to your Pi IP
scp D:\Robot_newcontrol\hardware\pi\ecosweep_manual_final_patched.py "pi@${PI_IP}:/home/pi/ecosweep_manual_final.py"
ssh "pi@${PI_IP}" "sudo systemctl restart ecosweep-bridge; sudo systemctl status ecosweep-bridge"
```

---

## 4. Watch Debug Logs (Optional)

After restart, watch the autonomy debug output when AUTO is on:

```bash
ssh pi@YOUR_PI_IP
sudo journalctl -u ecosweep-bridge -f
```

Look for lines like:
```
AUTO APPROACH_FAR bbox_cx=280 fc=320 err=-40 turn=-35 area=25000
```

- `bbox_cx` = object center X in frame
- `fc` = frame center (320)
- `err` = bbox_cx - fc (negative = object left, positive = object right)
- `turn` = value sent to Arduino (negative = turn left, positive = turn right)

---

## 5. If Robot Still Turns Wrong Way

Edit on the Pi:

```bash
nano /home/pi/ecosweep_manual_final.py
```

Find (around lines 77–78):

```python
TURN_LEFT_SIGN = -1
TURN_RIGHT_SIGN = -1
```

**Try:**
- Both `1` (original)
- Left `-1`, right `1`
- Left `1`, right `-1`
- Both `1` and also flip `TURN_SIGN` in Arduino if needed

Save (Ctrl+O, Enter), exit (Ctrl+X), then:

```bash
sudo systemctl restart ecosweep-bridge
```

---

## 6. Turn Off Debug Logging

When behavior looks correct, disable verbose logs:

```python
DEBUG_AUTONOMY = False
```

Then copy the file again and restart.
