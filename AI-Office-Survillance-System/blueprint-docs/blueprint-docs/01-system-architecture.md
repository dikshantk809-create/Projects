# 01 — Shared System Architecture

All three systems follow the same layered, edge-first reference architecture. Only
the **analytics layer** differs per product.

## High-level data flow

```
                       ┌──────────────────────── EDGE (per site) ────────────────────────┐
  Cameras              │                                                                  │
  ┌─────────┐  RTSP/   │   ┌────────────┐   ┌──────────────┐   ┌────────────────────┐     │
  │ IP CCTV │──CSI────▶│   │  Capture   │──▶│  Inference   │──▶│  Analytics / Rules │     │
  │ Pi Cam 3│          │   │ (OpenCV/   │   │ YOLO + track │   │ (zones, lines,     │     │
  │ USB cam │          │   │  GStreamer)│   │ + face/pose  │   │  debounce, FSM)    │     │
  └─────────┘          │   └────────────┘   └──────┬───────┘   └─────────┬──────────┘     │
                       │                           │ Hailo-8 NPU         │ events          │
                       │   local clip/evidence ◀───┘                     │                 │
                       └──────────────────────────────────────┬─────────┼─────────────────┘
                                                               │ events  │ (Redis Stream / MQTT, TLS)
                                                               ▼         ▼
  ┌────────────────────────────── CLOUD / ON-PREM SERVER ───────────────────────────────┐
  │  FastAPI (ingest + REST + WebSocket)                                                  │
  │     ├── auth (JWT/OAuth2, RBAC)                                                       │
  │     ├── event ingest  → validation → enrichment                                      │
  │     ├── domain services (attendance / restaurant BI / match engine)                  │
  │     └── notification fan-out (FCM push, Twilio SMS+WhatsApp, SMTP, webhook)           │
  │                                                                                       │
  │  Datastores:  PostgreSQL 16 + TimescaleDB (events/metrics) · Redis (cache/streams)    │
  │               MinIO/S3 (clips, faces, evidence)                                       │
  │                                                                                       │
  │  Analytics:   Grafana (Timescale + Prometheus)   Observability: Prometheus + Loki     │
  └───────────────────────────────────────────┬───────────────────────────────────────────┘
                                               │ REST + WS
                                               ▼
                              React + Tailwind dashboard (mobile-responsive)
                              Live feed (WebRTC/HLS), charts, timelines, alerts
```

## Why edge-first
Running detection on the edge (Pi 5 + Hailo, or Jetson) means:
- **Bandwidth:** only compact JSON events leave the site, not raw video.
- **Privacy:** raw frames + face crops can stay on-prem; only embeddings/metadata sync.
- **Latency:** sub-100 ms local alarms (intrusion, fire) independent of WAN.
- **Cost:** no per-camera cloud GPU inference bill.

The cloud/server tier aggregates events, owns the source-of-truth DB, serves the
dashboard, runs heavy/batch analytics, and fans out notifications.

## Core components (shared `platform/` library)
| Module | Responsibility |
|--------|----------------|
| `vision.detector.Detector` | Ultralytics YOLO wrapper (PyTorch/ONNX/Hailo backends), version-agnostic |
| `vision.tracker.Tracker` | ByteTrack/BoT-SORT multi-object tracking + stable IDs |
| `vision.face.FaceEngine` | InsightFace detect+embed+match (ArcFace) |
| `vision.zones` | polygon zones, tripwires/lines, point-in-zone, line-crossing |
| `common.events` | typed event schema (pydantic), debouncing, dedup |
| `alerts.dispatcher` | multi-channel notification fan-out with throttling |
| `storage.recorder` | rolling buffer → evidence clip writer (pre/post roll) |
| `api` | FastAPI app factory, JWT auth, RBAC, WebSocket hub |

## Event model (the contract between edge and cloud)
Every edge pipeline emits normalized events:
```json
{
  "event_id": "uuid",
  "site_id": "hq-floor-2",
  "camera_id": "cam-03",
  "ts": "2026-06-19T10:33:21.482Z",
  "type": "intrusion|attendance.entry|table.occupied|ball.bounce|...",
  "track_id": 142,
  "subject_id": "EMP-0012 | customer-hash | player-A | null",
  "confidence": 0.91,
  "zone": "lobby",
  "bbox": [x, y, w, h],
  "attributes": { "...domain specific..." },
  "media_ref": "s3://evidence/2026/06/19/clip-...mp4"
}
```
This single schema lets one ingest endpoint, one DB hypertable, and one alert engine
serve all three products.

## Scaling pattern
- **1 site, few cameras:** one Pi 5 (or mini-PC) per 1–4 cameras + one server VM.
- **Multi-site:** edge fleet managed via k3s/Balena; events stream to a central cluster.
- **Enterprise:** RTX GPU server(s) for centralized inference of many high-res streams
  + Kafka instead of Redis Streams; PostgreSQL with replicas; horizontal FastAPI pods.
