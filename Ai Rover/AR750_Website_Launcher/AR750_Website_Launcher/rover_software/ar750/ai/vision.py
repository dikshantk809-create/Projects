"""Two jobs for the camera: follow the crop row, and judge one plant.

Row following is plain colour work, no model needed, and it runs at full frame
rate on a Pi 4. Plant judging is a small TFLite classifier on the arm camera.
If the model file is missing, `Classifier.ready` is False and the mission logs
"model missing" instead of guessing, which is the honest behaviour.
"""
from __future__ import annotations

import math

import os
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import cv2                                       # type: ignore
except Exception:                                    # pragma: no cover
    cv2 = None

try:
    from tflite_runtime.interpreter import Interpreter  # type: ignore
except Exception:                                    # pragma: no cover
    try:
        from tensorflow.lite.python.interpreter import Interpreter  # type: ignore
    except Exception:
        Interpreter = None


# ----------------------------------------------------------------- row work
class RowFollower:
    """Find the middle of the crop row and say how hard to steer."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        lo, hi = cfg.get("green_hue", [30, 90])
        self.hue = (int(lo), int(hi))
        self.min_green = float(cfg.get("min_green_fraction", 0.04))
        self.gain = float(cfg.get("steer_gain", 0.9))
        self.last_offset = 0.0
        self.green_fraction = 0.0

    def green_mask(self, img: np.ndarray) -> Optional[np.ndarray]:
        if cv2 is None:
            return None
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lo = np.array([self.hue[0], 50, 40], np.uint8)
        hi = np.array([self.hue[1], 255, 255], np.uint8)
        m = cv2.inRange(hsv, lo, hi)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        return m

    def steer(self, img: np.ndarray) -> Tuple[float, float, Dict]:
        """Return (steer -1..1, confidence 0..1, debug)."""
        if img is None or cv2 is None:
            return 0.0, 0.0, {"reason": "no image"}
        h, w = img.shape[:2]
        band = img[int(h * 0.55):, :]                # look at the near ground
        m = self.green_mask(band)
        if m is None:
            return 0.0, 0.0, {"reason": "no opencv"}

        self.green_fraction = float(m.mean()) / 255.0
        if self.green_fraction < self.min_green:
            return 0.0, 0.0, {"reason": "no row in sight",
                              "green": self.green_fraction}

        # weight the columns by how much green is in them
        cols = m.sum(axis=0).astype(np.float64)
        total = cols.sum()
        if total <= 0:
            return 0.0, 0.0, {"reason": "empty"}
        centre = float((cols * np.arange(w)).sum() / total)
        offset = (centre - w / 2.0) / (w / 2.0)      # -1 left, +1 right
        offset = max(-1.0, min(1.0, offset))
        self.last_offset = offset
        conf = min(1.0, self.green_fraction / max(1e-6, self.min_green * 4))
        return -offset * self.gain, conf, {
            "centre_px": round(centre, 1),
            "offset": round(offset, 3),
            "green": round(self.green_fraction, 4),
        }

    def plant_ahead(self, img: np.ndarray) -> bool:
        """True when a plant sized blob sits in the middle of the near band."""
        if img is None or cv2 is None:
            return False
        h, w = img.shape[:2]
        band = img[int(h * 0.60):, int(w * 0.30):int(w * 0.70)]
        m = self.green_mask(band)
        if m is None:
            return False
        return float(m.mean()) / 255.0 > self.min_green * 3.0

    def draw(self, img: np.ndarray) -> np.ndarray:
        if img is None or cv2 is None:
            return img
        out = img.copy()
        h, w = out.shape[:2]
        cx = int(w / 2 * (1 + self.last_offset))
        cv2.line(out, (w // 2, h), (cx, int(h * 0.55)), (0, 255, 255), 2)
        cv2.line(out, (w // 2, h - 1), (w // 2, int(h * 0.55)), (120, 120, 120), 1)
        cv2.putText(out, "row %+0.2f  green %.1f%%" %
                    (self.last_offset, self.green_fraction * 100),
                    (8, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        return out


# ------------------------------------------------------------- plant judge
class Classifier:
    """Small image classifier, int8 TFLite, 224 x 224 in."""

    def __init__(self, cfg: dict, root: str = "."):
        self.cfg = cfg
        self.size = int(cfg.get("input_size", 224))
        self.min_conf = float(cfg.get("min_confidence", 0.6))
        self.model_path = os.path.join(root, cfg.get("model", ""))
        self.labels_path = os.path.join(root, cfg.get("labels", ""))
        self.labels: List[str] = []
        self.ready = False
        self._it = None
        self._in = None
        self._out = None
        self.last_ms = 0.0
        self.reason = "not loaded"

        if Interpreter is None:
            self.reason = "tflite runtime is not installed"
            return
        if not os.path.exists(self.model_path):
            self.reason = "model file not found: %s" % self.model_path
            return
        try:                                         # pragma: no cover
            self._it = Interpreter(model_path=self.model_path, num_threads=4)
            self._it.allocate_tensors()
            self._in = self._it.get_input_details()[0]
            self._out = self._it.get_output_details()[0]
            if os.path.exists(self.labels_path):
                with open(self.labels_path) as f:
                    self.labels = [l.strip() for l in f if l.strip()]
            self.ready = True
            self.reason = "ok"
        except Exception as e:                       # pragma: no cover
            self.reason = "could not load the model: %s" % e
            self.ready = False

    def classify(self, img: np.ndarray) -> Tuple[str, float]:
        """Return (label, confidence). ('unknown', 0.0) if it cannot say."""
        if not self.ready or img is None or cv2 is None:
            return "unknown", 0.0
        try:                                         # pragma: no cover
            t0 = time.time()
            x = cv2.resize(img, (self.size, self.size))
            x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB)
            if self._in["dtype"] == np.uint8:
                data = np.expand_dims(x.astype(np.uint8), 0)
            else:
                data = np.expand_dims(x.astype(np.float32) / 255.0, 0)
            self._it.set_tensor(self._in["index"], data)
            self._it.invoke()
            out = self._it.get_tensor(self._out["index"])[0]
            if out.dtype == np.uint8:
                scale, zero = self._out.get("quantization", (1.0, 0))
                out = (out.astype(np.float32) - zero) * (scale or 1.0)
            out = out.astype(np.float32)
            if out.sum() > 0:
                out = out / out.sum()
            i = int(np.argmax(out))
            conf = float(out[i])
            label = self.labels[i] if i < len(self.labels) else "unknown"
            self.last_ms = (time.time() - t0) * 1000.0
            if conf < self.min_conf:
                return "unknown", conf
            return label, conf
        except Exception:                            # pragma: no cover
            return "unknown", 0.0


# ------------------------------------------------------- simple weed finder
def ground_point(px: float, py: float, w: int, h: int, cam: dict
                 ) -> Optional[Dict[str, float]]:
    """Turn a pixel in the front camera into a spot on the ground, in mm.

    It assumes the ground is flat and the camera is where you said it is. On a
    level bed that is good to a couple of centimetres, which is enough for the
    gripper to find a weed. On a slope it will be wrong, and there is no way
    around that without a depth camera.

    Needs three numbers measured off the real rover, in cameras.front:
        height_mm    lens centre above the ground
        pitch_deg    how far it looks down from horizontal
        vfov_deg     vertical angle of view (about 48 for a Pi camera v2)
    Measure them once. Guessing them makes the arm miss.
    """
    hgt = float(cam.get("height_mm", 0) or 0)
    if hgt <= 0:
        return None                                  # not calibrated, say so
    pitch = math.radians(float(cam.get("pitch_deg", 30)))
    vfov = math.radians(float(cam.get("vfov_deg", 48)))
    hfov = 2 * math.atan(math.tan(vfov / 2) * (w / float(h)))

    # angle below horizontal of the ray through this pixel
    down = pitch + (py - h / 2.0) / h * vfov
    if down <= 0.02:                                 # at or above the horizon
        return None
    forward = hgt / math.tan(down)                   # mm in front of the lens
    across = -(px - w / 2.0) / w * hfov              # + is the rover's left
    side = forward * math.tan(across)
    return {"x_mm": round(forward + float(cam.get("forward_offset_mm", 0)), 1),
            "y_mm": round(side + float(cam.get("side_offset_mm", 0)), 1),
            "z_mm": 0.0}


def find_weed(img: np.ndarray, row_cfg: dict) -> Optional[Dict]:
    """A green blob sitting between the crop plants, low and small.

    Crude on purpose: on a kitchen plot the crop is in a line and anything
    green off the line, below a size, is worth pulling.
    """
    if img is None or cv2 is None:
        return None
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lo, hi = row_cfg.get("green_hue", [30, 90])
    m = cv2.inRange(hsv, np.array([lo, 60, 40], np.uint8),
                    np.array([hi, 255, 255], np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for c in cnts:
        a = cv2.contourArea(c)
        if not (150 < a < 0.02 * w * h):             # small blob only
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        cx = x + cw / 2.0
        if abs(cx - w / 2.0) < w * 0.12:             # too close to the row line
            continue
        if y + ch < h * 0.55:                        # too far away to reach
            continue
        score = a / (1 + abs(cx - w / 2.0))
        if best is None or score > best["score"]:
            best = {"score": score, "area": a,
                    "cx": cx, "cy": y + ch / 2.0,
                    "offset": (cx - w / 2.0) / (w / 2.0),
                    "box": (int(x), int(y), int(cw), int(ch))}
    return best
