# 02 — Hardware Guide (Small / Medium / Enterprise)

> Prices are 2026 ballpark USD for planning; verify with current suppliers.

## Tier A — Small scale (1 site, 1–4 cameras) — *Raspberry Pi edge*
| Item | Spec | Qty | ~Unit | Notes |
|------|------|-----|-------|-------|
| Raspberry Pi 5 | 8 GB | 1 | $80 | main edge node |
| **AI HAT+** | Hailo-8, 26 TOPS | 1 | $110 | **essential** for real-time multi-stream YOLO (~30 FPS); 8L (13 TOPS) cheaper |
| Camera | Pi Camera Module 3 (CSI) | 1–2 | $25 | wide/NoIR variants; or reuse existing IP cams |
| IP cameras | ONVIF/RTSP PoE 2–4 MP | per need | $40–90 | for CCTV retrofit |
| Storage | 256 GB+ NVMe SSD + USB/M.2 hat | 1 | $35 | clips/evidence; OS on SSD |
| Power | Official 27W USB-C PSU | 1 | $15 | |
| **UPS** | Mini-UPS / PoE UPS | 1 | $40 | ride-through + safe shutdown |
| Cooling | Active cooler/case | 1 | $15 | Hailo + sustained YOLO runs hot |
| Network | PoE switch (if IP cams) | 1 | $50 | |
| **Tier A total** | | | **~$300–450** | per edge node |

Throughput guide (Pi 5 + Hailo-8): ~30 FPS single 640px YOLO stream, or 2–4 cameras
at 8–15 FPS each (enough for analytics; not for 120 fps ball tracking).

## Tier B — Medium scale (multi-camera site / small chain) — *Jetson*
| Item | Spec | ~Unit | Notes |
|------|------|-------|-------|
| **NVIDIA Jetson Orin Nano** (Super, 8 GB) | 67 TOPS | $250–400 | 6–12 streams w/ TensorRT |
| Jetson Orin NX (16 GB) | 100+ TOPS | $600 | higher stream count / heavier models |
| NVMe SSD | 1 TB | $80 | |
| PoE switch (8-port) | | $120 | |
| IP cameras | 4–12 | $40–90 ea | |
| UPS | 600–1000 VA | $120 | |
| **Tier B total** | | **~$1.5k–3k** | per site |

## Tier C — Enterprise scale (many sites / high-res / 120 fps tennis) — *GPU server*
| Item | Spec | Notes |
|------|------|-------|
| GPU server | 1–2× RTX 4090 / RTX 6000 Ada / L40S | centralized inference, 20–50+ streams |
| CPU/RAM | 16+ cores, 128 GB | decode + batching |
| Storage | NVMe RAID + 50–100 TB NAS | clip retention |
| Network | 10 GbE, managed PoE+ switches | |
| Cameras | 4K / global-shutter; **≥120 fps** for tennis line-calling | |
| HA | dual PSU, rack UPS, redundant nodes | |
| Cost | **$8k–25k+** server + cameras | |

## Camera selection notes
- **Office/Restaurant:** 2–5 MP, good low-light (Starlight/IR), wide FOV, ONVIF/RTSP,
  PoE. Mount for face capture (entry, eye-level-ish) and overhead for counting/zones.
- **Tennis:** global-shutter, high frame-rate (**≥120 fps for calls**, 60 fps minimum),
  fast lens; ≥2 cameras for triangulating bounce; calibrate with court landmarks.
- **Night:** IR illuminators or thermal for true night intrusion; Pi NoIR + IR LED for
  Tier A.

## Per-project recommended starting hardware
| Project | Recommended start |
|---------|-------------------|
| Office Surveillance | Tier A per floor (Pi5+Hailo) → Tier B for large buildings |
| Restaurant Analytics | Tier A (one Pi per restaurant, 2–4 cams) |
| Tennis Analysis | Tier B/C — Jetson Orin or GPU box + 2× ≥120 fps cameras |
