#!/usr/bin/env bash
# Is the AR-750 up, and can it actually move?
#
#     bash scripts/status.sh
#
# One line per thing that matters. Read only - it starts, stops and changes
# nothing.
cd "$(dirname "$0")/.." || exit 1

echo "MODEL=$({ tr -d '\0' < /proc/device-tree/model; } 2>/dev/null)"
echo "OS=$(. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME")"
echo "IP=$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "SERVICE=$(systemctl is-active ar750 2>/dev/null)"
echo "STARTS_AT_BOOT=$(systemctl is-enabled ar750 2>/dev/null)"
echo "PIGPIOD=$(systemctl is-active pigpiod 2>/dev/null)"

python3 - <<'PY'
import urllib.request
try:
    body = urllib.request.urlopen("http://127.0.0.1:8080/api/health",
                                  timeout=6).read().decode()
    print("HEALTH=" + body)
except Exception as e:
    print("HEALTH=NONE  (" + str(e) + ")")
try:
    import pigpio
    p = pigpio.pi()
    print("PIGPIO_CONNECTED=" + str(bool(p.connected)))
    p.stop()
except Exception as e:
    print("PIGPIO_CONNECTED=False  (" + str(e) + ")")
PY

# A Pi 4 on too weak a supply works, mostly, and corrupts its SD card in the
# end. The firmware keeps count, so ask it rather than guess.
T=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)
if [ -z "$T" ]; then
  echo "POWER=unknown"
elif (( T & 0x1 )); then
  echo "POWER=UNDER-VOLTAGE RIGHT NOW - it needs a proper 5V 3A USB-C supply"
elif (( T & 0x10000 )); then
  echo "POWER=under-voltage has happened since boot - use a proper 5V 3A USB-C supply"
else
  echo "POWER=ok"
fi
echo "TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2)"
