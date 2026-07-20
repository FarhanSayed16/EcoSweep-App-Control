# Phase 1: Camera Module — Full Guide

This guide walks you through getting a **USB webcam** on your **Raspberry Pi** streaming to the **EcoSweep app** FPV screen. Follow the steps in order. If you hit any issue, note the step number and the error message so we can fix it.

---

## What You Need Before Starting

- **Raspberry Pi** (e.g. Pi 4) with Raspberry Pi OS (Bullseye/Bookworm), connected to power and network (Wi‑Fi or Ethernet).
- **USB webcam** that works on Linux (most UVC webcams do).
- **Real VNC** (or SSH) so you can use the Pi desktop or terminal from your PC.
- **Phone** with the EcoSweep app installed.
- **Same Wi‑Fi network** for Pi and phone (so the phone can open `http://<PI_IP>:port/...`).

---

## Step 1: Connect the USB Webcam and Verify on the Pi

### 1.1 Plug in the webcam

- Connect the USB webcam to the Raspberry Pi.
- Power on the Pi (or wait for it to boot) and connect via **Real VNC** (or SSH).

### 1.2 Check that the system sees the webcam

Open a **terminal** on the Pi (from VNC: Menu → Accessories → Terminal, or via SSH).

Run:

```bash
ls /dev/video*
```

You should see at least one device, e.g.:

- `/dev/video0` — usually the camera.
- Sometimes `/dev/video1` etc. for metadata; the first one is typically the one to use.

If you see nothing, try:

- Unplug and replug the webcam.
- Use a different USB port (prefer USB 2.0 or a powered hub if the Pi struggles).
- Run: `dmesg | tail -20` and look for errors mentioning the camera or USB.

### 1.3 Install v4l-utils (optional but useful)

```bash
sudo apt update
sudo apt install -y v4l-utils
```

List camera details:

```bash
v4l2-ctl --list-devices
```

You should see your webcam name and something like `/dev/video0`. Note the device (e.g. `/dev/video0`); we’ll use it in the next step.

---

## Step 2: Choose How to Stream (Option A or B)

You can use either:

- **Option A: mjpg-streamer** — lightweight, MJPEG only, quick to get running.
- **Option B: Flask + OpenCV** — same stack you’ll use for AI in Phase 2; one script does capture + HTTP stream.

Pick **one** and follow only that option.

---

### Option A: mjpg-streamer

#### A.1 Install mjpg-streamer

On the Pi:

```bash
sudo apt update
sudo apt install -y cmake libjpeg-dev
```

mjpg-streamer is often not in the default repos, so build from source:

```bash
cd ~
git clone https://github.com/jacksonliam/mjpg-streamer.git
cd mjpg-streamer/mjpg-streamer-experimental
make -j4
sudo make install
```

If `make` fails, install any missing packages it asks for (e.g. `libjpeg8-dev`).

#### A.2 Run the stream

Use your actual video device (e.g. `/dev/video0`). Example for port **8080**:

```bash
cd ~/mjpg-streamer/mjpg-streamer-experimental
./mjpg_streamer -i "input_uvc.so -d /dev/video0 -r 640x480 -f 15" -o "output_http.so -p 8080 -w ./www"
```

- `-d /dev/video0` — your camera device.
- `-r 640x480 -f 15` — resolution and framerate (adjust if the camera doesn’t support these).
- `-p 8080` — HTTP port.

Leave this terminal open. The stream will be:

- **Single JPEG snapshot:** `http://<PI_IP>:8080/?action=snapshot`
- **MJPEG stream:** `http://<PI_IP>:8080/?action=stream`

**Stream URL for the app:** `http://<PI_IP>:8080/?action=stream`  
Replace `<PI_IP>` with your Pi’s IP (see Step 3).

#### A.3 If the camera doesn’t work with input_uvc

Try without resolution/fps:

```bash
./mjpg_streamer -i "input_uvc.so -d /dev/video0" -o "output_http.so -p 8080 -w ./www"
```

