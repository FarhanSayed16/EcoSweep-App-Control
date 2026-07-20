# Phase 2: AI Integration (Garbage / Object Detection)

**Goal:** Run garbage/waste (and optional object/person) detection on the Raspberry Pi using the USB camera feed.

- **[PHASE-2-FULL-GUIDE.md](PHASE-2-FULL-GUIDE.md)** — TFLite path: dependencies, model, detection script.
- **[PHASE-2-YOLO-GUIDE.md](PHASE-2-YOLO-GUIDE.md)** — **YOLO path (recommended for Pi 4 4GB):** YOLOv8 Nano, install, run, garbage class mapping.

**In this repo:**
- `hardware/pi/phase2/detection.py` — TFLite skeleton; add `models/detect.tflite` and `models/labels.txt`.
- `hardware/pi/phase2/detection_yolo.py` — **YOLO path:** run `python3 detection_yolo.py` on Pi (uses yolov8n.pt; first run downloads it).

When Phase 2 is done, move to [../phase-3-autonomy/](../phase-3-autonomy/).
