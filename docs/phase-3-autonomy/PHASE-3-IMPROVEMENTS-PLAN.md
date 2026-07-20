# Phase 3 Improvements Plan — For Approval

This document outlines the planned fixes and enhancements for:
1. **Auto-start on boot** (webcam, YOLO stream, bridge)
2. **Robotic arm integration** (5-axis arm commands in autonomy)
3. **Obstacle detection and movement** (ultrasonic-based stop, proper behavior)

**Please review and approve before implementation.**

---

## Part A: Auto-Start on Boot (Headless Operation)

### Problem
When the Pi is powered by battery (no monitor), nothing starts automatically. You must SSH or connect a monitor to manually run:
- YOLO FPV stream (webcam + detection)
- Bridge script (Bluetooth + Arduino + autonomy)

### Planned Solution

| Item | What | Where |
|------|------|-------|
| **A.1** | **systemd service: ecosweep-yolo.service** | Starts `yolo_fpv_stream_optimized.py` after network and USB are ready. Waits for `/dev/video0` (webcam) to exist with a retry loop (e.g. 30 s) so USB webcam has time to enumerate. |
| **A.2** | **systemd service: ecosweep-bridge.service** | Starts `ecosweep_manual_final.py` (or your production bridge). Depends on `ecosweep-yolo.service` or starts after a short delay so the detection file can be written. Waits for Arduino serial port (`/dev/ttyUSB0` or `/dev/ttyACM0`) with retry. |
| **A.3** | **Startup script (optional)** | A single `ecosweep_start.sh` that: (1) waits for webcam + Arduino, (2) starts YOLO in background, (3) starts bridge. Can be called from `rc.local` or a single systemd service if you prefer one service instead of two. |
| **A.4** | **Install instructions** | Copy service files to `/etc/systemd/system/`, enable, and document in `docs/phase-3-autonomy/PHASE-3-STARTUP-GUIDE.md`. |

### Deliverables
- `hardware/pi/systemd/ecosweep-yolo.service`
- `hardware/pi/systemd/ecosweep-bridge.service`
- `hardware/pi/ecosweep_start.sh` (optional all-in-one)
- `docs/phase-3-autonomy/PHASE-3-STARTUP-GUIDE.md` (how to install and enable)

### Notes
- Paths in services will use `/home/pi/...` or a configurable `ECOSWEEP_DIR` — you can adjust to match your Pi layout.
- YOLO service will use the same Python/venv as your current setup (e.g. `yolov8-env` if you use one).

---

## Part B: Robotic Arm Integration in Autonomy

### Problem
- The 5-axis arm (base, arm, forearm, wrist, gripper) is not used by autonomy.
- Autonomy only sends `M:` (movement) commands; no `SA:` (servo action) or `S:` (angle) commands.
- When garbage is centered and close, the robot should lower the arm, close the gripper, then retract — but this sequence is missing.

### Arduino SA Commands (Already Supported)
From `EcoSweep_Master.ino`:
- **Base:** `BASE_LEFT_START/STOP`, `BASE_RIGHT_START/STOP`
- **Arm:** `ARM_UP_START/STOP`, `ARM_DOWN_START/STOP`
- **Forearm:** `FOREARM_FORWARD_START/STOP`, `FOREARM_BACKWARD_START/STOP`
- **Wrist:** `WRIST_ROTATE_LEFT_START/STOP`, `WRIST_ROTATE_RIGHT_START/STOP`
- **Gripper:** `GRIP_OPEN_START/STOP`, `GRIP_CLOSE_START/STOP`

### Planned Solution

| Item | What | Where |
|------|------|-------|
| **B.1** | **PICKUP state with arm sequence** | When autonomy reaches "close and centered" (front < 25 cm or bbox large enough), enter PICKUP state. Send: (1) `SA:ARM_DOWN_START` for ~0.5 s, then STOP; (2) `SA:GRIP_CLOSE_START` for ~1.5 s, then STOP; (3) `SA:ARM_UP_START` for ~0.5 s, then STOP; (4) `M:0,0`. Then go back to SEARCH. |
| **B.2** | **Optional: preset angles** | Instead of SA continuous movement, use `S:0,angle` … `S:4,angle` for a known "pickup" pose if you have calibrated angles. This is more repeatable but requires tuning. |
| **B.3** | **Bridge forwards SA from app** | Ensure the bridge forwards `SA:` and `S:` from the app to Arduino in manual mode (already does). In AUTO mode, autonomy will also send SA via the same `_write_arduino` path. |

