# PUTTING THE CODE ON THE RASPBERRY PI — every step

You are on Windows. This assumes nothing except that you have the Pi, a
microSD card, a card reader, and a 5 V supply for it.

You do **not** need the rover built. Do all of this on your desk first, with
the Pi sitting next to the laptop and nothing wired to it.

---

## What you need in your hand

| | |
|---|---|
| Raspberry Pi 4 | any RAM size |
| microSD card | 32 GB, class 10 |
| card reader | most laptops have a slot; otherwise a USB one |
| USB-C power supply | the official 5 V 3 A one, or your buck converter later |
| your wifi name and password | the Pi joins the same wifi as this laptop |

---

## STEP 1 — Put the operating system on the card

1. On this laptop, download **Raspberry Pi Imager** from
   <https://www.raspberrypi.com/software/> and install it.
2. Put the microSD card in the reader.
3. Open Imager and choose:
   - **Device** → Raspberry Pi 4
   - **Operating System** → Raspberry Pi OS (64-bit)
   - **Storage** → your card. *Check the size — it wipes whatever you pick.*
4. Click **Next**. It asks **"Would you like to apply OS customisation
   settings?"** → click **EDIT SETTINGS**. **Do not skip this.** It is what
   makes the next steps possible.

   On the **General** tab:
   - Set hostname: `ar750`
   - Set username and password: username `pi`, and a password you will
     remember. *Write it down.*
   - Configure wireless LAN: your wifi name and password
   - Wireless LAN country: `IN`
   - Set locale settings: your timezone

   On the **Services** tab:
   - Tick **Enable SSH** → **Use password authentication**

5. Save, then **Yes** to apply, then **Yes** to erase. It takes 5–10 minutes.

---

## STEP 2 — Start the Pi

1. Card out of the laptop, into the Pi.
2. Power in. The green light will flicker.
3. Wait **three minutes** the first time. It is resizing itself and joining
   your wifi. Nothing to watch.

---

## STEP 3 — Talk to it from your laptop

Open **PowerShell** on Windows (press Start, type `powershell`, Enter) and:

```powershell
ssh pi@ar750.local
```

First time it asks `Are you sure you want to continue connecting?` → type
`yes` and Enter. Then your password. *Nothing appears while you type the
password — that is normal, keep typing and press Enter.*

You should land on a line like `pi@ar750:~ $`. **You are now on the Pi.**

**If `ar750.local` does not work:** your router may not do `.local` names.
Log into your router's page and find the device called `ar750` to get its IP
(something like `192.168.1.42`), then use `ssh pi@192.168.1.42` instead — and
use that IP everywhere below in place of `ar750.local`.

Type `exit` to come back to your own laptop.

---

## STEP 4 — Copy the code across

There is no separate "Raspberry Pi version" to find. The folder
**`rover_software`** next to `AR-750.bat` *is* the rover's program — the same
one you have been clicking through on the laptop. On the Pi it finds real
hardware instead of fakes; nothing else changes.

### The easy way

On the laptop, run **`AR-750.bat`** and pick **5 — Send the code to the
Raspberry Pi**, then **S**. It asks for the Pi as `pi@ar750.local`, remembers
it, and copies the folder across as **`~/AR750_Rover`**.

It deliberately leaves out the Windows virtual environment, the `__pycache__`
folders and the laptop's `data\` folder, so **the Pi's own database, photos
and password are never overwritten**. Send it again after every change and you
lose nothing on the rover.

No network to the Pi? Pick **Z** instead. It writes `AR750_Rover.zip` next to
`AR-750.bat` for a USB stick; unzip it in the Pi's home folder.

### By hand, if you would rather

In PowerShell **on your own laptop** (type `exit` first if you are still on the
Pi):

```powershell
cd "$env:USERPROFILE\Desktop\Agricultural farm rover\Claude outputs\AR750_Website_Launcher\AR750_Website_Launcher"
scp -r ".\rover_software" pi@ar750.local:AR750_Rover
```

`scp` is already part of Windows — nothing to install. It lists every file as
it goes and takes a minute or two.

Doing it this way **does** carry the Windows `.venv` folder and the laptop's
`data\` folder across, which is why the menu is the better route: `.venv`
holds Windows binaries that are useless on the Pi, and `data\` would
overwrite whatever the rover has already recorded.

## STEP 5 — Install it

Get back on the Pi and run the installer:

```powershell
ssh pi@ar750.local
```

```bash
cd ~/AR750_Rover
bash install.sh
```

**About ten minutes.** It installs Python packages, pigpio, the I2C tools,
turns I2C on, sets the rover to start by itself at boot, and finishes by
running the safety tests. You want the last line to end in **`0 failed`**.

It also runs on a Pi with nothing wired to it. Every part that is missing
simply reports itself as not fitted, which is what the Settings page shows
you.

It is safe to run again any time. It never touches your data or password.

---

## STEP 6 — Try it with no hardware at all

Still on the Pi:

```bash
python3 -m ar750.main --sim
```

It prints something like:

```
  website     : http://192.168.1.42:8080
  FIRST TIME: sign in with   admin / agrirover
