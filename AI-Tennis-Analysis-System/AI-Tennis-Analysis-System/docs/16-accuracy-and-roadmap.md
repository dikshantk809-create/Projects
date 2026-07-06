# 16 — Accuracy Reality & Roadmap to 95%+

## Why a single camera can't match Hawk-Eye
- **Hawk-Eye:** 10+ calibrated cameras @ ≥120 fps, 3D triangulation, ~3.6 mm avg error.
- **Single camera @ 30–50 fps:** the ball moves 0.3–0.8 m between frames at 150+ km/h, so
  the exact bounce frame is uncertain; one viewpoint also can't resolve depth, so the
  bounce point on the court plane has cm–dm error near lines.

## Realistic targets (this system)
| Setup | Line-call agreement | Use |
|-------|--------------------|-----|
| 1 cam, 30–50 fps | ~80–88% (good on clear calls; flag close calls) | practice, casual |
| 1 cam, 120 fps, calibrated | ~88–92% | club/academy |
| 2+ synced cams, 120–240 fps, triangulated | 95%+ achievable | semi-pro |

## Engineering levers (in priority order)
1. **Higher FPS + global shutter** — biggest single win for bounce timing.
2. **Sub-frame bounce estimation** — fit ballistic trajectory + interpolate the bounce
   instant between frames (don't just take the nearest frame).
3. **Kalman/physics smoothing** of the ball track to reject TrackNet jitter.
4. **Calibration quality** — accurate corner detection + lens distortion correction.
5. **Multi-camera triangulation** — recover true 3D bounce; this is the path to 95%+.
6. **Confidence-gated calls** — assert clear calls, route close calls (< ~3 cm margin)
   to replay/human review instead of guessing. This keeps *trust* high even when
   absolute accuracy is bounded.

Ship behavior: always surface `margin_cm` + `confidence`; mark `close` calls for review.
