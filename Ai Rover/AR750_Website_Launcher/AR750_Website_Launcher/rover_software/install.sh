#!/usr/bin/env bash
# One command to set the AR-750 up on a fresh Raspberry Pi.
#
#     bash install.sh
#
# It is safe to run more than once. It never deletes your data, your settings
# or your password - those all live in data/ and are left alone.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

say() { printf "\n\033[1;33m==>\033[0m %s\n" "$1"; }

say "Checking where we are"
if [ -f /etc/rpi-issue ] || grep -qi raspberry /proc/device-tree/model 2>/dev/null; then
  ON_PI=1; echo "    Raspberry Pi. Installing everything."
else
  ON_PI=0; echo "    Not a Pi. Installing only what is needed to run the simulator."
fi

# Raspberry Pi OS "trixie" no longer gives the first user sudo without a
# password. Ask for it once, here, at the top - then keep it fresh in the
# background, because building pigpio alone can outlast sudo's 15 minutes
# and a second password prompt halfway down is the one nobody is watching for.
if ! sudo -n true 2>/dev/null; then
  echo ""
  echo "    The Pi needs its own password once, for sudo."
  echo "    Type it and press ENTER - nothing shows while you type."
  echo ""
  sudo -v
fi
# refresh sudo every 50 s, but look every 5 s whether the installer is still
# there, so this never outlives it by more than a moment
( while kill -0 "$$" 2>/dev/null; do
    sudo -n true 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$$" 2>/dev/null || exit 0
      sleep 5
    done
  done ) &
SUDO_KEEPALIVE=$!
trap 'kill "$SUDO_KEEPALIVE" 2>/dev/null || true' EXIT

say "System packages"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-pip python3-opencv python3-yaml
  if [ "$ON_PI" = "1" ]; then
    # One at a time, on purpose. apt-get refuses the WHOLE list if a single
    # name is missing, and Raspberry Pi OS renames and drops these between
    # releases - with set -e that used to stop the installer on line one.
    for pkg in i2c-tools python3-smbus build-essential python3-setuptools wget; do
      if sudo apt-get install -y -qq "$pkg" >/dev/null 2>&1; then
        echo "    $pkg"
      else
        echo "    $pkg - not in this release, skipped"
      fi
    done
  fi
else
  echo "    No apt here, skipping. Install python3, pip and opencv yourself."
fi

if [ "$ON_PI" = "1" ]; then
  say "Turning on the interfaces the rover needs"
  if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_i2c 0 && echo "    I2C on (ADS1115, IMU)"
  else
    echo "    raspi-config not found - turn I2C on yourself:"
    echo "      sudo raspi-config  ->  Interface Options  ->  I2C  ->  Yes"
  fi
  echo "    Camera: nothing to do, recent Pi OS finds it on its own."
  # The Raspberry Pi AI Camera (IMX500) needs its own firmware package
  # before it will stream. Fetched when one is plugged in, or when
  # config.yaml says one is coming (sensor: imx500) - so swapping the camera
  # later needs no second install. A Camera v2 does not need it.
  CAMS="$(timeout 20 rpicam-hello --list-cameras 2>/dev/null || true)"
  WANT_IMX500=0
  case "$CAMS" in *imx500*|*IMX500*) WANT_IMX500=1 ;; esac
  grep -Eq '^[[:space:]]*sensor:[[:space:]]*imx500' ar750/config.yaml 2>/dev/null && WANT_IMX500=1
  if [ "$WANT_IMX500" = "1" ]; then
    if dpkg -s imx500-all >/dev/null 2>&1; then
      echo "    AI Camera (IMX500) firmware: already here"
    elif sudo apt-get install -y -qq imx500-all >/dev/null 2>&1; then
      echo "    AI Camera (IMX500) firmware installed. Reboot once after fitting the camera."
    else
      echo "    AI Camera firmware did not install:  sudo apt install imx500-all"
    fi
  fi
  echo "    SBUS remote: only if you use it, add these to"
  echo "      /boot/firmware/config.txt   then reboot:"
  echo "         enable_uart=1"
  echo "         dtoverlay=disable-bt"
fi

say "Python packages"
PIPFLAGS="--quiet"
python3 -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" 2>/dev/null \
  && PIPFLAGS="$PIPFLAGS --break-system-packages" || true

# apt has already put OpenCV on as python3-opencv, which is a prebuilt wheel
# for this Pi. Letting pip install opencv-python-headless on top of it either
# takes an hour compiling or quietly shadows the fast one, so if cv2 already
# imports, that line comes out of the list.
REQ=requirements.txt
if python3 -c "import cv2" >/dev/null 2>&1; then
  echo "    OpenCV is already here from apt - not fetching it again"
  REQ="$(mktemp)"
  grep -v -i "^opencv" requirements.txt > "$REQ"
