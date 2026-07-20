# -*- coding: utf-8 -*-
import bluetooth
import serial
import time
import threading
import queue
import subprocess
import os

try:
    from phase3.autonomy import run_autonomy_loop as _run_autonomy_loop_impl
except ImportError:
    _run_autonomy_loop_impl = None

# Arduino serial handle and app socket
arduino = None
client_sock = None
server_sock = None

# --- Phase 3: command queue and telemetry ---
# All commands to Arduino (from app or autonomy) go through this queue; one writer thread sends them.
to_arduino_queue = queue.Queue()
serial_lock = threading.Lock()

# Latest telemetry from Arduino (DATA:SENSORS, DATA:BATT). Thread-safe.
telemetry = {
    "sensors": {"front": 0, "left": 0, "right": 0},
    "batt": {"robot_v": 0.0, "controller_v": 0.0},
    "updated": 0.0,
}
telemetry_lock = threading.Lock()

# When True, autonomy thread may send M:/SA: commands. Set by MODE:AUTO_ON / MODE:AUTO_OFF from app.
autonomy_active = False
autonomy_active_lock = threading.Lock()

# Standard SPP UUID so Android SPP clients can discover/connect
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
RFCOMM_CHANNEL = 1  # Flutter classic SPP commonly connects on channel 1

# Simple audio paths (place your wav files here)
SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "sounds")
ENGINE_IDLE = os.path.join(SOUNDS_DIR, "engine_idle.wav")
ENGINE_G1   = os.path.join(SOUNDS_DIR, "engine_gear1.wav")
ENGINE_G2   = os.path.join(SOUNDS_DIR, "engine_gear2.wav")
ENGINE_G3   = os.path.join(SOUNDS_DIR, "engine_gear3.wav")
SHIFT_WAV   = os.path.join(SOUNDS_DIR, "shift.wav")
TURBO_WAV   = os.path.join(SOUNDS_DIR, "turbo.wav")

# Engine loop process
engine_proc = None
current_gear = 1
moving = False
last_speed_abs = 0


def play_once(path):
    try:
        subprocess.Popen(["aplay", "-q", path])
    except Exception as e:
        print(f"Audio play_once error: {e}")


