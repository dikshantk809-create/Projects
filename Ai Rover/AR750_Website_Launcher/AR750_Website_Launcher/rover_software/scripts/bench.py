"""Bench tests. Run these on the Pi, one at a time, BEFORE the first drive.

    python3 scripts/bench.py wheels     # each wheel, one at a time, slowly
    python3 scripts/bench.py steering   # sweep the steering, check the angles
    python3 scripts/bench.py rc         # print what the remote is sending
    python3 scripts/bench.py adc        # print the raw sensor readings
    python3 scripts/bench.py pump       # 10 seconds of pump, to measure flow
    python3 scripts/bench.py cameras    # save one frame from each camera
    python3 scripts/bench.py encoders   # push the rover and watch it count
    python3 scripts/bench.py imu        # tilt it and watch the angle
    python3 scripts/bench.py range      # wave your hand in front of it
    python3 scripts/bench.py probe      # run the soil probe up and down
    python3 scripts/bench.py boom       # nozzle sizing and the spray rate maths

Put the rover ON BLOCKS with the wheels off the ground for the wheel test.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml                                          # noqa: E402

CFG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "ar750", "config.yaml")
cfg = yaml.safe_load(open(CFG))


def wheels():
    """Both axles (or both sides), on blocks. Also finds the duty they
    actually start at."""
    from ar750.hw.drive import Drive
    d = Drive(cfg["drive"], cfg["rover"])

    hb = cfg["drive"].get("hbridge", {})
    if d.skid:
        print("  driver           %s, tank style (left and right sides)" % d.driver.upper())
        print("  left side        GPIO %s fwd (IN1) / %s rev (IN2)"
              % (hb.get("left_fwd_pin", 12), hb.get("left_rev_pin", 19)))
        print("  right side       GPIO %s fwd (IN3) / %s rev (IN4)"
              % (hb.get("right_fwd_pin", 13), hb.get("right_rev_pin", 26)))
        print("  PWM              %s Hz, min_duty %.2f"
              % (hb.get("pwm_hz", 1000), hb.get("min_duty", 0.0)))
        if d.driver == "l298n":
            print("  Keep the ENA and ENB jumpers ON, and leave the 5V terminal empty.")
    elif d.hbridge:
        print("  driver           BTS7960 H bridge")
        print("  front            GPIO %s fwd / %s rev"
              % (hb.get("front_fwd_pin", 12), hb.get("front_rev_pin", 19)))
        print("  rear             GPIO %s fwd / %s rev"
              % (hb.get("rear_fwd_pin", 13), hb.get("rear_rev_pin", 10)))
        print("  PWM              %s Hz, min_duty %.2f"
              % (hb.get("pwm_hz", 1000), hb.get("min_duty", 0.0)))
        print("  R_EN and L_EN must be tied to 3.3 V or nothing will move.")
    else:
        esc = cfg["drive"].get("esc", {})
        print("  driver           brushed ESC, servo pulse")
        print("  front / rear     GPIO %s / %s"
              % (esc.get("front_pin", 12), esc.get("rear_pin", 13)))
        print("  arming           %.1f s of %d us before it will move"
              % (d.arm_seconds, esc.get("neutral_us", 1500)))
    print("  mode             %s"
          % ("SIMULATION - " + (d.reason or "no hardware") if d.sim
             else "real hardware"))
    print()
    print("  ALL FOUR WHEELS OFF THE GROUND? Starting in 3 seconds.")
    time.sleep(3)

    def hold(label, f, secs=1.5, turn=0.0):
        print("   %-18s" % label, end="", flush=True)
        d.set_throttle(f)
        d.set_turn(turn)
        t_end = time.time() + secs
        while time.time() < t_end:
            d.tick()
            time.sleep(0.02)
        s = d.snapshot()
        if d.skid:
            print("left %5.0f%%  right %5.0f%%"
                  % (s["left_duty"] * 100, s["right_duty"] * 100))
        elif d.hbridge:
            print("front %5.0f%%  rear %5.0f%%"
                  % (s["front_duty"] * 100, s["rear_duty"] * 100))
        else:
            print("front %4d us  rear %4d us" % (s["front_us"], s["rear_us"]))
        d.set_throttle(0.0)
        d.set_turn(0.0)
        for _ in range(30):
            d.tick()
            time.sleep(0.02)

    try:
        while not d.armed:
            d.tick()
            time.sleep(0.05)
        for label, f in (("forward, slow", 0.25), ("forward, faster", 0.5),
                         ("stop", 0.0), ("back, slow", -0.25),
                         ("back, faster", -0.5)):
            hold(label, f)
        if d.skid:
            # tank style: it should spin, the two sides going opposite ways
            hold("spin right", 0.0, turn=0.6)
            hold("spin left", 0.0, turn=-0.6)

        print()
        print("  Creeping up to find where the motors actually start turning.")
        print("  WATCH THE WHEELS and note the first number that moves them.")
        for pct in range(5, 55, 5):
            print("   %3d%%" % pct, end="", flush=True)
            d.set_throttle(pct / 100.0)
            t_end = time.time() + 1.2
            while time.time() < t_end:
                d.tick()
                time.sleep(0.02)
            print("  ...")
        d.set_throttle(0.0)
        for _ in range(40):
            d.tick()
            time.sleep(0.02)

        print()
        if d.skid:
            print("  If one side ran backwards on 'forward', swap that side's two")
            print("  motor wires on the L298N (or set invert_left / invert_right).")
            print("  If 'spin right' spun it left, swap the left and right pairs.")
        else:
            print("  If an axle ran backwards, set invert_front or invert_rear in")
            print("  config.yaml. Do NOT swap the motor wires.")
        if d.hbridge:
            print("  Put the percentage where they started turning into")
            print("  drive.hbridge.min_duty as a fraction - 15% is 0.15.")
        else:
            print("  If nothing moved at all, the ESC never armed. Most want")
            print("  to see neutral for a couple of seconds at power-on.")
    finally:
        d.release()


def steering():
    """Sweep the steering and check what the wheels actually do."""
    from ar750.hw.drive import Drive
    from ar750.hw.ackermann import Steering
    d = Drive(cfg["drive"], cfg["rover"])
    st = Steering(cfg["drive"]["steering"], cfg["rover"])
    print("simulation" if d.sim else "real servo", " ", d.reason)
    print()
    info = st.describe()
    for k, v in info.items():
        print("  %-22s %s" % (k, v))
    print()
    print("  WHEELS OFF THE GROUND. Sweeping in 3 seconds.")
    time.sleep(3)
    try:
        for target in (0, 10, 20, st.wheel_max, 0, -10, -20, -st.wheel_max, 0):
            sv = st.servo_for_wheel(target)
            d.write_servo(sv)
            R = st.turn_radius(target)
            print("  wheels %6.1f deg -> servo %6.1f deg -> radius %s"
                  % (target, sv, ("%.0f mm" % R) if R else "straight ahead"))
            time.sleep(1.2)
        print()
        print("  Put a protractor against a front wheel at full lock and")
        print("  compare. If the real angle differs, put the measured number")
        print("  into drive.steering.max_wheel_deg and everything else follows.")
        print("  If it does not come back to straight, adjust trim_us.")
    finally:
        d.centre_steering()
        time.sleep(0.5)
        d.release()


def probe():
    """Run the soil probe down and up, watching the limit switches."""
    from ar750.hw.probe import SoilProbe
    p = SoilProbe(cfg)
    if p.sim:
        print("probe not connected: %s" % p.reason)
        return
    print("Nothing under the probe? Starting in 3 seconds.")
    time.sleep(3)
    try:
        print("  homing (up)...")
        print("   ", p.home()[1])
        print("  going down...")
        t0 = time.time()
        ok, msg = p.deploy()
        print("   ", msg, " took %.1f s" % (time.time() - t0))
        time.sleep(1)
        print("  coming back up...")
        t0 = time.time()
        ok, msg = p.retract()
        print("   ", msg, " took %.1f s" % (time.time() - t0))
        print()
        print("  Both legs should take about the same time. If one is much")
        print("  slower the screw needs greasing or the nut is tight.")
        print("  If it says jammed, check the limit switch actually closes.")
    finally:
        p.close()


def boom():
    """Nozzle sizing. Do this BEFORE you buy nozzles."""
    from ar750.hw.boom import Boom

    class FakeState:
        estop = False
        spray_armed = True
        telemetry = type("t", (), {"tank_ml": 0, "tank_pct": 0})()
        def set(self, **kw): pass

    b = Boom(cfg, FakeState())
    speed = float(cfg["rover"]["max_speed_mps"]) * float(
        cfg["ai"]["row"].get("base_speed", 0.35))
    print("  nozzles          %d at %.0f mm spacing" % (b.nozzles, b.nozzle_spacing_m * 1000))
    print("  fitted flow      %.0f ml/min each" % b.ml_per_min_per_nozzle)
    print("  row speed        %.2f m/s  (%.2f km/h)" % (speed, speed * 3.6))
    print("  target rate      %.0f litres per hectare" % b.target_l_per_ha)
    print()
    full = b.rate_l_per_ha(speed, ["centre"])
    print("  wide open it would put down %.0f l/ha" % full)
    want = b.right_nozzle_ml_min(speed_mps=speed)
    print("  to hit the target WITHOUT pulsing you would need %.0f ml/min nozzles" % want)
    d, note = b.duty_for_rate(b.target_l_per_ha, speed)
    print("  with the nozzles you have, the valves pulse at %.0f%% duty" % (d * 100))
    if note:
        print("  NOTE: %s" % note)
    print()
    print("  rate against speed, with the nozzles you have:")
    for mps in (0.15, 0.25, 0.35, 0.5, 0.75, 1.0):
        r = b.rate_l_per_ha(mps, ["centre"])
        dd, _ = b.duty_for_rate(b.target_l_per_ha, mps)
        print("    %.2f m/s -> %6.0f l/ha full open, %4.0f%% duty for target"
              % (mps, r, dd * 100))
    print()
    print("  MEASURE YOUR REAL FLOW: hold a jug under one nozzle for a minute")
    print("  at working pressure, and put the millilitres into config.yaml as")
    print("  boom.ml_per_min_per_nozzle. Every number above depends on it.")


def rc():
    from ar750.hw.rc import RCReceiver
    r = RCReceiver(cfg["rc"])
    print("protocol:", cfg["rc"].get("protocol"), "  ctrl-C to stop\n")
    names = cfg["rc"].get("map", {})
    try:
        while True:
            live = "LIVE" if r.live else "no signal"
            raw = " ".join("%+.2f" % v for v in r.snapshot()[:6])
            named = "  ".join("%s %+.2f" % (k, r.channel(k)) for k in names)
            print("\r%-9s  [%s]  %s   " % (live, raw, named), end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
    finally:
        r.close()


def adc():
    from ar750.hw.io import Analog
    a = Analog(cfg["sensors"])
    print("simulation" if a.sim else "real ADS1115", "  ctrl-C to stop\n")
    try:
        while True:
            print("\rbattery %5.2f V   soil %s   tank %s      "
                  % (a.battery_volts() or 0.0,
                     "%.0f%%" % a.soil_percent() if a.soil_percent() is not None else "—",
                     "%.0f%%" % a.tank_percent() if a.tank_percent() is not None else "—"),
                  end="", flush=True)
            time.sleep(0.3)
    except KeyboardInterrupt:
        print()


def pump():
    """Run the pump for 10 seconds into a measuring cup, then do the sum."""
    from ar750.hw.io import Outputs
    o = Outputs(cfg["spray"], cfg["lamps"])
    print("Put the nozzle in a measuring cup. 10 seconds of pump in 5.")
    time.sleep(5)
    o.set("front", True)
    o.set("pump", True)
    for i in range(10, 0, -1):
        print("\r  %2d" % i, end="", flush=True)
        time.sleep(1)
    o.set("pump", False)
    o.set("front", False)
    o.close()
    print("\n\nMeasure what came out, in ml, and divide by 10.")
    print("Put that number in config.yaml as ml_per_second.")
    print("The dose it puts on a plant is only as good as this number.")


def cameras():
    import cv2
    from ar750.hw.camera import Camera
    for name in ("front", "arm"):
        c = Camera(name, cfg["cameras"][name])
        time.sleep(1.5)
        f = c.frame()
        if f is None:
            print(name, "gave no picture")
        else:
            out = "bench_%s.jpg" % name
            cv2.imwrite(out, f)
            print("%-6s %dx%d  saved %s%s" % (name, f.shape[1], f.shape[0], out,
                                              "  (simulated)" if c.sim else ""))
        c.close()


def encoders():
    """Push the rover along by hand and watch the counts."""
    from ar750.hw.encoders import Encoders
    e = Encoders(cfg["drive"], cfg["rover"])
    if e.sim:
        print("no encoders: %s" % e.reason)
        print("fit them, then set drive.encoder.enabled: true in config.yaml")
        return
    print("Push the rover forward one metre, slowly. ctrl-C to stop.\n")
    try:
        while True:
            e.read()
            print("\r  left %7.3f m   right %7.3f m   %5.2f / %5.2f m/s   "
                  % (e.left_m, e.right_m, e.left_mps, e.right_mps),
                  end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n\nBoth numbers should match the real distance you pushed it.")
        print("If they are out by the same ratio, fix ticks_per_rev:")
        print("  new value = old value x (what it said / what it really was)")
        print("If one wheel reads backwards, swap its A and B wires.")
    finally:
        e.close()


def imu():
    from ar750.hw.imu import IMU
    m = IMU(cfg["sensors"])
    if m.sim:
        print("no tilt sensor: %s" % m.reason)
        print("fit an MPU6050 on the I2C bus, then set sensors.imu.enabled: true")
        return
    print("Tilt the rover side to side, then nose up. ctrl-C to stop.\n")
    try:
        while True:
            d = m.read() or {}
            print("\r  tilt %5.1f   pitch %6.1f   roll %6.1f   heading %5.1f   "
                  % (d.get("tilt_deg", 0), d.get("pitch_deg", 0),
                     d.get("roll_deg", 0), d.get("heading_deg", 0)),
                  end="", flush=True)
            time.sleep(0.12)
    except KeyboardInterrupt:
        print("\n\nOn a level floor tilt should sit under a degree or two.")
        print("If it does not, the sensor is not mounted flat.")
    finally:
        m.close()


def range_():
    from ar750.hw.rangefinder import RangeFinder
    r = RangeFinder(cfg["sensors"])
    if r.sim:
        print("no range sensor: %s" % r.reason)
        print("fit one, then set sensors.range_front.enabled: true")
        return
    stop = float(cfg["sensors"]["range_front"].get("stop_cm", 35))
    print("Hold your hand in front of it and move it in and out. ctrl-C to stop.\n")
    try:
        while True:
            d = r.read()
            bar = "#" * int(min(50, (d or 0) / 4))
            print("\r  %6s cm  %-52s %s" % (d if d else "----", bar,
                  "WOULD STOP" if r.blocked() else ""), end="", flush=True)
            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\n\nIt stops the rover below %.0f cm." % stop)
        print("Readings that jump about mean the echo pin divider is wrong,")
        print("or the sensor is pointing at something soft.")
    finally:
        r.close()


JOBS = {"wheels": wheels, "steering": steering, "rc": rc, "adc": adc,
        "pump": pump, "cameras": cameras, "encoders": encoders, "imu": imu,
        "range": range_, "probe": probe, "boom": boom}

if __name__ == "__main__":
    job = sys.argv[1] if len(sys.argv) > 1 else ""
    if job not in JOBS:
        print(__doc__)
        raise SystemExit(1)
    JOBS[job]()
