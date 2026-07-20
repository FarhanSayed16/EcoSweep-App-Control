# EcoSweep Next Steps – Checklist

Use this alongside [roadmap-ai-camera-automation.md](roadmap-ai-camera-automation.md). Tick items as you complete them.

---

## Phase 1: Camera (USB Webcam on Pi)

- [ ] **1.1** On Pi (Real VNC or SSH): plug in USB webcam; run `ls /dev/video*` and `v4l2-ctl --list-devices` to confirm device (e.g. `/dev/video0`).
- [ ] **1.2** On Pi: install mjpg-streamer or set up Flask + OpenCV for streaming.
  - mjpg-streamer: `sudo apt install mjpg-streamer` (or build from source); run:  
    `mjpg_streamer -i "input_uvc.so -d /dev/video0" -o "output_http.so -p 8080"`.
  - Or write a small Flask script that reads from `/dev/video0` and serves MJPEG at `/video_feed`.
- [ ] **1.3** On Pi: note Pi’s IP (e.g. `hostname -I`). Stream URL will be e.g. `http://<PI_IP>:8080/?action=stream` (mjpg-streamer) or `http://<PI_IP>:5000/video_feed` (Flask).
- [ ] **1.4** On phone: open app → Settings → set “Camera Stream URL” to the Pi stream URL. Save.
- [ ] **1.5** Connect to robot via Bluetooth, open FPV tab; confirm live image from USB webcam.

**Done when**: You see a stable live feed from the USB webcam in the app FPV screen.

---

## Phase 2: AI (Garbage Detection on Pi)

**YOLO path (Pi 4 4GB):** See [phase-2-ai/PHASE-2-YOLO-GUIDE.md](phase-2-ai/PHASE-2-YOLO-GUIDE.md). Run `python3 detection_yolo.py` on Pi.

- [ ] **2.1** On Pi: **YOLO:** `pip3 install ultralytics opencv-python-headless`; **TFLite:** OpenCV + tflite-runtime.
- [ ] **2.2** **YOLO:** Use yolov8n.pt (auto-download) or custom `models/yolov8n.pt`. **TFLite:** `models/detect.tflite` + `labels.txt`.
- [ ] **2.3** On Pi: run **YOLO:** `python3 detection_yolo.py`; **TFLite:** `python3 detection.py`. Confirm detections.
- [ ] **2.4** Optional: annotated stream (boxes on video).

**Done when**: Pi outputs “garbage” (and optional other classes) with bounding boxes in real time.

---

## Phase 3: Autonomy (Robot Moves and Cleans Properly)

- [ ] **3.1** On Pi: ensure bridge can send `M:`/`S:`/`SA:` to Arduino from Pi logic (not only from app).
- [ ] **3.2** On Pi: read Arduino telemetry (sensors, battery) in the bridge or a separate autonomy script.
- [ ] **3.3** On Pi: implement autonomy state machine (SEARCH → APPROACH → ALIGN → PICKUP → CONTINUE) using detections + sensors.
- [ ] **3.4** On Pi: map detection position/size to movement (turn toward target, move forward, stop, trigger gripper).
- [ ] **3.5** Test in a safe area with one “garbage” target; refine distances and timing.
- [ ] **3.6** Add safety: stop on very close ultrasonic or on “person” detection.

**Done when**: In AUTO mode, the robot reliably detects garbage, drives to it, and performs the intended cleaning/pickup action.

---

## Phase 4: Voice (Later)

- [ ] **4.1** On Pi: add mic; speech-to-text (e.g. Vosk or cloud API).
- [ ] **4.2** On Pi or app: text-to-speech for status messages.
- [ ] **4.3** Wire voice commands to start/stop/status and optional `DATA:SPEAK:` to app.

---

## Where to Work

| Phase | Work on Pi (Real VNC/SSH) | Work on App | Work on Arduino |
|-------|---------------------------|-------------|------------------|
| 1     | Webcam, stream server     | Set camera URL in Settings | — |
| 2     | OpenCV, TFLite, detection script | Optional: overlay later | — |
| 3     | Autonomy logic, send M:/S:/SA: | Optional: show “Autonomous” | Optional: PATH execution |
| 4     | Mic, STT, TTS             | Optional: TTS, voice UI | — |

Start with Phase 1; complete each phase before moving to the next.
