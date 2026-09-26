# The AR-750, as it actually stands

Written 22 September 2026, after reading every module and running the console
against the real server. This is the honest inventory: what is built, what is
wired to nothing yet, and what is worth doing next and in what order.

If you only read one thing, read **What is not fitted** and then **Do these
five first**.

---

## 1. What this machine is

A four-wheel-drive, car-steered garden rover, about 120 kg, that drives down a
row of vegetables, stops at each plant, photographs it, decides whether it has
a problem, and sprays a measured band of the right chemical over it if it does.
It carries a 700 mm spray boom with five nozzles in three sections, a soil
probe on a lead screw, one forward camera, and a Raspberry Pi running the whole
thing.

It steers like a car. It cannot turn on the spot, and full lock still needs a
4.9 m circle. More of the software is shaped by that one fact than by anything
else — `hw/ackermann.py` exists entirely because of it.

Two computers are involved:

| | runs on | what for |
|---|---|---|
| **Simulator** | your laptop | the whole program with the hardware replaced by fakes. Every page and every button is real; the numbers are invented. |
| **Rover** | Raspberry Pi | the same folder, copied across, with the hardware present. |

They are not two codebases. `rover_software/` is what goes on the Pi.

---

## 2. Every part, and what it does

### The website — `ar750/web/`

Served by the Pi on port 8080, behind a sign-in. Eight pages:

| Page | What it is for |
|---|---|
| **Live** | battery / tank / soil / job gauges, the camera, mode, the spray boom, a drive pad, steering, the soil probe, the message log, and the table of everything checked since power-on |
| **Field map** | every plant it has ever seen, positioned, click one for its whole history |
| **Plants** | the same set as a searchable, filterable list |
| **Charts** | battery, soil and tank over time; plants checked vs problems found per day; a tally of what it keeps finding |
| **Runs & photos** | every outing with its numbers, the photo gallery, the timelapse recordings |
| **Alerts** | everything it has flagged, kept in the database so it survives a power cut |
| **Timetable** | patrols — a named job at a time on chosen days, with or without permission to spray |
| **Settings** | 35 settings in seven groups, what hardware is actually fitted, and the sign-in details |

Behind them, the API (`web/server.py`):

```
GET  /                    the console          GET  /login          sign in
POST /api/login           sign in              POST /api/logout
GET  /api/me              who am I             POST /api/account    change login
GET  /api/state           one snapshot         WS   /ws             live, 5/second
GET  /cam/front           the camera           GET  /photos/<n>     one plant photo
GET  /video/<name>        one recording        POST /api/command    everything it does
GET  /api/field           every plant          GET  /api/plant/<p>  its history
GET  /api/history         per-day counts       GET  /api/samples    chart lines
GET  /api/missions        every outing         GET  /api/recordings
GET  /api/alerts          the alert log        GET  /api/photos     the gallery
GET  /api/report.csv      the whole log        GET  /api/photoset.zip  training set
GET  /api/settings        what you can change  POST /api/settings
GET  /api/patrols         the timetable        POST /api/patrols
POST /api/notify/test     a test message       GET  /api/health     is it alive
```

`POST /api/command` is the one that does things. It takes:
`estop`, `clear_estop`, `mode`, `drive`, `speed_limit`, `probe`, `steer_centre`,
`spray_arm`, `auto_spray`, `spray_now`, `spray_stop`, `lamps`, `probe_soil`,
`mission_start`, `mission_stop`, `answer`, `clear_alerts`, `mark_home`,
`go_home`, `stop_home`, `record`.

Everything except `/login`, `/api/login` and `/api/health` needs a session.
Six wrong passwords from one address and that address waits two minutes. The
password is stored as a PBKDF2-SHA256 hash with a random salt, never in
readable form.

### The brain — `ar750/ai/`

**`mission.py`** is a state machine, ticked 50 times a second:

```
FIND_ROW -> FOLLOW -> AT_PLANT -> DECIDE -> ACT -> MOVE_ON
               ^                                      |
               +--------------------------------------+
```

It finds the row, follows it, stops when a plant is in front, looks at it for a
configured number of seconds, decides, acts, and moves on by the configured
plant spacing. At the end of a row it turns into the next one. It can wait for
you: if the model is not confident enough, it stops and asks, and the console
puts the question and the photo in front of you with a Yes and a No.

**`vision.py`** does two separate jobs:

- *Row following* is plain colour work — a green mask and where its centre of
  mass sits. No model needed, runs at full frame rate on a Pi 4.
- *Plant judging* is a small int8 TFLite classifier at 224x224. **There is no
  model file yet**, so `Classifier.ready` is False and every plant is logged as
  `not_checked`. It will not guess a disease it has not been taught, which is
  the right behaviour and also means the machine currently photographs and
  files rather than diagnoses.

