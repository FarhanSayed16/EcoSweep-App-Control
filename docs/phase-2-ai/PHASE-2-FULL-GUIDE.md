# Phase 2: AI Integration (Garbage / Object Detection) — Full Guide

This guide walks you through adding **garbage and object detection** on the Raspberry Pi using the USB camera. By the end, the Pi will run a model on each frame and output detections (e.g. “garbage”, “bottle”, “person”) with bounding boxes. Phase 3 will use these detections for autonomous cleaning.

---

## What You Need Before Starting

- **Phase 1 done**: USB webcam streaming (Flask or mjpg-streamer) and FPV working in the app.
- **Raspberry Pi** (Pi 4 recommended) with Raspberry Pi OS (Bullseye/Bookworm).
- **Real VNC or SSH** access to the Pi.
- **USB webcam** and `camera_stream.py` (or mjpg-streamer) from Phase 1.

---

## Phase 2 Overview

| Step | What you do |
|------|-------------|
| 2.1 | Install Python dependencies (OpenCV, TensorFlow Lite or YOLO). |
| 2.2 | Get or train a **garbage/waste detection** model and export for Pi (TFLite or ONNX). |
| 2.3 | Write `detection.py`: read camera frames → run model → get boxes + labels. |
| 2.4 | Optional: draw boxes on the stream and serve an **annotated** feed for debugging. |
| 2.5 | Define a simple detection format (for Phase 3 autonomy). |

**Deliverable:** Pi runs real-time garbage (and optional object/person) detection from the USB camera and outputs detections (e.g. to console or annotated stream).

---

## Step 2.1: Install Dependencies on the Pi

Connect to the Pi (Real VNC or SSH) and open a terminal.

### Option A: TensorFlow Lite (recommended for Pi 4)

TFLite is lighter and runs well on Pi 4.

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv libopencv-dev python3-numpy
pip3 install tflite-runtime opencv-python-headless
```

If `tflite-runtime` fails to install (e.g. no wheel for your Python version), try:

```bash
pip3 install tensorflow
```

Then in code you use `import tensorflow.lite as tflite` instead of `import tflite_runtime.interpreter as tflite`.

### Option B: YOLO (e.g. Ultralytics YOLOv8)

More accurate, heavier. Use if you have Pi 4 with 4 GB+ RAM and want better detection.

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv libopencv-dev
pip3 install ultralytics opencv-python-headless
```

This guide focuses on **Option A (TFLite)** first; YOLO is summarized later.

---

## Step 2.2: Get a Garbage Detection Model

You need a model that outputs **bounding boxes** and **class labels**. Options:

### Option 2.2.1 — Use a pre-trained COCO/SSD model and map classes (quick start)

