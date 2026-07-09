<div align="center">

<img src="https://capsule-render.vercel.app/api?type=cylinder&color=0:FF416C,100:FF4B2B&height=220&section=header&text=AI%20Office%20Surveillance&fontSize=52&fontColor=ffffff&animation=fadeIn&desc=Turn%20Ordinary%20CCTV%20into%20Intelligent%20Security&descSize=18&descAlignY=75" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=700&color=FF416C&center=true&vCenter=true&width=720&lines=Face-Based+Attendance+%F0%9F%99%82;Productivity+Analytics+%F0%9F%93%8A;24%2F7+Intrusion+%2B+Safety+Detection+%F0%9F%9A%A8;Fire+%7C+Smoke+%7C+Weapon+%7C+Fall+Detection+%F0%9F%94%A5;Edge+AI+on+Raspberry+Pi+5+%E2%9A%A1" alt="Typing SVG" />

<br/><br/>

![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![YOLO11](https://img.shields.io/badge/YOLO11-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi_5-A22846?style=for-the-badge&logo=raspberrypi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

<img src="https://img.shields.io/badge/Edge_AI-⚡_Real--Time-red?style=flat-square"/>
<img src="https://img.shields.io/badge/Detection-YOLO11_+_ByteTrack-blue?style=flat-square"/>
<img src="https://img.shields.io/badge/Face_Recognition-InsightFace_ArcFace-purple?style=flat-square"/>
<img src="https://img.shields.io/badge/Privacy-GDPR_Aware-green?style=flat-square"/>

</div>

---

## 🎯 What Is This?

> **Ordinary office CCTV/IP cameras → Intelligent AI platform.**
> Attendance, productivity analytics & 24/7 security — sab kuch existing cameras se, bina expensive hardware ke.

Ek **edge-first** system: Raspberry Pi 5 (+ AI HAT) har floor par cameras se RTSP stream leta hai, AI models locally chalata hai, aur sirf compact **events** backend ko bhejta hai. Result — low bandwidth, fast alerts, aur data aapke premises par.

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    A["📷 CCTV / IP Cameras<br/>(RTSP)"] --> B["⚡ Edge Node — Pi 5<br/>YOLO11 Detect → ByteTrack<br/>InsightFace → Pose → Rules"]
    B -->|"🎬 Evidence Clips"| C[("💾 Local Storage")]
    B -->|"📨 Events"| D["🚀 FastAPI Backend"]
    D --> E[("🐘 PostgreSQL<br/>TimescaleDB")]
    D --> F["🔔 Alerts<br/>Push / SMS / WhatsApp"]
    D --> G["📊 React Dashboard<br/>+ Grafana"]

    style A fill:#1a1a2e,color:#fff,stroke:#FF416C
    style B fill:#FF416C,color:#fff,stroke:#FF4B2B,stroke-width:3px
    style C fill:#16213e,color:#fff,stroke:#0f3460
    style D fill:#009688,color:#fff,stroke:#00695C
    style E fill:#4169E1,color:#fff,stroke:#1E3A8A
    style F fill:#FF9800,color:#000,stroke:#F57C00
    style G fill:#61DAFB,color:#000,stroke:#0288D1
```

**Pipeline:** `Capture → Edge Inference → Event Stream → Backend → Datastore → Dashboard/Alerts`

---

## ✨ Features

<table>
<tr>
<td width="33%" valign="top" align="center">

### 🙂 Smart Attendance
Face-based entry/exit logging with **InsightFace/ArcFace** — no cards, no proxies. Multi-frame voting + confidence thresholds for accuracy.

</td>
<td width="33%" valign="top" align="center">

### 📊 Productivity Analytics
Zone-based presence, activity trends & aggregate insights. **Trends, not verdicts** — privacy-first design.

</td>
<td width="33%" valign="top" align="center">

### 🚨 24/7 Security
Intrusion detection with tripwires & zones, night-mode monitoring, and **automatic evidence clip recording**.

</td>
</tr>
<tr>
<td width="33%" valign="top" align="center">

### 🔥 Safety Detection
Fire, smoke, weapon, fall & violence detection — high recall with human-confirmation workflow.

</td>
<td width="33%" valign="top" align="center">

### 🔔 Instant Alerts
Push notifications, SMS, WhatsApp & email fan-out the moment something happens.

</td>
<td width="33%" valign="top" align="center">

### 📈 Live Dashboard
React + Grafana dashboards — Live view, Attendance, Productivity, Security & Admin panels.

</td>
</tr>
</table>

---

## 🧠 AI Stack

| Layer | Technology | Job |
|-------|-----------|-----|
| 👁️ Detection | **YOLO11** (Ultralytics) | Person / object detection |
| 🎯 Tracking | **ByteTrack** | Multi-object tracking across frames |
| 🙂 Recognition | **InsightFace / ArcFace** | Face embeddings & matching |
| 🤸 Behavior | **YOLO11-Pose** | Pose-based activity estimation |
| 📏 Rules Engine | Zones, Tripwires, Debouncer | Attendance, intrusion & safety logic |
| 🎬 Evidence | OpenCV Recorder | Auto clip recording on incidents |

---

## 📂 Project Structure

```
AI-Office-Survillance-System/
│
├── ⚡ backend/          → FastAPI: routes, services (attendance, productivity,
│                          security, recognition), models, workers
├── 📊 dashboard/        → React dashboard (Live | Attendance | Productivity
│                          | Security | Admin)
├── 📘 blueprint-docs/   → Architecture, hardware guide, cost estimation,
│                          tech stack, security & compliance
├── 📚 docs/             → API design, training pipeline, deployment,
│                          Raspberry Pi setup guides
├── 🚀 run.sh            → One-command startup
├── 🌱 seed.bat          → Seed demo data
└── 🛑 stop.bat          → Stop all services
```

---

## ⚙️ Quick Start

```bash
# Clone the repo
git clone https://github.com/dikshantk809-create/Projects.git
cd Projects/AI-Office-Survillance-System

# Linux / macOS
./run.sh

# Windows
seed.bat     # seed demo data
run.sh       # via Git Bash / WSL
stop.bat     # stop services
```

📖 **Detailed setup:** dekho [`docs/`](./docs) — Raspberry Pi setup, deployment & training pipeline guides.

---

## 🎛️ Hardware (Per Floor)

| Component | Spec |
|-----------|------|
| 🧠 Edge Node | Raspberry Pi 5 (8GB) + AI HAT+ (Hailo-8) |
| 📷 Cameras | Pi Camera 3 / 2–4 IP cameras (RTSP) |
| 💾 Storage | 256GB+ NVMe |
| 🔌 Power | UPS + PoE switch + active cooling |
| 🏢 Scale-up | Jetson Orin (large buildings) |

---

## 📊 Realistic Accuracy

| Task | Accuracy | Note |
|------|----------|------|
| Face recognition | ~99%+ | Well-lit frontal faces; multi-frame voting |
| Person detection | 90–97% | YOLO11 + ByteTrack indoor scenes |
| Behavior proxies | 70–90% | Reported as **trends**, not verdicts |
| Safety detection | High recall | Human confirmation before action |

---

## 🔐 Privacy & Compliance First

> ⚠️ Ye system **biometric data** process karta hai. Deployment se pehle:

- ✅ Employee **consent & notice** mandatory
- ✅ Data **retention limits** + audit logging
- ✅ **DPIA** (GDPR/BIPA compliance)
- ✅ Aggregate analytics > individual scoring
- 📘 Full guide: [`blueprint-docs/05-security-and-compliance.md`](./blueprint-docs/05-security-and-compliance.md)

---

## 🗺️ Roadmap

- [x] Edge pipeline — detect → track → face → pose → rules
- [x] Evidence clip recording
- [x] FastAPI backend + event ingest
- [x] React dashboard + Grafana
- [ ] YOLO26 upgrade
- [ ] Custom behavior model fine-tuning
- [ ] Multi-site cloud sync
- [ ] Mobile app for alerts

---

<div align="center">

## 🤝 Connect

[![GitHub](https://img.shields.io/badge/GitHub-dikshantk809--create-181717?style=for-the-badge&logo=github)](https://github.com/dikshantk809-create)
[![Email](https://img.shields.io/badge/Email-dikshantk809%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:dikshantk809@gmail.com)

<br/>

### ⭐ Star the repo if this project impressed you!

*"Security that thinks, cameras that understand."*

**Built with ❤️ & 🧠 by Dikshant**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:FF4B2B,100:FF416C&height=110&section=footer" width="100%"/>

</div>
