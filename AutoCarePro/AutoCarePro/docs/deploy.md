# Sharing AutoCare Pro — one link, many devices

You want: **the app open on a phone, another laptop, a teacher's PC — all at the
same time — from one link.** There are three ways, and they suit different
moments. Read §0 first; it changes what "sharing" means for this app.

---

## 0. Read this first: what is shared and what is not

AutoCare Pro stores data in the **browser's `localStorage`**, on each visitor's
own device. So when you share a link:

- ✅ Everyone gets the **full working application** — every screen, every
  algorithm, every chart.
- ✅ Everyone gets their **own copy of the seeded demo data**, so nothing looks
  empty.
- ❌ Everyone does **not** see *your* vehicles. If you add a vehicle on your
  laptop, a visitor on their phone will not see it — they have their own
  database.

**This is a shared *app*, not a shared *database*.** For a demo, a viva or a
portfolio link that is exactly right: each viewer gets a clean, populated,
fully interactive copy that they cannot break for anyone else.

If you genuinely need one shared dataset across devices, that is the cloud-sync
item on the roadmap: implement `read()`/`write()` in `js/storage.js` against
Firebase or Supabase (see `docs/storage.md §6`). Nothing else in the code
changes.

**One thing you *can* share across devices today:** *Settings → Export JSON* on
one device, then *Import JSON* on another. Your exact data, moved by hand.

---

## 1. Same Wi-Fi — phone + laptop, 10 seconds, no internet

Best for: showing it to someone sitting next to you, or testing the responsive
layout on a real phone.

1. Double-click **`Run-AutoCare-Pro.bat`** (Windows) or run `./run.sh`, and
   press **`1`** (or just wait — it is the default).
2. The console prints two addresses:

```
   This computer   http://localhost:5500/index.html
   Same Wi-Fi      http://192.168.1.7:5500/index.html
                   ^ open this on your phone or another PC
```

3. Type the **Same Wi-Fi** address into your phone's browser. Both devices must
   be on the same network.

If the phone cannot reach it, Windows Firewall is blocking Node — the first time
you run it Windows shows a prompt; tick **Private networks** and allow it.
(Later: Windows Security → Firewall → Allow an app → find Node.js → tick Private.)

No internet needed at all. The link dies when you stop the server.

---

## 2. Public link from your laptop — Cloudflare quick tunnel

Best for: sending a link to someone who is *not* on your Wi-Fi, during a live
demo. The code keeps running on your laptop; the tunnel just forwards traffic.

1. Double-click **`Run-AutoCare-Pro.bat`** and press **`2`**.
2. First run downloads `cloudflared` (~40 MB, once, no account, no signup).
   It is saved next to the launcher, so later runs start immediately.
3. It starts the server, opens a tunnel and prints a link like:

```
https://mixed-pretty-annual-rider.trycloudflare.com
```

4. Share that link. It works on any phone or PC, anywhere, simultaneously.

Manual equivalent if you prefer typing:

```bat
node share.js          :: server + tunnel in one window
```

**Honest limits:**

- The link lives **only while that window is open**. Close it, or shut the
  laptop, and it is dead.
- A quick tunnel gets a **new random URL every time** you start it. Don't print
  it on a report cover.
- Everything goes through your laptop's upload speed.
- Cloudflare shows a one-time interstitial page to first-time visitors.

For anything you want to hand in or put on a CV, use §3 instead.

---

## 3. Permanent free hosting — the right answer for a project link

AutoCare Pro is 100% static files: no backend, no database, no build step. That
means any free static host will run it, **and it stays online when your laptop
is off.**

### 3a. Netlify Drop — fastest, ~60 seconds, no account needed to start

1. Go to **<https://app.netlify.com/drop>**
2. **Drag the extracted `AutoCarePro` folder** onto the page.
3. You get a live URL immediately, e.g. `https://autocare-pro-svms.netlify.app`.
4. Sign in (free) to keep it permanently and to rename it to something tidy.

Full PWA works here — HTTPS means the service worker registers and the install
prompt appears.

### 3b. GitHub Pages — best if the project is already on GitHub

```bash
cd AutoCarePro
git init
git add .
git commit -m "AutoCare Pro — Smart Vehicle Maintenance System"
git branch -M main
git remote add origin https://github.com/<your-username>/autocare-pro.git
git push -u origin main
```

Then on GitHub: **Settings → Pages → Source: `main` / root → Save.**
Your link: `https://<your-username>.github.io/autocare-pro/`

Two things to know:

- The site lives in a **subfolder**, so every path must be relative. It already
  is — `index.html`, `manifest.json` and `service-worker.js` all use `./` and
  relative paths, so nothing needs changing.
- The first deploy takes a minute or two.

### 3c. Vercel — one command

```bash
npm i -g vercel
cd AutoCarePro
vercel        # accept the defaults; it detects a static site
```

### 3d. Cloudflare Pages

Dashboard → Workers & Pages → Create → Pages → **Upload assets** → drag the
folder. Or connect the GitHub repo for automatic redeploys on every push.

---

## 4. Which one should you use?

| Situation | Use |
|---|---|
| Showing a friend sitting next to you | Launcher option **1** (§1) |
| Live demo to someone remote, right now | Launcher option **2** (§2) |
| Link on a report / CV / LinkedIn / submission | §3a Netlify Drop or §3b GitHub Pages |
| Someone who just wants to click one file | Send `AutoCare-Pro.html` — it needs nothing |
| No internet anywhere | `AutoCare-Pro.html`, or §1 on a hotspot |

**My recommendation for a college project:** push it to GitHub and turn on
Pages (§3b). You get a permanent link *and* the repository — and for a CSE minor
project, the examiner being able to read the source is worth as much as the live
demo.

---

## 5. Checklist before you share a link

- [ ] Open the link yourself on a phone **and** a laptop before sending it.
- [ ] Confirm the dashboard shows the two demo vehicles (fresh visitors get the
      seeded data automatically).
- [ ] On HTTPS hosting, check DevTools → Application → Service Workers shows
      *activated*, and that the install icon appears in the address bar.
- [ ] Tell your audience the data is per-device — see §0 — so nobody thinks the
      app is broken when their changes don't appear on your screen.
- [ ] If you are tunnelling (§2), keep the laptop awake: Settings → Power →
      Screen and sleep → *Never* while you are demoing.
