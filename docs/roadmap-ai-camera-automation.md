# EcoSweep Roadmap: Camera, AI, and Autonomous Cleaning

This document is the master plan for taking EcoSweep from “manual + basic telemetry” to **intelligent autonomous cleaning**: USB camera on the Pi, AI for garbage/object detection, and proper automated behavior. Voice assistant is planned for later.

---

## 1. Vision and Roles

### Camera and AI in EcoSweep (your role description)

- **Camera**: Real-time view of the environment → FPV in the app, plus **input for AI** (object/garbage detection, obstacles, people).
- **AI**: Uses camera + sensors to:
  - Detect **garbage/waste** (main cleaning objective),
  - Detect **obstacles** and **people**,
  - Support **path optimization** and safe movement.
- **Outcome**: Robot detects garbage “exactly as it is,” and movements/cleaning actions perform properly in an automated way.

### Where Things Run

| Layer        | Responsibility |
|-------------|----------------|
| **Flutter app** | FPV stream URL, show video (and later optional AI overlays), manual control, mission planning, Bluetooth to Pi. |
| **Raspberry Pi** | USB webcam capture, **video streaming**, **AI inference** (garbage/object detection), **autonomous logic** (when to move, where to go, when to trigger pickup), send `M:` / `S:` / `SA:` to Arduino. Optionally send detection data to app. |
| **Arduino** | Motors, servos, ultrasonics, IMU, compass. Execute movement and servo commands from Pi (or app in manual). Optionally simple local safety (e.g. stop on very close obstacle). |

**Important**: Autonomous “brain” (what to do with detections) lives on the **Pi**. The app stays as the remote UI and manual override; the Pi drives automation when in autonomous mode.

---

## 2. Current State vs Target

### What Exists Today

| Area | Status |
|------|--------|
| **App** | Manual control, FPV screen with configurable URL (`http://.../video_feed`), Bluetooth, dashboard, mission planning (waypoints), settings. |
| **Pi** | `ecosweep_bridge.py`: Bluetooth SPP ↔ Arduino serial, audio (engine/shift). **No camera, no AI.** |
| **Arduino** | Motors, servos, sensors, `M:`/`S:`/`SA:`/`GEAR:`/`MODE:`, telemetry. `PATH:` only ACKed (no waypoint execution). |
| **Camera** | Not on Pi yet. App expects an HTTP stream (e.g. Flask or mjpg-streamer). |
| **AI** | None. No garbage/object detection. |
| **Autonomy** | Mode switch (AUTO_ON) exists; no logic that “sees” garbage and moves/picks. |

### Target State (after this roadmap)

| Area | Target |
|------|--------|
| **Camera** | USB webcam on Pi; stable HTTP stream (e.g. Flask or mjpg-streamer); app FPV shows that stream. |
| **AI** | Pi runs a model (e.g. TensorFlow Lite / YOLO / OpenCV-based) for **garbage/waste detection** (and optionally obstacles/people). Detections in real time. |
| **Autonomy** | Pi uses AI + sensors to: find garbage → drive toward it → trigger pickup (e.g. gripper/sweep) → continue. Movements and “cleaning” behavior are consistent and predictable. |
| **Later** | Voice assistant (commands, feedback). |

---

## 3. Phased Execution Plan

### Phase 1: Camera Module (USB Webcam on Pi)

**Goal**: Pi captures from USB webcam and serves a stream the app can display. No AI yet.

| Step | Where | What to do |
|------|--------|------------|
| 1.1 | **Pi (Real VNC / SSH)** | Connect USB webcam; check it’s detected: `ls /dev/video*`, `v4l2-ctl --list-devices`. Install deps if needed: `sudo apt install v4l-utils`. |
| 1.2 | **Pi** | Choose streaming method: **(A)** mjpg-streamer (lightweight, MJPEG), or **(B)** Flask + OpenCV (same stack you’ll use for AI). For “camera only” first, mjpg-streamer is quick. Example: `mjpg_streamer -i "input_uvc.so -d /dev/video0" -o "output_http.so -p 8080"`. Stream URL: `http://<PI_IP>:8080/?action=stream`. |
| 1.3 | **Pi** | If using Flask instead: write a small app (e.g. `camera_stream.py`) that reads frames from the webcam and serves MJPEG (or JPEG) at e.g. `/video_feed`. Run on port 5000 or 8080. |
| 1.4 | **App** | In **Settings**, set “Camera Stream URL” to `http://<PI_IP>:8080/?action=stream` (or your Flask `/video_feed`). **Note:** The FPV screen currently has its own URL field (and may use a hardcoded default). For consistency, you can later make FPV read the same URL from Settings (e.g. shared_preferences or a shared service) so one place controls the stream. |
| 1.5 | **Test** | On phone (same Wi‑Fi as Pi), open app → connect to robot via Bluetooth → open FPV tab. Confirm live image from USB webcam. |

