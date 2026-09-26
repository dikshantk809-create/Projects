# AR-750

Everything the rover needs: the brain, the website, the wiring guide and the
bench tests. One folder. Copy it to the Pi and run one command.

Built from `AR-750_Rover_Complete_Assembly.f3d` — every dimension in the config
was read out of that model, not estimated.

| | |
|---|---|
| Brain | Raspberry Pi 4 |
| Drive | four wheel drive, one motor per differential, through two BTS7960 boards (or two ESCs - `drive.driver` picks) |
| Steering | Ackermann, one servo, ±24.7° at the wheels |
| Turning circle | 2.78 m — **it steers like a car and cannot turn on the spot** |
| Wheelbase / track | 540 / 430 mm, 209.6 mm wheels |
| Sprayer | 700 mm boom, 5 nozzles in 3 sections, 5 litre tank |
| Soil probe | lead screw, 190 mm of travel, ~65 mm into the soil |
| Camera | one, in the front pod, 254 mm above the ground |
| Remote | your 6 channel set |
| Crop | vegetables |

**There is no arm and no gripper on this machine.** A weed gets photographed,
logged and left for you to pull. The software says so rather than pretending
otherwise.

---

## Start here

**On a laptop, with no rover at all:**

```bash
pip install -r requirements.txt
python3 -m ar750.main --sim
```

Open <http://localhost:8080>, sign in with **admin / agrirover**. Everything is
simulated — a fake camera, fake sensors, a fake crop row. Press **Auto → Start
the row** and watch the whole thing work.

**On the Pi:**

```bash
bash install.sh
python3 -m ar750.main
```

It prints the address to type into your phone.

---

## The two ways to drive it

**Manual.** Your 6 channel remote, and it means car things: throttle forward
and back, steering left and right. Channel 5 is the three position switch —
manual, hold, auto. Channel 6 arms the pump. If the remote is off you can drive
from the website instead, with the pad. **The remote always wins:** move a
stick while it is driving itself and it drops into manual on the spot.

**Auto.** It finds the crop row with the front camera, follows it, stops at
each plant, swings the arm camera in, decides what is wrong, and writes on the
website what it found and what you should do. If the answer is a spray it asks
you first — unless you have deliberately turned on "let it spray on its own",
and even then it will not spray anything it is unsure about, and never a virus.

At the end of a row it turns into the next one and carries on. If your beds are
further apart than its 2.78 m turning circle it loops round; if they are not,
it does a three point turn. A row has a hard length cap, so a row follower that
latches onto a hedge cannot walk the rover into the fence.

**The boom pulses.** With 140 mm nozzle spacing at the speed this rover follows
a row, ordinary nozzles put down about six times too much. The section valves
switch about ten times a second and the software sets how long they stay open
to hit the rate you asked for. Run `python3 scripts/bench.py boom` before you
buy nozzles — it tells you what size you actually need.

---

## What the website does

Seven sections down the left (across the bottom on a phone):

**Live** — the camera, everything it is doing right now, the mode buttons, the
drive pad, the steering readout, the boom, the soil probe, and the big orange
card when it needs an answer from you. Also where it is, drawn as it moves.

**Field map** — every plant it has ever looked at, on a map, coloured by how it
was last time. Tap one for its whole history.

**Plants** — the same thing as a searchable list. Find r2p07 and see every time
it has been checked, what was wrong, what was sprayed and when.

**Charts** — battery, soil and tank over the last hour to the last week; plants
checked against problems found, day by day; and what it has been finding most.

**Runs** — every outing, how long it took, what it found, and the timelapse
video of it, which you can play or download. Plus the whole log as a CSV.

**Timetable** — "check the row every weekday at seven". It only goes if it is
parked, not stopped, above 40% battery and the remote is off.

**Settings** — every limit, dose, threshold and switch, changed from the page
and applied at once. Your username and password too. And an honest list of what
hardware is actually fitted.

**It tells you when something happens.** Put a Telegram bot token and chat id in
Settings and press Test: after that your phone gets a message when it finds a
problem, when a run ends, when the battery is low, or when anything trips the
emergency stop. Nothing needs a port open to the internet.

---

## Signing in

The first time it is **admin / agrirover**, and it makes you change both before
you can do anything. After that your username and password live on the website
itself — you never edit a file. They are stored hashed in `data/users.json`, so
that file does not contain your password either.

To reach the console from outside your house, read `docs/REMOTE_ACCESS.md`.
Short version: use Tailscale, and do not forward a port on your router.

