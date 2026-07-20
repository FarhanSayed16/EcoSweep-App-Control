# detection_yolo.py - Garbage/object detection with YOLOv8 on Pi (Phase 2, YOLO path)
# Run on Pi: python3 detection_yolo.py
# Requires: pip3 install ultralytics opencv-python-headless
# First run downloads yolov8n.pt (~6 MB). Use yolov8n only on Pi 4 (4GB).

import cv2
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, 'models', 'yolov8n.pt')  # optional: use your own .pt

# COCO classes that we treat as "garbage" for EcoSweep (customize as needed)
GARBAGE_CLASS_IDS = {
    39,   # bottle
    40,   # wine glass
    41,   # cup
    42,   # fork
    43,   # knife
    44,   # spoon
    46,   # banana
    47,   # apple
    48,   # sandwich
    49,   # orange
    50,   # broccoli
    51,   # carrot
    52,   # hot dog
    53,   # pizza
    54,   # donut
    55,   # cake
    # Add more COCO class ids you want to pick as garbage
}


def main():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Install Ultralytics: pip3 install ultralytics opencv-python-headless")
        return

    # Use built-in yolov8n if no custom model
    if os.path.isfile(MODEL_PATH):
        model = YOLO(MODEL_PATH)
    else:
        model = YOLO('yolov8n.pt')  # downloads on first run

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Run every Nth frame to improve FPS on Pi
    infer_every_n = 1  # 1 = every frame; 2 = every 2nd frame; 3 = every 3rd
    frame_count = 0

    print("Phase 2 YOLO detection running. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % infer_every_n != 0:
            cv2.imshow('EcoSweep YOLO', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        results = model.predict(frame, verbose=False, imgsz=320)
        # imgsz=320 for speed on Pi; use 416 or 640 if you need more accuracy

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                name = model.names[cls_id]
                is_garbage = cls_id in GARBAGE_CLASS_IDS

                color = (0, 255, 0) if is_garbage else (0, 165, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{name} {'[GARBAGE]' if is_garbage else ''} {conf:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                print(f"DETECT: {name} {conf:.2f} @ ({x1},{y1},{x2},{y2}) {'GARBAGE' if is_garbage else ''}")

        cv2.imshow('EcoSweep YOLO', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