**Deliverable**: Reliable FPV from USB webcam on Pi to the app.

---

### Phase 2: AI Integration on Pi (Garbage / Object Detection)

**Goal**: Pi runs a detection model on camera frames; identifies garbage/waste (and optionally obstacles/people). Results can be logged or sent to the next phase.

| Step | Where | What to do |
|------|--------|------------|
| 2.1 | **Pi** | Set up Python env: OpenCV, TensorFlow Lite **or** a small YOLO/object-detection lib. Prefer TFLite for Pi 4 (speed vs accuracy). |
| 2.2 | **Pi** | Choose or train a **garbage/waste detection** model: (A) Use a public “garbage detection” / “waste classification” dataset and train a small model (TFLite or YOLO), or (B) Start with a generic “object detection” model and map certain classes to “garbage” (e.g. bottle, can, wrapper). Export to TFLite or ONNX for Pi. |
| 2.3 | **Pi** | Write `detection.py` (or integrate into `camera_stream.py`): capture frame → run inference → get bounding boxes + labels (e.g. “garbage”, “person”, “obstacle”). Optionally draw boxes and serve **annotated** stream for debugging. |
| 2.4 | **Pi** | Define a simple “detection result” format (e.g. list of objects with class, bounding box, confidence). This will be input for Phase 3 (autonomous logic). No Arduino or app change required yet if you only log or visualize. |
| 2.5 | **Optional – App** | If you want overlays in the app: Pi can send detection data over Bluetooth (e.g. new `DATA:DETECT:...` line in the existing protocol). App parses and draws boxes on the FPV view. Can be done after autonomy works. |

**Deliverable**: Pi performs real-time garbage (and optionally object/person) detection from the USB camera.

---

### Phase 3: Autonomous Behavior (Robot Works “Properly”)

**Goal**: Pi uses **AI detections + sensors** (from Arduino) to decide **where to move** and **when to trigger cleaning** (e.g. gripper/sweep). Movements and cleaning actions are consistent and correct (“exactly how the garbage is there”).

| Step | Where | What to do |
|------|--------|------------|
| 3.1 | **Protocol** | Extend Pi ↔ Arduino usage: Pi already forwards app commands. Ensure Pi can **send** `M:speed,turn`, `S:id,angle`, `SA:...` based on its own logic (not only forward from app). Pi should also **read** Arduino telemetry (`DATA:SENSORS:...`, `DATA:BATT:...`) to avoid obstacles and respect battery. |
| 3.2 | **Pi** | Implement **autonomous state machine** (e.g. in `ecosweep_bridge.py` or a separate `autonomy.py`): states such as: SEARCH (turn/cruise to find garbage) → APPROACH (drive toward detected garbage) → ALIGN (fine-tune using camera + ultrasonics) → PICKUP (send servo/gripper command) → RETRY or CONTINUE. Use detection bounding box position (e.g. center in frame = aligned) and size (e.g. closer = larger). |
| 3.3 | **Pi** | **Garbage targeting**: From detection (e.g. “garbage” at pixel (x, y)), compute simple motion: e.g. turn toward center of frame, move forward if clear (ultrasonics), stop when close; then trigger `SA:GRIP_CLOSE_START` / stop / `SA:GRIP_CLOSE_STOP` (or your actual pickup sequence). |
| 3.4 | **Arduino** | (Optional) Improve **PATH:** handling: parse waypoints from Pi (or app), implement a tiny P-controller using IMU/compass to steer toward next waypoint, advance when within distance. Useful for “sweep area” behavior. If you prefer “reactive only” (no waypoints), you can keep PATH as ACK and drive everything from Pi. |
| 3.5 | **Safety** | Pi: if ultrasonics show very close obstacle or person detected, send `M:0,0` (stop) and/or back off. Prefer **redundant** stop: Pi sends stop, and Arduino motor watchdog (already 500 ms) stops motors if no command. |
| 3.6 | **App** | When mode is AUTO_ON, app can show “Autonomous” and optionally live detections (if you added DATA:DETECT). No need to “drive” from app in auto mode; Pi is in charge. |

**Deliverable**: Robot, in autonomous mode, detects garbage from the camera, moves toward it, and performs a repeatable cleaning/pickup sequence; behavior matches the “exact objective” of EcoSweep.

---

### Phase 4: Voice Assistant (Later)

**Goal**: Control and feedback via voice (e.g. “start cleaning”, “stop”, “where are you?”). Deferred until Phase 1–3 are solid.

