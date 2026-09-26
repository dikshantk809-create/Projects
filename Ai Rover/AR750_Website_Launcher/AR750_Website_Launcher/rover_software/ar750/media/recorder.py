"""Recording what the rover saw on its way down the row.

A frame every couple of seconds, not 15 a second: a 20 minute outing becomes a
40 second timelapse you will actually watch, and a few megabytes instead of a
few hundred. At the end of the mission the frames are turned into an MP4 and the
loose frames are deleted.

Each frame is stamped with the time, the distance and what the rover was doing,
so the video is a record you can point at, not just a pretty clip.
"""
from __future__ import annotations

import os
import shutil
import threading
import time
from typing import Optional

try:
    import cv2                                           # type: ignore
except Exception:                                        # pragma: no cover
    cv2 = None


class Recorder:
    def __init__(self, rover, out_dir: str):
        self.r = rover
        self.dir = out_dir
        os.makedirs(self.dir, exist_ok=True)
        self._run = False
        self._thread: Optional[threading.Thread] = None
        self._frames = 0
        self._started = 0.0
        self._mission_id = 0
        self._work = ""

    # --------------------------------------------------------------- control
    @property
    def running(self) -> bool:
        return self._run

    @property
    def frames(self) -> int:
        return self._frames

    def start(self, mission_id: int) -> None:
        if self._run or cv2 is None:
            return
        if not self.r.settings.get("record.enabled", True):
            return
        self._mission_id = int(mission_id or 0)
        self._started = time.time()
        self._frames = 0
        self._work = os.path.join(self.dir, "_work_%d" % int(self._started))
        os.makedirs(self._work, exist_ok=True)
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.r.state.say("Recording the run")

    def stop(self) -> Optional[str]:
        if not self._run:
            return None
        self._run = False
        if self._thread:
            self._thread.join(timeout=5)
        return self._finish()

    # ------------------------------------------------------------------ loop
    def _loop(self) -> None:
        every = float(self.r.settings.get("record.every_seconds", 2.0))
        while self._run:
            t0 = time.time()
            try:
                self._grab()
            except Exception:
                pass
            left = every - (time.time() - t0)
            # wake often so stop() does not have to wait a whole interval
            while left > 0 and self._run:
                time.sleep(min(0.2, left))
                left -= 0.2

    def _grab(self) -> None:
        img = self.r.cam_front.frame()
        if img is None:
            return
        f = img.copy()
        h, w = f.shape[:2]
        t = self.r.state.telemetry
        m = self.r.state.mission
        line1 = time.strftime("%d %b %H:%M:%S")
        line2 = "%.1f m   %s   %s" % (t.distance_m, self.r.state.mode,
                                      (m.get("step") or ""))
        cv2.rectangle(f, (0, h - 34), (w, h), (0, 0, 0), -1)
        cv2.putText(f, line1, (8, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (235, 235, 235), 1, cv2.LINE_AA)
        cv2.putText(f, line2, (8, h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (150, 220, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(self._work, "f%06d.jpg" % self._frames), f,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        self._frames += 1

    # ---------------------------------------------------------------- finish
    def _finish(self) -> Optional[str]:
        if cv2 is None or self._frames < 2:
            shutil.rmtree(self._work, ignore_errors=True)
            return None
        names = sorted(os.listdir(self._work))
        first = cv2.imread(os.path.join(self._work, names[0]))
        if first is None:
            shutil.rmtree(self._work, ignore_errors=True)
            return None
        h, w = first.shape[:2]
        name = "run_%s.mp4" % time.strftime("%Y%m%d_%H%M", time.localtime(self._started))
        path = os.path.join(self.dir, name)
        try:
            vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 8,
                                 (w, h))
            for n in names:
                fr = cv2.imread(os.path.join(self._work, n))
                if fr is not None:
                    vw.write(fr)
            vw.release()
        except Exception as e:
            self.r.state.say("could not save the video: %s" % e, "warn")
            shutil.rmtree(self._work, ignore_errors=True)
            return None
        shutil.rmtree(self._work, ignore_errors=True)
        try:
            self.r.db.add_recording(self._mission_id, name, "timelapse",
                                    self._started, time.time(), self._frames)
        except Exception:
            pass
        self.r.state.say("Saved the run as %s (%d frames)" % (name, self._frames))
        return name

    # -------------------------------------------------------------- tidying
    def prune(self, keep_days: int) -> None:
        cut = time.time() - keep_days * 86400
        try:
            for n in os.listdir(self.dir):
                p = os.path.join(self.dir, n)
                if os.path.isfile(p) and os.path.getmtime(p) < cut:
                    os.remove(p)
        except OSError:
            pass
