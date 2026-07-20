# EcoSweep Autonomy — Baby Steps Rebuild Plan

> **Philosophy:** Build autonomy one layer at a time. Each step adds exactly ONE new behavior. You test after each step. If it breaks, we know exactly which layer caused it.

---

## How It Works

A single constant at the top of the bridge file controls which autonomy features are active:

```python
AUTONOMY_STEP = 0   # Change this to enable each step (0–6)
```

| Step | What it does | What to test |
|------|-------------|--------------|
| **0** | All autonomy disabled. Manual control only. | "Can I drive the robot from the app?" |
| **1** | SEARCH: robot rotates in place (no detection) | "Does the robot spin left/right when I tap Auto ON?" |
| **2** | Detection read: logs what YOLO sees, stops on detection | "Does the log print when I put a bottle in front of the camera?" |
| **3** | Basic approach: drives straight forward when object detected | "Does the robot move forward toward the bottle?" |
| **4** | Steering: turns toward the object using PD controller | "Does the robot actually aim at the bottle, not wander?" |
| **5** | Pickup: arm sequence when close enough | "Does the arm reach down and grab?" |
| **6** | Full loop: recover + search again after pickup | "Does the robot back up and start looking for the next object?" |

---

## Step 0 — Baseline: Disable All Autonomy

**Goal:** Verify the bridge runs, app connects, manual control works, and YOLO is writing detections.

**What we change:** Set `AUTONOMY_STEP = 0`. The autonomy loop does nothing except log that it's alive.

**Test checklist:**
- [ ] Bridge starts without errors: `sudo python3 -u ecosweep_manual_final.py`
- [ ] App connects over Bluetooth
- [ ] Manual joystick drives the robot (forward, backward, turn)
- [ ] Robotic arm works manually from app
- [ ] YOLO is running: `cat /tmp/ecosweep_detection.json` shows fresh data with a recent timestamp
- [ ] Tapping "Auto ON" in app prints `AUTO_MODE ON` in bridge log but robot does NOT move

> [!IMPORTANT]
> **Do NOT proceed to Step 1 until all Step 0 checks pass.** If manual control doesn't work, autonomy never will.

---

## Step 1 — SEARCH: Rotate in Place

**Goal:** When Auto ON, the robot slowly rotates left for 2.5s, then right for 2.5s, scanning for objects. No detection logic.

**What we add:**
- Send `GEAR:3` when AUTO_ON (full motor power)
- Send `M:0,turn` (pure rotation, no forward movement) in the SEARCH state
- Flip direction every `SEARCH_TURN_DURATION_S`

**Test checklist:**
- [ ] Tap Auto ON → robot starts rotating in place
- [ ] Robot rotates smoothly (not jerky)
- [ ] Robot alternates direction every ~2.5s
- [ ] Tap Auto OFF → robot stops immediately
- [ ] Log shows `GEAR:3` sent on Auto ON, `GEAR:1` on Auto OFF

> [!WARNING]
> If the robot doesn't rotate at all, check:
> 1. Is the Arduino connected? (`Arduino connected on /dev/ttyUSB0` in log)
> 2. Are motors enabled? (Manual joystick should work in Step 0)
> 3. Is `GEAR:3` being sent? (Check log)

---

## Step 2 — Detection Read: Log and Stop

**Goal:** Robot rotates (Step 1) AND reads YOLO detections. When garbage is detected, robot STOPS and logs what it sees. No approach yet.

**What we add:**
- Read `/tmp/ecosweep_detection.json`
- Check timestamp staleness (reject if >1s old)
- If `has_garbage` → stop motors, log bbox details
- If garbage disappears → resume rotation

**Test checklist:**
- [ ] Robot rotates (Step 1 behavior)
- [ ] Place a bottle in front of camera → robot STOPS
- [ ] Log prints: `STEP2: Garbage detected! decision=CENTERED bbox_cx=320 area=25000 conf=0.65`
- [ ] Remove the bottle → robot resumes rotating
- [ ] Log prints detection data every 0.5s while object is visible
- [ ] Cover the camera (simulate YOLO failure) → robot keeps rotating (stale data rejected)

> **Key question after this step:** "Is the YOLO detection file being read correctly? Do the logged bbox values make sense?"

---

## Step 3 — Basic Approach: Drive Forward

**Goal:** When garbage is detected AND centered, drive STRAIGHT FORWARD (no steering). When object is not centered, just stop and log.

**What we add:**
- If `is_centered` → send `M:speed,0` (forward only, zero turn)
- If not centered → stop and log "Object is LEFT/RIGHT, offset=X px"
- Speed depends on bbox_area (far → fast, close → slow)

