<div align="center">

<img src="https://capsule-render.vercel.app/api?type=speech&color=0:CCFF00,100:00B140&height=230&section=header&text=AI%20Tennis%20Analysis&fontSize=55&fontColor=1a1a2e&animation=fadeIn&desc=AI%20Referee%20+%20Match%20Analytics%20for%20Tennis&descSize=18&descAlignY=72" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=700&color=00B140&center=true&vCenter=true&width=720&lines=Ball+Tracking+with+TrackNetV4+%F0%9F%8E%BE;Automated+IN%2FOUT+Line+Calling+%F0%9F%93%8F;Live+Scoring+%2B+Rally+Stats+%F0%9F%8F%86;Player+Movement+Heatmaps+%F0%9F%94%A5;Coach+%2B+Spectator+Dashboards+%F0%9F%93%8A" alt="Typing SVG" />

<br/><br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![YOLO11](https://img.shields.io/badge/YOLO11-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

<img src="https://img.shields.io/badge/Ball_Tracking-TrackNetV4-brightgreen?style=flat-square"/>
<img src="https://img.shields.io/badge/Players-YOLO11_+_ByteTrack-blue?style=flat-square"/>
<img src="https://img.shields.io/badge/Line_Calls-85--95%25_Agreement-yellow?style=flat-square"/>
<img src="https://img.shields.io/badge/Grade-Club_%2F_Academy-orange?style=flat-square"/>

</div>

---

## 🎾 What Is This?

> **Hawk-Eye ki premium accuracy, club-friendly budget mein.**
> Ball/player/court tracking, automated IN/OUT calls, live scoring, rally & serve stats — sab ek high-FPS camera aur AI se.

Ye system **club/academy grade** analytics target karta hai: 1 achhe camera se ~**85–92%** line-call agreement, aur 2+ synchronized ≥120fps cameras + calibration ke saath **95%+** tak. (Broadcast Hawk-Eye 10+ cameras use karta hai — hum realistic rahte hain. 📏)

---

## 🏗️ System Architecture

```mermaid
flowchart LR
    A["📹 High-FPS<br/>Camera"] --> B["🎾 Ball Tracker<br/>TrackNetV4 Heatmap"]
    A --> C["🏃 Player Tracker<br/>YOLO11 + ByteTrack"]
    A --> D["📐 Court Detector<br/>Lines → Homography"]
    B --> E["⬇️ Bounce<br/>Detection"]
    D --> E
    E --> F{"📏 IN / OUT<br/>Call"}
    F --> G["🏆 Scoring FSM"]
    C --> G
    G -->|"📨 Events"| H["🚀 FastAPI<br/>Backend"]
    H --> I[("🐘 PostgreSQL<br/>TimescaleDB")]
    H --> J["📊 Dashboards<br/>Spectator + Coach"]

    style A fill:#1a1a2e,color:#fff,stroke:#CCFF00
    style B fill:#00B140,color:#fff,stroke:#CCFF00,stroke-width:3px
    style C fill:#0066CC,color:#fff,stroke:#61DAFB
    style D fill:#7B2FBE,color:#fff,stroke:#B721FF
    style E fill:#FF9800,color:#000,stroke:#F57C00
    style F fill:#FF416C,color:#fff,stroke:#FF4B2B,stroke-width:3px
    style G fill:#FFD700,color:#000,stroke:#FFA000
    style H fill:#009688,color:#fff,stroke:#00695C
    style I fill:#4169E1,color:#fff,stroke:#1E3A8A
    style J fill:#61DAFB,color:#000,stroke:#0288D1
```

**Pipeline:** `Capture → Ball + Player + Court AI → Bounce → IN/OUT → Scoring → Events → Backend → Dashboards`

---

## ✨ Features

<table>
<tr>
<td width="33%" valign="top" align="center">

### 🎾 Ball Tracking
**TrackNetV4** heatmap-based tracking — chhoti, fast-moving ball ko bhi frame-by-frame follow karta hai.

</td>
<td width="33%" valign="top" align="center">

### 📏 Auto Line Calling
Bounce detection + court homography = automated **IN/OUT calls** with confidence scores.

</td>
<td width="33%" valign="top" align="center">

### 🏆 Live Scoring
Scoring FSM — points, games, sets automatically track hote hain. WebSocket se **live score** stream.

</td>
</tr>
<tr>
<td width="33%" valign="top" align="center">

### 🏃 Player Analytics
YOLO11 + ByteTrack se movement tracking — court coverage, speed, **position heatmaps**.

</td>
<td width="33%" valign="top" align="center">

### 📊 Coach Dashboard
Strengths/weaknesses, shot distribution, court heatmaps & **tactical suggestions**.

</td>
<td width="33%" valign="top" align="center">

### 🎬 Instant Replay
Line calls ke replays, serve-speed estimation & auto **highlights** — spectator view mein.

</td>
</tr>
</table>

---

## 🧠 AI Stack

| Layer | Technology | Job |
|-------|-----------|-----|
| 🎾 Ball | **TrackNetV4** (PyTorch) | Heatmap-based ball tracking |
| 🏃 Players | **YOLO11 + ByteTrack** | Detection & multi-frame tracking |
| 📐 Court | OpenCV lines + learned keypoints | Court detection → homography |
| ⬇️ Bounce | Trajectory inflection detector | Bounce localization on court plane |
| 🚀 Serve Speed | Ball displacement + calibration | Speed estimation |
| 🏆 Scoring | Finite State Machine | Point/game/set logic |

---

## 📂 Project Structure

```
AI-Tennis-Analysis-System/
│
├── ⚡ edge/             → tennis_pipeline.py (main inference loop)
├── 🚀 backend/          → FastAPI: scoring.py, court.py, services & routes
├── 📊 dashboard/        → React + Tailwind + Recharts (Spectator | Coach)
├── 🧠 ml/               → TrackNet training, YOLO fine-tuning, evaluation
├── 🐘 db/               → schema.sql — matches, rallies, shots, line_calls
├── 🐳 deploy/           → docker-compose, Dockerfiles, Grafana
├── 📘 blueprint-docs/   → Architecture, hardware, cost, tech stack
├── 📚 docs/             → API design, training, deployment, accuracy roadmap
└── 🧪 tests/
```

---

## ⚙️ Quick Start

```bash
# Clone & enter
git clone https://github.com/dikshantk809-create/Projects.git
cd Projects/AI-Tennis-Analysis-System

# Configure & launch
cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build

# 🚀 API      → http://localhost:8003/docs
# 📊 Dashboard → http://localhost:5176
```

> 📌 **Note:** Pehli match se pehle camera calibration zaroori hai — dekho [`docs/10-deployment.md`](./docs/10-deployment.md)

---

## 🎛️ Hardware Tiers

| Tier | Setup | Line-Call Accuracy | Cost |
|------|-------|-------------------|------|
| 🟢 **A** — Pi 5 + Hailo | Player/court analytics only | Ball calls ❌ | Budget |
| 🟡 **B** — Jetson Orin / RTX | 1× ≥120fps global-shutter cam | ~85–92% | $1.5k–3k |
| 🔴 **C** — Multi-cam Pro | 2+ synced ≥120fps + calibration | 95%+ | $10k–30k |

---

## 📊 Accuracy Reality Check

> 🎯 Hum **honest numbers** report karte hain:

- 📺 Broadcast Hawk-Eye: 10+ calibrated cams @ ≥120fps → few-mm accuracy
- 📷 Single 30–50fps camera → **indicative calls only**
- 🎾 Ye system: club-grade **85–92%** (1 cam) → **95%+** (multi-cam + calibration)
- 📘 Full analysis: [`docs/16-accuracy-and-roadmap.md`](./docs/16-accuracy-and-roadmap.md)

---

## 🔌 API Highlights

```http
POST  /matches                      → create match
POST  /ingest/events                → edge → backend events
GET   /matches/{id}/score           → live score
GET   /matches/{id}/stats           → rally/serve/shot stats
GET   /players/{id}/analytics       → player analytics
GET   /matches/{id}/highlights      → auto highlights
WS    /ws/match/{id}                → live score + ball stream
```

---

## 🗺️ Roadmap

- [x] **MVP** — player tracking + manual-assisted scoring
- [x] **Beta** — ball tracking + auto IN/OUT + live score
- [ ] **Production** — multi-cam calibration + accuracy validation
- [ ] 🎥 Multi-camera triangulation → 3D ball, 95%+ calls
- [ ] 🤸 Serve/stroke biomechanics analysis
- [ ] 🎬 Auto highlight reels with commentary
- [ ] 📺 Broadcast overlay graphics
- [ ] 👥 Doubles support + opponent scouting reports

---

<div align="center">

## 🤝 Connect

[![GitHub](https://img.shields.io/badge/GitHub-dikshantk809--create-181717?style=for-the-badge&logo=github)](https://github.com/dikshantk809-create)
[![Email](https://img.shields.io/badge/Email-dikshantk809%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:dikshantk809@gmail.com)

<br/>

### ⭐ Ace this repo with a star!

*"Every point tracked. Every call fair. Every match smarter."*

**Built with ❤️ & 🎾 by Dikshant**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00B140,100:CCFF00&height=110&section=footer" width="100%"/>

</div>
