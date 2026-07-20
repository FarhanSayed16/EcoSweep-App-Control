# EcoSweep Autonomy: Behavior Analysis and Improvement Plan

**Purpose:** Document what is happening, what should happen, issues, and mathematical corrections for the approach-and-pickup logic.

---

## 1. Expected Behavior (What Should Happen)

When an object is detected in the **green bounding box** (YOLO detection):

1. **Straight-line approach:** Robot should move **toward** the object in a straight line, correcting heading so the object stays centered in the camera view.
2. **Continuous detection:** Robot keeps detecting and adjusting until the object fills a maximum area (bbox_area ≥ PICKUP_BBOX_MIN) and is centered.
3. **Precise pickup:** Once conditions are met, the robotic arm should pick up the object at a precise, aligned location.

**Desired flow:**
```
Object detected (green box) → Robot turns TOWARD object → Drives FORWARD → 
Object grows in frame (centered) → Slows down → Aligns precisely → PICKUP
```

---

## 2. Current Behavior (What Is Happening)

**Reported symptom:** Robot moves **away** from the object or does **not** move toward it properly.

Possible manifestations:
- Robot turns in the wrong direction (away from the object)
- Robot drives backward instead of forward
- Robot oscillates or fails to center on the object
- Robot does not slow down as it gets close
- Pickup happens at wrong position (arm misses the object)

---

## 3. Current Logic (How It Works Today)

### 3.1 YOLO Detection (yolo_fpv_stream_optimized.py)

| Output | Description |
|--------|-------------|
| `bbox_center_x` | Center X of bounding box: `(x1 + x2) / 2` |
| `frame_center` | Frame center: `FRAME_WIDTH / 2 = 320` (for 640 px) |
| `bbox_area` | `(x2 - x1) × (y2 - y1)` in pixels² |
| `decision` | `MOVE_LEFT` if bbox_cx < 285; `MOVE_RIGHT` if bbox_cx > 355; `CENTERED` otherwise |

**Formula:**
```
CENTER_MARGIN_PX = 35
bbox_cx < frame_center - 35  →  MOVE_LEFT   (object on left side of frame)
bbox_cx > frame_center + 35  →  MOVE_RIGHT  (object on right side)
else                         →  CENTERED
```

### 3.2 Autonomy States (ecosweep_manual_final_patched.py)

| State | Condition | Action |
|-------|-----------|--------|
| SEARCH | No garbage | Rotate slowly (turn ±75) |
| APPROACH_FAR | bbox_area < 40,000 | Drive forward 70; turn only if off-center > 90 px |
| APPROACH_CLOSE | 40k ≤ bbox < 55k | Drive forward 40; proportional steering |
| PICKUP | bbox ≥ 55k, centered, stable 5 frames | Creep → arm down → grip → arm up |
| RECOVER | After pickup | Back up, turn, SEARCH |

### 3.3 Proportional Turn Calculation

```python
error = bbox_cx - frame_center
turn_raw = PROPORTIONAL_GAIN * error
turn_raw = clamp(turn_raw, -APPROACH_TURN_MAX, APPROACH_TURN_MAX)
# Minimum turn threshold
if 0 < turn_raw < ALIGN_TURN:  turn_raw = ALIGN_TURN
if -ALIGN_TURN < turn_raw < 0: turn_raw = -ALIGN_TURN
return turn_raw * TURN_LEFT_SIGN or TURN_RIGHT_SIGN
```

**Intended mapping:**
- Object on **left** (bbox_cx < 320): error < 0 → turn < 0 → robot turns **left** (toward object)
- Object on **right** (bbox_cx > 320): error > 0 → turn > 0 → robot turns **right** (toward object)
- Arduino: `left = speed + turn`, `right = speed - turn` → positive turn = turn right, negative = turn left

### 3.4 Distance Stages (bbox_area)

| bbox_area (px²) | Stage | Speed | Steering |
|-----------------|-------|-------|----------|
| < 40,000 | APPROACH_FAR | 70 | Turn only if \|offset\| > 90 px |
| 40,000–55,000 | APPROACH_CLOSE | 40 | Proportional |
| ≥ 55,000 + centered | PICKUP | Creep 25 | None (straight) |

---

## 4. Identified Issues and Root Causes

### 4.1 Turn Direction Inverted (Most Likely Cause of "Moving Away")

**Symptom:** Robot turns away from the object instead of toward it.

**Causes:**
- **Camera left/right inverted:** If the camera view is mirrored (e.g., selfie mode), left in image = right in real world.
- **Robot chassis orientation:** Motors or chassis may be mounted such that "left" and "right" are swapped relative to the camera.
- **Arduino TURN_SIGN:** Arduino uses `TURN_SIGN`; Pi uses `TURN_LEFT_SIGN` and `TURN_RIGHT_SIGN`. If these are wrong, turn direction flips.

**Fix:** Set `TURN_LEFT_SIGN = -1` and/or `TURN_RIGHT_SIGN = -1` in the bridge script (lines 77–78) to invert turn. Try one at a time.

---

### 4.2 Forward Direction Inverted

**Symptom:** Robot drives backward when it should drive forward.

**Causes:**
- Motor wiring: positive speed may drive the robot backward.
- Camera facing the "rear" of the robot: in that case, moving "forward" by motor command would move the robot away from what the camera sees.

**Fix:** In Arduino, invert the speed sign for forward, or physically verify motor wiring and camera orientation.

---

### 4.3 APPROACH_FAR: No Turn When Slightly Off-Center

**Current logic:** In APPROACH_FAR, turn is applied only if `bbox_off_center_px > FAR_TURN_MARGIN_PX` (90 px).

