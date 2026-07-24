# WorkLens AI — Resume Project Entry (copy-paste ready)

> Honest aur strong. Koi banaya hua (fake) number nahi — sab kuch jo tu interview me defend kar sake.

---

## ⭐ Recommended version (3–4 bullets)

**WorkLens AI — Smart Attendance & Productivity System**
*Python, OpenCV, PyTorch, YOLO11, InsightFace, Flask*

- Built an end-to-end computer-vision system that turns existing office/CCTV/webcam cameras into automatic, face-based attendance — with no extra hardware.
- Implemented real-time person & phone detection and tracking (YOLO11 + ByteTrack) and face recognition (InsightFace), running on a laptop GPU across multiple cameras at once.
- Developed a single-file Flask web dashboard with live multi-camera video, activity tracking (working / idle / walking / phone), unknown-person alerts, and multi-user login with roles.
- Generated automated Excel reports (per-person sheets + charts) and AI-written daily summaries; added phone/LAN access, remote access, and a central multi-office cloud dashboard.

**Tech:** Python, OpenCV, PyTorch (CUDA), YOLO11/Ultralytics, ByteTrack, InsightFace, Flask, pandas, openpyxl, SQLite.

---

## 📏 Compact version (2 lines — if space is tight)

**WorkLens AI — AI Attendance & Productivity from Cameras** | *Python, YOLO11, InsightFace, Flask*
Built a real-time computer-vision web app for automatic face-based attendance and productivity tracking from existing cameras — multi-camera GPU processing, live dashboard, alerts, and automated Excel + AI reports.

---

## 🔹 One-liner (for a "Projects" list)

**WorkLens AI** — Real-time office attendance & productivity system using YOLO11 detection + InsightFace face recognition, with a Flask live dashboard, multi-camera GPU processing, and automated Excel/AI reports. *(Python, OpenCV, PyTorch)*

---

## 🎤 Interview prep (read this — makes it 100% yours)

Be ready to explain the pipeline in one breath:
> "A camera frame goes to **YOLO11**, which detects people and phones. **ByteTrack** gives each person a stable ID across frames. **InsightFace** matches each face to an enrolled name for attendance. Simple logic labels the activity (working / idle / phone). **Flask** streams it all to a live web dashboard and logs events to CSV, which **pandas** turns into Excel reports."

Also know:
- **Why a GPU?** Real-time inference — running multiple AI models on live video needs GPU speed.
- **Privacy angle:** it only recognizes faces that were enrolled with consent; unknown faces stay "Unknown."
- **A hard problem you solved:** camera streams crashing the app, or all faces matching one name — pick one and explain how you fixed it. (Recruiters love a real debugging story.)

> Tip: AI tools se banana bilkul normal hai. Bas itna — system ko samajh le taaki confidently bata sake. Tab ye poori tarah tera project hai.

---

## ➕ Optional: real numbers you can add (after you test)
Measure these on your machine, then drop them in (only if true):
- "runs across __ cameras simultaneously in real time"
- "recognizes an enrolled person within ~__ seconds of appearing"
- "tested on a recorded video with __ people"
