# 14 — Raspberry Pi 5 Setup (Office edge node)

## 1. Flash OS
- Raspberry Pi OS (64-bit, Bookworm) to NVMe SSD (preferred) or A2 SD.
- Enable SSH, set hostname `office-edge-<floor>`, configure Wi-Fi/Ethernet.

## 2. Base packages
```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y python3-venv python3-pip git libgl1 libglib2.0-0 ffmpeg
```

## 3. AI HAT+ (Hailo-8) — accelerator
```bash
# Attach AI HAT+ to PCIe, then:
sudo apt install -y hailo-all          # HailoRT + firmware + tappas (RPi repo)
sudo reboot
hailortcli fw-control identify          # verify the Hailo device is detected
```
Convert YOLO to Hailo: export ONNX (`yolo export ... format=onnx`) then compile to
`.hef` with the Hailo Model Zoo / Dataflow Compiler on an x86 box; copy `.hef` to the Pi.

## 4. Camera
- **CSI (Pi Camera Module 3):** enabled by default on Bookworm; test `rpicam-hello`.
- **IP cameras:** use the RTSP URL as `AICAM_SOURCE`.

## 5. App
```bash
git clone <repo> && cd ai-camera-systems
python3 -m venv .venv && source .venv/bin/activate
pip install -e "platform[detect,face]" httpx
cp project-1-office-surveillance/.env.example project-1-office-surveillance/.env
# edit .env: AICAM_SOURCE, AICAM_BACKEND_URL, AICAM_INGEST_TOKEN, AICAM_DEVICE=hailo
```

## 6. Run as a service (auto-start)
```ini
# /etc/systemd/system/office-edge.service
[Unit]
Description=AI Office Edge Pipeline
After=network-online.target
[Service]
WorkingDirectory=/home/pi/ai-camera-systems
EnvironmentFile=/home/pi/ai-camera-systems/project-1-office-surveillance/.env
ExecStart=/home/pi/ai-camera-systems/.venv/bin/python project-1-office-surveillance/edge/office_pipeline.py
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now office-edge.service
journalctl -u office-edge -f
```

## 7. Hardening
Disk encryption, change default creds, `unattended-upgrades`, firewall (ufw), cameras on
isolated VLAN, device enrolled in fleet manager (Balena/k3s). See `../blueprint-docs/05`.
