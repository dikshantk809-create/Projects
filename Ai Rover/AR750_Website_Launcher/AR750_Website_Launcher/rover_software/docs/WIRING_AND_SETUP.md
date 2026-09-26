# AR-750 — wiring and setup

Everything here matches `ar750/config.yaml`. If you move a wire, change the
number in that file, not in the code.

Pin numbers are **BCM** (the GPIO number, not the position on the header).
Run `pinout` on the Pi if you want the picture.

The dimensions in this guide were read out of
`AR-750_Rover_Complete_Assembly.f3d`, not estimated:

| | |
|---|---|
| Wheelbase | 540 mm |
| Track | 430 mm |
| Wheel | 209.6 mm over the tyre, 75 mm wide |
| Ground clearance | 108 mm (the diff skid shoes are the lowest thing) |
| Body | 740 long × 516 wide × 189 high |
| Boom | 700 mm across, 5 nozzles at 140 mm, 235 mm off the ground |
| Tank | 300 × 200 × 100 mm, about 5 litres inside |
| Turning circle | 2.78 m — **it cannot turn on the spot** |

---

## 1. What this machine is, and what it is not

The AR-750 is **four wheel drive with Ackermann steering**. One motor drives
the front differential, one drives the rear, and a servo points the front
wheels. That is a car, not a tank.

Three consequences worth having in your head before you wire anything:

- **Both motors always do the same thing.** If you ever find yourself running
  one faster than the other to turn, stop. The diffs will let the inside wheels
  spin, it will go straight anyway, and the motors will fight through the
  ground.
- **It needs 2.8 m to turn round.** At the end of a row it either loops round a
  headland or does a three point turn. Plan your beds for that.
- **Know which driver you built.** A BTS7960 wants a PWM pin for each
  direction; a brushed ESC wants one pin carrying a 1000–2000 µs servo pulse.
  They are not interchangeable in the wiring or in `config.yaml`.

---

## 2. What the parts are

| What | Part | Why this one |
|---|---|---|
| Brain | Raspberry Pi 4 | |
| Drive motors | 2 × brushed motor, 42 mm × 75 mm in the model | one per axle, through the 5.94:1 gear train |
| Motor drivers | 2 × BTS7960 / IBT-2 | one per motor. 6–27 V, 43 A. A brushed ESC also works — see §4 |
| Steering | 1 × metal gear servo, 20 kg·cm or better | it pushes the whole linkage |
| Probe | gearmotor + lead screw + 2 limit switches | drives the moisture spike into the soil |
| Boom | 1 pump, 3 solenoid valves, 5 nozzles | the valves give you three sections |
| Sensors | ADS1115 4-channel ADC | the Pi has no analogue input |
| Camera | one Pi camera in the front pod | it follows the row *and* judges the plants |
| Power | 4S pack, 20 Ah, plus a 5 V 5 A buck | |

---

## 3. Power

```
12 V pack ───────┬── main switch ── fuse 30 A ──┬── front driver (B+ / B-)
                 │                              ├── rear driver  (B+ / B-)
                 │                              ├── pump + valves
                 │                              ├── probe motor driver
                 │                              └── lights
                 └── buck converter 5 V 5 A ────┬── Raspberry Pi
                                                └── steering servo
```

Rules that matter:

- **One common ground.** Pi GND, both motor driver grounds, the ADC, the receiver and
  the valve driver grounds all meet at one point. Most "it went mad on its own"
  problems are a missing ground.
- **Do not power the steering servo from the Pi's 5 V pin.** It pulls several
  amps when it hits the stops. Give it the buck converter directly.
- **A fuse on the main, and one per motor driver.** A heavy machine with a jammed wheel
  will happily set fire to a wire.
- **Flyback diodes on the pump and every solenoid valve.** Without them the
  back-EMF resets the Pi, and you will spend an evening blaming the software.

---

## 4. The drive — two motor drivers

`drive.driver` in `config.yaml` says which kind you built. **Default is
`bts7960`,** which is what the parts list buys.

### bts7960 — two pins per motor

