# The first drive — the numbers you have to measure

The code is finished. Whether the rover *drives well* is now almost entirely a
question of whether about fifteen numbers in `ar750/config.yaml` match the
machine you actually built. Every one of them ships with a sensible guess, and
a guess is not a measurement.

Work down this list in order. Each item says what to measure, the command that
measures it, the setting it goes in, and what goes wrong if you skip it.

`WIRING_AND_SETUP.md` says how it is all connected. This says what to do once
it is.

---

## Before you start

- The rover is **on blocks, all four wheels off the ground**, for everything
  down to section 4.
- The spray tank has **plain water** in it, nothing else, until section 6 is
  finished and you are happy.
- You are near the battery's main switch, and you can reach it.
- Nobody else is in the room, and nothing is under the probe.

Everything below runs on the Pi:

```bash
cd ~/AR750_Rover
```

---

## 1. The battery, before anything else draws from it

| | |
|---|---|
| **Measure** | what pack you actually bought |
| **Command** | `python3 scripts/bench.py adc` |
| **Settings** | `safety.battery.chemistry`, `cells`, `warn_v`, `stop_v`, `capacity_ah` |

The defaults are a 12 V lead-acid brick: six cells, warn at 11.8 V, stop at
11.0 V. If you fitted lithium, **all four of those are wrong**, and the number
that matters most is `stop_v` — it is the one that stops the motors before you
damage the pack.

Check the voltage `bench.py adc` reports against a multimeter on the terminals.
If they disagree, the divider resistors in `sensors.battery` do not match what
you soldered, and every battery reading the console shows you is fiction.

**Skip it and:** "come home at 25%" fires at the wrong time, or never.

---

## 2. Which way the wheels go, and how slowly they will still turn

| | |
|---|---|
| **Measure** | the throttle at which each axle actually starts moving |
| **Command** | `python3 scripts/bench.py wheels` |
| **Settings** | `drive.hbridge.min_duty`, `drive.invert_front`, `drive.invert_rear` |

A geared motor below about 15% duty just buzzes: it heats up, it draws current,
and it does not turn. `bench.py wheels` walks the duty up until each axle
starts and tells you the number. Put it in `min_duty`.

While it runs, watch which way each axle spins. If one runs backwards, flip
`invert_front` or `invert_rear` — **do not** swap the motor wires, because then
the encoder counts go the wrong way too.

**Skip it and:** the rover stalls at low speed, which is exactly the speed it
does its whole job at.

---

## 3. Straight ahead, and full lock

| | |
|---|---|
| **Measure** | the servo pulse that points the wheels dead straight, and how far they go before the linkage binds |
| **Command** | `python3 scripts/bench.py steering` — protractor on a front wheel |
| **Settings** | `drive.steering.centre_us`, `trim_us`, `us_per_deg`, `servo_max_deg`, `reverse` |

Three separate things, in this order:

1. **Centre.** Find the pulse where the wheels are genuinely straight, not
   nearly. Put the difference in `trim_us`. A degree of error here is a rover
   that curves off the row over ten metres and blames the row follower.
2. **Direction.** If asking for left gives you right, set `reverse: true`.
3. **Lock.** Turn until the linkage is about to bind, *stop before it does*,
   and set `servo_max_deg` to a little less. A servo grinding against its own
   linkage burns out.

`drive.steering.max_wheel_deg: 0` means "work it out from the linkage
measurements", which is what you want unless you have changed the geometry.
The console's Steering panel shows you what it worked out, and the turning
circle it implies — on the standard build, 28° and 4.9 m.

**Skip it and:** it will not hold a row, and the field map drifts sideways.

---

## 4. Distance — the one that makes the field map mean anything

| | |
|---|---|
| **Measure** | encoder ticks per wheel revolution |
| **Command** | `python3 scripts/bench.py encoders` — turn a wheel by hand, slowly, one full turn |
| **Settings** | `drive.encoder.enabled: true`, `ticks_per_rev` |

Encoders are the difference between "go 350 mm to the next plant" as a
measurement and as a hope. Without them the rover works out distance from what
it *told* the motors to do, so a wheel spinning in mud reads exactly like a
wheel gripping.

The console says which you are on: the Distance tile reads **measured** in
green, or **estimated, drifts** in grey.

**Skip it and:** the plant numbers stay exact, but their positions on the map
slowly stop matching the real row.

---

## 5. Stopping before it hits something

| | |
|---|---|
| **Measure** | that the front rangefinder answers at all |
| **Command** | `python3 scripts/bench.py range` — wave your hand in front of it |
| **Settings** | `sensors.range_front`, `safety.tilt_stop_deg` |

