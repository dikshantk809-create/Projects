# ML — Office Surveillance

Pretrained models (COCO YOLO11 + InsightFace ArcFace) cover MVP with no training.
Fine-tune these for production:

| Target | Approach | Dataset |
|--------|----------|---------|
| Fire / smoke | YOLO11 fine-tune | D-Fire, FireNet, custom site footage |
| Weapon (gun/knife) | YOLO11 fine-tune | Sohas weapons, custom |
| Phone-in-hand | YOLO11 fine-tune (vs generic 'cell phone') | custom labeled office frames |
| Behavior (working/idle/phone/talking/walking/break/meeting) | YOLO11-pose → temporal GRU/TCN on keypoint sequences | self-collected, consented |
| Fall | pose heuristics + temporal confirm | UR Fall, custom |
| Violence/fight | VideoMAE / X3D clip classifier | RWF-2000, Hockey Fight |

Pipeline: label (CVAT/Roboflow) → train → evaluate (PR per class) → export
ONNX→HEF(Hailo)/TensorRT → register (MLflow) → canary device → fleet.
