"""Rolling pre/post-roll evidence clip recorder.

Keep a ring buffer of recent frames; when an incident fires, flush pre-roll + record
post-roll to an MP4. Hash the file for chain-of-custody (security investigations).
"""
from __future__ import annotations
import hashlib
import os
import time
from collections import deque
from datetime import datetime
from typing import Optional
import numpy as np


class EvidenceRecorder:
    def __init__(self, out_dir: str = "./evidence", fps: int = 15,
                 pre_roll_s: int = 5, post_roll_s: int = 10, size: Optional[tuple] = None):
        self.out_dir = out_dir
        self.fps = fps
        self.pre = deque(maxlen=pre_roll_s * fps)
        self.post_roll_frames = post_roll_s * fps
        self.size = size
        os.makedirs(out_dir, exist_ok=True)
        self._recording = False
        self._post_left = 0
        self._writer = None
        self._path = None

    def push(self, frame: np.ndarray):
        """Call every frame. Buffers pre-roll and writes post-roll while recording."""
        self.pre.append(frame.copy())
        if self._recording and self._writer is not None:
            self._writer.write(frame)
            self._post_left -= 1
            if self._post_left <= 0:
                self._finish()

    def trigger(self, tag: str = "incident") -> Optional[str]:
        """Start an evidence clip: flush pre-roll then record post-roll. Returns path."""
        if self._recording or not self.pre:
            return None
        import cv2
        h, w = self.pre[-1].shape[:2]
        size = self.size or (w, h)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._path = os.path.join(self.out_dir, f"{tag}-{ts}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(self._path, fourcc, self.fps, size)
        for f in self.pre:
            self._writer.write(f)
        self._recording = True
        self._post_left = self.post_roll_frames
        return self._path

    def _finish(self):
        if self._writer:
            self._writer.release()
        self._recording = False
        self._writer = None

    @staticmethod
    def sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
