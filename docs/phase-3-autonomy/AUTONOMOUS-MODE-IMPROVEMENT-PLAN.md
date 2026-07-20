# Autonomous Mode — Improvement Plan

Plan to improve autonomy: accurate movement, robotic arm pickup, obstacle avoidance, and precision.

**Status: Implemented.** Changes are in `ecosweep_manual_final_patched.py` and `yolo_fpv_stream_optimized.py`.

---

## Current Issues

| Issue | Description |
|-------|-------------|
| **1. Movement accuracy** | Tires not turning accurately toward object; approach not smooth. |
| **2. Robotic arm** | 5-axis arm not working in auto mode; not picking up objects. |
| **3. Speed / precision** | Speed and alignment not fine enough for reliable pickup. |
| **4. Turning** | Object detection works but wheel turning / steering is off. |
| **5. Obstacle avoidance** | Ultrasonic and camera-based avoidance should be used properly. |

---

## Planned Improvements

### 1. Proportional Steering (Smoother Turning)

**Problem:** Bridge uses fixed `TURN_SPEED` (80). Object at 1px off-center gets same turn as 100px off-center.

**Change:** Use `bbox_center_x` from detection file to compute turn proportional to error.

| File | Change |
|------|--------|
| `yolo_fpv_stream_optimized.py` | Already writes `bbox_center_x`. No change. |
| `ecosweep_manual_final_patched.py` | Read `bbox_center_x`, compute `error = bbox_cx - frame_center`, send `M:0,turn` where `turn` is proportional to error. |

---

### 2. Speed Tiers (More Precise Approach)

**Problem:** Same speed for approach and fine alignment; robot overshoots or is too slow.

**Change:** Add separate speeds:
- **SEARCH:** Slow (e.g. 30) + turn
- **APPROACH:** Medium (e.g. 70) when object far
- **APPROACH_CLOSE:** Slow (e.g. 40) when front &lt; 40 cm
- **ALIGN:** Very slow turn (e.g. 30)

| File | Change |
|------|--------|
| `ecosweep_manual_final_patched.py` | Add constants, use tiered speeds in each state. |

---

### 3. Robotic Arm Pickup (Proper Sequence)

**Problem:** Arm sequence exists but may not run correctly or reach the object.

**Changes:**
- Ensure we are close enough: `FRONT_CLOSE_CM` tuned (e.g. 15–20 cm) so arm can reach.
- Add optional **base rotation** to aim arm at object before pickup.
- Use `S:id,angle` presets if SA continuous movement is unreliable.
- Add short **forward creep** before pickup so object is under gripper.
- Lengthen gripper close time if needed.

| File | Change |
|------|--------|
| `ecosweep_manual_final_patched.py` | Tune `FRONT_CLOSE_CM`, `PICKUP_*` timings; optional forward creep; optional base turn. |
| Arduino | No change if SA commands work; may need servo timing tweaks in firmware. |

---

### 4. Obstacle Avoidance (Ultrasonic + Camera)

**Current:** Ultrasonic stops when `front < FRONT_SAFE_CM`; person stops when `person_detected`.

**Improvements:**
- Use **left** and **right** ultrasonics: if front blocked, try turn toward clearer side.
- Camera: treat other large objects (e.g. chair, couch) as obstacles if YOLO detects them.
- Add **stuck detection**: if moving forward but front distance not decreasing, back up and turn.

| File | Change |
|------|--------|
| `yolo_fpv_stream_optimized.py` | Optionally add `obstacle_detected` (e.g. chair, couch) to detection JSON. |
| `ecosweep_manual_final_patched.py` | Use left/right telemetry for smarter recovery; add stuck detection; use `obstacle_detected` if added. |

---

### 5. Turning Direction and Center Margin

**Problem:** Robot may turn wrong way or oscillate around center.

**Changes:**
- Add configurable **turn sign**: `TURN_LEFT_SIGN`, `TURN_RIGHT_SIGN` (+1 or -1) to fix inverted steering.
- Tune `CENTER_MARGIN_PX` in YOLO: smaller = stricter center, larger = looser.

| File | Change |
|------|--------|
| `ecosweep_manual_final_patched.py` | Add turn sign constants. |
| `yolo_fpv_stream_optimized.py` | `CENTER_MARGIN_PX` tunable (e.g. 25–40). |

---

### 6. Detection File — Extra Data for Autonomy

**Current:** `decision`, `confidence`, `person_detected`, `bbox_center_x`, `bbox_center_y`, `timestamp`.

**Add (optional):**
- `bbox_area` or `bbox_height` — object size (closer = larger).
- `obstacle_detected` — if YOLO sees chair, table, etc.

| File | Change |
|------|--------|
| `yolo_fpv_stream_optimized.py` | Add `bbox_area`; optionally add obstacle classes and `obstacle_detected`. |

---

## Implementation Order

1. **Proportional steering** — smoother turns toward object.
2. **Speed tiers** — better approach and alignment.
3. **Turn sign + center margin** — fix wrong direction and wobble.
4. **Pickup tuning** — distance, creep, timings.
5. **Obstacle avoidance** — left/right ultrasonic, stuck detection.
6. **Camera obstacles** — optional YOLO obstacle classes.

---

## Files to Update (Summary)

| File | Improvements |
|------|--------------|
| `ecosweep_manual_final_patched.py` | Proportional turn, speed tiers, turn sign, pickup tuning, left/right avoidance, stuck detection |
| `yolo_fpv_stream_optimized.py` | CENTER_MARGIN_PX, bbox_area, optional obstacle_detected |

After changes, update **ECOSWEEP-PI-COMPLETE-SETUP-GUIDE.md** and deploy both files to the Pi.