fi
# shellcheck disable=SC2086
pip3 install $PIPFLAGS -r "$REQ"
[ "$REQ" = "requirements.txt" ] || rm -f "$REQ"

if [ "$ON_PI" = "1" ]; then
  say "Raspberry Pi extras (motor board, servo board, ADC, receiver)"
  # shellcheck disable=SC2086
  pip3 install $PIPFLAGS \
    adafruit-circuitpython-pca9685 adafruit-circuitpython-ads1x15 \
    pyserial smbus2 || echo "    some extras failed, the rover will simulate those parts"
fi

if [ "$ON_PI" = "1" ]; then
  # Every motor, valve, servo, switch and sensor on the rover goes through
  # pigpio. If it is missing the rover does not fail - it quietly simulates,
  # the website looks fine, and the wheels never turn. So this is checked,
  # not assumed.
  say "pigpio - the library every motor, valve and sensor goes through"
  if command -v pigpiod >/dev/null 2>&1 || [ -x /usr/local/bin/pigpiod ]; then
    # the daemon is the slow half to get; the python client is one pip line
    echo "    already here"
    if ! python3 -c "import pigpio" >/dev/null 2>&1; then
      # shellcheck disable=SC2086
      pip3 install $PIPFLAGS pigpio >/dev/null 2>&1 \
        && echo "    python client added" \
        || echo "    python client did not install:  pip3 install --break-system-packages pigpio"
    fi
  elif sudo apt-get install -y -qq pigpio python3-pigpio >/dev/null 2>&1; then
    # Bookworm and older ship it
    echo "    installed from apt"
  else
    # Trixie dropped it from apt. The source still builds on a Pi 4 (not a
    # Pi 5, whose GPIO sits behind a different chip), so build it.
    echo "    not in apt on this release - building it from source (a few minutes)"
    PGTMP="$(mktemp -d)"
    # Chained with && on purpose. Inside "( ... ) || something" bash switches
    # set -e off for the whole group, so a failed download used to run on
    # into tar, cd and make regardless, and still report success.
    if ( cd "$PGTMP" \
         && wget -q https://github.com/joan2937/pigpio/archive/refs/tags/v79.tar.gz \
         && tar xzf v79.tar.gz 2>/dev/null \
         && cd pigpio-79 \
         && make -j4 >/dev/null 2>&1 ); then
      # make install also tries to install the python client with a setup.py
      # call newer Pythons dislike. The daemon is what matters here; the
      # client comes from pip just below.
      ( cd "$PGTMP/pigpio-79" && sudo make install >/dev/null 2>&1 ) || true
      echo "    built and installed"
    else
      echo "    THE BUILD FAILED. It downloads from github.com, so the Pi"
      echo "    needs the internet for this one step. Run install.sh again"
      echo "    once it has it - nothing else is lost."
    fi
    # "sudo make install" leaves root-owned files in the build folder, so a
    # plain rm cannot remove them - and under set -e that one failed rm used
    # to stop the whole installer here, before either service existed.
    rm -rf "$PGTMP" 2>/dev/null || sudo rm -rf "$PGTMP" 2>/dev/null || true
    # the python half is pure python and lives on PyPI
    # shellcheck disable=SC2086
    pip3 install $PIPFLAGS pigpio >/dev/null 2>&1 || true
  fi

  # A daemon built from source has no service, and the apt one ships with
  # "-l". On Trixie "-l" leaves the client unable to find the daemon at all
  # (error -2002), so both cases get the same unit, bound to localhost by
  # name. Only localhost: nothing else on the wifi should be able to drive
  # the rover's pins.
  PIGPIOD="$(command -v pigpiod || echo /usr/local/bin/pigpiod)"
  # pigpio's "make install" runs ldconfig as its LAST line, after a python
  # setup.py step that newer Pythons refuse - so it often never gets there,
  # and pigpiod then cannot find its own libpigpio.so. Run it here instead.
  sudo ldconfig 2>/dev/null || true
  # A rover that is already running holds a connection to pigpiod, and
  # restarting the daemon under it breaks that connection. Stop the rover
  # first; it is started again, with the new code, further down.
  sudo systemctl stop ar750 >/dev/null 2>&1 || true
  if [ -x "$PIGPIOD" ]; then
    sudo tee /etc/systemd/system/pigpiod.service >/dev/null <<EOF
