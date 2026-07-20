# EcoSweep Autonomy: Complete Logic Review and Issue List

**Purpose:** Thorough analysis of the autonomy logic across Bridge, YOLO, and Arduino. Documents all identified issues, root causes, and proposed fixes. **Do not implement until approved.**

---

## 1. Data Flow Overview

```
YOLO (yolo_fpv_stream_optimized.py)
    → writes /tmp/ecosweep_detection.json
Bridge (ecosweep_manual_final_patched.py)
    → reads detection, runs state machine
    → sends M:speed,turn and SA: commands over serial
Arduino (EcoSweep_Master.ino)
    → parses M:speed,turn, applies gear and TURN_SIGN
    → left = speed + turn, right = speed - turn
```

---

## 2. YOLO Detection Logic

| Output | Formula | Notes |
|--------|---------|-------|
| `bbox_center_x` | `(x1 + x2) / 2` | X center of best garbage box |
| `frame_center` | `FRAME_WIDTH / 2 = 320` | For 640px width |
| `bbox_area` | `(x2 - x1) × (y2 - y1)` | Pixels² |
| `decision` | `MOVE_LEFT` if bbox_cx < 285 | `MOVE_RIGHT` if bbox_cx > 355, else `CENTERED` |

- Runs YOLO every **2 frames** (`YOLO_EVERY_N_FRAMES = 2`). Detection file can be stale for ~100ms.
- `CENTER_MARGIN_PX = 35` in YOLO and Bridge must match (they do).

---

## 3. Bridge Autonomy Logic (Current)

### 3.1 State Machine

| State | Entry | Action | Exit |
|-------|-------|--------|------|
| IDLE | AUTO off | Stop | AUTO on → SEARCH |
| SEARCH | No garbage | Rotate ±75, flip every 1.2s | Garbage seen → APPROACH_FAR or APPROACH_CLOSE |
| APPROACH_FAR | bbox < 40,000 | Speed 70, proportional turn | bbox ≥ 40k → APPROACH_CLOSE; pickup ready → PICKUP |
| APPROACH_CLOSE | 40k ≤ bbox < 55k | Speed 40, proportional turn | pickup ready → PICKUP |
| PICKUP | bbox ≥ 55k, centered, stable 5 frames | Creep → arm down → grip → arm up | → RECOVER |
| RECOVER | After PICKUP | Back up, turn, | → SEARCH |
| STOP | Person or obstacle | Stop | Clear → RECOVER |

### 3.2 Proportional Turn (Bridge)

```python
error = bbox_cx - frame_center
turn_raw = PROPORTIONAL_GAIN * error
turn_raw = clamp(turn_raw, -80, 80)
if 0 < turn_raw < 35:  turn_raw = 35
if -35 < turn_raw < 0: turn_raw = -35
# Then:
turn = turn * TURN_LEFT_SIGN  if turn <= 0 else turn * TURN_RIGHT_SIGN
```

- Object left (bbox_cx < 320): error < 0 → turn_raw < 0 → we want turn left.
- Arduino: positive turn → turn right; negative turn → turn left. So turn_raw sign matches intent.
- `TURN_LEFT_SIGN` and `TURN_RIGHT_SIGN` invert the final value. Use -1 only if robot turns away from the object.

### 3.3 Arduino Motor Logic

```cpp
left  = speed + turn
right = speed - turn
turn is scaled by TURN_SIGN (default +1)
```

- Positive turn → left faster, right slower → robot turns right.
- Negative turn → left slower, right faster → robot turns left.

---

## 4. Identified Issues

### 4.1 [CRITICAL] Threshold Naming and Redundancy

**Issue:** `FAR_BBOX = 40000` and `SLOW_APPROACH_BBOX = 40000` are identical. `FAR_BBOX` is never used in the code.

**Impact:** Confusing; easy to change one and break behavior.

**Fix:** Remove `FAR_BBOX` or unify naming. Use a single constant, e.g. `APPROACH_CLOSE_BBOX = 40000`.

---

### 4.2 [CRITICAL] Turn Sign Calibration

**Issue:** With `TURN_LEFT_SIGN = -1` and `TURN_RIGHT_SIGN = -1`, the bridge inverts the turn. Whether this is correct depends on:

- Camera left/right vs. robot left/right
- Possible mirroring (camera or stream)
- Arduino `TURN_SIGN`

**Math:**
- Object left → error < 0 → turn_raw < 0 (desired: turn left).
- With `TURN_LEFT_SIGN = 1`: send negative → Arduino turns left ✓
- With `TURN_LEFT_SIGN = -1`: send positive → Arduino turns right ✗ (away from object)

So `-1` makes the robot turn away if the nominal math is correct. Use `-1` only if the robot physically turns the wrong way with `+1`.

**Fix:** Add a calibration procedure and document all four combinations:
- (1, 1)
- (-1, -1)
- (1, -1)
- (-1, 1)

---

### 4.3 [HIGH] Motor Stop on Detection Loss

**Issue:** In APPROACH_FAR/APPROACH_CLOSE, when `has_garbage` is false we send `M:0,0` and `continue`. Detection can flicker (occlusion, YOLO every 2 frames).

**Impact:** Robot stops on every brief detection loss, causing jerky stop-go.

**Fix:** Add a short grace period (e.g. 0.2s) before stopping. Keep last valid (speed, turn) until timeout, then stop.

---

### 4.4 [HIGH] PICKUP_BBOX_LOST_THRESHOLD Too Low

**Issue:** `PICKUP_BBOX_LOST_THRESHOLD = 38000` vs `PICKUP_BBOX_MIN = 55000`. On loss, we trigger PICKUP if `last_centered_bbox_area >= 38000` and `time_since_lost` in 0.05–0.8s.

**Impact:** Pickup can fire when the object was only ~38k (smaller than normal 55k), possibly too far for the arm.

**Fix:** Raise to ~48000–50000, or align with a clearer “almost close enough” condition.

---

### 4.5 [HIGH] Autonomy M Commands Bypass Throttle

**Issue:** App M commands go through `_pending_m` and `M_TO_ARDUINO_INTERVAL = 0.08` (12 Hz). Autonomy calls `_write_arduino()` directly every loop (≈10 Hz).

**Impact:** M commands can be sent faster than intended. With more autonomy activity, Arduino serial buffer could overflow.

**Fix:** Route autonomy M commands through the same throttle, or add a separate throttle in the autonomy loop.

---

### 4.6 [MEDIUM] PICKUP Blocks Loop

**Issue:** PICKUP state uses `time.sleep()` for creep, arm down, grip, arm up (~3.4 s total). During this time the autonomy loop does not run.

**Impact:** AUTO_MODE off during pickup will not stop the sequence until it finishes.

**Fix:** Break PICKUP into smaller steps with per-step `AUTO_MODE` checks, or use a non-blocking state machine with timers.

---

### 4.7 [MEDIUM] Boundary at bbox_area = 40000

**Issue:** `bbox_area < SLOW_APPROACH_BBOX` selects APPROACH_FAR; `bbox_area >= SLOW_APPROACH_BBOX` selects APPROACH_CLOSE. At exactly 40000, behavior depends on evaluation order.

**Current:** Transition to APPROACH_CLOSE happens in `if bbox_area >= SLOW_APPROACH_BBOX` inside the APPROACH block. One iteration can be FAR, the next CLOSE. Acceptable, but worth documenting.

**Fix:** Keep as is, but ensure FAR/CLOSE logic is consistent with the chosen convention (e.g. use `<` vs `>=` explicitly).

---

### 4.8 [MEDIUM] Stuck Detection Disabled When Ultrasonic Off

**Issue:** When `ULTRASONIC_OBSTACLE_ENABLED = False`, the stuck check is skipped and `stuck_since = now` every loop. Robot never transitions to RECOVER from stuck.

**Impact:** If the robot gets stuck (e.g. against a wall) without ultrasonics, it will not recover.

**Fix:** Add a non-ultrasonic stuck heuristic (e.g. no bbox growth for several seconds when approaching).

---

### 4.9 [LOW] Minimum Turn Can Cause Oscillation

**Issue:** `ALIGN_TURN = 35` forces a minimum turn when error is small. Near center (e.g. error 10 px), we still apply ±35.

**Impact:** Robot can oscillate when almost centered.

