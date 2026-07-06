# 07 — AI Models Overview (shared)

| Capability | Model / method | Notes & realism |
|------------|----------------|-----------------|
| Object detection (person, phone, bag, weapon proxies, food, ball...) | **YOLO11** (n/s/m) default; **YOLO26** upgrade | NMS-free YOLO26 simplifies edge export; pick size by device |
| Multi-object tracking | **ByteTrack** (default), **BoT-SORT** for appearance re-ID | stable `track_id` for counting, dwell, rallies |
| Face detection + recognition | **InsightFace**: SCRFD detector + **ArcFace** `buffalo_l` embeddings | cosine match vs enrolled gallery; multi-frame voting |
| Pose estimation | **YOLO11-pose** (COCO 17-kpt) | feeds action/fall/behavior classifiers |
| Action / behavior recognition | pose-sequence + lightweight temporal model (GRU/TCN) or VideoMAE for richer classes | "working/idle/phone/talking/eating" = noisy proxies |
| Fall detection | pose heuristics (aspect ratio, vertical velocity, ground contact) + temporal confirm | high recall; tune to cut false alarms |
| Fire / smoke | YOLO fine-tuned on fire/smoke datasets (D-Fire etc.) | pair with color/flicker heuristics; validate on-site |
| Weapon detection | YOLO fine-tuned (gun/knife datasets) | expect false positives; human-verify before action |
| Violence / fight | temporal action model (e.g. X3D / VideoMAE) on clip windows | hardest class; treat as alert-for-review |
| Tennis ball | **TrackNetV4** heatmap tracker (640×360, multi-frame, motion-aware) | tiny fast object; needs high FPS for calls |
| Court lines | classical line detection + homography to a court model | enables IN/OUT via bounce projection |
| Bounce / line call | trajectory + bounce detection → project to court plane → IN/OUT | **95%+ needs multi ≥120 fps cams**; single cam = indicative |
| Re-identification (returning customers) | OSNet / ArcFace embeddings + vector search | privacy: store hashes, consent required |

## Model lifecycle
- **Pretrained first:** COCO YOLO + InsightFace get you to MVP with zero training.
- **Fine-tune** domain classes (fire, weapon, food types, "phone-in-hand") on curated
  datasets; track with MLflow, version data with DVC.
- **Export per device:** PyTorch → ONNX → (Hailo HEF for Pi / TensorRT for Jetson/GPU).
- **Evaluate** with held-out + on-site validation sets; record precision/recall per
  class; set deployment thresholds from PR curves.
- **Monitor drift** in production; schedule periodic re-labeling + retraining.

See each project's `ml/` folder and `docs/09-training-pipeline` section for the
concrete datasets, classes, and training commands.
