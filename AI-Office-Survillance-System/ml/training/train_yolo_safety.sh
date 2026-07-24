#!/usr/bin/env bash
# Fine-tune YOLO11 for fire/smoke/weapon detection. Requires `pip install ultralytics`.
# data.yaml lists train/val paths + class names (e.g. fire, smoke, gun, knife).
yolo detect train model=yolo11s.pt data=ml/datasets/safety/data.yaml \
  epochs=100 imgsz=640 batch=16 patience=20 project=ml/export name=safety
# Export for edge:
yolo export model=ml/export/safety/weights/best.pt format=onnx opset=12   # → Hailo HEF via hailomz
