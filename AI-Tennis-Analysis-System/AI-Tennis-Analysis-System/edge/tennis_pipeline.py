#!/usr/bin/env python3
"""AI Tennis Analysis — edge pipeline.

Per frame: track ball (TrackNetV4) + players (YOLO11+ByteTrack); buffer the ball
trajectory; on a detected bounce, project to the court plane and emit an IN/OUT call;
estimate serve speed; push events to the backend. Scoring is maintained server-side.

Run on Jetson Orin / GPU for real ball tracking. On Pi it can still do player/court
analytics. Calibrate the court first (see docs/14).
"""
from __future__ import annotations
import os, time
import cv2, httpx

from aicam_platform.common import get_settings, get_logger
from aicam_platform.common.events import Event, EventType
from aicam_platform.vision import Tracker
from ball_tracker import BallTracker
import sys, os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../backend")))
from app.services.court import CourtModel, detect_bounce, serve_speed_kmh

log = get_logger("tennis-edge")
S = get_settings()
PERSON = 0


class TennisEdge:
    def __init__(self, court: CourtModel | None = None, match_id: str = "demo"):
        self.players = Tracker(model_path=S.model_path, tracker="bytetrack",
                               device=S.device, conf=0.3, imgsz=S.imgsz, classes=[PERSON])
        self.ball = BallTracker(weights=os.getenv("AICAM_TRACKNET_WEIGHTS"))
        self.court = court
        self.match_id = match_id
        self.client = httpx.Client(base_url=S.backend_url, timeout=5,
                                   headers={"Authorization": f"Bearer {S.ingest_token}"})
        self.traj: list[tuple[int, float, float]] = []

    def _post(self, ev: Event):
        try: self.client.post("/api/v1/ingest/events", content=ev.model_dump_json())
        except Exception as e: log.warning(f"post failed: {e}")

    def _handle_bounce(self, frame_idx: int):
        if not self.court or len(self.traj) < 5:
            return
        idxs = detect_bounce(self.traj[-8:])
        if not idxs:
            return
        _, bx, by = self.traj[-8:][idxs[-1]]
        cx, cy = self.court.project(bx, by)
        result = self.court.call(cx, cy)
        self._post(Event(site_id=S.site_id, camera_id=S.camera_id,
                         type=EventType.LINE_CALL, confidence=result["confidence"],
                         attributes={"match_id": self.match_id, **result,
                                     "bounce_cx": cx, "bounce_cy": cy, "frame": frame_idx}))
        log.info(f"CALL {result['call']} margin={result['margin_cm']}cm "
                 f"conf={result['confidence']} close={result['close']}")

    def run(self):
        src = int(S.source) if S.source.isdigit() else S.source
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            raise SystemExit(f"cannot open {S.source}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        log.info(f"tennis edge on {S.source} @ ~{fps:.0f} fps")
        i = 0
        while True:
            ok, frame = cap.read()
            if not ok: break
            i += 1
            # players (every few frames is fine)
            if i % 3 == 0:
                for t in self.players.update(frame):
                    self._post(Event(site_id=S.site_id, camera_id=S.camera_id,
                                     type=EventType.DETECTION, track_id=t.track_id,
                                     attributes={"role": "player", "match_id": self.match_id,
                                                 "foot": list(t.foot)}))
            # ball every frame (needs high FPS)
            try:
                pos = self.ball.update(frame)
            except RuntimeError as e:
                log.error(str(e)); break
            if pos:
                self.traj.append((i, pos[0], pos[1]))
                self._handle_bounce(i)
        cap.release()


if __name__ == "__main__":
    # In production, load court calibration from the backend (match.court_calibration).
    TennisEdge().run()
