# -*- coding: utf-8 -*-
"""
Phase 3: Autonomy state machine for EcoSweep.
Reads detection from a JSON file (written by YOLO script), uses telemetry for safety,
sends M:/SA: commands via the bridge queue.
"""
import json
import time
import os

# Default path for detection file (YOLO script writes here)
DEFAULT_DETECTION_FILE = "/tmp/ecosweep_detection.json"

# --- Tunable constants ---
LOOP_INTERVAL_S = 0.15
FRONT_SAFE_CM = 15
FRONT_CLOSE_CM = 25
SEARCH_SPEED = 40
SEARCH_TURN = 80
APPROACH_SPEED = 100
APPROACH_TURN = 80
PICKUP_GRIP_DURATION_S = 1.5
PERSON_STOP_CONF = 0.5
GARBAGE_MIN_CONF = 0.4
NO_DETECTION_TIMEOUT_S = 2.0


def _read_detection(path):
    """Read detection JSON. Returns dict with decision, confidence, person_detected; or None if missing/invalid."""
    try:
        if not os.path.isfile(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, IOError):
        return None


def run_autonomy_loop(send_to_arduino_fn, get_telemetry_fn, is_autonomy_active_fn, detection_file_path=None):
    """
    Main autonomy loop. Run this in a thread from the bridge.
    send_to_arduino_fn(cmd_str), get_telemetry_fn() -> {sensors: {front, left, right}, ...}, is_autonomy_active_fn() -> bool.
    """
    path = detection_file_path or DEFAULT_DETECTION_FILE
    state = "SEARCH"
    last_garbage_time = 0.0
    last_no_garbage_time = 0.0
    search_direction = 1  # 1 = turn right, -1 = turn left (alternate in SEARCH)

    print("🤖 Autonomy thread started. Reading detection from:", path)

    while True:
        try:
            time.sleep(LOOP_INTERVAL_S)

            if not is_autonomy_active_fn():
                if state != "IDLE":
                    send_to_arduino_fn("M:0,0")
                    state = "IDLE"
                continue

            telemetry = get_telemetry_fn()
            front_cm = telemetry.get("sensors", {}).get("front", 999)
            detection = _read_detection(path)

            decision = (detection or {}).get("decision", "NONE")
            confidence = (detection or {}).get("confidence", 0.0)
            person_detected = (detection or {}).get("person_detected", False)

            has_garbage = decision in ("MOVE_LEFT", "MOVE_RIGHT", "CENTERED") and confidence >= GARBAGE_MIN_CONF
            now = time.time()

            # ---- Safety: STOP on person or very close obstacle ----
            if person_detected and confidence >= PERSON_STOP_CONF:
                send_to_arduino_fn("M:0,0")
                state = "STOP"
                last_no_garbage_time = now
                continue
            if front_cm < FRONT_SAFE_CM and front_cm >= 0:
                send_to_arduino_fn("M:0,0")
                state = "STOP"
                last_no_garbage_time = now
                continue
            if state == "STOP":
                if not person_detected and front_cm >= FRONT_SAFE_CM:
                    state = "SEARCH"
                else:
                    continue

            # ---- SEARCH: no garbage or lost target ----
            if state == "SEARCH":
                if has_garbage:
                    state = "APPROACH"
                    last_garbage_time = now
                    last_no_garbage_time = 0.0
                else:
                    last_no_garbage_time = now if last_no_garbage_time == 0 else last_no_garbage_time
                    turn = SEARCH_TURN * search_direction
                    send_to_arduino_fn(f"M:{SEARCH_SPEED},{turn}")
                    search_direction *= -1
                continue

            # ---- APPROACH: turn toward target or drive forward ----
            if state == "APPROACH":
                if not has_garbage:
                    if last_no_garbage_time == 0:
                        last_no_garbage_time = now
                    if now - last_no_garbage_time > NO_DETECTION_TIMEOUT_S:
                        state = "SEARCH"
                        send_to_arduino_fn("M:0,0")
                    else:
                        send_to_arduino_fn("M:0,0")
                    continue
                last_garbage_time = now
                last_no_garbage_time = 0.0

                if decision == "MOVE_LEFT":
                    send_to_arduino_fn(f"M:0,-{APPROACH_TURN}")
                elif decision == "MOVE_RIGHT":
                    send_to_arduino_fn(f"M:0,{APPROACH_TURN}")
                elif decision == "CENTERED":
                    if front_cm >= 0 and front_cm < FRONT_CLOSE_CM:
                        state = "ALIGN"
                        send_to_arduino_fn("M:0,0")
                    else:
                        send_to_arduino_fn(f"M:{APPROACH_SPEED},0")
                continue

            # ---- ALIGN: fine-tune then PICKUP ----
            if state == "ALIGN":
                if not has_garbage:
                    state = "SEARCH"
                    send_to_arduino_fn("M:0,0")
                    continue
                if decision == "CENTERED":
                    state = "PICKUP"
                    send_to_arduino_fn("M:0,0")
                elif decision == "MOVE_LEFT":
                    send_to_arduino_fn(f"M:0,-{APPROACH_TURN // 2}")
                elif decision == "MOVE_RIGHT":
                    send_to_arduino_fn(f"M:0,{APPROACH_TURN // 2}")
                continue

            # ---- PICKUP: gripper then continue ----
            if state == "PICKUP":
                send_to_arduino_fn("SA:GRIP_CLOSE_START")
                time.sleep(PICKUP_GRIP_DURATION_S)
                send_to_arduino_fn("SA:GRIP_CLOSE_STOP")
                send_to_arduino_fn("M:0,0")
                state = "CONTINUE"
                continue

            # ---- CONTINUE: same as SEARCH ----
            if state == "CONTINUE":
                state = "SEARCH"
                last_no_garbage_time = now

        except Exception as e:
            print("Autonomy loop error:", e)
            try:
                send_to_arduino_fn("M:0,0")
            except Exception:
                pass
            state = "SEARCH"
