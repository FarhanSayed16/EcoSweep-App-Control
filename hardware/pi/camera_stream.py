# camera_stream.py - Serves MJPEG stream from USB webcam for EcoSweep FPV
# Phase 1: Copy this to your Pi (e.g. ~/ecosweep-phase1/) and run: python3 camera_stream.py
# Stream URL for app: http://<PI_IP>:5000/video_feed

import cv2
from flask import Flask, Response

app = Flask(__name__)


def get_camera():
    cap = cv2.VideoCapture(0)  # 0 = /dev/video0; use 1 if camera is /dev/video1
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam. Check /dev/video0 and permissions.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    return cap


def generate_frames():
    cap = get_camera()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, buf = cv2.imencode('.jpg', frame)
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'
            )
    finally:
        cap.release()


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/')
def index():
    return '<html><body><img src="/video_feed" /></body></html>'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