Also `python3 scripts/bench.py imu` — tilt the rover and watch the angle move.

These two are the reason the machine is allowed to drive itself. Until the
rangefinder is fitted, **nothing stops it driving into a person, a wall or the
crop**, and until the IMU is fitted, `tilt_stop_deg: 20` is a number that can
never fire.

The Settings page lists both under "What is actually fitted". Neither should
say *not fitted* on the day you first let it run a row unattended.

**Skip it and:** you are relying on being there to press the stop button.

---

## 6. The one number the whole spray system is built on

| | |
|---|---|
| **Measure** | how much one nozzle actually delivers in one minute |
| **Command** | `python3 scripts/bench.py boom` and a measuring jug |
| **Setting** | `boom.ml_per_min_per_nozzle` |

Do this with **plain water**. One nozzle, one jug, sixty seconds by a clock,
read the millilitres.

The default is 350 ml/min, which is a guess about a nozzle you may not have
bought. Everything the rover calculates — litres per hectare, how long a band
lasts, how much is left in the tank, whether it is allowed to spray at all —
is arithmetic on top of that single figure. Get it wrong and the machine will
confidently and repeatedly apply the wrong dose, and the log will say it
applied the right one.

While you are there:

- `boom.tank_litres` — what you actually fitted, not what the model says.
- `boom.target_l_per_ha` — from the label on the bottle, not from here.
- `boom.max_l_per_ha` — a ceiling you are sure you never want to cross.
- `boom.min_duty` — below this the band goes stripey; the rover warns rather
  than pretending.

**Skip it and:** every dose is wrong, and nothing in the system can tell.

---

## 7. The probe, and the camera

| | |
|---|---|
| **Command** | `python3 scripts/bench.py probe` — nothing underneath the spike |
| **Settings** | `probe.travel_mm`, `depth_below_ground_mm`, `timeout_s`, `settle_s` |

Watch it go down, hit the switch, wait, and come back up. If it never reaches a
switch it calls itself jammed after `timeout_s` and stops, which is the
behaviour you want.

Then the camera:

| | |
|---|---|
| **Measure** | lens height above the ground, and its downward angle |
| **Command** | `python3 scripts/bench.py cameras` |
| **Settings** | `cameras.front.height_mm`, `pitch_deg`, `vfov_deg` |

Measure them off the built rover with a tape and a phone level. Until they are
real, the rover cannot work out where on the ground a thing it sees actually
is, and the Settings page will keep saying *Front camera measured: not fitted*.

---

## 8. The remote — your override

| | |
|---|---|
| **Check** | which stick is on which channel |
| **Command** | `python3 scripts/bench.py rc` |
| **Settings** | the `rc:` block |

Move one stick at a time and watch which number changes. The remote always
wins over the website — move any stick and the rover drops straight back to
manual — so this is the control you will reach for when something is going
wrong. It is worth ten minutes.

---

## 9. The row itself

| | |
|---|---|
| **Measure** | your actual planting |
| **Settings** | `ai.plant_spacing_mm`, `row_length_m`, `rows`, `row_gap_mm` |

These are on the Settings page under **Deciding**, so you can change them from
your phone standing in the garden, which is where you will want to.

`row_length_m` is a hard cap: the rover will not run further than that down one
row whatever it thinks it sees. Set it to a little more than your longest row
and it becomes a useful backstop.

---

## 10. Then, and only then

1. Wheels back on the ground, in a **clear open space**, nothing planted.
2. Remote on. Rover in **MANUAL**. Drive it by hand. Check it stops when you
   let go, check it steers both ways, check the emergency stop.
3. Still in the open: **AUTO**, boom **disarmed**, and let it run a row of
   nothing. It will photograph empty soil and log it as not-checked, which is
   fine — you are watching the driving, not the diagnosis.
4. Real row, boom still disarmed. Let it do a full pass and read the log.
5. Only now: water in the tank, boom armed, `auto_spray` **off** so it asks you
   about every plant. Watch what it wants to do before you let it do it.
6. When you have watched it ask a few dozen times and agreed with it every
   time, turn `auto_spray` on.

There is no step that skips 5.

---

## Checking it all still works, later

On the Pi:

```bash
cd ~/AR750_Rover
python3 -m tests.test_decisions        # the safety rules
python3 scripts/bench.py <part>        # any one part, any time
```

And the whole website, end to end, against a throwaway copy that touches none
of your data — the last section of `PI_SETUP_STEP_BY_STEP.md`, or choice 4 on
the laptop's `AR-750.bat`.
