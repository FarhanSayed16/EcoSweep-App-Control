# Phase 2 (YOLO Path): Garbage Detection on Pi 4 with YOLOv8

**Your setup:** Raspberry Pi 4 Model B, 4 GB RAM, 32 GB SD card.

**Answer: Yes — you can use YOLO.** Use **YOLOv8 Nano (yolov8n)** for best balance of speed and accuracy on Pi 4. Expect about **2–4 FPS** on CPU; that is enough for EcoSweep (detect garbage → move → pick). For much higher FPS you’d add a USB accelerator (e.g. Coral TPU) later.

---

## Why YOLO on Pi 4 4GB Works

| Item | Your Pi | Requirement |
|------|---------|-------------|
| RAM | 4 GB | YOLOv8n needs ~1–2 GB at inference; 4 GB is enough. |
| Storage | 32 GB | OS + Python + Ultralytics + model ~2–4 GB; 32 GB is enough. |
| FPS | 2–4 (CPU) | Enough for “see garbage → approach”; no need for 30 FPS. |
| Model | yolov8n.pt | Nano model; small and fast. Do **not** use medium/large on Pi. |

---

## Plan (YOLO Path)

| Step | What to do |
|------|-------------|
| 1 | On Pi: install Python 3, OpenCV, Ultralytics (`pip3 install ultralytics opencv-python-headless`). |
| 2 | Use **YOLOv8 Nano** (`yolov8n.pt`). First run will download it automatically (~6 MB). |
| 3 | Optional: train/fine-tune on a **garbage** dataset and export to `.pt` or ONNX; or map COCO classes (bottle, cup, etc.) to “garbage”. |
| 4 | Run `detection_yolo.py`: camera → YOLOv8 → boxes + labels; print or show in window. |
| 5 | Optional: serve annotated MJPEG stream (same as Phase 1, but draw YOLO boxes on each frame). |
| 6 | Same detection format for Phase 3: class name, bbox, confidence. |

---

## Step 1: Install on Pi (YOLO path)

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv libopencv-dev
pip3 install ultralytics opencv-python-headless
```

If you hit memory errors during `pip install`, use:

```bash
pip3 install --no-cache-dir ultralytics opencv-python-headless
```

---

## Step 2: Model Choice

- **Quick start:** Use the default **COCO-trained** `yolov8n.pt` (downloads on first run). Map COCO classes to “garbage” (e.g. bottle=39, cup=41, etc.; see COCO class list).
- **Better for garbage:** Fine-tune YOLOv8n on a garbage/litter dataset (e.g. TACO, Open Litter Map, or a Kaggle dataset), then use your trained `.pt` on the Pi.

For Phase 2, the quick start is enough; you can swap to a custom model later.

---

## Step 3: Run Detection (script in repo)

Use the script `hardware/pi/phase2/detection_yolo.py` (see below). It:

- Loads YOLOv8n (or your `.pt` path).
- Reads from the USB camera.
- Runs inference every frame (or every 2nd frame for higher FPS).
- Draws boxes and prints detections (class, confidence, bbox).
- Optionally you can add Flask to serve the annotated stream.

**First run:** Ultralytics will download `yolov8n.pt` (~6 MB) automatically.

---

## Step 4: Optional — Annotated stream

Reuse your Phase 1 Flask app: in the frame loop, run `model(frame)` or `model.predict(frame)`, draw `results[0].boxes` on the frame, encode as MJPEG, and serve. Same URL in the app for FPV; you’ll see boxes on the video.

---

## Step 5: Detection format for Phase 3

From YOLO results:

- **class_name:** `model.names[class_id]` (e.g. "bottle", "person").
- **bbox:** `xyxy` (x1, y1, x2, y2) in pixels.
- **confidence:** `float(score)`.

Define which class names are “garbage” (e.g. bottle, cup, …) and pass these detections to Phase 3 autonomy.

---

## Performance tips (Pi 4)

- Use **yolov8n** only (nano); do not use `yolov8s/m/l/x` on Pi 4 CPU.
- Run inference every **2nd or 3rd frame** to double/quadruple effective FPS.
- Reduce camera resolution (e.g. 320x320 or 416x416) before inference if needed.
- Add cooling (heat sink/fan) to avoid thermal throttling.
- Later: export to **ONNX** and use OpenCV DNN or ONNX Runtime for possible speedup; or add a **Coral USB accelerator** for much higher FPS.

---

## Summary

| Question | Answer |
|----------|--------|
| Can you use YOLO on Pi 4 4GB + 32GB? | **Yes.** |
| Which model? | **YOLOv8 Nano (yolov8n.pt).** |
| Expected FPS? | **~2–4 FPS** on CPU; enough for EcoSweep. |
| What to do next? | Install Ultralytics + OpenCV, then run `detection_yolo.py` (provided in repo). |

Use **`hardware/pi/phase2/detection_yolo.py`** as the main script for the YOLO path; the TFLite script remains for the TFLite path.