| Signal | Pin | Goes to |
|---|---|---|
| Front RPWM | GPIO 12 | front board, forward |
| Front LPWM | GPIO 19 | front board, reverse |
| Rear RPWM | GPIO 13 | rear board, forward |
| Rear LPWM | GPIO 10 | rear board, reverse |
| R_EN, L_EN | 3.3 V | **both boards, tied high and left there** |
| Steering servo | GPIO 18 | hardware PWM |
| Grounds | common | |

The BTS7960 is 6–27 V and 43 A, so a 12 V pack at 13.8 V off the charger or a
LiFePO4 at 14.6 V is nowhere near its limit. There is nothing to arm and no
calibration. Forget the enable pins and nothing moves at all — that is the
usual first fault.

### esc — one pin per motor

| Signal | Pin | Note |
|---|---|---|
| Front ESC signal | GPIO 12 | hardware PWM |
| Rear ESC signal | GPIO 13 | hardware PWM |
| Steering servo | GPIO 18 | hardware PWM |
| Grounds | common | |

**Check the voltage before you buy one.** Almost every hobby brushed ESC on
sale is built for RC cars and stops at 3S, which is 12.6 V — below a freshly
charged 12 V pack. And the cheap "30 A brushed ESC" everyone links to is a
4–8 V micro ESC for toy cars; 12 V destroys it on the first switch-on. The one
that genuinely does 7–35 V with an RC-style input is the Cytron MDDS30, about
fourteen times the price of two BTS7960 boards.

Also pull the **red BEC wire** out of both ESC servo plugs. Two BECs fighting
the buck converter is a classic way to cook a Pi.

### Either way, before the wheels touch the ground

1. `python3 scripts/bench.py wheels` with the rover **on blocks**.
2. If an axle runs backwards, set `invert_front` or `invert_rear` in the
   config. Do not swap the motor wires.
3. The test creeps the throttle up from 5%. Watch the wheels, note the first
   percentage that actually turns them, and put it into
   `drive.hbridge.min_duty` as a fraction — 15% is `0.15`. A geared motor
   below that just buzzes and gets hot.
4. On an ESC, if nothing moves at all it has not armed — most want to see
   neutral for a couple of seconds at power-on, which `arm_seconds` does.

---

## 5. Steering

One servo drives the whole linkage:

```
servo horn (12 mm) → drag link → steer plate (pivot, 40 mm in / 64 mm out)
                                    → tie rods → steering arms (39.8 mm)
```

Wind that through and full servo travel gives **±24.7°** at the road wheels,
which on a 540 mm wheelbase is a **1.17 m** turning radius — a 2.78 m circle
for the whole machine.

Set it up:

```bash
python3 scripts/bench.py steering
```

It sweeps through the angles and prints what each one should do. Put a
protractor against a front wheel at full lock. If the real angle is different
from 24.7°, put the measured number into `drive.steering.max_wheel_deg` and
every other number follows from it. If the wheels do not come back to straight,
adjust `trim_us` a few microseconds at a time.

**Set the servo's mechanical limits before you connect the drag link.** A servo
trying to push the linkage past its stops will strip its gears in seconds.

---

## 6. The spray boom

| Signal | Pin | Drives |
|---|---|---|
| Pump | GPIO 16 | through a MOSFET or relay |
| Left section | GPIO 17 | nozzles 1 and 2 |
| Centre section | GPIO 27 | nozzle 3 |
| Right section | GPIO 22 | nozzles 4 and 5 |

### The nozzle problem — read this before you buy nozzles

The rate a boom puts down is:

```
litres per hectare = 0.6 × (ml/min per nozzle) ÷ (km/h × nozzle spacing in m)
```

This rover follows a row at `base_speed` × `max_speed_mps` = 0.35 × 0.45 =
**0.16 m/s**, which is 0.57 km/h. At 140 mm spacing a 350 ml/min nozzle gives
**2646 l/ha**. A vegetable crop wants around 200. That is thirteen times too
much, and you cannot fix it by driving faster — that would need 7.5 km/h down a
vegetable bed.

Two honest fixes, and you want both:

1. **Buy the smallest nozzles you can find**, and run them at low pressure. For
   200 l/ha at this speed and spacing you need about **26 ml/min** per nozzle.
2. **Let the valves pulse.** The software switches the section valves about ten
   times a second and sets the fraction of time they are open to hit your
   target rate. That is how commercial PWM nozzle control works and the
   solenoid valves in the design can already do it.