**`treatment.py`** is a lookup table, not a brain: 19 entries covering healthy,
tomato early blight, late blight, leaf mould, septoria, bacterial spot, mosaic
virus, leaf curl virus, spider mite, aphid, whitefly, powdery mildew, downy
mildew, cabbage leaf miner, nitrogen deficiency, water stress, weed, unknown
and not-checked. Each says what to use, at what rate, and what you should do by
hand.

### The hardware layer — `ar750/hw/`

Every one of these degrades to simulation if the board is not there, which is
why the laptop and the Pi behave identically.

| File | What it drives | Without it |
|---|---|---|
| `ackermann.py` | the steering geometry, turn radius, Ackermann split | — (pure maths, always available) |
| `drive.py` | two motors via BTS7960 or ESC, plus the steering servo | it cannot move |
| `boom.py` | five nozzles, three sections, PWM valves at ~10 Hz | nothing can be sprayed |
| `probe.py` | the lead-screw soil probe and its limit switches | no soil reading at all |
| `camera.py` | the front camera, or a generated crop row | the camera pane is a test pattern |
| `encoders.py` | wheel encoders, real distance, slip detection | distance is estimated and drifts |
| `imu.py` | MPU-6050, real tilt and heading | the lean cut-out can never fire |
| `rangefinder.py` | HC-SR04 in front | **nothing stops it driving into something** |
| `rc.py` | your 6-channel remote, over SBUS / PPM / PWM | no manual override |
| `io.py` | GPIO outputs, the pump, the lamps, the ADC | — |

### The record — `ar750/core/db.py`

One SQLite file at `data/ar750.db`. No server, no setup, copy it to a USB stick
and open it anywhere. Five tables: `missions`, `plants`, `samples`, `alerts`,
`recordings`, `patrols`. Every plant it looks at becomes a row with its plot
number (`r2p07` = row 2, plant 7), what it was called, how sure, how bad, what
was done, how much was sprayed, the soil reading and the photo filename.

### Everything else

- `core/settings.py` — the 35 things you can change while standing in the
  garden, saved to `data/settings.json`, validated against hard limits that
  the website cannot talk it out of.
- `core/schedule.py` — patrols. One only ever starts if the rover is parked,
  not stopped, above 40% battery and the remote is off; otherwise it says why
  and waits for the next slot.
- `core/notify.py` — a message on the page, and optionally Telegram.
- `media/recorder.py` — a frame every couple of seconds during AUTO, turned
  into an MP4 at the end. A 20-minute outing becomes a 40-second timelapse.

### The safety interlocks that exist today

1. Emergency stop from the website, the SPACE key, or the remote. It latches;
   clearing it is deliberate.
2. The pump must be armed before anything can spray, and arming is a separate
   action from spraying.
3. **It will not spray while standing still.** A boom that sprays stationary
   dumps the whole dose in one spot, so the rover shuts the valves if it stops.
4. A hard ceiling on litres per hectare (600) and on millilitres per outing
   (6000) that no setting can exceed.
5. It will never spray on its own below 70% confidence — a hard floor, not a
   preference. Below your own threshold it stops and asks you.
6. Battery: warn at one voltage, stop at another, and come home at a chosen
   percentage.
7. Tilt cut-out at a chosen angle — *configured, but see below*.
8. Front obstacle stop — *configured, but see below*.
9. Everything private needs a sign-in, with rate limiting on wrong passwords.

---

## 3. What is not fitted

This is the part that matters. As of today the console reports:

| | state | consequence |
|---|---|---|
| Wheel encoders | **not fitted** | distance is worked out from what the motors were *told*, which drifts. A wheel spinning in mud reads the same as a wheel gripping. |
| Tilt sensor (IMU) | **not fitted** | the "stop if it leans more than 22°" setting can never fire. |
| Front range sensor | **not fitted** | nothing stops it driving into something. |
| Soil probe | **not fitted** | no soil moisture reading at all. |
| Boom valves | **not fitted** | nothing can be sprayed. |
| Drive and steering | **simulation** | it cannot move. |
| Plant AI model | **no model file** | every plant is logged as "not checked". |
| Front camera measured | set | the arm can aim at what the camera sees. |

None of that is a bug. It is a machine that has been written before it has been
wired. But it does mean the current state is: **a complete, working console and
brain, driving nothing.**

---

## 4. What changed on 22 September 2026

- **Four launcher files became one.** `AR-750.bat` is a menu: open the console,
  connect to the real rover, look at the design, check everything is working,
  stop the console, quit. The menu reports whether Python is installed, whether
  it has been set up, and whether the console is running.
- **The console was rebuilt.** Animated radial gauges, sparklines seeded from
  the database, a live trail that fades, a pannable and zoomable field map, a
  photo gallery, a new Alerts page (the `/api/alerts` endpoint existed and
  nothing had ever called it), a command palette on Ctrl+K, keyboard driving on
  WASD, SPACE for emergency stop, and a light theme for reading outdoors.
- **Colour-blind fix.** The old field map drew fine / problem / sprayed as
  green / orange / red. Measured against a deuteranope's vision, sprayed-red
  and fine-green are 2.7 ΔE apart — effectively the same colour. The map now
  draws a **circle, a triangle and a diamond**, and sprayed is violet, not red.
  Red is now reserved for danger only, which is better semantics anyway: a
  sprayed plant is not an error.
