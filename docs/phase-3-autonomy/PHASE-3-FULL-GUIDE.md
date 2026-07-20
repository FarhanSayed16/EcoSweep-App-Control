# Phase 3: Autonomous Behavior — Full Guide

**Goal:** Use your Phase 2 detections (garbage, bbox, MOVE_LEFT/MOVE_RIGHT/CENTERED) plus Arduino telemetry so the robot **moves toward garbage**, **aligns**, and **triggers pickup** without the app driving it. The Pi is the “brain”; the app only shows status and can override.

---

## Prerequisites

- **Phase 2 done:** YOLO garbage detection on Pi; you have class, bbox, confidence, and decision logic (MOVE_LEFT, MOVE_RIGHT, CENTERED).
- **Pi bridge:** `ecosweep_bridge.py` (or equivalent) that connects app ↔ Pi ↔ Arduino (Bluetooth SPP + serial).
- **Arduino:** Accepts `M:speed,turn`, `SA:...`, and sends `DATA:SENSORS:...`, `DATA:BATT:...` (and optionally MODE, GEAR).

---

## Phase 3 Overview

| Step | What you do |
|------|-------------|
| 3.1 | Ensure the Pi can **send** `M:` and `SA:` to the Arduino from its own logic (not only forward from the app), and **read** Arduino telemetry (sensors, battery). |
| 3.2 | Implement an **autonomy state machine** on the Pi: SEARCH → APPROACH → ALIGN → PICKUP → CONTINUE. |
| 3.3 | Use your detection decisions (left/right/centered) and bbox to drive: turn toward target, move forward when centered, stop when close, trigger gripper. |
| 3.4 | Add **safety:** stop on very close ultrasonic or on “person” detection. |
| 3.5 | Test in a safe area; tune distances and timing. |

---

## Step 3.1: Pi Can Send Commands and Read Telemetry

- **Send:** Your bridge already forwards app → Arduino. Add a path where **Pi logic** can also write to the Arduino serial (e.g. a function `send_to_arduino("M:100,0)\n")` and call it from the autonomy loop). If the bridge is single-threaded, you may run autonomy in a separate thread/process that shares the serial port (e.g. via a queue) or integrate the autonomy loop into the bridge.
- **Read:** The bridge already receives Arduino → app. Parse lines like `DATA:SENSORS:front,left,right` and `DATA:BATT:...` and expose them to the autonomy logic (e.g. global variables or a small “telemetry” object updated by the serial reader).

Deliverable: autonomy code can both **send** `M:`/`SA:` and **read** front/left/right distances (and optionally battery).

---

## Step 3.2: State Machine (Concept)

- **SEARCH:** No garbage in frame (or confidence too low). Send a slow turn or cruise (e.g. `M:50,80` or alternating left/right) until garbage is detected.
- **APPROACH:** Garbage detected. Use MOVE_LEFT / MOVE_RIGHT to turn toward it; when CENTERED, send forward (e.g. `M:100,0`). Optionally use bbox size or ultrasonics to decide “close enough.”
- **ALIGN:** Fine-tune so the object is centered (reuse your left/right/centered logic). When aligned and close, go to PICKUP.
- **PICKUP:** Send gripper close (e.g. `SA:GRIP_CLOSE_START`, wait 1–2 s, `SA:GRIP_CLOSE_STOP`), then `M:0,0`. Optionally back up slightly, then go to SEARCH or CONTINUE.
- **CONTINUE:** Same as SEARCH; look for next garbage.

Transitions: SEARCH → (garbage detected) → APPROACH → (centered and close) → ALIGN → (aligned) → PICKUP → (done) → SEARCH/CONTINUE. If obstacle too close (ultrasonic) or person detected, go to a **STOP** state (send `M:0,0`) then back to SEARCH when safe.

---

## Step 3.3: Targeting (Concrete)

- **Frame center:** `fx = FRAME_WIDTH / 2`, `fy = FRAME_HEIGHT / 2`.
- **Garbage bbox center:** `cx = (x1 + x2) / 2`, `cy = (y1 + y2) / 2`.
- **Margin:** e.g. 30 pixels.
  - If `cx < fx - margin` → **MOVE_LEFT:** e.g. `M:0, -80` (turn left).
  - If `cx > fx + margin` → **MOVE_RIGHT:** e.g. `M:0, 80`.
  - Else **CENTERED:** e.g. `M:100, 0` (forward). After a short time or when front ultrasonic < threshold, go to PICKUP.
