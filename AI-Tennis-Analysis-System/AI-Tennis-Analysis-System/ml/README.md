# ML — Tennis Analysis
| Model | Purpose | Data |
|-------|---------|------|
| TrackNetV4 | ball heatmap tracking (640x360, multi-frame) | labeled rally clips (ball x,y per frame) |
| YOLO11 | player detection (pretrained ok) | COCO person; fine-tune for partial bodies |
| Court keypoint net / classical | court corners → homography | annotated court images |
| Bounce model | trajectory inflection → bounce frame | labeled bounce frames |

Eval metrics: ball-tracking precision @ tolerance px, bounce-frame error (frames),
IN/OUT agreement vs human line judge, serve-speed MAE vs radar. Track in MLflow.