Or try `/dev/video1` if you have multiple video devices.

---

### Option B: Flask + OpenCV (good for later AI)

This uses the same Python stack (OpenCV) you’ll use in Phase 2.

#### B.1 Install Python and dependencies

On the Pi:

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv libopencv-dev
pip3 install flask
```

(Use `pip3 install --user flask` if you get permission errors.)

#### B.2 Create the camera stream script

Create a folder for Phase 1 scripts (you can put it in your project or home):

```bash
mkdir -p ~/ecosweep-phase1
cd ~/ecosweep-phase1
```

Create the file. You can either:

**Option 1 — Copy from the project:** If you have the EcoSweep repo on the Pi (or copy the file over), use the script at `hardware/pi/camera_stream.py`. Copy it to `~/ecosweep-phase1/camera_stream.py`.

**Option 2 — Create manually:**

```bash
nano camera_stream.py
```

Paste the following. Change `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` if your camera is on `/dev/video1`.

```python
# camera_stream.py - Serves MJPEG stream from USB webcam for EcoSweep FPV
import cv2
from flask import Flask, Response

app = Flask(__name__)

def get_camera():
    cap = cv2.VideoCapture(0)  # 0 = /dev/video0
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam. Check /dev/video0 and permissions.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    return cap

def generate_frames():
    cap = get_camera()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, buf = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
    finally:
        cap.release()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '<html><body><img src="/video_feed" /></body></html>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

Save and exit (in nano: Ctrl+O, Enter, Ctrl+X).

#### B.3 Run the Flask stream

```bash
cd ~/ecosweep-phase1
python3 camera_stream.py
```

Leave this running. You should see something like:

- `Running on http://0.0.0.0:5000/`

**Stream URL for the app:** `http://<PI_IP>:5000/video_feed`  
Replace `<PI_IP>` with your Pi’s IP (Step 3).

#### B.4 Test in a browser (on your PC)

On a computer on the same network, open:

- `http://<PI_IP>:5000/video_feed`

You should see the live camera image. If you get “Cannot open webcam,” check:

- `ls /dev/video*` and use the correct index in `cv2.VideoCapture(0)` or `(1)`.
- Run with: `sudo python3 camera_stream.py` only if needed for permissions (normally not required).

---

## Step 3: Find the Pi’s IP Address

On the Pi, run:

```bash
hostname -I
```

The first number is the Pi’s IP, e.g. `192.168.1.50` or `10.0.0.25`.

Use this IP in the stream URL:

- **Option A (mjpg-streamer):** `http://192.168.1.50:8080/?action=stream`
- **Option B (Flask):** `http://192.168.1.50:5000/video_feed`

### Firewall (if stream doesn’t load on phone)

If the phone cannot open the URL, allow the port on the Pi:

```bash
sudo ufw allow 8080    # for mjpg-streamer
# or
sudo ufw allow 5000    # for Flask
sudo ufw reload
```

If `ufw` is not enabled, the ports are usually open by default.

---

## Step 4: Configure the App (Phone)

### 4.1 Open the EcoSweep app

On your phone (same Wi‑Fi as the Pi), open the EcoSweep app.

### 4.2 Set the Camera Stream URL

1. Go to the **Settings** tab (last tab in the bottom bar).
2. Find **“Camera Stream URL”** (or “Camera Settings”).
3. Enter the stream URL you built in Step 3, e.g.:
   - `http://192.168.1.50:8080/?action=stream` (mjpg-streamer), or  
   - `http://192.168.1.50:5000/video_feed` (Flask).
4. Save or leave the field (the app may save automatically).

### 4.3 FPV screen URL (if needed)

The **FPV** tab may have its own URL field or a hardcoded default. If the FPV screen doesn’t show your stream:

- Look for a URL input on the FPV screen and set it to the **same** URL as in Settings.
- Or, in the app code, the FPV screen might use a default like `http://10.96.89.158:5000/video_feed` — change that to your Pi IP and port, or we can later make FPV read the URL from Settings.