Below about 15% duty the band starts to go stripey, and the dashboard says so
rather than quietly spraying a bad pattern.

```bash
python3 scripts/bench.py boom
```

prints all of this for the nozzles you actually fitted.

**Measure your real flow.** Hold a jug under one nozzle for one minute at
working pressure and put the millilitres into `boom.ml_per_min_per_nozzle`.
Every number above depends on it.

---

## 7. The soil probe

| Signal | Pin |
|---|---|
| Motor, down | GPIO 24 |
| Motor, up | GPIO 23 |
| Bottom limit switch | GPIO 25 |
| Top limit switch | GPIO 26 |

Both switches wire to ground and the pin, with the internal pull-up doing the
rest — so a **broken wire reads as "switch pressed"**, which stops the motor.
That is the safe way round. Wire them the other way and a broken wire means the
motor runs until the screw reaches the end.

The spike travels 190 mm between the switches and ends up about 65 mm into the
soil. Test it with nothing underneath:

```bash
python3 scripts/bench.py probe
```

Both legs should take about the same time. If one is much slower, the screw
wants greasing.

---

## 8. Sensors, lights and the remote

| Signal | Pin |
|---|---|
| I²C (ADS1115, IMU) | GPIO 2, 3 |
| Headlights | GPIO 9 |
| Tail lights | GPIO 11 |
| Front range sensor | trig GPIO 7, echo GPIO 8 **through a divider** |
| Wheel encoders | 5, 6 (front) and 20, 21 (rear) |

ADC channels: A0 soil probe, A1 tank level, A2 battery through a divider,
A3 motor current.

Battery divider for 4S: R1 = 100 kΩ, R2 = 20 kΩ, which is 6.0 — so 16.8 V
arrives as 2.8 V. `battery_divider: 6.0` must match what you actually fitted.

The range sensor's echo pin puts out 5 V and the Pi's pins are 3.3 V: 1 kΩ from
ECHO to the Pi pin, 2 kΩ from that pin to ground. Skip it and you damage the Pi.

### The remote

This is a car, so the sticks mean car things:

| Channel | Does |
|---|---|
| 1 | steering — this points the wheels |
| 2 | soil probe up / down |
| 3 | throttle, forward and back |
| 4 | boom sections |
| 5 | 3-position switch: manual / hold / auto |
| 6 | 2-position switch: arms the pump |

SBUS needs an inverter into GPIO 15 and `enable_uart=1` plus
`dtoverlay=disable-bt` in `/boot/firmware/config.txt`. PPM goes straight to
GPIO 4. Six separate PWM wires go to 14, 15, 19, 26, 0, 1.

The remote always wins. Move a stick while it is driving itself and it drops
into manual on the spot.

---

## 9. The camera

One Pi camera, in the front pod. From the model its lens centre sits **254 mm
above the ground and 95 mm ahead of the front axle**, looking forward.

Tilt it down about 12° so it sees the row rather than the horizon, then put the
real numbers into `cameras.front`:

- `height_mm` — lens centre to the ground
- `pitch_deg` — how far below horizontal
- `vfov_deg` — 48 for a Pi camera v2, about 66 for a v3 wide

Until `height_mm` is set the rover will not try to work out where anything is
on the ground; it says the camera is not measured instead of guessing.

This one camera does two jobs — following the row and judging the plants — so
keep the lens clean and the hood on.

---

## 10. Installing

```bash
cd ~/AR750_Rover
bash install.sh
python3 -m ar750.main            # or --sim to try it with no hardware
```

It prints the address to type into your phone. Sign in with **admin /
agrirover**; it makes you change both straight away. To reach it from outside
the house, read `REMOTE_ACCESS.md` — use Tailscale, do not forward a port.

Before the first drive, in this order:

```bash
python3 scripts/bench.py wheels     # on blocks, wheels off the ground
python3 scripts/bench.py steering   # protractor on a front wheel
python3 scripts/bench.py rc         # check your channel map
python3 scripts/bench.py probe      # nothing underneath it
python3 scripts/bench.py boom       # nozzle sizing, before you buy nozzles
python3 scripts/bench.py adc        # battery and soil readings
```

---

## 11. What it still cannot do

