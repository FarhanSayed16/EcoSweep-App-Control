# Phase 3: Production Integration (ecosweep_manual_final.py)

You integrated Phase-3 autonomy into your **production bridge** (`ecosweep_manual_final.py`) instead of running the repo’s `ecosweep_bridge.py`. That’s the right choice: one process owns Bluetooth and Arduino, no duplicate bridges.

---

## Critical fix: serial write from two threads

**Problem:** Two threads write to the same Arduino serial port without coordination:

1. **Main loop** – when the app sends manual commands: `arduino.write((line + "\n").encode())`
2. **autonomy_loop** – when AUTO_MODE is on: `arduino.write(cmd.encode())` or `arduino.write(b"M:0,0\n")`

If both write at the same time, bytes can interleave (e.g. `M:100,0\n` + `M:0,0\n` → `M:M:100,0\n0,0\n`), so the Arduino can receive invalid or mixed commands.

**Fix:** Use a **single lock** for all Arduino writes. Every place that does `arduino.write(...)` must hold that lock.

1. Add near the top (with other globals):
   ```python
   serial_lock = threading.Lock()
   ```
2. In the **main loop**, when forwarding to Arduino:
   ```python
   if arduino:
       try:
           with serial_lock:
               arduino.write((line + "\n").encode())
       except:
           pass
   ```
3. In **autonomy_loop**, for every `arduino.write(...)`:
   ```python
   try:
       with serial_lock:
           arduino.write(b"M:0,0\n")   # or cmd.encode() etc.
   except:
       pass
   ```

Apply this pattern to **all** `arduino.write` calls in both the main loop and `autonomy_loop`. After this, your integration is safe from serial contention.

---

## What you did right

- One bridge process: Bluetooth + Arduino + autonomy in `ecosweep_manual_final.py`.
- YOLO writes `/tmp/ecosweep_detection.json`; autonomy reads it (~10 Hz).
- MODE:AUTO_ON / MODE:AUTO_OFF from the app; when AUTO_ON, manual lines are skipped so only autonomy drives.
- Person detection → stop (safety).
- Low confidence → slow turn (search).
- MOVE_LEFT / MOVE_RIGHT / CENTERED → turn or forward.

---

## How to test (step by step)

### 1. Manual mode (AUTO_OFF)

- Start `ecosweep_manual_final.py` on the Pi.
- Connect the app over Bluetooth.
- **Do not** turn on Autonomous mode.
- Use the joystick: robot should move exactly as before (forward, turn, stop).
- If this fails, fix manual control before testing autonomy.

### 2. Autonomy with no garbage (search)

- Ensure `yolo_fpv_stream_optimized.py` is running (so `/tmp/ecosweep_detection.json` exists and has `decision: "NONE"` or low confidence).
- In the app, turn **Autonomous** mode ON (MODE:AUTO_ON).
- Robot should **slowly rotate** (your `M:0,60` when confidence < 0.4). No forward dash.
- Turn Autonomous OFF; robot should stop and manual control should work again.

### 3. Autonomy with garbage in frame

- Point the camera at a bottle/cup (garbage class).
- Turn Autonomous ON.
- Robot should **turn** toward the object (MOVE_LEFT / MOVE_RIGHT) and then **move forward** when CENTERED.
- If it never centers or overshoots, tune in YOLO (CENTER_MARGIN_PX) or in the bridge (APPROACH_SPEED, TURN_SPEED).

### 4. Safety: person in frame

- With Autonomous ON, show a person to the camera (or a clear “person” detection).
- Robot should **stop** (M:0,0) and not move until person is gone or you turn AUTO_OFF.

### 5. FPV and detection file (optional)

- On the Pi: `cat /tmp/ecosweep_detection.json` (run a few times while camera sees different things). You should see `decision`, `confidence`, `person_detected` change.
- In the app, open FPV: you should see the YOLO stream; when autonomous, the robot should react to what’s in that view.

---

## Next steps (optional improvements)

1. **Ultrasonic “close” stop**  
   If your Arduino sends `DATA:SENSORS:front,left,right` (cm), parse it in the main loop and pass `front` into autonomy (or a shared variable). In autonomy, when `decision == "CENTERED"` and `front < 25` (or your chosen cm), stop forward and optionally run a short gripper sequence (see below).

2. **Gripper pickup sequence**  
   When aligned and close, send:
   - `SA:GRIP_CLOSE_START` (or your Arduino’s close command)
   - wait 1–2 s
   - `SA:GRIP_CLOSE_STOP`
   - then `M:0,0` and go back to search (e.g. set a “pickup done” state and then send slow turn again).

3. **State machine (SEARCH → APPROACH → ALIGN → PICKUP)**  
   Your current logic is “one decision per tick”. For more stable behavior you can add explicit states (e.g. only allow forward when “centered for N ticks” or “front < 25 cm”), then transition to a short PICKUP state (gripper) and back to SEARCH. The repo’s `phase3/autonomy.py` is an example you can mirror in `ecosweep_manual_final.py` if you want.

4. **Logging**  
   Add simple prints in autonomy_loop (e.g. decision, confidence, person_detected) or log to a file so you can confirm behavior when testing.

---

## Checklist

- [ ] Add `serial_lock` and use it around **every** `arduino.write()` in main loop and autonomy_loop.
- [ ] Test manual mode (AUTO_OFF) – joystick full control.
- [ ] Test AUTO_ON with no garbage – slow rotate only.
- [ ] Test AUTO_ON with garbage – turn then forward.
- [ ] Test person in frame – robot stops.
- [ ] (Optional) Add ultrasonic-based stop and gripper sequence when close and centered.

Once the serial lock is in place and the tests pass, your Phase-3 production integration is in good shape.