---

## Step 5: Test End-to-End

1. **Pi:** Make sure the stream is running (mjpg-streamer **or** Flask terminal still open).
2. **Phone:** Connect to the robot via **Bluetooth** (Settings → connect to the Pi/robot).
3. **Phone:** Open the **FPV** tab.
4. You should see the **live image from the USB webcam**.  
   - If you see “Connecting…” or a broken image, go to **Troubleshooting** below.

**Phase 1 is done when:** You see a stable live feed from the USB webcam in the app FPV screen.

---

## Troubleshooting

### “No such file or directory” for /dev/video0

- Run `ls /dev/video*`. Use the device you see (e.g. `/dev/video1`) in the stream command or in `camera_stream.py` as `cv2.VideoCapture(1)`.
- Ensure the webcam is plugged in and the Pi has booted fully.

### “Cannot open webcam” (Flask/OpenCV)

- Try `cv2.VideoCapture(0)` then `(1)`. One of them should be the camera.
- Check permissions: `groups` and add your user to `video` if needed:  
  `sudo usermod -aG video $USER`  
  Then log out and back in (or reboot).

### Stream works in browser on PC but not on phone

- Confirm phone and Pi are on the **same Wi‑Fi** (not guest network).
- Confirm the URL on the phone uses the **correct Pi IP** and port (8080 or 5000).
- Try opening the same URL in the phone’s browser (e.g. Chrome). If it works there but not in the app, the issue is likely the URL the app is using (check Settings and FPV screen).

### App shows “Please connect to a device first” on FPV

- The FPV screen may require a **Bluetooth connection** to the robot before showing the stream. Connect to the robot in Settings first, then open FPV.

### mjpg_streamer: “input_uvc.so: error opening device”

- Use `-d /dev/video0` (or the device from `ls /dev/video*`).
- Try without `-r` and `-f`:  
  `./mjpg_streamer -i "input_uvc.so -d /dev/video0" -o "output_http.so -p 8080 -w ./www"`.

### Port 5000 or 8080 already in use

- Stop the other program using that port, or use a different port (e.g. 5001) and update the URL in the app accordingly.

### Stream is very slow or laggy

- Lower resolution in mjpg-streamer (e.g. `-r 320x240`) or in `camera_stream.py` (e.g. 320x240).
- Reduce FPS (e.g. 10) in the stream script.

---

## Optional: Run the Stream at Boot (Pi)

So you don’t have to start the stream manually each time:

### For mjpg-streamer (systemd)

Create a service file:

```bash
sudo nano /etc/systemd/system/mjpg-streamer.service
```

Paste (adjust paths and device if needed):

```ini
[Unit]
Description=MJPEG Streamer for EcoSweep
After=network.target

[Service]
Type=simple
ExecStart=/home/pi/mjpg-streamer/mjpg-streamer-experimental/mjpg_streamer -i "input_uvc.so -d /dev/video0" -o "output_http.so -p 8080 -w /home/pi/mjpg-streamer/mjpg-streamer-experimental/www"
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mjpg-streamer
sudo systemctl start mjpg-streamer
```

### For Flask (systemd)

```bash
sudo nano /etc/systemd/system/ecosweep-camera.service
```

Paste (adjust path and user):

```ini
[Unit]
Description=EcoSweep Camera Stream (Flask)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/pi/ecosweep-phase1
ExecStart=/usr/bin/python3 camera_stream.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ecosweep-camera
sudo systemctl start ecosweep-camera
```

---

## Summary Checklist

- [ ] USB webcam connected; `ls /dev/video*` shows a device.
- [ ] Stream running on Pi (Option A **or** B).
- [ ] Pi IP noted; URL works in a browser on PC or phone.
- [ ] App Settings: Camera Stream URL set to that URL.
- [ ] Bluetooth connected to robot; FPV tab shows live camera.

When all are done, Phase 1 is complete. If anything doesn’t work, note the step number and the exact message or behavior and we can fix it step by step.
