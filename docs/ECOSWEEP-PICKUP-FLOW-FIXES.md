# EcoSweep Pickup Flow: What’s Wrong and What to Change

**Desired flow:**
1. Robot moves toward detected object
2. Robot stops at a short distance so the arm can reach
3. Arm picks up the object precisely
4. Robot holds, moves backward, then throws the garbage

---

## 1. Current vs Desired Flow

| Step | Desired | Current | Gap |
|------|---------|---------|-----|
| 1 | Move toward object | ✓ APPROACH_FAR / APPROACH_CLOSE | Turn direction may be wrong (use TURN_LEFT/RIGHT_SIGN if needed) |
| 2 | Stop at close distance | Uses bbox_area ≥ 55k + centered | Distance may be too far or too close for your arm |
| 3 | Creep to final position | 0.4 s creep at speed 25 | Fixed time/distance; may overshoot or undershoot |
| 4 | Arm picks precisely | Arm down → Grip close → Arm up | No base/wrist alignment; object may not be under gripper |
| 5 | Hold and back up | ✓ Back up 0.5 s | OK |
| 6 | Throw garbage | ✗ Missing | Gripper is never opened; no throw step |

---

## 2. Main Problems

### 2.1 No Throw Step

- After pickup, the code goes to RECOVER: backup → turn → SEARCH.
- Gripper is never opened; object stays in gripper.
- Need to add a THROW phase: backup → turn toward bin/drop zone → open gripper → continue.

### 2.2 Stop Distance Not Reliable

- When ultrasonic is disabled, stop is based only on:
  - `bbox_area ≥ 55,000`
  - Object centered (±35 px)
- `bbox_area` depends on object size and camera, so the real distance can vary a lot.
- Result: robot often stops too far (arm can’t reach) or too close (overshoot).

### 2.3 Creep is Fixed Time, Not Distance

- `PICKUP_CREEP_DURATION_S = 0.4` with `PICKUP_CREEP_SPEED = 25`.
- Distance is fixed regardless of object size/position.
- Result: final position may not be under the gripper.

### 2.4 Arm Alignment

- Arm moves down → grip → up, but base and wrist are not aligned to the object.
- Object center is only used for steering; arm joints are not adjusted.
- Result: gripper may miss the object even when robot stops correctly.

---

## 3. Recommended Changes (by Priority)

### 3.1 Add Throw Phase (Critical)

**Location:** `hardware/pi/ecosweep_manual_final_patched.py`, PICKUP / RECOVER logic

**Change:**
- After arm up, add a THROW phase before SEARCH:
  1. Keep holding object
  2. Back up (already done)
  3. Optional: turn toward drop zone (bin)
  4. `SA:GRIP_OPEN_START` for ~0.5 s
  5. `SA:GRIP_OPEN_STOP`
  6. Then continue to SEARCH

**New constants:**
```python
THROW_GRIP_OPEN_S = 0.5  # Duration to open gripper (release object)
```

---

### 3.2 Calibrate Stop Distance (High)

**Location:** Bridge constants

**Tunables:**
- `PICKUP_BBOX_MIN` (currently 55,000) – lower = stop further, higher = stop closer
- `FRONT_CLOSE_CM` (18 cm) – only used when ultrasonic enabled
- `PICKUP_CREEP_SPEED` and `PICKUP_CREEP_DURATION_S` – final approach before arm

**Process:**
1. Place a typical object at arm’s reach.
2. Note its bbox_area in logs.
3. Set `PICKUP_BBOX_MIN` so the robot stops when bbox_area ≈ that value.
4. Adjust creep so the object ends under the gripper.

---

### 3.3 Tune Creep (High)

**Current:** 0.4 s at speed 25 (fixed creep).

**Ideas:**
- If overshoot: shorten `PICKUP_CREEP_DURATION_S` or lower `PICKUP_CREEP_SPEED`.
- If undershoot: lengthen duration or increase speed.
- Or: remove creep and rely on bbox_area to stop closer.

---

### 3.4 Optional: Arm Pre-positioning (Medium, Future)

To improve precision:
- Use `bbox_cx` to rotate the base so the object is in front of the gripper.
- Use `bbox_cy` (vertical) to set arm angle.
- Would require a mapping from pixel coords to servo angles.

---

## 4. Quick Fix Summary

| Fix | File | Action |
|-----|------|--------|
| Add throw | ecosweep_manual_final_patched.py | In RECOVER, after backup and turn, add `SA:GRIP_OPEN_START` → wait → `SA:GRIP_OPEN_STOP` |
| Calibrate stop | ecosweep_manual_final_patched.py | Tune `PICKUP_BBOX_MIN` (try 45k–65k) from real tests |
| Tune creep | ecosweep_manual_final_patched.py | Adjust `PICKUP_CREEP_DURATION_S` and `PICKUP_CREEP_SPEED` from tests |

---

## 5. Proposed RECOVER Sequence (With Throw)

```
RECOVER:
  1. Back up (BACKUP_DURATION_S)
  2. Stop
  3. Turn toward clearer side (or fixed throw direction)
  4. Stop
  5. SA:GRIP_OPEN_START
  6. Wait THROW_GRIP_OPEN_S
  7. SA:GRIP_OPEN_STOP
  8. → SEARCH
```

---

*Document version: 1.0 | Pickup flow analysis*
