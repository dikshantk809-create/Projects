# 09 — Training Pipeline (Office)

See `../ml/` for scripts. Tooling: Ultralytics (YOLO), PyTorch (behavior temporal head),
CVAT/Roboflow (labeling), MLflow (tracking), DVC (data versioning).

1. **Collect** consented footage; sample frames/clips per target class.
2. **Label** bounding boxes (safety classes) or activity windows (behavior).
3. **Train**
   - Safety detector: `bash ml/training/train_yolo_safety.sh`
   - Behavior: `python ml/training/train_behavior.py --data ml/datasets/behavior`
4. **Evaluate** PR curves per class; choose deployment thresholds; check bias across
   demographics for fairness.
5. **Export** PyTorch → ONNX → HEF (Hailo, Pi) / TensorRT (Jetson/GPU).
6. **Register** in MLflow; canary to one device; then fleet rollout.
7. **Monitor** drift; schedule periodic relabel + retrain.
