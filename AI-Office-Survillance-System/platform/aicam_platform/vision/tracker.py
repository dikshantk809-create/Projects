"""Multi-object tracking wrapper.

Default: ByteTrack (fast, no appearance model, best speed/MOTA for counting & dwell).
Use BoT-SORT when you need appearance re-ID (e.g. re-acquiring a person after
occlusion, returning-customer matching). Both are provided by Ultralytics' built-in
trackers; this class uses `model.track(..., persist=True)` for stable IDs across frames.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class Track:
    track_id: int
    cls_id: int
    label: str
    conf: float
    xyxy: tuple[float, float, float, float]

    @property
    def xywh(self):
        x1, y1, x2, y2 = self.xyxy
        return (x1, y1, x2 - x1, y2 - y1)

    @property
    def foot(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2, y2)


class Tracker:
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        tracker: str = "bytetrack",       # "bytetrack" | "botsort"
        device: str = "cpu",
        conf: float = 0.35,
        iou: float = 0.5,
        imgsz: int = 640,
        classes: Optional[list[int]] = None,
    ):
        self.cfg = f"{tracker}.yaml"
        self.device, self.conf, self.iou, self.imgsz, self.classes = device, conf, iou, imgsz, classes
        self.model_path = model_path
        self._model = None

    def _ensure(self):
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
        return self._model

    def update(self, frame: np.ndarray) -> list[Track]:
        model = self._ensure()
        r = model.track(
            frame, persist=True, tracker=self.cfg, conf=self.conf, iou=self.iou,
            imgsz=self.imgsz, device=self.device, classes=self.classes, verbose=False,
        )[0]
        tracks: list[Track] = []
        if r.boxes is None or r.boxes.id is None:
            return tracks
        names = r.names
        for b in r.boxes:
            cls_id = int(b.cls[0])
            tracks.append(Track(
                track_id=int(b.id[0]),
                cls_id=cls_id,
                label=names.get(cls_id, str(cls_id)),
                conf=float(b.conf[0]),
                xyxy=tuple(float(v) for v in b.xyxy[0].tolist()),
            ))
        return tracks