Forgotten the password? Delete `data/users.json` and restart — it goes back to
admin / agrirover. That also means anyone who can reach the Pi's files can do
the same, which is a good reason to keep the Pi somewhere sensible.

---

## The safety rules, in one place

- The pump is locked until you arm it, from the website or channel 6.
- The boom will not open while it is standing still, and shuts off if the rover
  stops while spraying. A boom that sprays in one place puts the whole dose on
  one plant.
- It asks before spraying. "Let it spray on its own" only acts above 85%
  confidence, and never on a virus or anything it is unsure about.
- Limits it cannot be argued out of, whatever the website sends: 600 litres per
  hectare, 6000 ml in an outing, 1.2 m/s, and it can never be told to spray on
  less than 70% confidence. Those four are in the code, not in a file.
- Dead man: if the website stops talking to it, it stops driving in about half
  a second.
- Emergency stop kills the motors, the pump and every valve, centres the
  steering, pulls the soil probe out of the ground, and stops the recording.
- Low battery stops it. Before that, at a level you choose, it comes home.
- A weed is logged and photographed, never acted on. This machine has no
  gripper, and spraying one weed between two vegetables hits the vegetables.
- **No AI model loaded means every plant is logged as "not checked", with a
  photo saved.** It will not guess a disease it did not see.

---

## Two things worth being straight about

**There is no trained model in here.** Train one on your own plants, your own
camera and your own light; a model trained on internet photos scores well on
internet photos and badly in a real garden. `docs/TRAINING_THE_MODEL.md` walks
through it end to end, and **Runs → Download the photo set** hands you every
photo the rover has taken, already sorted into folders, ready to correct and
train on. Until you do, the rover still drives, still photographs every plant,
still keeps the history — and says plainly that it has not checked anything.

**The distance is estimated, not measured, until you fit wheel encoders.** The
AR-750 as drawn has none, so the odometry comes from what the motors were told to
do and it drifts. That matters more here than on a simpler machine: the turn at
the end of a row is dead reckoning, so after two or three rows you will be
straightening it by hand. The dashboard says "estimated, drifts" underneath the
number so you are never misled. Encoders are the cheapest worthwhile upgrade
and the code already supports them.

The doses in `ai/treatment.py` are common recommendations for kitchen garden
vegetables, not a prescription. The label on the bottle you actually bought
wins, and the waiting time before you can eat the crop matters most of all.

---

## What is in this folder

```
install.sh              one command setup on the Pi
requirements.txt
ar750/
  config.yaml           pins, wiring, calibration. Set once when you build it.
  rover.py              the 50 Hz control loop, the modes, the safety rules
  main.py               starts everything
  core/
    state.py            one object holding what the rover is doing now
    settings.py         the settings the website can change, and the hard caps
    auth.py             usernames and passwords, hashed
    db.py               the memory: plants, runs, readings, alerts
    schedule.py         patrols
    notify.py           Telegram
  hw/
    drive.py            both motor drivers and the steering servo
    ackermann.py        the steering linkage, and what it means for turning
    boom.py             5 nozzles, 3 sections, the litres-per-hectare maths
    probe.py            the lead screw soil probe and its limit switches
    rc.py               SBUS / PPM / PWM receiver
    io.py               lamps, ADC
    camera.py           the front camera
    encoders.py         wheel encoders, if you fit them
    imu.py              tilt and heading, if you fit one
    rangefinder.py      the front stop sensor, if you fit one
  ai/
    vision.py           row following and the plant classifier
    treatment.py        what to do about each problem, and what NOT to do
    mission.py          the auto job, as a state machine you can watch
  media/recorder.py     the timelapse of each run
  web/
    server.py           the API, the live feed, sign in
    static/             the console: index, login, style, app, charts
docs/
  WIRING_AND_SETUP.md   every pin, the power wiring, the calibrations
  REMOTE_ACCESS.md      reaching it from outside, safely
  TRAINING_THE_MODEL.md collecting photos, training, and not trusting it yet
scripts/
  bench.py              bench test each part before the first drive
  build_preview.py      one file showing the console with no rover behind it
  fetch_fonts.py        make the console work with no internet
tests/
  test_decisions.py     107 checks, no hardware needed
data/                   made at runtime: the database, photos, videos, settings
models/                 put your trained model here
```

Every piece of hardware degrades to simulation if it is missing, so the whole
rover runs on a laptop and the website behaves exactly the same.
