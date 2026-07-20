#!/bin/bash
# EcoSweep all-in-one startup script. Run manually or from rc.local.
# Usage: ./ecosweep_start.sh

ECOSWEEP_DIR="${ECOSWEEP_DIR:-/home/pi/ecosweep}"
cd "$ECOSWEEP_DIR" || exit 1

echo "Waiting for webcam..."
for i in $(seq 1 60); do [ -e /dev/video0 ] && break; sleep 1; done
sleep 5

echo "Waiting for Arduino..."
for i in $(seq 1 30); do [ -e /dev/ttyUSB0 ] || [ -e /dev/ttyACM0 ] && break; sleep 1; done
if [ ! -e /dev/ttyUSB0 ] && [ ! -e /dev/ttyACM0 ]; then echo "Arduino not found"; exit 1; fi

python3 phase2/yolo_fpv_stream_optimized.py &
YOLO_PID=$!
sleep 10

python3 ecosweep_manual_final.py
kill $YOLO_PID 2>/dev/null
