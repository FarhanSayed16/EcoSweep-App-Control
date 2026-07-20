# Phase 2: Less Lag + What to Do Next (Phase 3)

## Why the stream feels laggy

In your current `yolo_fpv_stream.py`, the **same loop** does:

1. Read frame  
2. Run YOLO (slow on Pi)  
3. Draw boxes  
4. Encode JPEG  
5. Yield to Flask  

So every client frame waits for YOLO + encode. That makes the stream feel laggy and uneven.

---

## Fix: YOLO in a background thread

**Idea:** One thread only does: **capture → YOLO (every N frames) → draw → encode → store “latest JPEG”**. The **Flask generator** only **reads the latest JPEG** and yields it. It never runs YOLO or encodes, so the stream is not blocked.

**In the repo:** `hardware/pi/phase2/yolo_fpv_stream_optimized.py`

- **Background thread:** Opens camera, runs YOLO every N frames, draws boxes, encodes JPEG, writes result to a shared `_latest_jpeg` (with a lock).
- **Flask `/video_feed`:** In a loop, reads `_latest_jpeg` and yields it. No YOLO, no encode in this path.
- **Extra:** Uses `model.predict(..., imgsz=320)` for faster inference; you can tune `YOLO_EVERY_N_FRAMES`, `JPEG_QUALITY`, `FRAME_WIDTH/HEIGHT`.

**On the Pi:** Replace or run alongside your current script:

```bash
# e.g. in ~/ecosweep-phase2/
python3 yolo_fpv_stream_optimized.py
```

Set the app FPV URL to `http://<PI_IP>:5000/video_feed` as before. Stream should feel smoother and less laggy.

---

## Other tweaks (if still laggy)

- **YOLO_EVERY_N_FRAMES = 4 or 5** — Fewer inferences per second, smoother stream.
- **FRAME_WIDTH / FRAME_HEIGHT** — e.g. 320x240 to reduce encode time.
- **YOLO_IMGSZ = 256** — Faster YOLO, slightly less accuracy.
- **JPEG_QUALITY = 55–60** — Faster encode, slightly worse image.
- **Cooling** — Heat sink/fan so the Pi doesn’t throttle.

---

## What to do next: Phase 3 (Autonomy)

Phase 2 is done: you have detections (garbage, bbox, confidence) and decision logic (MOVE_LEFT, MOVE_RIGHT, CENTERED). Next is **Phase 3: use that + Arduino to move and pick**.

### Phase 3 in short

| Step | What to do |
|------|------------|
| **3.1** | On the Pi, autonomy must **send** `M:speed,turn` and `SA:...` to the Arduino (not only forward from the app). Ensure your bridge (or a new script) can **send** commands and **read** Arduino telemetry (e.g. `DATA:SENSORS:...`, `DATA:BATT:...`). |
| **3.2** | Implement a small **state machine** on the Pi: e.g. **SEARCH** (turn/cruise until garbage detected) → **APPROACH** (drive toward target) → **ALIGN** (center in frame using MOVE_LEFT/MOVE_RIGHT/CENTERED) → **PICKUP** (send gripper command, then continue). Use your existing decision logic (left/right/centered) and bbox center/size. |
| **3.3** | **Targeting:** From YOLO bbox center (cx, cy) and frame center (fx, fy): if cx < fx - margin → MOVE_LEFT; if cx > fx + margin → MOVE_RIGHT; else CENTERED → send forward for a short time, then trigger pickup (e.g. `SA:GRIP_CLOSE_START`, wait, `SA:GRIP_CLOSE_STOP`). Use ultrasonics to stop if something is very close (safety). |
| **3.4** | **Safety:** If `DATA:SENSORS` shows very close obstacle or “person” detected, send `M:0,0` (stop). Rely also on the Arduino motor watchdog (500 ms) as a backup. |
| **3.5** | **App:** When mode is AUTO_ON, the app can show “Autonomous” and optionally live detections; the Pi is in charge of movement, not the app. |

### Where the code lives

- **Pi:** Extend `ecosweep_bridge.py` or add `autonomy.py` that:
  - Reads Arduino serial (telemetry).
  - Gets detection decisions from your YOLO pipeline (or runs YOLO in the same process and uses MOVE_LEFT/MOVE_RIGHT/CENTERED).
  - Sends `M:...` and `SA:...` to the Arduino.
- **Arduino:** No change required for basic autonomy; it already executes `M:` and `SA:`.

Use **`docs/roadmap-ai-camera-automation.md`** (Phase 3 section) and **`docs/phase-3-autonomy/`** for the full Phase 3 plan. A detailed Phase 3 step-by-step guide can be added there when you start implementing.
