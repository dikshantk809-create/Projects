# Laptop KISI BHI WiFi par + ghar ka CCTV connect — Setup Guide

**Aapka scenario:** Project laptop par chalta hai. Aap laptop lekar kahin bhi jao
(dost ka ghar, client ka office, koi bhi WiFi/hotspot) — ghar ka DVR/CCTV
laptop se apne aap connect ho jaye, bilkul waise hi jaise ghar ke WiFi par hota hai.

**Ek zaroori shart:** Ghar par ek PC/computer ON rehna chahiye jisme sirf
Tailscale chalta ho (project NAHI - bas ye chhota app). Wahi ghar ke network
ka darwaza banta hai. (Chahe to baad me ₹5,000 ka Raspberry Pi laga do —
24x7 chalta hai, bijli na ke barabar khata hai.)

---

## EK BAAR ka setup (~15 minute)

### A) Ghar ke PC par (jo ON rahega)
1. https://tailscale.com/download → install → Google account se sign in
2. Ab **subnet router** on karo — taaki ye PC poore ghar ke network (DVR samet)
   ka raasta de. PowerShell ADMIN me chala kar:
   ```
   tailscale set --advertise-routes=192.168.0.0/24
   ```
3. Browser me https://login.tailscale.com/admin/machines kholo →
   ghar wale PC ke aage `...` → **Edit route settings** → `192.168.0.0/24`
   ko **Approve** kar do.
4. PC ki Settings → Power → **Sleep: Never** (warna PC so jayega).

### B) Apne laptop par
1. Wahi Tailscale install karo, **USI account** se sign in
2. System tray me Tailscale icon → right-click → **Preferences** →
   **"Use subnet routes"** ✓ (agar dikhe; Windows par aksar default ON hota hai)

---

## Bas — ab use karna
- Laptop kisi bhi WiFi/hotspot se connect karo
- Tailscale ON ho (tray icon dikhna chahiye)
- `START-WORKLENS.bat` chalao — **kuch bhi change kiye bina** ghar ke saare
  8 camera connect ho jayenge, kyunki `192.168.0.105` ab Tailscale ke
  through ghar tak pahunchta hai. Encrypted, secure.

## Speed ke liye (important)
- Video ghar ke internet ke UPLOAD se aata hai. Humne DVR ka **sub-stream**
  (subtype=1) already set kar rakha hai — 8 camera ~2-4 Mbps me chal jate hain.
  Ghar ka upload 5 Mbps+ ho to smooth chalega.
- Agar bahar se chalate waqt video atke: START-WORKLENS.bat me
  `AICAM_CAM_COUNT=8` ko kam karke `4` kar do, ya dashboard me sirf
  zaroori camera ON rakho.

## Demo dene ka aur bhi aasan tarika
Kisi ko sirf DIKHANA hai (unke ghar ka CCTV nahi jodna):
- Laptop ka **webcam** har jagah bina kisi setup ke chalta hai
- **Drop recorded footage** (ANALYSE VIDEO card) me ghar ki recording daal kar
  live jaisa demo ho jata hai — internet ki zaroorat hi nahi

## Kya NAHI karna
Router me DVR ka port internet par kholna (port forwarding) — insecure hai,
hacker bots dhoondhte rehte hain, aur aajkal ISP public IP dete bhi nahi.
Tailscale hi sahi raasta hai.