- Download a **TFLite object-detection** model (e.g. SSD MobileNet from [TensorFlow Hub](https://tfhub.dev/) or [TF Lite detection models](https://www.tensorflow.org/lite/examples/object_detection/overview)).
- These detect 80+ COCO classes (person, bottle, cup, etc.). Map relevant classes to “garbage” (e.g. bottle, wine glass, cup, cell phone, book → garbage for cleaning).
- **Pros:** No training; works in minutes. **Cons:** Not tuned for “litter” or “waste pile”; you treat COCO classes as garbage.

**Example — download a TFLite SSD model:**

```bash
mkdir -p ~/ecosweep-phase2/models
cd ~/ecosweep-phase2/models
# Example: EfficientDet-Lite (small, good for Pi)
wget -O detect.tflite "https://storage.googleapis.com/download.tensorflow.org/models/tflite/coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip"
unzip -o coco_ssd_mobilenet_v1_1.0_quant_2018_06_29.zip
# Or use a direct .tflite link if you find one; rename to detect.tflite
```

If the above URL is outdated, search for “TensorFlow Lite object detection model” and download a `.tflite` file. Place it as `~/ecosweep-phase2/models/detect.tflite` and note the **label list** (e.g. COCO labels).

### Option 2.2.2 — Use a garbage/litter dataset and train (better accuracy)

- Datasets: [TACO](https://github.com/pedropro/TACO), [Open Litter Map](https://openlittermap.com/), or “garbage detection” on Kaggle.
- Train a small object detector (e.g. SSD or EfficientDet) and export to TFLite.
- **Pros:** Model recognizes “garbage” / “litter” directly. **Cons:** Requires training (Python on PC or Colab).

### Option 2.2.3 — Use a ready-made garbage TFLite model (if available)

Search for “garbage detection tflite” or “waste detection model raspberry pi”. If you find a `.tflite` + labels file, place them in `~/ecosweep-phase2/models/` and use them in Step 2.3.

---

## Step 2.3: Write `detection.py`

Create a script that:

1. Opens the camera (same as Phase 1).
2. For each frame (or every N-th frame to save CPU): preprocess → run TFLite → get boxes and classes.
3. Optionally draw boxes and show/save the result.
4. Output detections in a simple format (e.g. list of `{class_name, bbox, confidence}`) for Phase 3.

### Folder structure on Pi

```text
~/ecosweep-phase2/
  models/
    detect.tflite
    labels.txt          # one label per line, index = class id
  detection.py
  camera_stream_with_detection.py   # optional: stream with boxes
```

### Example `labels.txt` (COCO-style, first 20 lines)

Use the label file that matches your model. For COCO SSD:

```text
person
bicycle
car
motorcycle
airplane
bus
train
truck
boat
traffic light
fire hydrant
stop sign
parking meter
bench
bird
cat
dog
horse
sheep
cow
...
```

Garbage-relevant classes you might map: bottle (40), cup (41), etc. (check COCO class list).

### Skeleton `detection.py` (TFLite)

Use the script below as a starting point. Replace `MODEL_PATH` and `LABELS_PATH` with your paths. Adjust input size and preprocessing to match your model (e.g. 320x320 or 300x300).

```python
# detection.py - Run garbage/object detection on camera frames (Phase 2)
import cv2
import numpy as np
import os

# Paths - change to match your model
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'detect.tflite')
LABELS_PATH = os.path.join(os.path.dirname(__file__), 'models', 'labels.txt')

# Try TFLite runtime first, then TensorFlow
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

def load_labels(path):
    with open(path, 'r') as f:
        return [line.strip() for line in f.readlines()]

def run_detection(interpreter, frame, input_size=(320, 320)):
    """Run TFLite detection; return list of (class_id, confidence, bbox)."""
    # Resize frame to model input size
    img = cv2.resize(frame, input_size)
    # Some models expect RGB, NHWC
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    input_data = np.expand_dims(img_rgb.astype(np.uint8), axis=0)

    interpreter.set_tensor(interpreter.get_input_details()[0]['index'], input_data)
    interpreter.invoke()

    # Output format depends on the model (e.g. SSD: locations, classes, scores, num_detections)
    out_details = interpreter.get_output_details()
    # Adapt indices to your model; common: [1]=classes, [2]=scores, [0]=boxes
    boxes = interpreter.get_tensor(out_details[0]['index'])[0]
    classes = interpreter.get_tensor(out_details[1]['index'])[0]
    scores = interpreter.get_tensor(out_details[2]['index'])[0]

    h, w = frame.shape[:2]
    detections = []
    for i, score in enumerate(scores):
        if score < 0.5:
            continue
        ymin, xmin, ymax, xmax = boxes[i]
        x1 = int(xmin * w)
        y1 = int(ymin * h)
        x2 = int(xmax * w)
        y2 = int(ymax * h)
        detections.append((int(classes[i]), float(score), (x1, y1, x2, y2)))
    return detections

def main():
    labels = load_labels(LABELS_PATH) if os.path.isfile(LABELS_PATH) else []
    interpreter = tflite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        detections = run_detection(interpreter, frame)
        for class_id, conf, (x1, y1, x2, y2) in detections:
            label = labels[class_id] if class_id < len(labels) else str(class_id)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f'{label} {conf:.2f}', (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            print(f"DETECT: {label} {conf:.2f} @ ({x1},{y1},{x2},{y2})")
        cv2.imshow('EcoSweep Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
```

**Important:** TFLite model input/output shapes and order differ per model. Check your model’s documentation and adjust:

- `get_input_details()` / `get_output_details()` for input size and dtype.
- Preprocessing (normalize to 0–1 or quantized range).
- Which output index is boxes, classes, scores (and their shapes).

Use this skeleton to plug in your actual model and labels.

---

## Step 2.4: Optional — Annotated Stream (boxes on video)

To see detections in the app or browser, serve an MJPEG stream with boxes drawn (same idea as Phase 1, but each frame is run through the detector first).

- Reuse your Phase 1 Flask app: in the frame loop, call your detection function, draw boxes on the frame, then encode and yield the frame.
- Serve at e.g. `/video_feed` on port 5000 (or a second port like 5001) and open that URL in the app or browser.

Example idea (merge into your existing `generate_frames()`):

```python
# Inside generate_frames():
ret, frame = cap.read()
if not ret:
    break
detections = run_detection(interpreter, frame)
for class_id, conf, (x1, y1, x2, y2) in detections:
    label = labels[class_id] if class_id < len(labels) else str(class_id)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(frame, f'{label} {conf:.2f}', (x1, y1 - 10), ...)
_, buf = cv2.imencode('.jpg', frame)
yield (...)
```

Run one process: either “stream only” (Phase 1) or “stream + detection”. For Phase 2 completion, console output of detections is enough; annotated stream is optional.

---

## Step 2.5: Detection Format for Phase 3

Use a simple, consistent format so Phase 3 (autonomy) can consume it. For each detection, expose at least:

- **class_name** (e.g. `"garbage"`, `"bottle"`, `"person"`).
- **bbox**: `(x1, y1, x2, y2)` in pixel coordinates.
- **confidence**: float in [0, 1].

You can also compute:

- **center_x** = (x1 + x2) / 2 (for “turn toward target”).
- **area** or “size” (for “how close” or “big enough to pick”).

If you use COCO classes, define a list of class names that count as “garbage” (e.g. bottle, cup, …) and in Phase 3 treat any detection in that list as a cleaning target.

---

## YOLO Option (Brief)

If you prefer YOLO (e.g. Ultralytics YOLOv8):

1. Install: `pip3 install ultralytics opencv-python-headless`.
2. Download a small model: `yolov8n.pt` (nano) or train/fine-tune on a garbage dataset and export to ONNX or use `.pt`.
3. In Python:
   - `from ultralytics import YOLO`
   - `model = YOLO('yolov8n.pt')` (or your model)
   - `results = model(frame)`
   - Parse `results[0].boxes` for xyxy and class ids, map ids to names.
4. Same as above: draw boxes, optional annotated stream, same detection format for Phase 3.

---

## Checklist — Phase 2

- [ ] **2.1** Dependencies installed on Pi (OpenCV + TFLite or YOLO).
- [ ] **2.2** A detection model available (TFLite or YOLO) and, if needed, `labels.txt` (or class names).
- [ ] **2.3** `detection.py` runs: reads camera, runs model, prints or returns detections with class, bbox, confidence.
- [ ] **2.4** (Optional) Annotated stream with boxes visible in browser or app.
- [ ] **2.5** Detection format documented or implemented (class_name, bbox, confidence) for Phase 3.

---

## Troubleshooting

- **“Cannot open webcam”** — Same as Phase 1: check `ls /dev/video*`, use the correct index in `cv2.VideoCapture(0)`.
- **TFLite “wrong input shape”** — Print `interpreter.get_input_details()` and resize/preprocess to the exact shape and dtype (e.g. 320x320, uint8 or float32).
- **Slow FPS** — Run inference every 2nd or 3rd frame; reduce input size (e.g. 256x256); use a quantized model.
- **Low memory** — Use TFLite (not full TensorFlow) and a small model (e.g. SSD MobileNet, EfficientDet-Lite).
- **Wrong classes** — Verify `labels.txt` matches the model’s class order (often COCO order for SSD).

---

## What’s Next (Phase 3)

After Phase 2, you will have:

- Real-time detections (class, bbox, confidence) on the Pi.

Phase 3 will:

- Read these detections + Arduino telemetry (ultrasonics, battery).
- Implement a state machine (SEARCH → APPROACH → ALIGN → PICKUP).
- Send `M:` and servo commands to the Arduino so the robot moves and cleans based on where garbage is detected.

Keep your `detection.py` and model in `~/ecosweep-phase2/` (or `hardware/pi/phase2/`); Phase 3 will call the same detection loop or import the same functions.

---

## Quick “What to Do” Summary

1. **On Pi:** Install OpenCV + TFLite (Step 2.1).
2. **On Pi:** Create `~/ecosweep-phase2/` (or copy `hardware/pi/phase2/` from the repo). Add a TFLite model as `models/detect.tflite` and `models/labels.txt` (Step 2.2).
3. **On Pi:** Run `python3 detection.py` (use the skeleton in `hardware/pi/phase2/detection.py`; fix input/output shape if your model differs). Confirm detections in the console and/or window (Step 2.3).
4. **Optional:** Serve an annotated stream (boxes on video) so you can see detections in the app or browser (Step 2.4).
5. **Phase 3:** Use the same detection output (class, bbox, confidence) to drive the robot (Step 2.5).