```

Type that address into your phone or your laptop browser. **Both have to be
on the same wifi.** Sign in with `admin` / `agrirover` — it makes you change
both straight away, and from then on the username and password live on the
website. You never edit any code to change them.

Click around. Put it in AUTO, press **Start the row**, watch it work. Nothing
moves, because nothing is wired — that is the point of `--sim`.

Press **Ctrl+C** on the Pi to stop it.

---

## STEP 7 — Make it start on its own

`install.sh` already set this up. To start it now without rebooting:

```bash
sudo systemctl start ar750
```

Useful afterwards:

```bash
systemctl status ar750        # is it running?
journalctl -u ar750 -f        # what is it saying? Ctrl+C to stop watching
sudo systemctl stop ar750     # stop it
sudo systemctl disable ar750  # stop it starting at boot while you build
```

**Note:** the service runs the real thing, not `--sim`. While you are still
building, `sudo systemctl disable ar750` and run it by hand instead.

---

## STEP 8 — Once the electronics are wired

Wire it following the circuit diagram, then, **with the rover on blocks and
all four wheels off the ground**, in this order:

```bash
cd ~/AR750_Rover
python3 scripts/bench.py wheels     # on blocks. Note the min_duty it finds
python3 scripts/bench.py steering   # protractor on a front wheel
python3 scripts/bench.py rc         # check your remote's channel map
python3 scripts/bench.py probe      # nothing underneath the spike
python3 scripts/bench.py boom       # BEFORE you buy nozzles
python3 scripts/bench.py pump       # the pump on its own
python3 scripts/bench.py adc        # battery and soil readings
python3 scripts/bench.py cameras    # is the lens seeing anything
python3 scripts/bench.py encoders   # turn a wheel by hand, watch it count
python3 scripts/bench.py imu        # tilt it and watch the angle
python3 scripts/bench.py range      # wave your hand in front of it
```

Then edit the settings the tests told you to:

```bash
nano ~/AR750_Rover/ar750/config.yaml
```

`Ctrl+O`, Enter to save; `Ctrl+X` to leave.

The ones you will actually change:

| Setting | Why |
|---|---|
| `drive.hbridge.min_duty` | the percentage `bench.py wheels` found |
| `drive.invert_front` / `invert_rear` | if an axle ran backwards |
| `safety.battery.chemistry` and `cells`/`warn_v`/`stop_v` | match the pack you bought |
| `boom.ml_per_min_per_nozzle` | catch one nozzle in a jug for a minute |
| `cameras.front.height_mm` and `pitch_deg` | measure them once it is built |

---

## STEP 9 — Check the whole console on the Pi

The same 53 checks the laptop runs are in the folder you just copied. On the
Pi:

```bash
cd ~/AR750_Rover
bash scripts/selftest.sh
```

And for a one-screen answer to "is it up, and can it actually move?":

```bash
bash scripts/status.sh
```

It reports whether the rover service is running, whether it starts at boot,
whether **pigpio** is answering (without it the website works but nothing
moves), and whether the Pi has ever been short of power since it booted — a
Pi 4 on a weak supply mostly works, and then corrupts its SD card.

It stands up a throwaway copy with its own empty data folder, calls every page
and presses every button, and prints a pass/fail line for each. Nothing the
rover has recorded is read or written. Worth doing once here, because it is
the first time those checks run against the real hardware layer rather than
the laptop's fakes.

---

## WHEN IT GOES WRONG

**`ssh: Could not resolve hostname ar750.local`**
The Pi is not on the network yet, or your router does not do `.local`. Wait
three minutes after power-on. Then find its IP on your router's page and use
that instead.

**`Permission denied (publickey,password)`**
Wrong password, or you did not tick Enable SSH in Step 1. Reflash the card
and do the OS customisation properly this time.

**The website address it prints does not open**
Your phone is on mobile data, or on a different wifi. Both devices must be
on the same network.

**`sudo: apt-get: command not found`, or install.sh fails**
You flashed the wrong image. It must be Raspberry Pi OS, not Ubuntu or
anything else.

**Everything installs but nothing moves when you test the wheels**
The R_EN and L_EN pins on the BTS7960 boards are not tied to 3.3 V. This is
the fault everybody hits first. Sheet 4 of the circuit diagram.

---

## REACHING IT FROM OUTSIDE YOUR HOUSE

`docs/REMOTE_ACCESS.md` inside the same folder. Short version: install
Tailscale on the Pi and on your phone, and use the address it gives you.

**Do not forward a port on your router.** That puts a machine which can drive
itself and spray chemicals on the open internet behind one password.
