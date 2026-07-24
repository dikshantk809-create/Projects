"""Version-agnostic YOLO detector wrapper.

Works with YOLO11 (default) or YOLO26 (2026 SOTA, NMS-free) just by changing the
model path/weights. Supports torch / onnx / engine weights; for Hailo on Raspberry Pi
you typically run the .hef through HailoRT — swap `_infer` accordingly (see edge docs).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class Detection:
    cls_id: int
    label: str
    conf: float
    xyxy: tuple[float, float, float, float]

    @property
    def xywh(self) -> tuple[float, float, float, float]:
        x1, y1, x2, y2 = self.xyxy
        return (x1, y1, x2 - x1, y2 - y1)


class Detector:
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        device: str = "cpu",
        conf: float = 0.35,
        iou: float = 0.5,
        imgsz: int = 640,
        classes: Optional[list[int]] = None,
    ):
        self.model_path = model_path
        self.device = device
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.classes = classes
        self._model = None  # lazy

    def _ensure(self):
        if self._model is None:
            from ultralytics import YOLO  # lazy import keeps platform importable w/o torch
            self._model = YOLO(self.model_path)
        return self._model

    @property
    def names(self) -> dict[int, str]:
        return self._ensure().names

    def detect(self, frame: np.ndarray) -> list[Detection]:
        model = self._ensure()
        r = model.predict(
            frame, conf=self.conf, iou=self.iou, imgsz=self.imgsz,
            device=self.device, classes=self.classes, verbose=False,
        )[0]
        out: list[Detection] = []
        names = r.names
        if r.boxes is None:
            return out
        for b in r.boxes:
            cls_id = int(b.cls[0])
            out.append(Detection(
                cls_id=cls_id,
                label=names.get(cls_id, str(cls_id)),
                conf=float(b.conf[0]),
                xyxy=tuple(float(v) for v in b.xyxy[0].tolist()),
            ))
        return out