| Step | Where | What to do |
|------|--------|------------|
| 4.1 | **Pi** | Add mic input; speech-to-text (e.g. Vosk offline or cloud API). Parse intent → send commands to Arduino (or to app via Bluetooth). |
| 4.2 | **Pi / App** | Text-to-speech for status (“Cleaning started”, “Garbage detected”). Can run on Pi or be sent to app to speak. |
| 4.3 | **Protocol** | Reuse or extend `DATA:SPEAK:` and app log for voice feedback; add optional “VOICE:command” from app to Pi if needed. |

---

## 4. What to Do Where – Quick Reference

| Task | Where | Notes |
|------|--------|--------|
| USB webcam stream | **Raspberry Pi** | mjpg-streamer or Flask + OpenCV; same Pi that runs the bridge. |
| Set FPV URL | **App (Settings)** | User sets `http://<PI_IP>:port/...`; optionally make FPV read from Settings. |
| Garbage/object detection | **Raspberry Pi** | Python + OpenCV + TFLite (or YOLO); runs on each frame (or every N frames). |
| “Where to move / when to pick” | **Raspberry Pi** | State machine reads detections + Arduino telemetry, sends `M:`/`S:`/`SA:`. |
| Execute movement & servos | **Arduino** | Already does this; Pi (or app) sends same commands. |
| Safety (stop on obstacle) | **Arduino** (watchdog) + **Pi** (ultrasonics + person/garbage logic). |
| FPV display, manual control, mission UI | **App** | No change for Phase 1–2 except URL; optional overlay in Phase 2–3. |
| Voice (later) | **Pi** (primary) or **App** | Mic on Pi; TTS on Pi or app. |

---

## 5. Recommended Order of Work (Next Steps)

Do in this order so each step builds on the previous.

1. **Camera (Phase 1)**  
   - On Pi: plug USB webcam, install mjpg-streamer (or Flask), start stream.  
   - On app: set Camera URL in Settings to Pi stream; open FPV and confirm picture.  
   - **Done when**: You see live USB webcam in the app.

2. **AI (Phase 2)**  
   - On Pi: add OpenCV + TFLite (or YOLO), run a garbage/waste detection model on the same camera feed.  
   - Log or visualize detections (e.g. annotated stream or console).  
   - **Done when**: Pi prints or shows bounding boxes for “garbage” in real time.

3. **Autonomy (Phase 3)**  
   - On Pi: implement the state machine that uses detections + telemetry to send `M:` and servo commands.  
   - Test in a safe area: robot should approach a single “garbage” target and trigger pickup.  
   - Refine: alignment, distances, multiple objects, safety stops.  
   - **Done when**: Robot reliably detects garbage and performs the correct movements and cleaning actions.

4. **Voice (Phase 4)**  
   - After 1–3 are stable, add mic + STT + TTS and wire to commands and `DATA:SPEAK:`.

---

## 6. App Changes Summary

- **Phase 1**: No code change if FPV already uses a configurable URL; otherwise, make FPV use the Camera URL from Settings (and ensure Settings is saved/loaded).
- **Phase 2**: No mandatory change; optional: parse `DATA:DETECT:...` and draw boxes on FPV.
- **Phase 3**: Optional: show “Autonomous – Pi in control” and live detections; ensure AUTO_ON/AUTO_OFF and mode display work.
- **Phase 4**: Optional: send voice commands from app; show TTS messages.

---

## 7. Pi Software Layout (Suggested)

```
hardware/pi/
  ecosweep_bridge.py    # Existing: Bluetooth ↔ Arduino
  camera_stream.py     # New (Phase 1): USB webcam → HTTP stream
  detection.py         # New (Phase 2): OpenCV + TFLite, garbage detection
  autonomy.py          # New (Phase 3): State machine, sends M:/S:/SA: to Arduino
  run_with_camera.sh   # Optional: start stream + bridge (+ AI + autonomy later)
```

You can later merge stream + detection + autonomy into one process, or keep them as separate processes that communicate (e.g. via sockets or shared memory).

---

## 8. Summary

- **Camera**: USB webcam on Pi → HTTP stream → app FPV (Phase 1).  
- **AI**: Garbage (and optional object/person) detection on Pi (Phase 2).  
- **Autonomy**: Pi uses AI + sensors to move and clean “properly” (Phase 3).  
- **Voice**: Later (Phase 4).  

All “intelligence” and camera/AI pipeline stay on the **Raspberry Pi**; the **app** remains the remote UI and manual control; the **Arduino** keeps doing low-level motors and servos. Following the phases above gives you a clear, step-by-step path from current state to a working EcoSweep that detects garbage exactly and performs the right movements and cleaning actions.
