# 16 — Raspberry Pi 4 Setup (CPU-only edge, USB webcam)

> This is the **budget / learning** path. The full system targets a **Pi 5 + AI HAT+
> (Hailo-8)** — see [`14-raspberry-pi-setup.md`](14-raspberry-pi-setup.md). A **Pi 4 has
> no PCIe connector for the AI HAT+**, so there is no Hailo acceleration here: detection
> runs on the Pi 4 CPU with a small model. Good enough for a single-camera demo, not for
> a multi-camera production floor.

## Recommended architecture

Split the work across the two machines you already have:

```
USB webcam → Raspberry Pi 4 (edge: YOLO11n via NCNN, CPU)
                 │  events over Wi-Fi/LAN (HTTP)
                 ▼
        Your PC  (docker compose: FastAPI + Postgres/Timescale + dashboard + Grafana)
                 ▼
        Browser  → dashboard http://localhost:5174  (Live panel updates in real time)
```

The Pi 4 is too weak to comfortably run TimescaleDB + MinIO + Grafana + the API, so the
heavy backend stays on the PC (where it already runs via Docker). The Pi only runs the
lightweight detection loop.

## What works vs. not on a Pi 4

| Feature | Pi 4 (CPU) |
|---|---|
| Person + phone detection, tracking | ✅ (small model, ~2–8 FPS) |
| Behavior proxy (working/idle/phone/walking) | ✅ |
| Night intrusion (unknown person) | ✅ |
| Live events on the dashboard | ✅ |
| **Name-based attendance / face recognition** | ⚠️ Off by default — InsightFace is too heavy. Enroll + enable later, or do it on the PC. |
| Multi-camera, fire/smoke/weapon models | ❌ Needs Pi 5 + Hailo or a GPU box |

---

## Phase 0 — Prove it live on your PC first (10 min, no Pi)

This de-risks everything: confirm the camera → AI → dashboard loop works before touching
the Pi.

1. Start the backend (as today): run `run.bat` and wait for the dashboard at
   `http://localhost:5174`. Optionally `seed.bat` for demo charts.
2. Install the edge deps on the PC (Python 3.11+):
   ```bash
   python -m venv .venv && .venv\Scripts\activate      # Windows
   pip install -e "platform[detect]" httpx opencv-python
   ```
3. Create `edge/.env` from the template and point it at the local backend:
   ```
   AICAM_SOURCE=0
   AICAM_MODEL_PATH=yolo11n.pt
   AICAM_DEVICE=cpu
   AICAM_IMGSZ=480
   AICAM_FPS_LIMIT=8
   AICAM_FACE_ENABLED=false
   AICAM_SHOW=true
   AICAM_BACKEND_URL=http://localhost:8001
   AICAM_INGEST_TOKEN=please-change-me-too     # = OFFICE_INGEST_TOKEN in .env
   ```
4. Run it:
   ```bash
   cd edge && python office_pipeline.py
   ```
   A window opens with boxes on people/phones, and the dashboard **Live Detections &
   Alerts** panel fills in real time. That is the "it actually works" moment.

---

## Phase 1 — Move the edge onto the Pi 4

### 1. OS
Raspberry Pi OS (64-bit, Bookworm) on an A2 SD card or USB SSD. Enable SSH; connect to the
same network as the PC.

### 2. One-command setup
Clone the repo on the Pi, then:
```bash
bash edge/setup_pi4.sh          # headless (for the service)
# bash edge/setup_pi4.sh --gui  # if a monitor is attached and you want the preview
```
This installs system + Python deps, exports a fast **NCNN** model (`yolo11n_ncnn_model`),
creates `edge/.env`, and writes a `office-edge.service` with the correct paths.

NCNN is an ARM-optimized inference engine — markedly faster than plain PyTorch on the Pi 4.

### 3. Point the Pi at your PC
Find the PC's LAN IP (`ipconfig` on Windows → IPv4, e.g. `192.168.1.50`). Edit `edge/.env`:
```
AICAM_BACKEND_URL=http://192.168.1.50:8001
AICAM_INGEST_TOKEN=please-change-me-too        # identical to the server's OFFICE_INGEST_TOKEN
```
Allow the backend port through the PC firewall (PowerShell as admin, one time):
```powershell
New-NetFirewallRule -DisplayName "AI Office 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```
Verify from the Pi: `curl http://192.168.1.50:8001/health` → `{"status":"ok",...}`.

### 4. Test, then run as a service
```bash
cd edge && ../.venv/bin/python office_pipeline.py     # foreground; expect a 2s heartbeat
# then:
sudo cp edge/office-edge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now office-edge.service
journalctl -u office-edge -f
```

---

## Tuning the Pi 4

- **Too slow?** Lower `AICAM_IMGSZ` (320 → 256) and `AICAM_FPS_LIMIT` (4 → 2).
- **More accuracy, slower:** raise `AICAM_IMGSZ` to 416/480.
- **Active cooling** matters — the Pi 4 throttles when hot under sustained inference.
- **USB webcam** should be on a USB 3.0 (blue) port. Test with `AICAM_SOURCE=1` if `0` is wrong.
- Want a small speed bump in hardware? A **Coral USB Accelerator** (Edge TPU) is the realistic
  add-on for a Pi 4 (the Hailo AI HAT+ is Pi 5 only).

## Enabling face recognition later (optional)
On the PC (or a Pi 5), `pip install -e "platform[face]"`, set `AICAM_FACE_ENABLED=true`,
enroll consented employees, and name-based attendance events will start flowing. Review
[`../blueprint-docs/05-security-and-compliance.md`](../blueprint-docs/05-security-and-compliance.md)
first — biometric processing needs consent + a DPIA.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `cannot open source 0` | Try `AICAM_SOURCE=1`; check the webcam with `rpicam-hello` / `ls /dev/video*` |
| `events_sent` stays 0 | Wrong `AICAM_BACKEND_URL`, firewall, or token mismatch. Test `curl .../health` |
| Preview error / headless | Set `AICAM_SHOW=false` (no display) — it auto-disables and keeps running |
| Very low FPS | Lower `AICAM_IMGSZ`/`AICAM_FPS_LIMIT`; ensure NCNN model (not `.pt`); add cooling |
| Dashboard Live panel empty | Edge not posting, or browser can't reach backend; check the heartbeat log |