[Unit]
Description=pigpio daemon, for the AR-750
After=network.target

[Service]
Type=forking
ExecStart=$PIGPIOD -n localhost
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable pigpiod >/dev/null 2>&1 || true
    sudo systemctl restart pigpiod || true
    sleep 2
  fi

  if python3 - <<'PYCHECK' 2>/dev/null
import sys, pigpio
pi = pigpio.pi()
ok = pi.connected
pi.stop()
sys.exit(0 if ok else 1)
PYCHECK
  then
    echo "    pigpiod is running and answering - the rover can drive its pins"
  else
    echo ""
    echo "    !!  pigpio is NOT working. The website will run, but the rover"
    echo "    !!  will only SIMULATE - no wheel, valve or servo will move."
    echo "    !!  Check:  systemctl status pigpiod"
    echo ""
    # put the daemon's own words in the log, so the next person does not
    # have to go and look
    systemctl status pigpiod --no-pager -n 15 2>&1 | sed 's/^/        /' || true
  fi
fi

say "Folders"
mkdir -p data/photos data/recordings data/logs models
chmod 700 data || true
# run as "sudo bash install.sh", these would belong to root and the rover,
# running as the ordinary user, could not write a single photo into them
[ -n "${SUDO_USER:-}" ] && chown -R "$SUDO_USER" data models 2>/dev/null || true

say "Fonts for working offline"
python3 scripts/fetch_fonts.py || echo "    skipped, the console will use system fonts"

if [ "$ON_PI" = "1" ]; then
  say "Starting it automatically when the Pi boots"
  # Who the rover runs as. $USER alone was not enough: under "set -u" an
  # unset USER stopped the installer dead right here, before the service
  # existed, and under "sudo bash install.sh" it made the rover run as root.
  RUNAS="${SUDO_USER:-${USER:-$(id -un)}}"
  echo "    runs as: $RUNAS"
  SERVICE=/etc/systemd/system/ar750.service
  sudo tee "$SERVICE" >/dev/null <<EOF
[Unit]
Description=AR-750 rover
After=network-online.target pigpiod.service
Wants=network-online.target pigpiod.service

[Service]
ExecStart=/usr/bin/python3 -m ar750.main
WorkingDirectory=$HERE
User=$RUNAS
Restart=on-failure
RestartSec=5
# without this, python holds its output in a buffer and journalctl -f shows
# nothing for minutes, which makes a rover that is working look dead
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable ar750 >/dev/null 2>&1 \
    || echo "    could not set it to start at boot:  sudo systemctl enable ar750"
  # Restart rather than start, so sending new code and running this again
  # actually puts the new code in charge. It comes up in IDLE: nothing moves
  # until someone asks it to.
  if sudo systemctl restart ar750; then
    echo "    Running now, and starts by itself every time the Pi boots."
  else
    echo "    Enabled, but it did not start:  journalctl -u ar750 -n 40"
  fi
fi

# set -e is on, so from here everything that can legitimately fail has to say
# so and carry on - an installer that aborts silently on its last line, after
# doing all the work, is worse than one that tells you what went wrong.
say "Checking it all imports"
if python3 -m compileall -q ar750 >/dev/null 2>&1; then
  echo "    fine"
else
  echo "    SOMETHING WILL NOT COMPILE - the lines above say which file"
fi

say "Running the safety tests"
set +e
python3 -m tests.test_decisions | tail -3
TESTS=${PIPESTATUS[0]}
set -e
if [ "$TESTS" != "0" ]; then
  echo "    SOME TESTS FAILED. Do not drive it until you know why:"
  echo "        python3 -m tests.test_decisions"
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
cat <<EOF

--------------------------------------------------------------------
 Ready.

   Try it with no hardware:   python3 -m ar750.main --sim
   Run it for real:           python3 -m ar750.main

   Then open   http://${IP:-<this-pi>}:8080
   Sign in with   admin / agrirover   and change it straight away.

 Is it up, and can it move?        bash scripts/status.sh
 Every page and button, end to end: bash scripts/selftest.sh
   (on a throwaway copy - none of your data is touched)

 Before the first drive, bench test each part:
   python3 scripts/bench.py wheels     (on blocks, wheels off the ground)
   python3 scripts/bench.py steering   (protractor on a front wheel)
   python3 scripts/bench.py rc         (check your channel map)
   python3 scripts/bench.py probe      (nothing underneath it)
   python3 scripts/bench.py boom       (nozzle sizing, before you buy nozzles)
--------------------------------------------------------------------
EOF