| Missing | What it costs you |
|---|---|
| **Wheel encoders** | The distance on the dashboard is worked out from what the motors were told, so it drifts. Worse here than on a simpler rover, because the three point turn at the end of a row is dead reckoning: after two or three rows you will be straightening it by hand. Fit these first. |
| **IMU** | The tilt cut-out can never fire without one, and this machine is 400 mm tall on a 430 mm track. On a side slope that matters. |
| **Front range sensor** | Nothing stops it driving into a person or a wall. At 120 kg that is not a small thing. |
| **Current sensor** | A jammed wheel or a seized diff shows up here seconds before a driver board gets hot enough to fail. |
| **A hardware stop button** | Wired to cut both motor drivers’ enable lines directly. The red button on the website goes through software; a real one does not care whether the software is alive. |
| **Trained AI model** | Until you train one, every plant is logged as "not checked" with a photo saved. See `TRAINING_THE_MODEL.md`. |

---

## 12. Safety, in plain words

The pump cannot run until you arm it. The boom will not open while the rover is
standing still, because a boom that sprays in one spot puts the whole dose on
one plant — and if it stops while spraying, the software shuts the boom off.
It will never spray a virus, because nothing cures a virus, and it will never
spray a plant it is not sure about.

The robotic arm (section 13) moves only when you move it, from the phone. The
rover never reaches out on its own: a weed gets photographed, logged and left
for you. In Auto the arm holds still, and an emergency stop freezes it where
it is.

The rates in `ar750/ai/treatment.py` are common recommendations for kitchen
garden vegetables. **They are not a prescription.** The label on the bottle you
actually bought is what counts, rules differ in every country, and the waiting
time before you can pick and eat the crop is the number that matters most.

---

## 13. The robotic arm and the camera servo

**The small build** (Raspberry Pi 4, L298N, 3S LiPo, MG996R on the camera,
5-DOF arm, soil module, AI Camera) has no boom, probe or lights, so its
servos go straight to Pi pins and pigpio makes the pulses - no extra board.
Every wire for it, with pictures, is in `WIRING_SMALL_BUILD.html` in this
folder; `config.yaml` is already set up for it (`servos.driver: gpio`,
`drive.layout: skid`, `drive.driver: l298n`).

**The full AR-750** uses its spare pins for the boom, the probe and the
lights, so there the servos hang off one **PCA9685 16-channel servo board**
instead (`servos.driver: pca9685`, `channel` = the board's output):

| PCA9685 pin | Goes to |
|---|---|
| VCC | Pi 3.3 V (pin 1) - the board's own logic |
| GND | Pi GND, **and** the servo supply's minus |
| SDA | GPIO 2 (pin 3) - same bus as the ADC |
| SCL | GPIO 3 (pin 5) |
| V+ (green terminal) | a separate **5-6 V, 5 A or more** supply, for the servos only |

Six servos pulling at once can draw several amps. Feed them from the Pi's 5 V
and the Pi browns out and reboots mid-move. Only the grounds are joined.

| Channel | Servo | Name in `config.yaml` |
|---|---|---|
| 0 | Base (turn) | `base` |
| 1 | Shoulder | `shoulder` |
| 2 | Elbow | `elbow` |
| 3 | Wrist up / down | `wrist` |
| 4 | Wrist turn | `roll` |
| 5 | Gripper | `grip` |
| 6 | Camera left / right | `pan` |

Different arm? Change the `servos:` list in `ar750/config.yaml` - one line per
joint, with its channel, its limits and where it rests. The phone page builds
its sliders from that list, so nothing else needs changing.

**Before the first move**, every angle in the config is a starting guess:

1. Switch on with the arm folded in its park pose. A hobby servo cannot say
   where it is, so the software assumes park - anywhere else and the first
   move is a jump.
2. On the phone, open **Remote**, tap **Take control**, then move one joint at
   a time with **+** and **-**. Note the angle where it touches something.
3. Put `min` and `max` a few degrees inside those in `config.yaml`, and send
   the code across again. A servo pushed past a hard stop stalls, heats up and
   strips its gears.
4. If **Left** turns the camera right, set `reverse: true` on the `pan` line.

Without the board the page still works: the angles move on screen and the
card says **simulated**.
