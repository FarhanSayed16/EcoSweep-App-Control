#!/usr/bin/env python3
# EcoSweep Minimal Bridge - Bluetooth + Arduino relay only.
# No autonomy, no YOLO, no sounds. Just app <-> Arduino.
# Use this to verify Bluetooth connectivity works before adding features.

import os
import sys
import bluetooth
import serial
import time
import threading
from threading import Lock

SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"
RFCOMM_CHANNEL = 1  # Android SPP expects channel 1
TELEMETRY_INTERVAL = 0.2
KEEPALIVE_INTERVAL = 2.0
M_THROTTLE = 0.1

arduino = None
client_sock = None
serial_lock = Lock()
m_pending = None
m_last = 0.0
m_lock = Lock()


def log(msg):
    print(msg, flush=True)


def setup_bluetooth():
    """Prepare Bluetooth for SPP. Do NOT reset (down/up) - it breaks Android SDP."""
    pre = "" if os.geteuid() == 0 else "sudo "
    os.system(pre + "sdptool add SP")
    os.system(pre + "hciconfig hci0 piscan")
    time.sleep(1)


def connect_arduino():
    global arduino
    for port in ["/dev/ttyUSB0", "/dev/ttyACM0"]:
        try:
            if os.path.exists(port):
                arduino = serial.Serial(port, 9600, timeout=0.5)
                time.sleep(2)
                log(f"Arduino OK: {port}")
                return True
        except Exception as e:
            log(f"Arduino {port}: {e}")
    log("Arduino: not connected (keepalive will run)")
    return False


def write_arduino(line):
    if not arduino:
        return
    try:
        with serial_lock:
            arduino.write((line.strip() + "\n").encode())
    except Exception:
        pass


def app_to_arduino():
    global client_sock, m_pending, m_last
    try:
        while True:
            now = time.time()
            with m_lock:
                if m_pending and (now - m_last) >= M_THROTTLE:
                    write_arduino(m_pending)
                    m_last = now
                    m_pending = None

            data = client_sock.recv(1024)
            if not data:
                break
            for line in data.decode(errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("M:"):
                    with m_lock:
                        m_pending = line
                        if (now - m_last) >= M_THROTTLE:
                            write_arduino(line)
                            m_last = now
                            m_pending = None
                else:
                    write_arduino(line)
    except Exception as e:
        log(f"App thread: {e}")
    finally:
        log("App thread stopped")


def arduino_to_app():
    global client_sock
    last_send = 0.0
    last_data = time.time()
    try:
        while True:
            now = time.time()
            sent = False
            if arduino and arduino.in_waiting > 0:
                try:
                    line = arduino.readline().decode(errors="ignore").strip()
                    if line:
                        last_data = now
                        if (now - last_send) >= TELEMETRY_INTERVAL:
                            try:
                                client_sock.send((line + "\n").encode())
                                last_send = now
                                sent = True
                            except Exception:
                                break
                except Exception:
                    break
            if not sent and (now - last_data) >= KEEPALIVE_INTERVAL:
                try:
                    client_sock.send(b"DATA:SENSORS:999,999,999\n")
                    last_send = now
                    last_data = now
                except Exception:
                    break
            time.sleep(0.02)
    except Exception as e:
        log(f"Arduino thread: {e}")
    finally:
        log("Arduino thread stopped")


def main():
    global client_sock
    log("EcoSweep Minimal Bridge starting...")
    setup_bluetooth()
    connect_arduino()

    while True:
        server_sock = None
        client_sock = None
        try:
            server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            server_sock.bind(("", RFCOMM_CHANNEL))
            server_sock.listen(1)
            try:
                bluetooth.advertise_service(
                    server_sock, "EcoSweep-SPP",
                    service_id=SPP_UUID,
                    service_classes=[SPP_UUID, bluetooth.SERIAL_PORT_CLASS],
                    profiles=[bluetooth.SERIAL_PORT_PROFILE],
                )
            except Exception as e:
                log(f"Advertise: {e}")
            log("Waiting for Bluetooth connection...")
            client_sock, _ = server_sock.accept()
            log("Connected.")

            t1 = threading.Thread(target=app_to_arduino, daemon=True)
            t2 = threading.Thread(target=arduino_to_app, daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        except Exception as e:
            log(f"Error: {e}")
        finally:
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
            log("Disconnected. Reconnecting in 3s...")
            time.sleep(3)


if __name__ == "__main__":
    main()
