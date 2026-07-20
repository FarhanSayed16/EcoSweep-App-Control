# -*- coding: utf-8 -*-
# Patched version: telemetry parsing, obstacle detection (camera + ultrasonic), arm PICKUP.
# Copy to Pi as ecosweep_manual_final.py (back up original first).

import sys
import bluetooth
import serial
import socket
import time
import threading
import subprocess
import os
import json
from threading import Lock

BIND_RETRY_SEC = 5
BIND_RETRY_MAX = 6
# Throttle telemetry to app (prevents Bluetooth overload / disconnect)
TELEMETRY_INTERVAL = 0.15  # Max ~6–7 Hz to app
KEEPALIVE_INTERVAL = 1.5   # Send keepalive when no Arduino data for this many seconds
M_TO_ARDUINO_INTERVAL = 0.08  # Throttle M: commands to Arduino (max ~12 Hz) to avoid buffer overflow

SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
# Android SPP expects channel 1
RFCOMM_CHANNEL = 1

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "sounds")
ENGINE_IDLE = os.path.join(SOUNDS_DIR, "engine_idle.wav")
ENGINE_G1 = os.path.join(SOUNDS_DIR, "engine_gear1.wav")
ENGINE_G2 = os.path.join(SOUNDS_DIR, "engine_gear2.wav")
ENGINE_G3 = os.path.join(SOUNDS_DIR, "engine_gear3.wav")
SHIFT_WAV = os.path.join(SOUNDS_DIR, "shift.wav")
TURBO_WAV = os.path.join(SOUNDS_DIR, "turbo.wav")

arduino = None
client_sock = None
server_sock = None
engine_proc = None
current_gear = 1
moving = False

AUTO_MODE = False
auto_lock = Lock()
serial_lock = threading.Lock()
telemetry_lock = Lock()
telemetry = {"front": 999, "left": 999, "right": 999, "updated": 0.0}

DETECTION_FILE = "/tmp/ecosweep_detection.json"
# ============================================================
# AUTONOMY STEP LEVEL — Change this to enable features one-by-one
# 0 = disabled (manual only)   1 = search rotation only
# 2 = search + detect-stop     3 = search + forward approach (no steering)
# 4 = search + PD steering     5 = + pickup arm sequence
# 6 = full loop (pickup + recover + repeat)
# ============================================================
AUTONOMY_STEP = 0   # <-- START HERE, test, then increment
# --- Autonomy tuning (improved) ---
# Speed tiers (higher = more visible movement; Arduino gear scale still applies)
SEARCH_SPEED = 40
SEARCH_TURN = 50
APPROACH_SPEED_FAR = 50       # When object far (was 70 — too fast, lost detection)
APPROACH_SPEED_CLOSE = 30     # When front < FRONT_APPROACH_CLOSE_CM
APPROACH_TURN_MAX = 55
TRACKING_TURN_MAX = 35        # Gentler max turn during APPROACH_FAR (prevents blur)
TRACKING_TURN_CLOSE = 20      # Even gentler when APPROACH_CLOSE (less oscillation)
ALIGN_TURN = 30               # Fine-tune turn when close
SPEED_RAMP_MAX = 15           # Max speed change per 100ms cycle (smooth acceleration)
# Obstacle / safety
ULTRASONIC_OBSTACLE_ENABLED = False  # TEMP: set True to re-enable once sensor works
FURNITURE_OBSTACLE_ENABLED = False   # Stop on chair/couch etc; False = less strict, you manage
FRONT_SAFE_CM = 15            # Stop if front < this
FRONT_APPROACH_CLOSE_CM = 40  # Switch to slow approach
FRONT_CLOSE_CM = 18           # Close enough for pickup (arm reach)
# Distance stages by bbox_area (pixels²)
APPROACH_CLOSE_BBOX = 40000   # bbox < this = APPROACH_FAR; >= this = APPROACH_CLOSE
PICKUP_BBOX_MIN = 65000       # Higher = must be closer before pickup (was 55000)
PICKUP_BBOX_LOST_THRESHOLD = 55000  # Lost detection but had bbox >= this = was close, try pickup
PICKUP_STABLE_FRAMES = 3      # Conditions must hold N frames before PICKUP (was 5)
FAR_TURN_MARGIN_PX = 55       # APPROACH_FAR: start turning sooner (was 90)
CENTER_MARGIN_PX = 35         # CENTERED = within this many pixels of frame center
SEARCH_TURN_DURATION_S = 2.5  # Wider sweeps to cover more area (was 1.2)
SEARCH_FORWARD_BURST_S = 0.5  # Drive forward briefly between sweeps
SEARCH_FORWARD_SPEED = 40     # Slow forward during burst
GARBAGE_MIN_CONF = 0.35  # Match YOLO CONF_THRESHOLD properly (no hack)
NO_DETECTION_TIMEOUT_S = 3.5
DETECTION_LOSS_GRACE_S = 1.0  # Coast 1s on brief loss
# Tracking memory: bridge remembers last detection for this long
MEMORY_TIMEOUT_S = 1.5        # Trust memory for 1.5s max
MEMORY_DECAY_RATE = 0.92      # Slower decay = memory lasts longer (was 0.85)
STUCK_TIMEOUT_S = 3.0         # If no progress toward object
# PD steering (proportional + derivative for smooth, fast centering)
PROPORTIONAL_GAIN = 0.55      # Gentler P response (was 0.85 — too aggressive)
DERIVATIVE_GAIN = 0.20        # More damping to reduce overshoot (was 0.15)
CENTER_DEADZONE_PX = 12       # Tighter deadzone for precision (was 15)
TURN_ONLY_THRESHOLD_PX = 80   # If offset > this, stop driving and only turn (was 50)
# Calibration: +1 = nominal; -1 = invert (use if robot turns AWAY from object)
TURN_LEFT_SIGN = 1
TURN_RIGHT_SIGN = 1
# Detection smoothing (exponential moving average)
EMA_ALPHA = 0.4  # 0.0 = ignore new data, 1.0 = no smoothing. 0.4 = good balance.
# Pickup sequence timings (tune on real hardware)
PICKUP_CREEP_SPEED = 25
PICKUP_CREEP_DURATION_S = 0.6   # Longer creep = closer to object before gripping (was 0.3)
PICKUP_GRIP_OPEN_S = 0.6         # Open gripper before lowering
PICKUP_ARM_DOWN_S = 1.0           # Longer to reach ground (was 0.5)
PICKUP_FOREARM_FORWARD_S = 0.8    # Extend forearm toward ground
PICKUP_GRIP_CLOSE_S = 2.0         # Slightly longer for firm grip (was 1.8)
PICKUP_FOREARM_RETRACT_S = 0.5    # Retract forearm after gripping
PICKUP_ARM_UP_S = 1.0             # Longer to fully raise (was 0.6)
PICKUP_DISPOSE_BASE_TURN_S = 0.5  # Rotate arm to dump side
PICKUP_DISPOSE_OPEN_S = 0.5       # Release object
PICKUP_DISPOSE_BASE_RETURN_S = 0.5  # Return arm to center
BACKUP_SPEED = -70
BACKUP_DURATION_S = 0.5
PICKUP_COOLDOWN_S = 2.0           # Avoid re-targeting same spot after pickup
# Set True to log autonomy state/bbox/error/turn (for debugging)
DEBUG_AUTONOMY = True
DEBUG_AUTONOMY_INTERVAL_S = 0.5  # Log at most every N seconds
# Phase 0 verification: log when IMU/MQ telemetry is received (throttled)
# Phase 0: Log when IMU/MQ packets are forwarded (for app Advanced Sensors card)
TELEMETRY_LOG_IMU_MQ = True
TELEMETRY_LOG_IMU_MQ_INTERVAL_S = 5.0
_last_imu_mq_log_time = 0.0


