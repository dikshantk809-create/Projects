# Raspberry Pi 4 pe REAL me chalana — Step by Step (Hinglish)

Yeh guide tumhare exact setup ke liye hai: **Raspberry Pi 4 + USB webcam + tumhara PC**.
Koi extra accelerator nahi. Simple steps follow karo.

---

## Pehle ek zaroori baat (padho)

Yeh project asal me **Raspberry Pi 5 + AI HAT+ (Hailo chip)** ke liye banaya gaya tha — woh
ek special AI accelerator hota hai jo fast detection karta hai.

- **Pi 4 me woh Hailo HAT nahi lagta** (Pi 4 me PCIe slot nahi hota).
- Pi 4 ka CPU thoda slow hai, toh hum **chhota model + kam FPS** chalayenge.
- Result: **1 camera ka chhota working demo** ho jayega. Pura office (multi-camera,
  fire/weapon detection) Pi 4 akela handle nahi karega — uske liye Pi 5 ya GPU PC chahiye.

**Best tareeka (recommended):** kaam do machine me baant do —

```
USB webcam  ──►  Raspberry Pi 4   (sirf AI detection chalata hai)
                      │   events WiFi se bhejta hai
                      ▼
                Tumhara PC   (Docker: backend + database + dashboard)
                      ▼
                Browser  ──►  dashboard pe LIVE data dikhta hai
```

PC bhaari kaam karega (jaise abhi karta hai), Pi 4 sirf camera + detection. 👍

---

## PHASE 0 — Pehle apne PC pe live chala ke dekho (10 min, Pi ki zaroorat nahi)

Yeh sabse important step hai. Pehle confirm karo ki camera → AI → dashboard ka pura
chakkar chal raha hai. Pi baad me.

**Step 1 — Backend chalu karo (jaise hamesha):**
`run.bat` double-click karo. Dashboard khulne tak wait karo: http://localhost:5174
(chaaho to `seed.bat` bhi chala lo demo charts ke liye).

**Step 2 — PC pe edge ke deps install karo** (Python 3.11+ hona chahiye). Ek terminal me:
```
python -m venv .venv
.venv\Scripts\activate
pip install -e "platform[detect]" httpx opencv-python
```

**Step 3 — `edge` folder me `.env` file banao** is content ke saath:
```
AICAM_SOURCE=0
AICAM_MODEL_PATH=yolo11n.pt
AICAM_DEVICE=cpu
AICAM_IMGSZ=480
AICAM_FPS_LIMIT=8
AICAM_FACE_ENABLED=false
AICAM_SHOW=true
AICAM_BACKEND_URL=http://localhost:8001
AICAM_INGEST_TOKEN=please-change-me-too
```

**Step 4 — Edge chalao:**
```
cd edge
python office_pipeline.py
```
Ek window khulega jisme logon par aur phone par **box** banenge. Aur dashboard ke
**"Live Detections & Alerts"** panel me real-time me events aate dikhenge.
✅ Yahi "sach me kaam kar raha hai" wala moment hai.

(Band karne ke liye window me **q** dabao ya terminal me Ctrl+C.)

---

## PHASE 1 — Ab detection Pi 4 pe le jao

### Step 1 — Pi 4 taiyaar karo
- **Raspberry Pi OS (64-bit, Bookworm)** SD card / SSD pe flash karo.
- SSH on karo, aur Pi ko **wahi WiFi/network** se jodo jis pe tumhara PC hai.
- USB webcam Pi ke **USB 3.0 (neela) port** me lagao.

### Step 2 — Project Pi pe le aao aur ek command chalao
Pi pe project clone/copy karo, fir repo folder me:
```
bash edge/setup_pi4.sh
```
Yeh sab kuch khud install karega: deps, ek **fast NCNN model** (Pi pe tez chalta hai),
`edge/.env` file, aur ek `office-edge.service`.
(Pehli baar 10–20 min lag sakte hain — patience. Agar Pi pe monitor laga hai aur live
window chahiye to `bash edge/setup_pi4.sh --gui` chalao.)

### Step 3 — Pi ko apne PC ka pata batao
PC ka IP nikaalo: PC pe `ipconfig` chalao → **IPv4 Address** (jaise `192.168.1.50`).
Phir Pi pe `edge/.env` edit karo:
```
nano edge/.env
```
Ye do line theek karo:
```
AICAM_BACKEND_URL=http://192.168.1.50:8001     # <- apne PC ka IP daalo
AICAM_INGEST_TOKEN=please-change-me-too        # <- server ke OFFICE_INGEST_TOKEN se bilkul same
```

**PC pe firewall me port 8001 kholo** (ek baar, PowerShell ko admin me chala ke):
```
New-NetFirewallRule -DisplayName "AI Office 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow
```
Pi se check karo ki PC milta hai: `curl http://192.168.1.50:8001/health`
→ `{"status":"ok",...}` aaye to perfect.

### Step 4 — Test karo, fir auto-start lagao
Pehle haath se chala ke dekho:
```
cd edge
../.venv/bin/python office_pipeline.py
```
Har 2 second me aisi line aani chahiye:
`running - 4.0 fps | persons=1 phones=0 | events_sent=37`
Aur PC ke dashboard pe live events. ✅

Phir boot pe auto-start ke liye:
```
sudo cp edge/office-edge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now office-edge.service
journalctl -u office-edge -f      # live logs dekhne ke liye
```

---

## Pi 4 ko fast/slow tune karna
- **Slow lag raha hai?** `.env` me `AICAM_IMGSZ` ghatao (320 → 256) aur `AICAM_FPS_LIMIT` (4 → 2).
- **Zyada accuracy chahiye (thoda slow)?** `AICAM_IMGSZ=416` ya `480`.
- Pi 4 garam ho ke slow ho jata hai → ek **cooling fan/heatsink** lagao.
- Thoda hardware boost chahiye? Pi 4 ke liye **Google Coral USB Accelerator** sahi option hai
  (Hailo AI HAT+ sirf Pi 5 me chalta hai).

## Naam-waali attendance (face recognition) baad me
Demo me face recognition **band** hai (Pi 4 ke liye bahut heavy). Baad me PC/Pi 5 pe
`pip install -e "platform[face]"`, fir `AICAM_FACE_ENABLED=true`, aur employees enroll
karke naam-wise attendance chalu kar sakte ho. Pehle
`blueprint-docs/05-security-and-compliance.md` padho — biometric data ke liye consent zaroori hai.

---

## Problem aaye to

| Problem | Solution |
|---|---|
| `cannot open source 0` | `.env` me `AICAM_SOURCE=1` try karo; `ls /dev/video*` se webcam check karo |
| `events_sent` 0 hi reh raha | `AICAM_BACKEND_URL` galat, ya firewall, ya token alag. `curl .../health` se test karo |
| Window error / Pi pe monitor nahi | `AICAM_SHOW=false` rakho — woh khud preview band karke chalta rahega |
| Bahut slow FPS | `AICAM_IMGSZ`/`AICAM_FPS_LIMIT` ghatao; NCNN model use karo (`.pt` nahi); fan lagao |
| Dashboard Live panel khaali | Edge events nahi bhej raha — heartbeat log aur backend URL check karo |
| Pi se PC ka IP ping nahi hota | Dono same WiFi pe hain? PC firewall me 8001 khula hai? |

---

### Chhota recap
1. Pehle **PC pe** Phase 0 chala ke confirm karo (sabse fast win).
2. Fir **Pi 4 pe** `setup_pi4.sh` → `.env` me PC ka IP + token → test → service.
3. Backend + dashboard hamesha **PC pe** Docker me chalega.
