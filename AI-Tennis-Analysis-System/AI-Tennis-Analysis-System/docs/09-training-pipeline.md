# 09 — Training Pipeline (Tennis)
1. Collect rally clips from your camera(s) at target FPS; label ball (x,y)/frame,
   bounces, court corners. 2. Train TrackNet (`ml/training/train_tracknet.py`) on Gaussian
   heatmaps; YOLO players (pretrained ok); court keypoints. 3. Evaluate ball precision,
   bounce-frame error, IN/OUT agreement vs human judge. 4. Export TrackNet (torch.jit)
   + YOLO (TensorRT). 5. Calibrate per court before matches. Track all in MLflow.
