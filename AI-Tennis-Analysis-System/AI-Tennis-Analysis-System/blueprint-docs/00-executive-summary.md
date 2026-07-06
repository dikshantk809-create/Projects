# 00 — Executive Summary

## What this is
Three enterprise AI camera systems that convert ordinary IP/CCTV cameras (or
Raspberry Pi cameras) into intelligent analytics + security platforms:

1. **AI Office Surveillance** — face-based attendance, productivity analytics, and
   24/7 intrusion + safety (fire/smoke/weapon/fall/violence) detection.
2. **AI Restaurant Analytics** — footfall counting, dwell-time & behavior analytics,
   POS-integrated food intelligence, demand forecasting, and night security.
3. **AI Tennis Analysis** — ball/player/court tracking, automated line-calling,
   scoring, and player/coach analytics.

All three share one platform library (`platform/`) and one operational pattern:
**capture → edge inference → event stream → backend → datastore → dashboard/alerts.**

## Why a shared platform
The three problems look different but 70% of the engineering is identical: ingest
RTSP, run YOLO detection, track objects, define zones/lines, debounce events, store
time-series, push real-time updates, and fan out alerts. We build that once and let
each product own only its domain logic (attendance, table dwell, line-calling).

## Target market & positioning
| Project | Buyer | Competing with | Wedge |
|---------|-------|----------------|-------|
| Office | SMB/enterprise facilities & HR/security | Verkada, manual attendance, basic NVRs | AI on *existing* cameras, attendance + safety in one |
| Restaurant | Restaurant owners, small chains | RetailNext, Footfallcam, manual logs | POS + vision fusion, cheap Pi edge node |
| Tennis | Clubs, academies, prosumers | Hawk-Eye (premium), PlaySight, SwingVision | Affordable club-grade analytics & calls |

## Realistic accuracy & expectation setting
- Face recognition: 99%+ on cooperative, well-lit frontal faces; degrades with angle,
  occlusion, low light. Use multi-frame voting + a confidence threshold + manual
  fallback.
- Person detection/counting: 90–97% with YOLO11/26 + ByteTrack in typical indoor
  scenes; line-crossing counting needs good camera placement (top-down/angled).
- Action/behavior ("idle", "phone use", "talking"): these are **noisy proxies**
  (70–90% depending on class and camera angle). Report as trends, not verdicts.
- Safety detectors (fire/smoke/weapon/violence/fall): high recall is achievable but
  **false positives are real** — always require human confirmation before
  irreversible action and tune thresholds on-site.
- Tennis line-calling: a single 30–50 fps camera yields *indicative* calls only.
  **95%+ pro-grade calls require multiple ≥120 fps calibrated cameras** (the Hawk-Eye
  approach). Project 3 ships the realistic single/dual-cam path and documents the
  upgrade to high accuracy.

## Build phases (applies to each project)
1. **MVP (4–6 wks):** single camera, core detection, DB + API + minimal dashboard.
2. **Beta (6–10 wks):** multi-camera, full analytics, alerts, Grafana, auth/RBAC.
3. **Production (8–12 wks):** edge fleet, HA datastore, observability, security
   hardening, compliance (DPIA, retention), load + accuracy validation.

## Critical risks
- **Legal/biometric:** Projects 1 & 2 need consent, retention limits, DPIA. See doc 05.
- **Accuracy liability:** never auto-fire/auto-penalize on a model output alone.
- **Edge thermal/throughput:** budget a Hailo AI HAT+ per Pi for real-time multi-stream.
- **Data volume:** video + events grow fast; use TimescaleDB retention + tiered storage.
