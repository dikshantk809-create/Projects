"""TrackNetV4 ball-tracking wrapper.

TrackNet predicts a heatmap of the (tiny, fast) ball from a stack of consecutive frames
(640x360). We take the argmax as the ball position. This wrapper isolates the model so
you can drop in trained weights without touching the pipeline. Without weights it raises
a clear error (ball calls require the trained model).
"""
from __future__ import annotations
from collections import deque
import numpy as np


class BallTracker:
    def __init__(self, weights: str | None = None, in_frames: int = 3, size=(640, 360)):
        self.weights = weights
        self.in_frames = in_frames
        self.size = size
        self.buf: deque = deque(maxlen=in_frames)
        self._model = None

    def _ensure(self):
        if self._model is None:
            if not self.weights:
                raise RuntimeError("TrackNet weights not set — train via ml/training/train_tracknet.py")
            import torch
            self._model = torch.jit.load(self.weights).eval()  # or load custom arch
        return self._model

    def update(self, frame) -> tuple[float, float] | None:
        """Push a frame; return (x,y) ball position in original image px, or None."""
        import cv2
        small = cv2.resize(frame, self.size)
        self.buf.append(small)
        if len(self.buf) < self.in_frames:
            return None
        model = self._ensure()
        import torch
        stack = np.concatenate([f.transpose(2, 0, 1) for f in self.buf], axis=0)[None]
        with torch.no_grad():
            heat = model(torch.tensor(stack, dtype=torch.float32) / 255.0)[0, 0].numpy()
        if heat.max() < 0.5:
            return None
        sy, sx = np.unravel_index(heat.argmax(), heat.shape)
        h, w = frame.shape[:2]
        return (sx * w / self.size[0], sy * h / self.size[1])