def _log(msg):
    print(msg, flush=True)
    sys.stdout.flush()
    sys.stderr.flush()


def reset_bluetooth_adapter():
    sudo = "" if os.geteuid() == 0 else "sudo "
    os.system(sudo + "hciconfig hci0 down")
    time.sleep(1)
    os.system(sudo + "hciconfig hci0 up")
    os.system(sudo + "hciconfig hci0 piscan")
    os.system(sudo + "sdptool add SP")
    time.sleep(1)


def play_once(path):
    try:
        if os.path.isfile(path):
            subprocess.Popen(["aplay", "-q", path])
    except Exception:
        pass


def start_loop(path):
    global engine_proc
    stop_loop()
    try:
        if os.path.isfile(path):
            engine_proc = subprocess.Popen(
                ["bash", "-lc", f"while true; do aplay -q '{path}'; done"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def stop_loop():
    global engine_proc
    if engine_proc:
        try:
            engine_proc.terminate()
            engine_proc.wait(timeout=0.5)
        except Exception:
            try:
                engine_proc.kill()
            except Exception:
                pass
    engine_proc = None


def engine_loop_for_gear(gear):
    if gear == 1:
        return ENGINE_G1
    if gear == 2:
        return ENGINE_G2
    if gear == 3:
        return ENGINE_G3
    return ENGINE_IDLE


def connect_arduino():
    global arduino
    ports = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyAMA0"]
    for port in ports:
        try:
            if os.path.exists(port):
                arduino = serial.Serial(port, 9600, timeout=1)
                time.sleep(2)
                _log(f"Arduino connected on {port}")
                return True
        except Exception as e:
            _log(f"Arduino {port}: {e}")
    _log("Arduino: NOT connected - using keepalive for app")
    return False


def _write_arduino(cmd):
    """Thread-safe Arduino write."""
    if not arduino:
        return
    try:
        with serial_lock:
            if isinstance(cmd, str):
                arduino.write((cmd.strip() + "\n").encode())
            else:
                arduino.write(cmd if cmd.endswith(b"\n") else cmd + b"\n")
    except Exception:
        pass


def _parse_telemetry(line):
    """Parse DATA:SENSORS:front,left,right and update shared telemetry."""
    if not line or not line.strip().startswith("DATA:SENSORS:"):
        return
    try:
        parts = line.strip().split(":", 2)[2].split(",")
        if len(parts) >= 3:
            f, l, r = int(parts[0]), int(parts[1]), int(parts[2])
            with telemetry_lock:
                telemetry["front"] = f
                telemetry["left"] = l
                telemetry["right"] = r
                telemetry["updated"] = time.time()
    except (ValueError, IndexError):
        pass


def _get_telemetry():
    """Thread-safe copy of telemetry."""
    with telemetry_lock:
        return dict(telemetry)


_prev_error = 0.0  # Module-level for derivative calculation


def _pd_turn(bbox_cx, frame_center):
    """PD controller: proportional + derivative for smooth, fast centering."""
    global _prev_error
    error = bbox_cx - frame_center
    if abs(error) < CENTER_DEADZONE_PX:
        _prev_error = error
        return 0

    # P term
    p_term = PROPORTIONAL_GAIN * error
    # D term (rate of change of error - dampens oscillation)
    d_term = DERIVATIVE_GAIN * (error - _prev_error)
    _prev_error = error

    turn_raw = int(p_term + d_term)
    turn_raw = max(-APPROACH_TURN_MAX, min(APPROACH_TURN_MAX, turn_raw))

    # Minimum turn so robot actually rotates when slightly off-center
    if 0 < turn_raw < ALIGN_TURN:
        turn_raw = ALIGN_TURN
    elif -ALIGN_TURN < turn_raw < 0:
        turn_raw = -ALIGN_TURN
    return turn_raw


def _sleep_check_auto(duration_s):
    """Sleep in small chunks; return False if AUTO_MODE turned off (abort), True otherwise."""
    step = 0.1
    elapsed = 0.0
    while elapsed < duration_s:
        with auto_lock:
            if not AUTO_MODE:
                return False
        time.sleep(min(step, duration_s - elapsed))
        elapsed += step
    return True


def _recovery_turn(left_cm, right_cm):
    """Turn toward clearer side based on left/right ultrasonics. Negative=left, positive=right."""
    if left_cm < 0:
        left_cm = 999
    if right_cm < 0:
        right_cm = 999
    if left_cm >= right_cm:
        return -ALIGN_TURN * TURN_LEFT_SIGN  # Turn left
    return ALIGN_TURN * TURN_RIGHT_SIGN      # Turn right


def autonomy_loop():
    """
    Step-based autonomy loop. Controlled by AUTONOMY_STEP constant.
    Step 0: Disabled (just log alive)
    Step 1: SEARCH only (rotate in place)
    Step 2: SEARCH + detect-and-stop (log detections)
    Step 3: SEARCH + approach forward when centered (no steering)
    Step 4: SEARCH + approach with PD steering
    Step 5: SEARCH + approach + pickup arm sequence
    Step 6: Full loop (search + approach + pickup + recover)
    """
    global AUTO_MODE

    state = "SEARCH"
    search_direction = 1
    last_search_flip_time = 0.0
    last_no_garbage_time = 0.0
    last_garbage_time = 0.0
    last_debug_log_time = 0.0
    last_approach_speed = 0
    last_approach_turn = 0
    last_seen_bbox_area = 0
    last_centered_bbox_area = 0
    last_bbox_growth_time = 0.0
    pickup_stable_count = 0
    stuck_since = 0.0
    last_front_for_stuck = 999
    pickup_retry_count = 0
    # Tracking memory state
    mem_cx = 0.0
    mem_area = 0.0
    mem_time = 0.0
    mem_conf = 0.0
    mem_decision = "NONE"
    mem_used_count = 0
    # Detection hysteresis
    consecutive_detection_count = 0

    _log(f"Autonomy loop started. AUTONOMY_STEP = {AUTONOMY_STEP}")

    while True:
        time.sleep(0.1)

        # ---- Check if AUTO_MODE is on ----
        with auto_lock:
            if not AUTO_MODE:
                if state != "IDLE":
                    _write_arduino("M:0,0")
                    state = "IDLE"
                    last_search_flip_time = 0.0
                continue

        if state == "IDLE":
            state = "SEARCH"
            last_search_flip_time = 0.0

        now = time.time()

        # ======== STEP 0: Do nothing (just verify loop runs) ========
        if AUTONOMY_STEP <= 0:
            if (now - last_debug_log_time) >= 2.0:
                _log("STEP0: Autonomy loop alive but disabled (AUTONOMY_STEP=0)")
                last_debug_log_time = now
            continue

        # ======== STEP 1+: Read detection file ========
        try:
            with open(DETECTION_FILE, "r") as f:
                det = json.load(f)
        except Exception:
            det = {}

        decision = det.get("decision", "NONE")
        confidence = det.get("confidence", 0.0)
        raw_bbox_cx = det.get("bbox_center_x", 0)
        raw_bbox_area = det.get("bbox_area", 0)
        frame_center = det.get("frame_center", 320)

        # Reject stale detection data
        det_age = now - det.get("timestamp", 0)
        if det_age > 1.5:
            decision = "NONE"
            confidence = 0.0

        has_garbage = (decision in ("MOVE_LEFT", "MOVE_RIGHT", "CENTERED")
                       and confidence >= GARBAGE_MIN_CONF)
        bbox_cx = raw_bbox_cx
        bbox_area = raw_bbox_area
        is_centered = has_garbage and abs(bbox_cx - frame_center) < CENTER_MARGIN_PX

        # ---- Tracking Memory: if YOLO lost detection, use memory ----
        if has_garbage:
            # Fresh detection → update memory
            mem_cx = bbox_cx
            mem_area = bbox_area
            mem_time = now
            mem_conf = confidence
            mem_decision = decision
            mem_used_count = 0
        elif (not has_garbage and mem_time > 0
              and (now - mem_time) < MEMORY_TIMEOUT_S
              and AUTONOMY_STEP >= 4 and state in ("APPROACH_FAR", "APPROACH_CLOSE")):
            # No fresh detection but memory is valid → use it
            mem_conf *= MEMORY_DECAY_RATE
            mem_used_count += 1
            if mem_conf >= GARBAGE_MIN_CONF:
                bbox_cx = mem_cx
                bbox_area = mem_area
                decision = mem_decision
                confidence = mem_conf
                has_garbage = True
                is_centered = abs(bbox_cx - frame_center) < CENTER_MARGIN_PX
                if mem_used_count <= 3:  # Log first few memory uses
                    _log(f"MEMORY: using last known cx={mem_cx:.0f} area={mem_area:.0f} "
                         f"conf={mem_conf:.2f} age={now - mem_time:.1f}s")

        # ======== STEP 1: SEARCH only (rotate in place) ========
        if AUTONOMY_STEP == 1:
            if last_search_flip_time == 0:
                last_search_flip_time = now
            if now - last_search_flip_time >= SEARCH_TURN_DURATION_S:
                search_direction *= -1
                last_search_flip_time = now
            turn = SEARCH_TURN * search_direction
            _write_arduino_m_throttled(f"M:0,{turn}")  # Pure rotation, no forward
            if (now - last_debug_log_time) >= 1.0:
                _log(f"STEP1: SEARCH dir={search_direction} turn={turn}")
                last_debug_log_time = now
            continue

        # ======== STEP 2: SEARCH + detect-and-stop ========
        if AUTONOMY_STEP == 2:
            if has_garbage:
                _write_arduino("M:0,0")  # STOP when object seen
                if (now - last_debug_log_time) >= 0.5:
                    _log(f"STEP2: DETECTED! decision={decision} bbox_cx={bbox_cx:.0f} "
                         f"area={bbox_area:.0f} conf={confidence:.2f} "
                         f"centered={is_centered} frame_center={frame_center}")
                    last_debug_log_time = now
            else:
                # Rotate to search
                if last_search_flip_time == 0:
                    last_search_flip_time = now
                if now - last_search_flip_time >= SEARCH_TURN_DURATION_S:
                    search_direction *= -1
                    last_search_flip_time = now
                turn = SEARCH_TURN * search_direction
                _write_arduino_m_throttled(f"M:0,{turn}")
                if (now - last_debug_log_time) >= 1.0:
                    _log(f"STEP2: searching... dir={search_direction} det_age={det_age:.1f}s")
                    last_debug_log_time = now
            continue

        # ======== STEP 3: SEARCH + approach forward (no steering) ========
        if AUTONOMY_STEP == 3:
            if has_garbage:
                if is_centered:
                    # Drive STRAIGHT forward (no turn)
                    speed = APPROACH_SPEED_CLOSE if bbox_area >= APPROACH_CLOSE_BBOX else APPROACH_SPEED_FAR
                    _write_arduino_m_throttled(f"M:{speed},0")
                    if (now - last_debug_log_time) >= 0.5:
                        _log(f"STEP3: FORWARD speed={speed} bbox_cx={bbox_cx:.0f} "
                             f"area={bbox_area:.0f} centered=YES")
                        last_debug_log_time = now
                else:
                    # Object visible but NOT centered — STOP and log offset
                    _write_arduino("M:0,0")
                    offset = bbox_cx - frame_center
                    side = "LEFT" if offset < 0 else "RIGHT"
                    if (now - last_debug_log_time) >= 0.5:
                        _log(f"STEP3: STOP - object is {side}, offset={offset:.0f}px "
                             f"bbox_cx={bbox_cx:.0f} fc={frame_center}")
                        last_debug_log_time = now
            else:
                # Rotate to search
                _write_arduino("M:0,0")
                if last_search_flip_time == 0:
                    last_search_flip_time = now
                if now - last_search_flip_time >= SEARCH_TURN_DURATION_S:
                    search_direction *= -1
                    last_search_flip_time = now
                turn = SEARCH_TURN * search_direction
                _write_arduino_m_throttled(f"M:0,{turn}")
            continue

        # ======== STEP 4+: Full approach with PD steering ========
        if AUTONOMY_STEP >= 4:

            # ---- SEARCH state ----
            if state == "SEARCH":
                _send_state_to_app(state)
                if has_garbage:
                    consecutive_detection_count += 1
                    if consecutive_detection_count >= 2:  # Hysteresis: 2 consecutive frames
                        state = "APPROACH_FAR" if bbox_area < APPROACH_CLOSE_BBOX else "APPROACH_CLOSE"
                        last_garbage_time = now
                        last_no_garbage_time = 0.0
                        last_seen_bbox_area = bbox_area
                        last_centered_bbox_area = bbox_area if is_centered else 0
                        last_bbox_growth_time = now
                        stuck_since = now
                        last_front_for_stuck = 999
                        pickup_stable_count = 0
                        consecutive_detection_count = 0
                        _log(f"STEP{AUTONOMY_STEP}: target acquired! state={state} area={bbox_area:.0f}")
                else:
                    consecutive_detection_count = 0  # Reset on miss
                    if last_search_flip_time == 0:
                        last_search_flip_time = now
                    elapsed_search = now - last_search_flip_time
                    if elapsed_search >= SEARCH_TURN_DURATION_S + SEARCH_FORWARD_BURST_S:
                        search_direction *= -1
                        last_search_flip_time = now
                    elif elapsed_search >= SEARCH_TURN_DURATION_S:
                        _write_arduino_m_throttled(f"M:{SEARCH_FORWARD_SPEED},0")
                    else:
                        turn = SEARCH_TURN * search_direction
                        _write_arduino_m_throttled(f"M:0,{turn}")
                continue

            # ---- APPROACH_FAR / APPROACH_CLOSE ----
            if state in ("APPROACH_FAR", "APPROACH_CLOSE"):
                _send_state_to_app(state)

                # Lost detection?
                if not has_garbage:
                    if last_no_garbage_time == 0:
                        last_no_garbage_time = now
                    time_since_lost = now - last_no_garbage_time

                    if AUTONOMY_STEP >= 5 and (
                        last_centered_bbox_area >= PICKUP_BBOX_LOST_THRESHOLD and
                        time_since_lost < 0.8 and time_since_lost > 0.05):
                        # Object was large + centered, suddenly gone → try pickup
                        state = "PICKUP"
                        _write_arduino("M:0,0")
                        _log(f"STEP{AUTONOMY_STEP}: lost detection near target, trying PICKUP")
                    elif time_since_lost > NO_DETECTION_TIMEOUT_S:
                        state = "SEARCH"
                        _write_arduino("M:0,0")
                        _log(f"STEP{AUTONOMY_STEP}: lost detection for {time_since_lost:.1f}s, back to SEARCH")
                    elif time_since_lost <= DETECTION_LOSS_GRACE_S:
                        # Coast gently, no turn
                        grace_speed = max(last_approach_speed // 2, 15) if last_approach_speed > 0 else 0
                        _write_arduino_m_throttled(f"M:{grace_speed},0")
                    else:
                        _write_arduino("M:0,0")
                    continue

                # Have detection
                last_garbage_time = now
                last_no_garbage_time = 0.0
                if bbox_area > last_seen_bbox_area:
                    last_bbox_growth_time = now
                last_seen_bbox_area = max(last_seen_bbox_area, bbox_area)
                if is_centered:
                    last_centered_bbox_area = max(last_centered_bbox_area, bbox_area)

                # Stuck heuristic (bbox not growing for STUCK_TIMEOUT_S)
                if not ULTRASONIC_OBSTACLE_ENABLED:
                    if (last_seen_bbox_area > 10000 and
                        now - last_bbox_growth_time > STUCK_TIMEOUT_S):
                        if AUTONOMY_STEP >= 6:
                            state = "RECOVER"
                            _write_arduino("M:0,0")
                            search_direction = 1 if bbox_cx >= frame_center else -1
                            _log(f"STEP{AUTONOMY_STEP}: stuck, recovering")
                            continue
                        else:
                            state = "SEARCH"
                            _write_arduino("M:0,0")
                            continue

                # Check pickup readiness (Step 5+)
                if AUTONOMY_STEP >= 5:
                    pickup_ready = (
                        bbox_area >= PICKUP_BBOX_MIN and
                        is_centered
                    )
                    if pickup_ready:
                        pickup_stable_count += 1
                        if pickup_stable_count >= PICKUP_STABLE_FRAMES:
                            state = "PICKUP"
                            _write_arduino("M:0,0")
                            pickup_stable_count = 0
                            _log(f"STEP{AUTONOMY_STEP}: PICKUP triggered! area={bbox_area:.0f}")
                            continue
                    else:
                        pickup_stable_count = 0

                # Switch to APPROACH_CLOSE if bbox big enough
                if bbox_area >= APPROACH_CLOSE_BBOX:
                    state = "APPROACH_CLOSE"

                # PD steering + tracking turn cap
                turn = _pd_turn(bbox_cx, frame_center)
                turn = int(turn * TURN_LEFT_SIGN) if turn <= 0 else int(turn * TURN_RIGHT_SIGN)
                # Clamp turn based on state: gentler when close
                max_turn = TRACKING_TURN_CLOSE if state == "APPROACH_CLOSE" else TRACKING_TURN_MAX
                turn = max(-max_turn, min(max_turn, turn))

                if state == "APPROACH_FAR":
                    if abs(bbox_cx - frame_center) > TURN_ONLY_THRESHOLD_PX:
                        target_speed = 0
                    else:
                        target_speed = APPROACH_SPEED_FAR
                else:
                    if abs(bbox_cx - frame_center) > TURN_ONLY_THRESHOLD_PX:
                        target_speed = 0
                    elif abs(bbox_cx - frame_center) > CENTER_MARGIN_PX:
                        target_speed = APPROACH_SPEED_CLOSE // 2
                    else:
                        target_speed = APPROACH_SPEED_CLOSE

                # Speed ramping: smooth acceleration/deceleration
                if target_speed > last_approach_speed:
                    fwd_speed = min(target_speed, last_approach_speed + SPEED_RAMP_MAX)
                elif target_speed < last_approach_speed:
                    fwd_speed = max(target_speed, last_approach_speed - SPEED_RAMP_MAX)
                else:
                    fwd_speed = target_speed

                last_approach_speed = fwd_speed
                last_approach_turn = turn
                _write_arduino_m_throttled(f"M:{fwd_speed},{turn}")

                if DEBUG_AUTONOMY and (now - last_debug_log_time) >= DEBUG_AUTONOMY_INTERVAL_S:
                    err = bbox_cx - frame_center
                    _log(f"STEP{AUTONOMY_STEP}: {state} cx={bbox_cx:.0f} fc={frame_center} "
                         f"err={err:.0f} turn={turn} spd={fwd_speed} area={bbox_area:.0f}")
                    last_debug_log_time = now
                continue

            # ---- PICKUP (Step 5+) ----
            if state == "PICKUP" and AUTONOMY_STEP >= 5:
                _send_state_to_app(state)
                _log("PICKUP: starting full sequence")
                _write_arduino("M:0,0")

                # Open gripper
                _write_arduino("SA:GRIP_OPEN_START")
                if not _sleep_check_auto(PICKUP_GRIP_OPEN_S):
                    _write_arduino("SA:GRIP_OPEN_STOP"); _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("SA:GRIP_OPEN_STOP")

                # Lower arm
                _write_arduino("SA:ARM_DOWN_START")
                if not _sleep_check_auto(PICKUP_ARM_DOWN_S):
                    _write_arduino("SA:ARM_DOWN_STOP"); _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("SA:ARM_DOWN_STOP")

                # Extend forearm
                _write_arduino("SA:FOREARM_FORWARD_START")
                if not _sleep_check_auto(PICKUP_FOREARM_FORWARD_S):
                    _write_arduino("SA:FOREARM_FORWARD_STOP"); _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("SA:FOREARM_FORWARD_STOP")

                # Creep forward
                _write_arduino(f"M:{PICKUP_CREEP_SPEED},0")
                if not _sleep_check_auto(PICKUP_CREEP_DURATION_S):
                    _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("M:0,0")
                _sleep_check_auto(0.1)

                # Close gripper
                _write_arduino("SA:GRIP_CLOSE_START")
                if not _sleep_check_auto(PICKUP_GRIP_CLOSE_S):
                    _write_arduino("SA:GRIP_CLOSE_STOP"); _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("SA:GRIP_CLOSE_STOP")

                # Retract forearm
                _write_arduino("SA:FOREARM_BACKWARD_START")
                if not _sleep_check_auto(PICKUP_FOREARM_RETRACT_S):
                    _write_arduino("SA:FOREARM_BACKWARD_STOP"); _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("SA:FOREARM_BACKWARD_STOP")

                # Raise arm
                _write_arduino("SA:ARM_UP_START")
                if not _sleep_check_auto(PICKUP_ARM_UP_S):
                    _write_arduino("SA:ARM_UP_STOP"); _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("SA:ARM_UP_STOP")

                # Dispose: rotate, release, return
                _write_arduino("SA:BASE_RIGHT_START")
                if not _sleep_check_auto(PICKUP_DISPOSE_BASE_TURN_S):
                    _write_arduino("SA:BASE_RIGHT_STOP"); _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("SA:BASE_RIGHT_STOP")

                _write_arduino("SA:GRIP_OPEN_START")
                if not _sleep_check_auto(PICKUP_DISPOSE_OPEN_S):
                    _write_arduino("SA:GRIP_OPEN_STOP"); state = "IDLE"; continue
                _write_arduino("SA:GRIP_OPEN_STOP")

                _write_arduino("SA:BASE_LEFT_START")
                if not _sleep_check_auto(PICKUP_DISPOSE_BASE_RETURN_S):
                    _write_arduino("SA:BASE_LEFT_STOP"); state = "IDLE"; continue
                _write_arduino("SA:BASE_LEFT_STOP")

                # Reset servos home
                for servo_id in range(5):
                    _write_arduino(f"S:{servo_id},90")
                    time.sleep(0.05)

                _log("PICKUP: sequence complete")
                _write_arduino("M:0,0")

                # Retry if object still there (Step 6)
                if AUTONOMY_STEP >= 6:
                    time.sleep(0.3)
                    try:
                        with open(DETECTION_FILE, "r") as f:
                            post_det = json.load(f)
                        post_has = (post_det.get("decision", "NONE") in
                                    ("MOVE_LEFT", "MOVE_RIGHT", "CENTERED")
                                    and post_det.get("confidence", 0) >= GARBAGE_MIN_CONF)
                    except Exception:
                        post_has = False
                    if post_has and pickup_retry_count < 1:
                        _log("PICKUP: object still detected, retrying approach")
                        pickup_retry_count += 1
                        state = "APPROACH_CLOSE"
                        continue
                    else:
                        pickup_retry_count = 0

                _sleep_check_auto(PICKUP_COOLDOWN_S)
                if AUTONOMY_STEP >= 6:
                    state = "RECOVER"
                else:
                    state = "SEARCH"
                continue

            # ---- RECOVER (Step 6 only) ----
            if state == "RECOVER" and AUTONOMY_STEP >= 6:
                _send_state_to_app(state)
                _write_arduino(f"M:{BACKUP_SPEED},0")
                if not _sleep_check_auto(BACKUP_DURATION_S):
                    _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("M:0,0")
                turn = SEARCH_TURN * search_direction
                _write_arduino(f"M:0,{turn}")
                if not _sleep_check_auto(0.4):
                    _write_arduino("M:0,0"); state = "IDLE"; continue
                _write_arduino("M:0,0")
                state = "SEARCH"
                search_direction *= -1
                last_search_flip_time = now
                pickup_stable_count = 0
                _log("RECOVER: done, back to SEARCH")
                continue

            # Fallback: if state doesn't match any step level, go to SEARCH
            if state not in ("SEARCH", "IDLE"):
                _log(f"STEP{AUTONOMY_STEP}: state '{state}' not handled at this step level, resetting to SEARCH")
                _write_arduino("M:0,0")
                state = "SEARCH"


# For M: throttling to Arduino
_pending_m = None
_last_m_send = 0.0
_pending_m_lock = Lock()
_last_autonomy_m_send = 0.0
_autonomy_m_lock = Lock()


def _write_arduino_m_throttled(cmd):
    """Send M: command from autonomy loop, throttled to avoid Arduino buffer overflow."""
    global _last_autonomy_m_send
    now = time.time()
    with _autonomy_m_lock:
        if (now - _last_autonomy_m_send) < M_TO_ARDUINO_INTERVAL:
            return
        _last_autonomy_m_send = now
    _write_arduino(cmd)


_last_state_sent = ""


def _send_state_to_app(state_name):
    """Send current autonomy state to app over Bluetooth for UI display."""
    global _last_state_sent, client_sock
    if state_name == _last_state_sent:
        return  # Don't spam
    _last_state_sent = state_name
    if client_sock:
        try:
            client_sock.send(f"DATA:AUTO_STATE:{state_name}\n".encode())
        except Exception:
            pass


def _app_to_arduino():
    """Thread: read from app, process, forward to Arduino. Exits when connection lost."""
    global client_sock, moving, current_gear, AUTO_MODE, _pending_m, _last_m_send
    try:
        while True:
            now = time.time()
            with _pending_m_lock:
                if _pending_m and (now - _last_m_send) >= M_TO_ARDUINO_INTERVAL:
                    if arduino:
                        _write_arduino(_pending_m)
                    _last_m_send = now
                    _pending_m = None

            data = client_sock.recv(1024)
            if not data:
                break
            text = data.decode(errors="ignore")
            now = time.time()
            for line in text.splitlines():
                if not line.strip():
                    continue
                if line.strip() == "MODE:AUTO_ON":
                    with auto_lock:
                        AUTO_MODE = True
                    _log("AUTO_MODE ON - autonomy will drive")
                    _write_arduino("GEAR:3")          # Full power for autonomous
                    if arduino:
                        _write_arduino(line.strip())
                    continue
                if line.strip() == "MODE:AUTO_OFF":
                    with auto_lock:
                        AUTO_MODE = False
                    _log("AUTO_MODE OFF - manual control")
                    _write_arduino("GEAR:1")          # Restore default for manual
                    if arduino:
                        _write_arduino(line.strip())
                    continue
                with auto_lock:
                    am = AUTO_MODE
                if am:
                    continue
                if line.startswith("SOUND:TURBO"):
                    play_once(TURBO_WAV)
                    continue
                if line.startswith("GEAR:"):
                    try:
                        g = int(line.split(":")[1])
                        if g != current_gear:
                            current_gear = max(1, min(3, g))
                            play_once(SHIFT_WAV)
                            if moving:
                                start_loop(engine_loop_for_gear(current_gear))
                    except Exception:
                        pass
                if line.startswith("M:"):
                    try:
                        speed = int(line[2:].split(",")[0])
                        is_moving_now = abs(speed) > 20
                        if is_moving_now and not moving:
                            start_loop(engine_loop_for_gear(current_gear))
                        elif not is_moving_now and moving:
                            stop_loop()
                        moving = is_moving_now
                    except Exception:
                        pass
                    with _pending_m_lock:
                        _pending_m = line.strip()
                        if (now - _last_m_send) >= M_TO_ARDUINO_INTERVAL:
                            if arduino:
                                _write_arduino(line.strip())
                            _last_m_send = now
                            _pending_m = None
                    continue
                if arduino:
                    _write_arduino(line.strip())
    except (OSError, bluetooth.BluetoothError) as e:
        _log(f"App thread exit: {e}")
    finally:
        stop_loop()
        _log("App->Arduino thread stopped.")


def _arduino_to_app():
    """Thread: read from Arduino, forward to app. Keepalive when Arduino silent."""
    global client_sock, _last_imu_mq_log_time
    last_send = 0.0
    last_arduino_data = time.time()
    try:
        while True:
            now = time.time()
            sent = False
            if arduino and arduino.in_waiting > 0:
                try:
                    resp = arduino.readline().decode(errors="ignore").strip()
                    if resp:
                        last_arduino_data = now
                        _parse_telemetry(resp)
                        # Phase 0: optional throttled log when IMU/MQ packets received
                        if TELEMETRY_LOG_IMU_MQ and (resp.startswith("DATA:IMU:") or resp.startswith("DATA:MQ:")):
                            if now - _last_imu_mq_log_time >= TELEMETRY_LOG_IMU_MQ_INTERVAL_S:
                                _log("Telemetry: IMU/MQ packets received (forwarded to app)")
                                _last_imu_mq_log_time = now
                        if now - last_send >= TELEMETRY_INTERVAL and client_sock:
                            try:
                                client_sock.send((resp + "\n").encode())
                                last_send = now
                                sent = True
                            except (OSError, bluetooth.BluetoothError):
                                break
                except (OSError, serial.SerialException):
                    break
            if not sent and client_sock and (now - last_arduino_data) >= KEEPALIVE_INTERVAL:
                try:
                    keep = "DATA:SENSORS:999,999,999\n"
                    client_sock.send(keep.encode())
                    last_send = now
                    last_arduino_data = now
                except (OSError, bluetooth.BluetoothError):
                    break
            time.sleep(0.01)
    except (OSError, bluetooth.BluetoothError) as e:
        _log(f"Arduino thread exit: {e}")
    finally:
        _log("Arduino->App thread stopped.")


def main():
    global client_sock, server_sock, arduino, moving, current_gear, AUTO_MODE

    reset_bluetooth_adapter()
    connect_arduino()
    _log("Autonomy thread starting (reads /tmp/ecosweep_detection.json). Toggle Auto ON in app to enable.")
    threading.Thread(target=autonomy_loop, daemon=True).start()

    disconnect_count = 0
    while True:
        client_sock = None
        server_sock = None
        try:
            server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            try:
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception:
                pass
            for attempt in range(BIND_RETRY_MAX):
                try:
                    server_sock.bind(("", RFCOMM_CHANNEL))
                    break
                except OSError as e:
                    if e.errno == 98 and attempt < BIND_RETRY_MAX - 1:
                        _log(f"RFCOMM channel {RFCOMM_CHANNEL} in use (attempt {attempt + 1}/{BIND_RETRY_MAX}). "
                             "Stop the service first: sudo systemctl stop ecosweep-bridge.service")
                        server_sock.close()
                        time.sleep(BIND_RETRY_SEC)
                        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                        try:
                            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        except Exception:
                            pass
                    else:
                        raise
            server_sock.listen(1)
            try:
                bluetooth.advertise_service(
                    server_sock,
                    "EcoSweep-SPP",
                    service_id=SPP_UUID,
                    service_classes=[SPP_UUID, bluetooth.SERIAL_PORT_CLASS],
                    profiles=[bluetooth.SERIAL_PORT_PROFILE],
                )
            except Exception as e:
                _log(f"Advertise SPP failed (continuing): {e}")
            _log("Waiting for Bluetooth connection...")
            client_sock, _ = server_sock.accept()
            _log("Connected. Starting app/arduino threads.")

            t1 = threading.Thread(target=_app_to_arduino, daemon=True)
            t2 = threading.Thread(target=_arduino_to_app, daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        except Exception as e:
            _log(f"Connection error: {e}")
        finally:
            disconnect_count += 1
            _log(f"Disconnected (count={disconnect_count}). Cleaning up.")
            stop_loop()
            try:
                if client_sock:
                    client_sock.close()
            except Exception:
                pass
            try:
                if server_sock:
                    server_sock.close()
            except Exception:
                pass
            if disconnect_count % 5 == 0:
                _log("Resetting Bluetooth adapter (every 5th disconnect).")
                reset_bluetooth_adapter()
            else:
                time.sleep(1)
            time.sleep(1)
            _log("Reconnecting...")


if __name__ == "__main__":
    main()