- **Pickup:** Send your gripper sequence (e.g. `SA:GRIP_CLOSE_START`, sleep, `SA:GRIP_CLOSE_STOP`). Then stop motors and continue searching.

---

## Step 3.4: Safety

- **Ultrasonic:** If `front < 15` cm (or your chosen threshold), send `M:0,0` and do not move forward; optionally back up (`M:-80,0`) then re-enter SEARCH.
- **Person:** If YOLO detects “person” with high confidence, send `M:0,0` and pause until person is out of frame or confidence drops.
- **Arduino:** Keep the existing motor watchdog (500 ms no command → stop) as a backup.

---

## Step 3.5: Where to Put the Code

- **Option A:** Extend `ecosweep_bridge.py`: add a thread that runs the state machine, reads shared telemetry (updated by the serial reader), and writes commands to a queue that the serial writer sends to the Arduino.
- **Option B:** Separate script `autonomy.py` that connects to the Arduino serial (if the bridge exposes it or you run a combined process that runs both bridge and autonomy and shares the serial port with proper locking).

Start with Option A if your bridge is single-threaded: one thread for app↔serial forwarding, one thread for autonomy that only produces commands; a single writer thread sends both app and autonomy commands to the Arduino (with a simple priority: e.g. autonomy when AUTO_ON, else app).

---

## Checklist — Phase 3

- [x] **3.1** Pi can send `M:`/`SA:` to Arduino from autonomy logic and read `DATA:SENSORS` (and optionally BATT). *(Done: `ecosweep_bridge.py` — telemetry parsing, `to_arduino_queue`, `arduino_writer` thread, `send_to_arduino()`, `get_telemetry()`, `autonomy_active` from MODE.)*
- [x] **3.2** State machine implemented (SEARCH → APPROACH → ALIGN → PICKUP → CONTINUE) and integrated with YOLO decisions. *(Done: `hardware/pi/phase3/autonomy.py`.)*
- [x] **3.3** Targeting: left/right/centered → turn or forward; pickup sequence when aligned and close. *(Done: YOLO writes `/tmp/ecosweep_detection.json`; autonomy reads it. Use `phase2/yolo_fpv_stream_optimized.py`.)*
- [x] **3.4** Safety: stop on close obstacle and on person; Arduino watchdog remains. *(Done in autonomy: STOP state on `front < 15` cm or `person_detected`.)*
- [ ] **3.5** Test in a safe area; tune margins, speeds, and distances.

When this is done, the robot will autonomously detect garbage, drive to it, align, and trigger the gripper; you can then refine timing and add more states (e.g. RETRY, waypoints) as needed.

---

## Phase 3 Run Instructions

1. **On the Raspberry Pi (from the `hardware/pi` directory):**
   - Start the **YOLO FPV stream** (writes detection file for autonomy):
     ```bash
     cd phase2 && python3 yolo_fpv_stream_optimized.py
     ```
     Leave this running (stream at `http://<PI_IP>:5000/video_feed`).
   - In another terminal, start the **bridge** (Bluetooth + Arduino + autonomy thread):
     ```bash
     cd /path/to/hardware/pi && python3 ecosweep_bridge.py
     ```
   - Ensure the Arduino is connected via USB and the app is connected over Bluetooth.

2. **In the app:** Turn on **Autonomous mode** (e.g. send `MODE:AUTO_ON`). The autonomy thread will then read `/tmp/ecosweep_detection.json` and send `M:`/`SA:` commands. Turn off with `MODE:AUTO_OFF`.

3. **Detection file format** (written by YOLO, read by autonomy):  
   `/tmp/ecosweep_detection.json`:
   - `decision`: `"NONE"` | `"MOVE_LEFT"` | `"MOVE_RIGHT"` | `"CENTERED"`
   - `confidence`: float
   - `person_detected`: bool (safety: autonomy stops when true)
   - Optional: `bbox_center_x`, `bbox_center_y`, `timestamp`

4. **Tuning:** Edit `hardware/pi/phase3/autonomy.py` for `FRONT_SAFE_CM`, `FRONT_CLOSE_CM`, `APPROACH_SPEED`, `PICKUP_GRIP_DURATION_S`, etc.
