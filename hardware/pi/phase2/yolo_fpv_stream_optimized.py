# yolo_fpv_stream_optimized.py - Less lag: YOLO in background thread, stream sends latest frame
# Phase 3: Writes /tmp/ecosweep_detection.json for autonomy (decision, confidence, person_detected).
# Copy to Pi (ecosweep-phase2/) and run: python3 yolo_fpv_stream_optimized.py
# Stream: http://<PI_IP>:5000/video_feed

import cv2
import json
import threading
import time
import tempfile
import os
from flask import Flask, Response

# Import YOLO only in the thread that uses it (avoids blocking main import)
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

import numpy as np

# ---------------- CONFIG ----------------
CAMERA_DEVICE = "/dev/video0"
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CAMERA_FPS = 30               # Higher FPS = shorter exposure = less motion blur
CONF_THRESHOLD = 0.35         # Keep proper threshold (no hack)
PORT = 5000
YOLO_EVERY_N_FRAMES = 2       # Every 2nd frame at 30FPS = ~15 YOLO/s (balanced)
YOLO_IMGSZ = 384              # Balance: faster than 416, better than 320
JPEG_QUALITY = 82
STREAM_TARGET_FPS = 15
BLUR_THRESHOLD = 0            # Disabled (Pi cam sharpness varies too much)
USE_TRACKER = False           # No heavy dependency; bridge memory handles persistence

GARBAGE_CLASSES = {
    "bottle", "cup", "cell phone", "book",
    "banana", "apple", "paper",
}
# Phase 3: detection file for autonomy
DETECTION_FILE = "/tmp/ecosweep_detection.json"
CENTER_MARGIN_PX = 35  # Tunable: smaller = stricter center, larger = looser

# Obstacle classes (chair, couch, etc.) - stop or avoid
OBSTACLE_CLASSES = {"chair", "couch", "bed", "dining table", "potted plant"}
# ---------------------------------------

# Shared state: separate capture (smooth) from YOLO (slower)
_latest_frame = None
_last_boxes = []              # Boxes to overlay (from last YOLO run)
_last_detection = {}          # Last detection dict for autonomy
_lock = threading.Lock()


def capture_worker():
    """Capture frames at full camera FPS. Never blocks on YOLO."""
    global _latest_frame

    cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
    if not cap.isOpened():
        print("Cannot open camera", CAMERA_DEVICE)
        return

    while True:
        ret, frame = cap.read()
        if ret:
            with _lock:
                _latest_frame = frame
        else:
            time.sleep(0.02)


def yolo_worker():
    """Background thread: run YOLO on latest frame, update detection + boxes. Does not block stream."""
    global _last_boxes, _last_detection

    if YOLO is None:
        print("Install ultralytics: pip3 install ultralytics")
        return

    model = YOLO("yolov8n.pt")
    frame_count = 0

    while True:
        time.sleep(0.01)  # Faster loop = fresher detections
        with _lock:
            frame = _latest_frame
        if frame is None:
            continue

        frame_count += 1
        if frame_count % YOLO_EVERY_N_FRAMES != 0:
            continue

        # Skip blurry frames (motion blur kills detection)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < BLUR_THRESHOLD:
            continue  # Frame too blurry, wait for next sharp one

        if USE_TRACKER:
            results = model.track(
                frame,
                conf=CONF_THRESHOLD,
                imgsz=YOLO_IMGSZ,
                persist=True,    # ByteTrack: maintain object IDs across frames
                verbose=False,
            )
        else:
            results = model.predict(
                frame,
                conf=CONF_THRESHOLD,
                imgsz=YOLO_IMGSZ,
                verbose=False,
            )

        # Best garbage detection for Phase 3 decision
        best_garbage = None
        best_conf = 0.0
        person_detected = False
        obstacle_detected = False
        boxes_to_draw = []

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                name = model.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                if name == "person":
                    person_detected = person_detected or (conf >= CONF_THRESHOLD)
                    continue
                if name in OBSTACLE_CLASSES and conf >= CONF_THRESHOLD:
                    obstacle_detected = True
                    continue
                if name not in GARBAGE_CLASSES:
                    continue
                if conf > best_conf:
                    best_conf = conf
                    best_garbage = (x1, y1, x2, y2, conf, name)
                boxes_to_draw.append((x1, y1, x2, y2, name, conf))

        with _lock:
            _last_boxes = boxes_to_draw

        # Phase 3: write detection file for autonomy
        fx = FRAME_WIDTH / 2
        decision = "NONE"
        confidence = 0.0
        bbox_cx = bbox_cy = 0
        bbox_area = 0
        if best_garbage:
            x1, y1, x2, y2, confidence, _ = best_garbage
            bbox_cx = (x1 + x2) / 2
            bbox_cy = (y1 + y2) / 2
            bbox_area = (x2 - x1) * (y2 - y1)
            if bbox_cx < fx - CENTER_MARGIN_PX:
                decision = "MOVE_LEFT"
            elif bbox_cx > fx + CENTER_MARGIN_PX:
                decision = "MOVE_RIGHT"
            else:
                decision = "CENTERED"
        det = {
            "decision": decision,
            "confidence": round(confidence, 3),
            "person_detected": person_detected,
            "obstacle_detected": obstacle_detected,
            "bbox_center_x": round(bbox_cx, 1),
            "bbox_center_y": round(bbox_cy, 1),
            "bbox_area": int(bbox_area),
            "frame_width": FRAME_WIDTH,
            "frame_center": fx,
            "timestamp": time.time(),
        }
        _last_detection = det
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(dir="/tmp", suffix=".json")
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(det, f)
            os.replace(tmp_path, DETECTION_FILE)   # atomic on Linux
        except Exception:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def generate_frames():
    """Flask generator: get latest frame, draw boxes, encode, yield. Runs at stream FPS, never blocks on YOLO."""
    frame_interval = 1.0 / STREAM_TARGET_FPS if STREAM_TARGET_FPS > 0 else 0.033

    while True:
        t0 = time.time()
        with _lock:
            frame = _latest_frame
            boxes = list(_last_boxes)
        if frame is not None:
            out = frame.copy()
            for (x1, y1, x2, y2, name, conf) in boxes:
                cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(out, f"{name} {conf:.2f}", (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
            _, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            data = buf.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
            )
        elapsed = time.time() - t0
        sleep_time = frame_interval - elapsed
        if sleep_time > 0.001:
            time.sleep(sleep_time)


def main():
    global _latest_frame

    # Pre-fill one frame so stream has something immediately
    cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            with _lock:
                _latest_frame = frame.copy()
        cap.release()

    t_capture = threading.Thread(target=capture_worker, daemon=True)
    t_yolo = threading.Thread(target=yolo_worker, daemon=True)
    t_capture.start()
    t_yolo.start()

    app = Flask(__name__)

    @app.route("/video_feed")
    def video_feed():
        return Response(
            generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/")
    def index():
        return "<h2>EcoSweep YOLO FPV (optimized)</h2><img src='/video_feed'>"

    print("YOLO FPV stream (optimized) on port", PORT, "- target", STREAM_TARGET_FPS, "FPS")
    app.run(host="0.0.0.0", port=PORT, threaded=True)


if __name__ == "__main__":
    main()
