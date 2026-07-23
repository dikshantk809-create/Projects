# WorkLens AI — Central Cloud (HQ) setup (Hinglish)

## Ye kya hai
Ab tak har office apne PC par alag chalta tha. **HQ** ek central dashboard hai jahan
**saare offices ek hi screen par** dikhte hain — kaun online hai, abhi kitne log,
phone use, aur aaj kaun sabse productive.

Kaam kaise karta hai (simple):
- Har office apne PC par `edge\run_app.bat` chalata hai → **AI wahin** chalti hai (camera, face, sab).
- Har office apna chhota sa data (kitne log, productivity) **HQ ko bhejta hai** — har 30 second me.
- HQ sirf dikhata hai. Koi video HQ par nahi jaati (sirf numbers) — isliye halka aur sasta.

---

## Part 1 — Pehle apne LAPTOP par test karo (free, abhi)

Isse pure system ko bina kuch kharch kiye chala ke dekh sakte ho.

1. `cloud\run_cloud.bat` chalao.
   - HQ khulega: **http://localhost:8080**
   - Login: username **`admin`**, password = `run_cloud.bat` me jo `WL_ADMIN_PASSWORD` hai (`admin123`).
2. HQ me **"Naya office add karo"** → naam daalo (jaise *Main Office*) → **token** milega. Copy karo.
3. `edge\run_app.bat` ko Notepad me kholo. Inn 2 lines se `REM ` hata do aur token paste karo:
   ```
   set AICAM_CLOUD_URL=http://localhost:8080
   set AICAM_CLOUD_TOKEN=yahan-wo-token-paste-karo
   ```
4. `edge\run_app.bat` chalao (normal jaise). 30 second me HQ me wo office **online (hara dot)** ho jayega, live numbers ke saath.

> Local test me HQ aur office dono ek hi laptop par chal rahe hain — sirf dikhane ke liye. Asli use me HQ ek alag always-on server par hoga.

---

## Part 2 — PERMANENT URL ke liye deploy (jab ready ho)

Local test me URL `localhost` hai — sirf usi PC par. Permanent, kahin-se-bhi-khulne wala
URL chahiye to HQ ko ek **hamesha-on server** par daalna padega. (Ye wo step hai jisme
thoda kharcha + ek account lagta hai — wo tumhe khud karna hoga, main pay/signup nahi kar sakta.)

**Do aasaan raaste:**

**A) Sasta cloud server (recommended, ~₹400–800/mo)**
1. Kisi cloud provider se ek chhota Linux server (VPS) lo (1GB RAM kaafi — koi GPU nahi chahiye, HQ halka hai).
2. Us par Python install karke `cloud\` folder copy karo.
3. Chala do:
   ```
   pip install flask
   set WL_ADMIN_PASSWORD=apna-strong-password
   python server.py
   ```
4. Server ka public IP/domain hi tumhara permanent HQ URL ban jayega (port 8080).
5. Har office ke `run_app.bat` me `AICAM_CLOUD_URL` me **localhost ki jagah wo public URL** daalo.

**B) Apna ek always-on PC + permanent tunnel (kam kharch)**
1. Ek PC jo hamesha on rahe, us par `run_cloud.bat` chalao.
2. Permanent URL ke liye **named Cloudflare Tunnel** lagao (free, par ek Cloudflare account + ek domain chahiye).
   - Ye `remote_access.bat` wale quick tunnel se alag hai — quick tunnel ka link har baar badalta hai;
     named tunnel ka URL **fix** rehta hai.

---

## Security (zaroori)
- HQ deploy karne se pehle **`WL_ADMIN_PASSWORD` zaroor badlo** (`admin123` mat rehne do).
- Public server par **https** use karo (provider ka SSL ya Cloudflare ke through).
- Office tokens secret hain — kisi ke saath share mat karo; leak ho to HQ me office delete karke naya add kar lena (naya token).

---

## Aksar poochhe jaane wale
- **Video bhi HQ jaati hai?** Nahi. Sdirectly camera/AI office ke PC par. HQ ko sirf numbers (count + productivity) jaate hain.
- **Internet gaya to?** Office ka apna dashboard (localhost:8000) tab bhi chalta rahega; net wapas aate hi HQ phir update ho jayega.
- **Ek office, ek token.** Naya office = HQ me naya add = naya token.

Kahin atak jao to bata dena — saath me kar lenge.