- **A real bug fixed.** The simulator's camera only ever produced a frame when
  OpenCV was installed, and the launcher deliberately does not download a 40 MB
  vision library. So `/cam/front` produced nothing, for ever, and the browser
  sat on an open request showing a black rectangle with no error. The camera
  now falls back to a PNG written with nothing but `zlib`, and the stream ends
  itself after five dry seconds so the page can say "no picture" and retry.
- **The console now survives a bad wifi.** If the websocket will not open, or
  drops, the page falls back to polling instead of freezing on the last frame,
  and the link chip says "slow link".
- **A self test was added**, as menu choice 4 and as
  `rover_software/tests/console_selftest.py`. It stands up a throwaway copy of
  the rover on its own port with its own empty data folder, then calls every
  URL and presses every button: 53 checks. All 53 pass today.

---

## 5. Do these five first

In this order. The first two are safety, and the machine should not move under
its own power until they are done.

**1. Fit the front range sensor.** Right now nothing stops the rover driving
into a person, a wall or a plant. An HC-SR04 costs almost nothing and the
software is already written and waiting for it — `hw/rangefinder.py`, config at
`sensors.range_front`. This is the single largest gap in the machine.

**2. Fit the tilt sensor.** `safety.tilt_stop_deg` is set to 22°, and on a
120 kg machine on a slope that setting is doing nothing at all until an
MPU-6050 is on the i2c bus. Wiring is in `docs/WIRING_AND_SETUP.md`.

**3. Measure the nozzle flow with a jug.** `boom.ml_per_min_per_nozzle` is
currently 320, which is a guess. Every litres-per-hectare number the rover
calculates is built on top of that one figure, so a wrong value means it is
confidently spraying the wrong dose. One nozzle, one jug, one minute, one
number. Do this before the boom is ever armed over a real plant.

**4. Train the model.** Until then it photographs and files but does not
diagnose, which is an expensive camera on wheels. The console already exports
the photo set in exactly the folder shape a classifier wants — Runs & photos,
"Download the photo set". Aim for 100+ photos per class, taken across different
days and different light. A model trained on one sunny afternoon works on one
sunny afternoon. `docs/TRAINING_THE_MODEL.md` has the rest.

**5. Fit the wheel encoders.** They are what turns "go 350 mm to the next
plant" from a guess into a measurement, and what stops the field map drifting
over a long row. The plant numbers stay exact either way, but the positions do
not.

---

## 6. After that

**Software gaps worth closing**

- **The first-login promise is not kept.** The first admin user is created with
  `must_change: true` and the README says "it makes you change both straight
  away", but nothing on the server actually enforces it — you can sign in with
  `admin` / `agrirover` and carry on for ever. Either enforce it (redirect to
  Settings until the password changes) or stop claiming it.
- **The console listens on 0.0.0.0 with no HTTPS.** Anyone on your wifi can
  reach the login page. `docs/REMOTE_ACCESS.md` already says to use Tailscale
  and not to open a router port, which is right; consider making that the
  documented default rather than the advanced option.
- **Battery percent is a linear map from voltage.** Discharge curves are not
  linear, so "come home at 25%" does not mean what it sounds like. A lookup
  table for your actual pack chemistry, or a coulomb counter, would make that
  setting trustworthy.
- **Row following is colour only.** A green mask will follow a line of weeds as
  happily as a line of crop. Worth knowing before the first unattended patrol.
- **Check `prune()` is actually scheduled.** `db.prune()` and
  `recorder.prune()` exist and `record.keep_days` is set to 30, but it is worth
  confirming something calls them, or the SD card fills up quietly over a
  season.
- **One encode per viewer.** `/cam/front` re-encodes for every open browser.
  Fine for one phone, worth a shared frame buffer if the whole family watches.

**Features worth having**

- A **dry-run mode**: do the entire mission, decide everything, log everything,
  and never open a valve. The safest way to test a new model in a real row.
- A **weather hook**: do not spray if rain is forecast within the rain-fast
  window the treatment table already knows about.
- **Absolute positions.** Everything is odometry relative to where it started,
  so two runs do not line up unless you mark home in the same spot. A GPS fix,
  even a cheap one, would make the field map mean the same thing week to week.
- **A season report** — the charts and the plant histories as one PDF you can
  keep, or hand to whoever asks what you sprayed and when.
- **More than one login**, if anyone else is going to drive it.

---

## 7. How to check it is all still working

`AR-750.bat` → choice 4. It stands up a throwaway copy of the rover on its own
port with its own empty data folder, calls every page and presses every button,
prints a pass/fail line for each, and deletes the copy again. Nothing you have
set up is read or written. The report is kept at
`rover_software/tests/last_selftest_report.txt`.

Run it after you change anything, and run it once on the Pi when the rover is
built — the same 53 checks will then be checking real hardware.
