# 14 — Raspberry Pi / Camera Setup (Tennis)
A Pi 5 can run player + court analytics and act as the dashboard host, but **real-time
ball tracking for line calls needs a Jetson Orin or GPU** (high FPS + TrackNet).
Camera: mount **elevated, behind the baseline**, global-shutter, **≥120 fps** for calls.
**Calibration (once per setup):** capture the 4 court corners; compute homography
(`court.compute_homography`) and save to the match's `court_calibration`. Re-calibrate if
the camera moves. For 95%+ accuracy add a second synchronized camera and triangulate.
