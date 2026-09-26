"""Two cameras: one looking forward, one on the hand looking at the plant.

Each runs in its own thread and keeps only the newest frame, so a slow web
client can never hold the rover up. If no camera is present a test pattern is
generated instead, which keeps the dashboard and the AI pipeline testable.
"""
from __future__ import annotations

import struct
import threading
import time
import zlib
from typing import Optional

import numpy as np

try:
    import cv2                                       # type: ignore
except Exception:                                    # pragma: no cover
    cv2 = None

try:
    from picamera2 import Picamera2                  # type: ignore
except Exception:                                    # pragma: no cover
    Picamera2 = None


class Camera:
    def __init__(self, name: str, cfg: dict, sim: bool = False):
        self.name = name
        self.cfg = cfg
        self.w = int(cfg.get("width", 640))
        self.h = int(cfg.get("height", 480))
        self.fps = int(cfg.get("fps", 15))
        self.source = cfg.get("source", "sim")
        self.enabled = bool(cfg.get("enabled", True))
        self.sim = sim or not self.enabled or self.source == "sim"

        self._frame: Optional[np.ndarray] = None
        self._jpeg: Optional[bytes] = None
        self._lock = threading.Lock()
        self._run = True
        self._cap = None
        self._picam = None
        self.overlay_text = ""
        self.ok = False
        # OpenCV writes JPEG. Without it we fall back to a PNG written with
        # nothing but zlib, so the simulator's camera pane still works on a
        # laptop that has not downloaded a 40 MB vision library.
        self.mime = "image/jpeg" if cv2 is not None else "image/png"

        if not self.sim:                             # pragma: no cover
            try:
                if self.source == "picam" and Picamera2 is not None:
                    self._picam = Picamera2(int(cfg.get("index", 0)))
                    c = self._picam.create_video_configuration(
                        main={"size": (self.w, self.h), "format": "RGB888"})
                    self._picam.configure(c)
                    self._picam.start()
                    self.ok = True
                elif cv2 is not None:
                    self._cap = cv2.VideoCapture(int(cfg.get("index", 0)))
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.w)
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.h)
                    self.ok = self._cap.isOpened()
                if not self.ok:
                    raise RuntimeError("camera did not open")
            except Exception:
                self.sim = True
                self._cap = self._picam = None

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ api
    def frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._jpeg

    def close(self) -> None:
        self._run = False
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        if self._cap is not None:                    # pragma: no cover
            self._cap.release()
        if self._picam is not None:                  # pragma: no cover
            try:
                self._picam.stop()
            except Exception:
                pass

    # -------------------------------------------------------------- inside
    def _loop(self) -> None:
        period = 1.0 / max(1, self.fps)
        while self._run:
            t0 = time.time()
            img = self._grab()
            if img is not None:
                self._stamp(img)
                with self._lock:
                    self._frame = img
                    self._jpeg = self._encode(img)
            dt = period - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)

    def _grab(self) -> Optional[np.ndarray]:
        if self._picam is not None:                  # pragma: no cover
            try:
                return self._picam.capture_array()
            except Exception:
                return None
        if self._cap is not None:                    # pragma: no cover
            ok, img = self._cap.read()
            return img if ok else None
        return self._test_pattern()

    def _test_pattern(self) -> np.ndarray:
        """A moving crop row, so row following and the dashboard can be tried."""
        t = time.time()
        img = np.zeros((self.h, self.w, 3), np.uint8)
        img[:, :] = (72, 96, 120)                     # soil
        # two rows of green plants drifting past
        for row, cx in ((0, 0.34), (1, 0.66)):
            sway = 0.05 * np.sin(t * 0.7 + row)
            for i in range(7):
                y = int(self.h * (0.25 + i * 0.12))
                x = int(self.w * (cx + sway) + (i - 3) * 4)
                r = max(6, int(self.h * 0.055 * (0.6 + i * 0.09)))
                colour = (40, 150, 60) if (i + row) % 5 else (35, 110, 120)
                if cv2 is not None:
                    cv2.circle(img, (x, y), r, colour, -1)
                else:
                    y0, y1 = max(0, y - r), min(self.h, y + r)
                    x0, x1 = max(0, x - r), min(self.w, x + r)
                    img[y0:y1, x0:x1] = colour
        return img

    def _stamp(self, img: np.ndarray) -> None:
        if cv2 is None:
            return
        label = "%s  %s" % (self.name.upper(),
                            time.strftime("%H:%M:%S"))
        cv2.putText(img, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1, cv2.LINE_AA)
        if self.overlay_text:
            cv2.putText(img, self.overlay_text, (8, self.h - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 240, 255), 1,
                        cv2.LINE_AA)

    def _encode(self, img: np.ndarray) -> Optional[bytes]:
        if cv2 is not None:
            # Only the live view uses this. Plant photos are saved from the
            # raw frame, so a lighter live picture costs them nothing.
            q = int(self.cfg.get("jpeg_quality", 60))
            ok, buf = cv2.imencode(".jpg", img,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), q])
            return buf.tobytes() if ok else None
        return _png(img)


def _png(img: np.ndarray) -> Optional[bytes]:
    """A PNG, written with only zlib and struct.

    Without this the simulator's camera pane is a black rectangle on any
    machine that has not installed OpenCV - which is every laptop that just
    ran the launcher, because the launcher deliberately does not download a
    40 MB vision library to look at a test pattern. The Pi has OpenCV and
    uses the JPEG path above; this is the fallback, not the normal route.

    The array is OpenCV-ordered (blue, green, red), so the channels are
    reversed on the way out.
    """
    try:
        arr = np.ascontiguousarray(img[:, :, ::-1], dtype=np.uint8)
        h, w, _ = arr.shape
        # every scanline is prefixed with its filter byte, here always 0
        raw = np.hstack([np.zeros((h, 1), np.uint8),
                         arr.reshape(h, w * 3)]).tobytes()

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + tag + data +
                    struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6))
                + chunk(b"IEND", b""))
    except Exception:
        return None