### Deliverables
- Update `ecosweep_manual_final_patched.py` autonomy loop: add PICKUP state, send SA sequence.
- Or update `phase3/autonomy.py` if you use the repo bridge; then ensure your production bridge uses equivalent logic.
- Tunable constants: `PICKUP_ARM_DOWN_S`, `PICKUP_GRIP_CLOSE_S`, `PICKUP_ARM_UP_S`.

### Notes
- Exact timing and order may need tuning for your arm geometry. We'll use conservative defaults.
- If the arm behaves oddly (wrong direction, wrong speed), we can switch to `S:id,angle` presets once you provide angles.

---

## Part C: Obstacle Detection and Movement

### Problem
- Autonomy does **not** use ultrasonic data (front/left/right) from the Arduino.
- The bridge forwards Arduino lines to the app but does **not** parse `DATA:SENSORS:` for the autonomy loop.
- So: no "stop when front < 15 cm", no "back up when stuck", no "avoid obstacle" behavior.
- Movement after detecting an obstacle is not proper (e.g. keeps driving forward into it, or doesn't recover).

### Planned Solution

| Item | What | Where |
|------|------|-------|
| **C.1** | **Parse telemetry in bridge** | When the bridge receives a line from Arduino, parse `DATA:SENSORS:front,left,right` and store in a shared variable (e.g. `telemetry = {"front": 0, "left": 0, "right": 0}`) with a lock. Still forward the line to the app. |
| **C.2** | **Pass telemetry to autonomy** | Autonomy loop reads `front`, `left`, `right` (cm) each tick. Use for: (a) **STOP** when `front < FRONT_SAFE_CM` (e.g. 15); (b) **don't drive forward** when front is too close; (c) **PICKUP** when `front < FRONT_CLOSE_CM` (e.g. 25) and centered. |
| **C.3** | **Obstacle recovery** | When `front < FRONT_SAFE_CM` and we were moving forward: (1) send `M:0,0`; (2) optionally send `M:-80,0` (back up) for ~0.5 s; (3) send `M:0,60` or `M:0,-60` (turn) to try a different direction; (4) re-enter SEARCH. |
| **C.4** | **Stuck detection (optional)** | If we've been in APPROACH with CENTERED for several seconds but `front` never decreases (we're not getting closer), assume stuck — back up, turn, SEARCH. |

### Deliverables
- Bridge: parse `DATA:SENSORS`, store in `telemetry`, pass to autonomy (or autonomy reads from shared state).
- Autonomy: use `front_cm` for STOP, PICKUP transition, and obstacle recovery.
- Tunable: `FRONT_SAFE_CM`, `FRONT_CLOSE_CM`, `BACKUP_DURATION_S`, `BACKUP_SPEED`.

### Notes
- Arduino already sends `DATA:SENSORS:front,left,right` every 250 ms. We only need the bridge to parse and expose it.
- `ecosweep_manual_final_patched.py` currently does not parse Arduino output at all — we will add that.

---

## Summary of Changes by File

| File | Changes |
|------|---------|
| `hardware/pi/ecosweep_manual_final_patched.py` | Parse DATA:SENSORS; pass telemetry to autonomy; add PICKUP state with SA sequence; add obstacle recovery (stop, back up, turn). |
| `hardware/pi/phase3/autonomy.py` | (If used) Already has telemetry + PICKUP; ensure it's wired correctly. |
| `hardware/pi/systemd/ecosweep-yolo.service` | **New.** Start YOLO stream after webcam ready. |
| `hardware/pi/systemd/ecosweep-bridge.service` | **New.** Start bridge after Arduino ready. |
| `hardware/pi/ecosweep_start.sh` | **New (optional).** Single script to start both with waits. |
| `docs/phase-3-autonomy/PHASE-3-STARTUP-GUIDE.md` | **New.** How to install and enable auto-start. |

---

## Implementation Order (After Approval)

1. **Part C** (obstacle detection) — Bridge parses telemetry, autonomy uses it. Foundation for safe movement.
2. **Part B** (arm integration) — Add PICKUP state with gripper/arm sequence.
3. **Part A** (auto-start) — systemd services and startup script.

---

## What You Need to Confirm

1. **Paths on your Pi:** Where do you keep the scripts? (e.g. `/home/pi/ecosweep/` or `/home/pi/ecosweep-phase2/`, etc.)
2. **Python environment:** Do you use a venv (e.g. `yolov8-env`)? If yes, we'll use its Python in the service.
3. **Bridge script name:** Is it `ecosweep_manual_final.py` or something else on the Pi?
4. **Arm sequence:** Do you prefer SA continuous movement (START/STOP with timers) or S:id,angle presets? If presets, do you have known angles for "pickup" pose?

Once you approve this plan and answer the questions above, implementation will follow in the order listed.
