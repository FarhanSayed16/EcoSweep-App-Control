# detection.py - Garbage/object detection on camera (Phase 2)
# Run on Pi: python3 detection.py
# Requires: OpenCV, TFLite (or tensorflow). Place models/detect.tflite and models/labels.txt.

import cv2
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, 'models', 'detect.tflite')
LABELS_PATH = os.path.join(SCRIPT_DIR, 'models', 'labels.txt')

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import tensorflow.lite as tflite
    except ImportError:
        tflite = None


def load_labels(path):
    if not os.path.isfile(path):
        return []
    with open(path, 'r') as f:
        return [line.strip() for line in f.readlines()]


def run_detection(interpreter, frame, input_size=(320, 320)):
    """
    Run TFLite object detection. Returns list of (class_id, confidence, (x1,y1,x2,y2)).
    Adapt input size and output parsing to your model (e.g. SSD MobileNet).
    """
    img = cv2.resize(frame, input_size)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    input_data = np.expand_dims(img_rgb.astype(np.uint8), axis=0)

    interpreter.set_tensor(interpreter.get_input_details()[0]['index'], input_data)
    interpreter.invoke()

    out = interpreter.get_output_details()
    # Typical SSD: [0]=locations, [1]=classes, [2]=scores, [3]=num_detections
    boxes = interpreter.get_tensor(out[0]['index'])[0]
    classes = interpreter.get_tensor(out[1]['index'])[0]
    scores = interpreter.get_tensor(out[2]['index'])[0]

    h, w = frame.shape[:2]
    detections = []
    for i in range(len(scores)):
        if scores[i] < 0.5:
            continue
        ymin, xmin, ymax, xmax = boxes[i]
        x1 = int(xmin * w)
        y1 = int(ymin * h)
        x2 = int(xmax * w)
        y2 = int(ymax * h)
        detections.append((int(classes[i]), float(scores[i]), (x1, y1, x2, y2)))
    return detections


def main():
    if tflite is None:
        print("Install tflite_runtime or tensorflow: pip3 install tflite-runtime")
        return
    if not os.path.isfile(MODEL_PATH):
        print(f"Place your TFLite model at: {MODEL_PATH}")
        print("See docs/phase-2-ai/PHASE-2-FULL-GUIDE.md for model options.")
        return

    labels = load_labels(LABELS_PATH)
    interpreter = tflite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()

    # Check input shape
    inp = interpreter.get_input_details()[0]
    input_size = (inp['shape'][2], inp['shape'][1])  # e.g. (320, 320)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Phase 2 detection running. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        detections = run_detection(interpreter, frame, input_size)
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
