"""Court geometry: homography from image → court plane (meters) and IN/OUT calls.

Standard singles court is 23.77 m (length) x 8.23 m (singles width); doubles width
10.97 m. We map the 4 detected court corners to real-world court coordinates, then
project a ball bounce point into court meters and test it against the lines.

Realism: a single camera's IN/OUT margin error is dominated by (a) bounce-frame timing
at low FPS and (b) homography calibration. Report `margin_cm` and `confidence` so close
calls can be flagged for replay rather than asserted. 95%+ needs multi-cam ≥120 fps.
"""
from __future__ import annotations
from dataclasses import dataclass

# Court dimensions in meters (origin at one baseline-left corner)
LENGTH = 23.77
SINGLES_W = 8.23
DOUBLES_W = 10.97


@dataclass
class CourtModel:
    homography: list           # 3x3 matrix (image px -> court meters)
    singles: bool = True

    def project(self, x: float, y: float) -> tuple[float, float]:
        """Apply homography to an image point → court-plane meters."""
        H = self.homography
        denom = H[2][0] * x + H[2][1] * y + H[2][2]
        cx = (H[0][0] * x + H[0][1] * y + H[0][2]) / denom
        cy = (H[1][0] * x + H[1][1] * y + H[1][2]) / denom
        return cx, cy

    def width(self) -> float:
        return SINGLES_W if self.singles else DOUBLES_W

    def call(self, cx: float, cy: float) -> dict:
        """IN/OUT for a bounce already in court meters. Returns call + signed margin.

        margin_cm > 0 means inside the line by that many cm; < 0 means out.
        """
        w = self.width()
        # distance inside each boundary (positive = inside)
        m_left = cx
        m_right = w - cx
        m_base0 = cy
        m_base1 = LENGTH - cy
        margin_m = min(m_left, m_right, m_base0, m_base1)
        call = "in" if margin_m >= 0 else "out"
        # confidence shrinks for calls within the ball-radius uncertainty band (~3 cm)
        band = 0.03
        confidence = min(1.0, abs(margin_m) / band) if abs(margin_m) < band else 1.0
        return {"call": call, "margin_cm": round(margin_m * 100, 1),
                "confidence": round(confidence, 2),
                "close": abs(margin_m) < band}


def compute_homography(image_corners, singles=True):
    """image_corners: 4 (x,y) px in order [baseline-left, baseline-right,
    far-baseline-right, far-baseline-left]. Returns CourtModel (needs OpenCV/numpy)."""
    import numpy as np, cv2
    w = SINGLES_W if singles else DOUBLES_W
    world = np.array([[0, 0], [w, 0], [w, LENGTH], [0, LENGTH]], dtype=np.float32)
    img = np.array(image_corners, dtype=np.float32)
    H, _ = cv2.findHomography(img, world)
    return CourtModel(homography=H.tolist(), singles=singles)


def detect_bounce(trajectory: list[tuple[int, float, float]], min_dy: float = 2.0):
    """Detect bounce frames as local minima in vertical (y increases downward in image,
    so a bounce is a local MAX in image-y then reversal). trajectory: [(frame,x,y)].
    Returns list of bounce indices. Heuristic baseline; refine with physics + Kalman."""
    bounces = []
    for k in range(1, len(trajectory) - 1):
        _, _, y0 = trajectory[k - 1]
        _, _, y1 = trajectory[k]
        _, _, y2 = trajectory[k + 1]
        # y goes down (increasing) then up (decreasing) => bounce at k
        if (y1 - y0) > min_dy and (y1 - y2) > min_dy:
            bounces.append(k)
    return bounces


def serve_speed_kmh(p0, p1, dt_s, court: CourtModel) -> float:
    """Estimate speed from two consecutive ball positions in image px over dt seconds."""
    c0 = court.project(*p0); c1 = court.project(*p1)
    dist_m = ((c1[0] - c0[0]) ** 2 + (c1[1] - c0[1]) ** 2) ** 0.5
    return round((dist_m / dt_s) * 3.6, 1) if dt_s > 0 else 0.0