**Fix:** Add a dead zone: if `abs(error) < DEADZONE_PX` (e.g. 15), use turn = 0.

---

### 4.10 [LOW] frame_center Default

**Issue:** Bridge uses `det.get("frame_center", 320)`. If YOLO changes `FRAME_WIDTH` but the default is not updated, they can diverge.

**Fix:** Use `det.get("frame_width", 640) / 2` or share frame config between YOLO and bridge.

---

### 4.11 [LOW] Detection Staleness

**Issue:** YOLO updates the detection file only when it runs (every 2 frames). Bridge reads on each loop (100ms). Old detections can persist up to ~100–200 ms.

**Impact:** Slight lag in reactions; acceptable for current speeds.

**Fix:** Optional: add a timestamp check and treat detections older than 0.5 s as invalid.

---

### 4.12 [LOW] SEARCH Uses search_direction, RECOVER Flips It

**Issue:** RECOVER does `search_direction *= -1` after turning. SEARCH uses `search_direction` for the next search. Logic is fine, but the interaction is subtle.

**Fix:** Add comments or a small diagram clarifying the flow.

---

## 5. Proposed Fixes (Priority Order)

| # | Issue | File | Proposed Change |
|---|--------|------|------------------|
| 1 | Turn sign | Bridge | Document calibration; try (1,1) first, then (-1,-1) if robot turns away |
| 2 | Redundant constants | Bridge | Remove FAR_BBOX or unify with SLOW_APPROACH_BBOX |
| 3 | Jerky stop on loss | Bridge | Grace period (0.2s) before stopping on detection loss |
| 4 | Lost threshold too low | Bridge | Raise PICKUP_BBOX_LOST_THRESHOLD to ~48000 |
| 5 | M command throttle | Bridge | Throttle autonomy M commands (reuse or mirror app throttle) |
| 6 | PICKUP blocking | Bridge | Add AUTO_MODE checks between PICKUP steps |
| 7 | Dead zone | Bridge | Add center dead zone (e.g. 15 px) to reduce oscillation |
| 8 | Stuck without ultrasonic | Bridge | Add bbox-area-based stuck heuristic |

---

## 6. Diagnostic Checklist (Before Changing Code)

1. **Turn direction:** With object on left, does the robot turn left or right? If right → invert.
2. **Forward direction:** Does positive speed move the robot toward the camera view?
3. **Camera orientation:** Is the camera axis aligned with robot forward? Mirrored?
4. **Detection stability:** Does the green box flicker? If yes, consider grace period.
5. **Arduino signs:** Check `LEFT_MOTOR_SIGN`, `RIGHT_MOTOR_SIGN`, `TURN_SIGN` in Arduino.

---

## 7. File References

| File | Role |
|------|------|
| `hardware/pi/ecosweep_manual_final_patched.py` | Autonomy state machine, proportional turn |
| `hardware/pi/phase2/yolo_fpv_stream_optimized.py` | YOLO, detection file writer |
| `hardware/arduino/EcoSweep_Master/EcoSweep_Master.ino` | Motor control, M:speed,turn |

---

## 8. Implementation Status (All 8 Fixes Applied)

| # | Fix | Status |
|---|-----|--------|
| 1 | Turn sign (1,1) + calibration comments | Done |
| 2 | Removed FAR_BBOX, use APPROACH_CLOSE_BBOX | Done |
| 3 | Grace period 0.2s on detection loss | Done |
| 4 | PICKUP_BBOX_LOST_THRESHOLD 38000→48000 | Done |
| 5 | Throttle autonomy M commands | Done |
| 6 | PICKUP/RECOVER check AUTO_MODE, abort to IDLE | Done |
| 7 | Center dead zone 15 px | Done |
| 8 | Bbox-based stuck when ultrasonic off | Done |

**If robot still turns away from object:** Set `TURN_LEFT_SIGN = -1` and `TURN_RIGHT_SIGN = -1` in the bridge script.

---

## 9. Next Steps

1. Copy updated `ecosweep_manual_final_patched.py` to Pi (see ECOSWEEP-UPDATE-PI-FROM-PC.md).
2. Restart `ecosweep-bridge` service.
3. Run diagnostic checklist and test.

---

*Document version: 1.1 | Implementation complete*
