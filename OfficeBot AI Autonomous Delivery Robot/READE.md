<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rounded&color=0:22314E,50:1f6feb,100:22c55e&height=220&section=header&text=🤖%20OfficeBot&fontSize=64&fontColor=ffffff&animation=fadeIn&desc=Autonomous%20Food%20Delivery%20Robot%20—%20ROS%202%20+%20Nav2&descSize=18&descAlignY=75" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=700&color=1F6FEB&center=true&vCenter=true&width=720&lines=Order+from+QR+%E2%86%92+Robot+Delivers+to+Desk+%F0%9F%9A%9A;SLAM+Mapping+%2B+Nav2+Navigation+%F0%9F%97%BA%EF%B8%8F;OTP-Secured+Handover+%F0%9F%94%90;Robot+Fleet+with+Auto-Charging+%F0%9F%94%8B;Zero-Install+Web+Platform+%E2%9A%A1" alt="Typing SVG" />

<br/><br/>

![ROS 2](https://img.shields.io/badge/ROS_2-22314E?style=for-the-badge&logo=ros&logoColor=white)
![Nav2](https://img.shields.io/badge/Nav2-1f6feb?style=for-the-badge&logo=ros&logoColor=white)
![Gazebo](https://img.shields.io/badge/Gazebo-f59e0b?style=for-the-badge&logo=gazebo&logoColor=black)
![Python](https://img.shields.io/badge/Python_3-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

<img src="https://img.shields.io/badge/SLAM-slam__toolbox-blueviolet?style=flat-square"/>
<img src="https://img.shields.io/badge/Localization-AMCL-blue?style=flat-square"/>
<img src="https://img.shields.io/badge/Web_App-Zero_Dependencies-22c55e?style=flat-square"/>
<img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square"/>
<img src="https://img.shields.io/badge/Status-Active-success?style=flat-square"/>

</div>

---

## 🎯 What Is This?

> **Web app ya table QR se order karo → ROS 2 + Nav2 robot aapki desk tak khaana pahunchata hai → wapas kitchen chala jaata hai.**

Ek complete **robotics + full-stack** project: real SLAM map par autonomous indoor navigation, poora ordering & kitchen-management platform, OTP-secured delivery, robot fleet, aur live analytics. Aur mazedaar baat — web platform **pure Python standard library** par chalta hai. **Zero installs.** ⚡

---

## 🧩 Architecture

```mermaid
flowchart LR
    A["📱 Customer<br/>Phone / Laptop / QR"] -- "HTTP" --> B["🖥️ OfficeBot PRO<br/>Web Platform<br/>Python + SQLite"]
    B -- "status + live map" --> A
    B -- "dispatch desk" --> C["🔌 ROS 2 Bridge<br/>nav goals"]
    C -- "live pose" --> B
    C -- "navigate_to_pose" --> D["🤖 Gazebo + Nav2<br/>Robot + SLAM Map"]
    D -- "AMCL pose" --> C

    style A fill:#22c55e,color:#000,stroke:#16a34a,stroke-width:2px
    style B fill:#1f6feb,color:#fff,stroke:#22314E,stroke-width:3px
    style C fill:#7F5AF0,color:#fff,stroke:#B721FF,stroke-width:2px
    style D fill:#22314E,color:#fff,stroke:#f59e0b,stroke-width:3px
```

**2 Modes:**

- 🎮 **Simulation (default)** — web app robot fleet internally animate karta hai. No ROS needed, kahin bhi chalega.
- 🤖 **Real mode** — ROS 2 bridge live pose stream karta hai aur web dispatches ko **real Nav2 goals** mein convert karta hai.

---

## ✨ Features

<table>
<tr>
<td width="33%" valign="top" align="center">

### 🍽️ Web + QR Ordering
Laptop se order karo ya table ka **QR scan** karke phone se — order page us desk par pre-set khulta hai.

</td>
<td width="33%" valign="top" align="center">

### 👨‍🍳 Kitchen Dashboard
Real workflow — **Prepare → Ready → Dispatch robot**. Ek click aur robot nikal padta hai.

</td>
<td width="33%" valign="top" align="center">

### 🗺️ Live SLAM Map
Robot **actual SLAM occupancy map** par live render hota hai — customer real-time tracking dekhta hai.

</td>
</tr>
<tr>
<td width="33%" valign="top" align="center">

### 🔐 OTP Delivery
Khaana sirf sahi **4-digit code** dalne par release hota hai. No mix-ups.

</td>
<td width="33%" valign="top" align="center">

### 🤖 Smart Fleet
2 robots — **nearest free robot** auto-assign hota hai. Battery low? Auto charge-dock return. 🔋

</td>
<td width="33%" valign="top" align="center">

### 📊 Analytics + AI
Revenue, busiest desk, avg delivery time & **demand prediction** — sab live charts mein.

</td>
</tr>
</table>

**Aur bhi:** 🧭 obstacle avoidance (pause/re-route) · 🗄️ SQLite persistence (restarts survive) · 🔊 voice alerts · 📄 printable QR sheet

---

## 🚀 Quick Start

### 🖥️ Web Platform (sirf Python 3 chahiye!)

```bash
python3 officebot_pro.py
```

| Page | URL |
|------|-----|
| 🍽️ Customer ordering | `http://localhost:5000/` |
| 👨‍🍳 Kitchen dashboard | `http://localhost:5000/admin` |
| 📊 Analytics + AI | `http://localhost:5000/stats` |

> 💡 **Windows one-click:** `Start_OfficeBot.bat` double-click karo — port kholta hai, server start karta hai, browser launch karta hai.

### 🤖 Robot Simulation (ROS 2)

```bash
# 1️⃣ Gazebo world + robot
ros2 launch <your_pkg> office_world.launch.py

# 2️⃣ Nav2 + saved SLAM map
ros2 launch nav2_bringup bringup_launch.py \
  map:=officebot_maps/office_15desk_map.yaml use_sim_time:=true
```

---

## 🔄 Order-to-Delivery Flow

```mermaid
flowchart LR
    A["🍽️ Order + Desk<br/>→ OTP milta hai"] --> B["👨‍🍳 Kitchen<br/>Prepare → Ready"]
    B --> C["🚚 Dispatch<br/>nearest robot"]
    C --> D["🗺️ Robot drives<br/>(live map)"]
    D --> E["🔐 OTP Enter<br/>→ Delivered ✅"]
    E --> F["🔙 Robot returns<br/>to kitchen"]

    style A fill:#22c55e,color:#000
    style B fill:#f59e0b,color:#000
    style C fill:#1f6feb,color:#fff
    style D fill:#7F5AF0,color:#fff
    style E fill:#FF416C,color:#fff
    style F fill:#22314E,color:#fff
```

---

## 📂 Project Structure

```
🤖 OfficeBot/
│
├── 🖥️ officebot_pro.py         → Main web platform (ordering, kitchen,
│                                  analytics, OTP, fleet, live map)
├── 🔌 officebot_nav_bridge.py  → ROS 2 bridge: web orders → Nav2 goals
├── ⚡ Start_OfficeBot.bat      → One-click launcher
├── 🌐 officebot_web/           → ROS-side order server + goal sender
├── 🏢 officebot_sim/ + _world/ → Gazebo worlds
├── 🗺️ officebot_maps/          → SLAM maps (.pgm + .yaml)
├── 📦 ros2_ws/                 → ROS 2 workspace (packages, launch files)
├── 📘 MAP_FIX_GUIDE.md         → Make all 15 desks reachable
└── 📚 docs/
```

---

## 📱 Phone / QR Access

Site `0.0.0.0:5000` par listen karti hai. `Start_OfficeBot.bat` port forward + firewall open karta hai — **same WiFi** ke phones access kar sakte hain. QR codes automatically aapke PC ke LAN IP par point karte hain (e.g. `http://192.168.0.103:5000`). 📲

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Tech |
|-------|------|
| 🤖 Robotics | ROS 2, Nav2, Gazebo, slam_toolbox, AMCL |
| 🖥️ Backend | Python 3 stdlib (`http.server`, `sqlite3`, `threading`) |
| 🗄️ Database | SQLite |
| 🌐 Frontend | HTML/CSS/JS, Chart.js, qrcode.js |

</div>

---

## 🗺️ Roadmap

- [x] Full web ordering + kitchen platform
- [x] SLAM map + Nav2 simulation
- [x] OTP delivery + robot fleet + auto-charging
- [ ] 🤖 Drive a physical robot from web dispatches
- [ ] 🗺️ Full 15-desk reachable map (extended SLAM)
- [ ] 📷 On-robot camera + face/QR confirmation at handover
- [ ] 💳 Real payments (UPI) + WhatsApp/SMS notifications
- [ ] 🛗 Multi-floor (elevator) navigation
- [ ] 📈 Demand-based fleet pre-positioning

---

<div align="center">

## 🤝 Connect

[![GitHub](https://img.shields.io/badge/GitHub-dikshantk809--create-181717?style=for-the-badge&logo=github)](https://github.com/dikshantk809-create)
[![Email](https://img.shields.io/badge/Email-dikshantk809%40gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:dikshantk809@gmail.com)

<br/>

### ⭐ Robot ne impress kiya? Star de do!

*"From QR scan to desk delivery — fully autonomous."*

**Built with ❤️ & 🤖 by Dikshant** · MIT License

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:22c55e,50:1f6feb,100:22314E&height=110&section=footer" width="100%"/>

</div>