**Issue:** If the object is 50 px off-center, the robot drives straight. It may never align, and the object can drift out of frame.

**Improvement:** Always apply a small corrective turn in APPROACH_FAR, or reduce `FAR_TURN_MARGIN_PX` so corrections start sooner.

---

### 4.4 Proportional Gain Too Low or Too High

**PROPORTIONAL_GAIN = 0.5**

- If too low: Robot corrects slowly; object drifts; may never center.
- If too high: Robot over-corrects; oscillates; unstable approach.

**Improvement:** Tune gain based on tests. A common starting point is `gain = 2 * MAX_TURN / FRAME_WIDTH` (e.g., 2 × 80 / 640 ≈ 0.25). Current 0.5 may be acceptable; test with 0.3–0.8.

---

### 4.5 Centering Uses Only X (Ignore Y)

**Current:** Steering uses only `bbox_cx` and `frame_center`. Vertical position (`bbox_cy`) is ignored.

**Effect:** Object can be centered horizontally but too high or too low. The arm may not reach it. Not the main cause of "moving away," but affects pickup precision.

**Improvement (future):** Consider arm tilt or robot height if the object is consistently too high/low.

---

### 4.6 Pickup Position Assumptions

**Current:** Pickup is triggered when:
- bbox_area ≥ 55,000
- decision == CENTERED (±35 px)
- front ultrasonic < 18 cm (or disabled)
- Stable for 5 frames

**Issue:** The arm’s physical reach and the camera’s field of view may not align. The object may be centered in the image but not under the gripper.

**Improvement:** Calibrate `PICKUP_BBOX_MIN` and `FRONT_CLOSE_CM` for your robot’s geometry. Optionally add a small forward creep before arm activation.

---

## 5. Mathematical Summary

### 5.1 Steering Error

```
frame_center = FRAME_WIDTH / 2 = 320
error_x = bbox_cx - frame_center

error_x > 0  →  Object on right  →  Turn right (positive)
error_x < 0  →  Object on left   →  Turn left (negative)
```

### 5.2 Proportional Control

```
turn = Kp × error_x
turn = clamp(turn, -TURN_MAX, +TURN_MAX)
```

Suggested: `Kp = (2 × TURN_MAX) / FRAME_WIDTH` for roughly one full turn at maximum lateral error.

### 5.3 Distance Proxy (bbox_area)

```
As robot approaches: object subtends larger angle → bbox grows.
bbox_area ∝ 1 / distance²  (approximately, for frontal view)
```

Thresholds are empirical. Recalibrate if your camera height or lens differs.

### 5.4 Correction for Inverted Turn

If the robot turns the wrong way:

```
turn_corrected = -turn_raw   # Invert sign
# Or use TURN_LEFT_SIGN = -1, TURN_RIGHT_SIGN = -1
```

---

## 6. Action Items (Priority Order)

| # | Action | File | Purpose |
|---|--------|------|---------|
| 1 | Set `TURN_LEFT_SIGN = -1` and/or `TURN_RIGHT_SIGN = -1` | ecosweep_manual_final_patched.py | Fix inverted turn direction |
| 2 | Reduce `FAR_TURN_MARGIN_PX` from 90 to 50–60 | ecosweep_manual_final_patched.py | Start turning sooner when off-center |
| 3 | Always apply proportional turn in APPROACH_FAR (remove margin gate) | ecosweep_manual_final_patched.py | Smoother approach |
| 4 | Add diagnostic logging (state, bbox_cx, error, turn) | ecosweep_manual_final_patched.py | Debug from logs |
| 5 | Verify camera orientation and motor forward direction | Physical | Ensure "forward" and "left/right" match camera |
| 6 | Tune `PROPORTIONAL_GAIN` (0.3–0.8) | ecosweep_manual_final_patched.py | Reduce oscillation or increase responsiveness |
| 7 | Calibrate `PICKUP_BBOX_MIN` and `FRONT_CLOSE_CM` | ecosweep_manual_final_patched.py | Precise pickup position |

---

## 7. Testing Procedure

1. **Manual test:** Place object in center of frame. Enable AUTO. Robot should drive straight forward.
2. **Left test:** Place object on left side. Robot should turn left first, then drive forward.
3. **Right test:** Place object on right side. Robot should turn right first, then drive forward.
4. **If robot turns away:** Invert `TURN_LEFT_SIGN` and `TURN_RIGHT_SIGN` (set to -1).
5. **If robot drives backward:** Check Arduino motor wiring and speed sign.
6. **Logging:** Add `print(f"state={state} bbox_cx={bbox_cx} error={error} turn={turn}")` in the autonomy loop for live debugging.

---

## 8. File References

| File | Role |
|------|------|
| `hardware/pi/ecosweep_manual_final_patched.py` | Autonomy logic, proportional turn, state machine |
| `hardware/pi/phase2/yolo_fpv_stream_optimized.py` | Detection, bbox_cx, decision (MOVE_LEFT/RIGHT/CENTERED) |
| `hardware/arduino/EcoSweep_Master/EcoSweep_Master.ino` | Motor control, M:speed,turn, TURN_SIGN |

---

## 9. Deploy to Raspberry Pi from PC

See **[ECOSWEEP-UPDATE-PI-FROM-PC.md](ECOSWEEP-UPDATE-PI-FROM-PC.md)** for:

- Copy `ecosweep_manual_final_patched.py` to Pi via SCP
- Restart `ecosweep-bridge` service
- Watch debug logs with `journalctl`

---

*Document version: 1.0 | Created for EcoSweep autonomy debugging and improvement*