def start_loop(path):
    global engine_proc
    stop_loop()
    try:
        # Loop using shell while true
        engine_proc = subprocess.Popen(["bash", "-lc", f"while true; do aplay -q '{path}'; done"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Audio loop start error: {e}")


def stop_loop():
    global engine_proc
    if engine_proc and engine_proc.poll() is None:
        try:
            engine_proc.terminate()
            engine_proc.wait(timeout=1)
        except Exception:
            try:
                engine_proc.kill()
            except Exception:
                pass
    engine_proc = None


def engine_loop_for_gear(gear):
    if gear == 1 and os.path.isfile(ENGINE_G1):
        return ENGINE_G1
    if gear == 2 and os.path.isfile(ENGINE_G2):
        return ENGINE_G2
    if gear == 3 and os.path.isfile(ENGINE_G3):
        return ENGINE_G3
    return ENGINE_IDLE if os.path.isfile(ENGINE_IDLE) else None


def find_arduino():
    global arduino
    ports = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyAMA0"]
    for port in ports:
        try:
            arduino = serial.Serial(port, 9600, timeout=1)
            print(f"✅ Arduino connected on {port} at 9600 baud.")
            time.sleep(2)
            return True
        except serial.SerialException:
            continue
    print("❌ Arduino not found. Check USB connection and permissions.")
    return False


def setup_bluetooth():
    global client_sock, server_sock
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", RFCOMM_CHANNEL))
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
        print(f"⚠ Service advertise failed (continuing): {e}")
    print(f"Waiting for Bluetooth connection on RFCOMM channel {RFCOMM_CHANNEL}...")
    client_sock, client_info = server_sock.accept()
    print(f"✅ Accepted connection from {client_info}")


def handle_audio_from_command(cmd_text):
    global current_gear, moving, last_speed_abs
    text = cmd_text.strip()

    # Manual sound triggers
    if text.startswith("SOUND:"):
        # e.g., SOUND:TURBO or SOUND:SHIFT
        what = text.split(":", 1)[1]
        if what.upper().startswith("TURBO") and os.path.isfile(TURBO_WAV):
            play_once(TURBO_WAV)
        elif what.upper().startswith("SHIFT") and os.path.isfile(SHIFT_WAV):
            play_once(SHIFT_WAV)
        return True  # do not forward to Arduino

    # Gear changes
    if text.startswith("GEAR:"):
        try:
            g = int(text.split(":", 1)[1])
            if g != current_gear:
                current_gear = max(1, min(3, g))
                if os.path.isfile(SHIFT_WAV):
                    play_once(SHIFT_WAV)
                # If moving, switch engine loop to new gear
                if moving:
                    loop = engine_loop_for_gear(current_gear)
                    if loop:
                        start_loop(loop)
        except ValueError:
            pass
        # Forward to Arduino too
        return False

    # Movement -> control engine loop
    if text.startswith("M:"):
        try:
            parts = text[2:].split(',')
            speed = int(parts[0])
        except Exception:
            speed = 0
        speed_abs = abs(speed)
        threshold = 20  # start/stop sounds
        was_moving = moving
        moving = speed_abs > threshold

        # Detect quick throttle lift -> turbo whoosh
        if was_moving and not moving and os.path.isfile(TURBO_WAV):
            if last_speed_abs - speed_abs > 80:  # crude drop detection
                play_once(TURBO_WAV)

        if moving and not was_moving:
            loop = engine_loop_for_gear(current_gear)
            if loop:
                start_loop(loop)
        elif not moving and was_moving:
            stop_loop()

        last_speed_abs = speed_abs
        # Forward to Arduino
        return False

    return False  # default: forward


def send_to_arduino(cmd):
    """Phase 3: Push a command (e.g. 'M:100,0' or 'SA:GRIP_CLOSE_START') to the Arduino send queue."""
    if cmd and cmd.strip():
        to_arduino_queue.put(cmd.strip())


def get_telemetry():
    """Phase 3: Return a copy of latest telemetry (sensors, batt). Thread-safe."""
    with telemetry_lock:
        return {
            "sensors": dict(telemetry["sensors"]),
            "batt": dict(telemetry["batt"]),
            "updated": telemetry["updated"],
        }


def is_autonomy_active():
    with autonomy_active_lock:
        return autonomy_active


def _parse_arduino_line(line):
    """Update shared telemetry from DATA:SENSORS: or DATA:BATT: lines."""
    line = line.strip()
    if line.startswith("DATA:SENSORS:"):
        try:
            parts = line.split(":", 2)[2].split(",")
            if len(parts) >= 3:
                front, left, right = int(parts[0]), int(parts[1]), int(parts[2])
                with telemetry_lock:
                    telemetry["sensors"]["front"] = front
                    telemetry["sensors"]["left"] = left
                    telemetry["sensors"]["right"] = right
                    telemetry["updated"] = time.time()
        except (ValueError, IndexError):
            pass
    elif line.startswith("DATA:BATT:"):
        try:
            parts = line.split(":", 2)[2].split(",")
            if len(parts) >= 2:
                rv, cv = float(parts[0]), float(parts[1])
                with telemetry_lock:
                    telemetry["batt"]["robot_v"] = rv
                    telemetry["batt"]["controller_v"] = cv
                    telemetry["updated"] = time.time()
        except (ValueError, IndexError):
            pass


def app_to_arduino():
    global autonomy_active
    print("App->Arduino thread started.")
    try:
        while True:
            data = client_sock.recv(1024)
            if not data:
                break
            text = data.decode(errors="ignore")
            for line in text.splitlines():
                if not line:
                    continue
                if handle_audio_from_command(line):
                    continue
                # Phase 3: Update autonomy flag from MODE commands (still forward to Arduino)
                upper = line.strip().upper()
                if upper == "MODE:AUTO_ON":
                    with autonomy_active_lock:
                        autonomy_active = True
                elif upper == "MODE:AUTO_OFF":
                    with autonomy_active_lock:
                        autonomy_active = False
                to_arduino_queue.put(line.strip())
    except OSError:
        print("App->Arduino thread: Connection lost.")
    finally:
        stop_loop()
        print("App->Arduino thread stopped.")


def _run_autonomy_loop():
    """Phase 3: Run autonomy state machine (reads detection file, uses telemetry, sends commands)."""
    if _run_autonomy_loop_impl is None:
        print("⚠ Autonomy module not found (phase3.autonomy). Autonomy disabled.")
        while True:
            time.sleep(60)
    _run_autonomy_loop_impl(send_to_arduino, get_telemetry, is_autonomy_active, "/tmp/ecosweep_detection.json")


def arduino_writer():
    """Phase 3: Single writer thread: read from queue, write to Arduino serial (with lock)."""
    print("Arduino writer thread started.")
    try:
        while True:
            cmd = to_arduino_queue.get()
            if arduino:
                with serial_lock:
                    try:
                        arduino.write((cmd + "\n").encode())
                    except (OSError, serial.SerialException):
                        pass
    except Exception as e:
        print(f"Arduino writer thread error: {e}")


def arduino_to_app():
    print("Arduino->App thread started.")
    try:
        while True:
            if arduino and arduino.in_waiting > 0:
                line = arduino.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                _parse_arduino_line(line)
                try:
                    client_sock.send((line + "\n").encode())
                except OSError:
                    break
            else:
                time.sleep(0.005)
    except (OSError, serial.SerialException):
        print("Arduino->App thread: connection error.")
    finally:
        stop_loop()
        print("Arduino->App thread stopped.")


def main():
    global client_sock, server_sock
    if not find_arduino():
        return
    try:
        setup_bluetooth()
        t1 = threading.Thread(target=app_to_arduino, daemon=True)
        t2 = threading.Thread(target=arduino_to_app, daemon=True)
        t_writer = threading.Thread(target=arduino_writer, daemon=True)
        t_autonomy = threading.Thread(
            target=_run_autonomy_loop,
            daemon=True,
        )
        t1.start()
        t2.start()
        t_writer.start()
        t_autonomy.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"Main loop error: {e}")
    finally:
        print("Cleaning up connections...")
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
        try:
            if arduino:
                arduino.close()
        except Exception:
            pass
        stop_loop()
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