**Test checklist:**
- [ ] Place bottle directly in front of robot, centered in camera
- [ ] Robot drives straight toward it
- [ ] Robot speed decreases as it gets closer (bbox_area grows)
- [ ] Move bottle to the left → robot STOPS and log says "Object is LEFT, offset=100px"
- [ ] Move bottle back to center → robot resumes forward
- [ ] Robot stops when object lost (removed from view)

> **Key question:** "Does the robot actually move forward when a centered object is detected? How fast? Does it feel responsive or laggy?"

---

## Step 4 — Steering: Turn Toward Object

**Goal:** Instead of stopping when the object is off-center, the robot turns toward it. This is where the PD controller comes in.

**What we add:**
- PD turn calculation based on bbox offset from frame center
- Stop-turn-go: if object is far off-center (>50px), stop forward and turn in place
- If close to centered, drive forward + gentle turn correction
- Detection loss grace period (0.6s coast)

**Test checklist:**
- [ ] Place bottle to the LEFT → robot turns LEFT toward it
- [ ] Place bottle to the RIGHT → robot turns RIGHT toward it
- [ ] Once centered, robot drives forward
- [ ] Robot doesn't oscillate (wobble left-right-left)
- [ ] Briefly cover camera (0.5s) → robot coasts, then resumes when object reappears
- [ ] Remove object for 2s+ → robot goes back to SEARCH rotation

> [!CAUTION]
> **This is the critical step.** If the robot turns the WRONG direction (e.g., object on left but robot turns right), tell me and we'll flip `TURN_LEFT_SIGN = -1`. If it oscillates wildly, we'll lower `PROPORTIONAL_GAIN`.

> **Key questions:**
> 1. "When bottle is on the left, does the robot turn left or right?"
> 2. "Does it oscillate or smoothly center on the object?"
> 3. "Does it drive toward the object once centered?"

---

## Step 5 — Pickup: Arm Sequence

**Goal:** When the object is close enough (large bbox + centered), stop and run the arm pickup sequence.

**What we add:**
- Pickup trigger: `bbox_area >= PICKUP_BBOX_MIN` AND `is_centered` for 3 stable frames
- Full arm sequence: open → lower → extend → creep → grip → retract → raise
- Dispose: rotate arm → release → return to home
- Resume SEARCH after pickup

**Test checklist:**
- [ ] Let robot approach until close → log shows `PICKUP: starting full sequence`
- [ ] Gripper opens first
- [ ] Arm lowers toward ground
- [ ] Forearm extends forward
- [ ] Robot creeps forward slightly
- [ ] Gripper closes around object
- [ ] Arm raises with object
- [ ] Arm rotates and releases
- [ ] All servos return to home (90°)

> **Key questions:**
> 1. "Does the arm reach the ground?" (If not → increase `PICKUP_ARM_DOWN_S`)
> 2. "Does the gripper close on the object?" (If not → increase `PICKUP_GRIP_CLOSE_S`)
> 3. "Does the pickup trigger too early/late?" (Tell me the bbox_area from logs when you think it should trigger)

---

## Step 6 — Full Loop: Recover + Search Again

**Goal:** After pickup (or when stuck), back up, turn, and start searching again. Full autonomy cycle.

**What we add:**
- RECOVER state: back up for 0.5s, turn, enter SEARCH
- Pickup cooldown (2s ignore after pickup)
- Pickup retry (if object still detected after grab, try once more)
- Lost-detection-to-pickup shortcut (if bbox was large + suddenly lost → assume close, try pickup)

**Test checklist:**
- [ ] After pickup, robot backs up
- [ ] Robot turns and starts searching again
- [ ] Place another object → robot finds and approaches it
- [ ] Full cycle: search → approach → pickup → recover → search works continuously

---

## Debug Commands Reference

Run these on the Pi to debug any step:

```bash
# Watch bridge logs live
sudo journalctl -u ecosweep-bridge.service -f

# Or run bridge manually with full output
sudo systemctl stop ecosweep-bridge.service
sudo python3 -u /home/pi/ecosweep_manual_final.py 2>&1 | tee /tmp/bridge_debug.log

# Check YOLO detection file
cat /tmp/ecosweep_detection.json | python3 -m json.tool

# Watch YOLO update rate
watch -n 0.5 cat /tmp/ecosweep_detection.json

# Check if YOLO service is running
sudo systemctl status ecosweep-yolo.service

# Check if Arduino is connected
ls -la /dev/ttyUSB* /dev/ttyACM*
```

---

## Important Notes

> [!IMPORTANT]
> - **Test one step at a time.** Don't skip ahead.
> - **After each step, tell me:** what worked, what didn't, and the exact log output.
> - **The `AUTONOMY_STEP` constant** is the only thing you change between tests. No other code changes until we discuss.
> - **Manual control always works** regardless of `AUTONOMY_STEP` value — it's unaffected.
> - All existing complex logic (EMA smoothing, stuck detection, etc.) is disabled until Step 6. We keep it simple first.
