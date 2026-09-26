"""Tests you can run on a laptop, no rover and no hardware needed.

    python3 -m tests.test_decisions

It checks the parts that decide whether to put chemicals on a plant, because
those are the parts that must never be wrong. It does not need pytest.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ar750.ai import treatment as tx           # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok    %s" % name)
    else:
        FAIL += 1
        print("  FAIL  %s  %s" % (name, extra))


def _axle_outputs(d):
    """What each axle (or, on a skid rover, each side) is actually being
    told, whichever driver is fitted."""
    if getattr(d, "hbridge", getattr(d, "driver", "esc") == "bts7960"):
        return d.front.duty, d.rear.duty
    return d.front.us, d.rear.us


# ------------------------------------------------------------------ treatment
print("\ntreatment table")

p = tx.plan("healthy", 0.99)
check("a healthy plant is left alone", p["action"] == "none" and p["healthy"])

p = tx.plan("not_checked", 0.0)
check("no model is not the same as healthy", not p["healthy"])
check("no model asks you", p["action"] == "needs_you")
check("no model never sprays", p["dose_ml"] == 0.0)

p = tx.plan("unknown", 0.2)
check("unsure is not healthy", not p["healthy"] and p["action"] == "needs_you")

p = tx.plan("tomato_early_blight", 0.95, auto_spray_conf=0.85)
check("sure about blight, may spray", p["action"] == "spray")
check("blight dose is carried", p["dose_ml"] > 0)
check("blight has a waiting time", p["phi_days"] > 0)

p = tx.plan("tomato_early_blight", 0.70, auto_spray_conf=0.85)
check("unsure about blight, asks first", p["action"] == "needs_you")
check("the dose is still quoted so you can say yes", p["dose_ml"] > 0)

p = tx.plan("tomato_mosaic_virus", 0.99)
check("a virus is never sprayed", p["action"] == "needs_you" and p["dose_ml"] == 0)

p = tx.plan("water_stress", 0.9, soil_pct=70.0)
check("wet soil vetoes thirsty", p["label"] == "healthy")
p = tx.plan("water_stress", 0.9, soil_pct=12.0)
check("dry soil keeps thirsty", p["label"] == "water_stress")

p = tx.plan("weed", 0.9)
check("a weed is pulled, not sprayed", p["action"] == "weed_pull")

p = tx.plan("something_the_model_invented", 0.9)
check("an unknown label falls back safely",
      p["label"] == "unknown" and p["dose_ml"] == 0.0)

for name, t in tx.TREATMENTS.items():
    if t.spray_ok:
        check("%s names a product" % name, bool(t.product))
        check("%s gives a dose" % name, bool(t.dose) and t.dose_ml_per_plant > 0)
        if t.kind in ("fungal", "bacterial", "pest"):
            # a pesticide always has a wait before you can pick the crop
            check("%s has a waiting time" % name, t.phi_days > 0)

# --------------------------------------------------------------------- rover
print("\nrover, in simulation")

import yaml                                        # noqa: E402
from ar750.rover import Rover                  # noqa: E402
from ar750.core.state import Mode              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(os.path.dirname(HERE), "ar750", "config.yaml")
cfg = yaml.safe_load(open(BASE))
cfg["rover"]["sim"] = True
cfg["ai"]["inspect_seconds"] = 0.2
tmp = os.path.join(HERE, "_test_config.yaml")
yaml.safe_dump(cfg, open(tmp, "w"))

r = Rover(tmp)
time.sleep(0.5)


class FakeAI:
    """Stands in for the TFLite model so the decisions can be tested."""
    ready = True
    reason = ""

    def __init__(self, label, conf):
        self.label, self.conf = label, conf

    def classify(self, img):
        return self.label, self.conf


try:
    check("starts stopped", r.state.mode == Mode.IDLE)
    check("spray is locked at boot", not r.state.spray_armed)
    check("the steering starts straight", abs(r.state.steer_deg) < 0.01)

    ok, msg = r.spray_sections(["centre"], 1.0)
    check("cannot spray while the pump is locked", not ok, msg)

    r.set_spray_armed(True)
    ok, msg = r.spray_sections(["centre"], 1.0)
    check("cannot spray while standing still", not ok, msg)

    r.estop("test")
    ok, msg = r.spray_sections(["centre"], 1.0)
    check("cannot spray during an emergency stop", not ok, msg)

    r.set_mode(Mode.MANUAL)
    check("cannot leave IDLE while stopped", r.state.mode != Mode.MANUAL)
    r.clear_estop()
    check("can leave IDLE once cleared", r.set_mode(Mode.MANUAL))

    # an ESC will not move until it has seen neutral for a moment, which is
    # real behaviour and not something to test around
    for _ in range(80):
        if r.drive_hw.armed:
            break
        time.sleep(0.05)
    check("the motor driver is ready", r.drive_hw.armed)

    # the website has to keep asking, that is the dead man rule
    for _ in range(14):
        r.web_drive(1.0, 0.0)
        time.sleep(0.05)
    check("it drives", r.state.telemetry.speed_mps > 0)
    _f, _r = _axle_outputs(r.drive_hw)
    check("both axles get the same command", _f == _r, "%s vs %s" % (_f, _r))
    d0 = r.state.telemetry.distance_m
    for _ in range(14):
        r.web_drive(1.0, 0.0)
        time.sleep(0.05)
    check("the trip meter counts", r.state.telemetry.distance_m > d0,
          "%s -> %s" % (d0, r.state.telemetry.distance_m))
    time.sleep(1.2)
    check("it stops itself when the website goes quiet",
          r.state.telemetry.speed_mps == 0)

    for _ in range(10):
        r.web_drive(0.6, -1.0)
        time.sleep(0.05)
    if getattr(r.drive_hw, "skid", False):
        # tank style: it turns by running one side faster than the other
        check("the stick turns it: the left side slows for a left turn",
              r.drive_hw.left_out < r.drive_hw.right_out,
              "L %.2f  R %.2f" % (r.drive_hw.left_out, r.drive_hw.right_out))
        check("nothing is ever sent to the steering pin",
              r.drive_hw.steer.pi is None)
        for _ in range(12):
            r.web_drive(0.0, 1.0)
            time.sleep(0.05)
        check("sideways on its own spins it on the spot",
              r.drive_hw.left_out > 0 > r.drive_hw.right_out,
              "L %.2f  R %.2f" % (r.drive_hw.left_out, r.drive_hw.right_out))
    else:
        check("the stick points the wheels", r.state.steer_deg < -10,
              "%.1f deg" % r.state.steer_deg)
        check("and that gives a turning radius",
              r.state.telemetry.turn_radius_mm is not None)
        check("the steering servo moved off centre",
              r.drive_hw.steer.us != r.drive_hw.servo_centre)

    r.set_mode(Mode.IDLE)
    time.sleep(0.3)
    check("IDLE stops the wheels", r.state.drive_throttle == 0
          and r.state.telemetry.speed_mps == 0)

    # ---- a confident disease, auto spray OFF: it must ask, not act
    r.classifier = FakeAI("tomato_early_blight", 0.97)
    r.set_auto_spray(False)
    r.set_spray_armed(True)
    r.set_mode(Mode.AUTO)
    r.mission.start(1)
    for _ in range(400):
        time.sleep(0.05)
        if r.state.pending:
            break
    q = (r.state.pending or {}).get("question", "")
    check("asks before spraying when auto spray is off", bool(r.state.pending))
    check("the question names the product", "Mancozeb" in q, q)
    check("the question names a boom section",
          any(w in q for w in ("left", "centre", "right")), q)
    check("the question gives the waiting time", "days" in q, q)
    r.mission.stop("test")

    # ---- a virus: never sprayed, whatever the switches say
    r.classifier = FakeAI("tomato_mosaic_virus", 0.99)
    r.set_auto_spray(True)
    r.set_mode(Mode.AUTO)
    r.mission.start(1)
    for _ in range(400):
        time.sleep(0.05)
        if r.state.pending:
            break
    check("a virus still asks, even with auto spray on", bool(r.state.pending))
    check("and the last run's question did not carry over",
          "mosaic" in (r.state.pending or {}).get("title", "").lower()
          or "virus" in (r.state.pending or {}).get("question", "").lower(),
          str((r.state.pending or {}).get("title")))
    q = (r.state.pending or {}).get("question", "")
    check("and it says to pull it by hand, because there is no gripper",
          "hand" in q or "gripper" in q, q)
    used = r.boom.used_ml
    r.mission.answer(True)
    time.sleep(0.5)
    check("nothing is sprayed on a virus", r.boom.used_ml == used)
    r.mission.stop("test")

    # ---- the session limit
    r.set_spray_armed(True)
    r.boom.used_ml = float(r.boom.max_ml_per_session) + 1
    ok, why = r.boom.can_spray(["centre"], 0.3)
    check("cannot exceed the session limit", not ok, why)
    r.boom.used_ml = 0.0

finally:
    r.shutdown()
    try:
        os.remove(tmp)
    except OSError:
        pass

# --------------------------------------------------------------- steering
print("\nsteering, because this one drives like a car")

from ar750.hw.ackermann import Steering                   # noqa: E402

full = yaml.safe_load(open(BASE))
st = Steering(full["drive"]["steering"], full["rover"])
d = st.describe()
check("it knows it cannot spin on the spot", d["can_spin_on_the_spot"] is False)
check("full lock is a believable angle", 10 < d["max_wheel_deg"] < 45,
      str(d["max_wheel_deg"]))
check("the turning circle is worked out, not guessed",
      2000 < d["turning_circle_mm"] < 5000, str(d["turning_circle_mm"]))
check("straight ahead has no turning radius", st.turn_radius(0) is None)
check("more lock means a tighter circle",
      st.turn_radius(20) < st.turn_radius(10) < st.turn_radius(5))
check("the inner wheel turns more than the outer",
      st.ackermann(20)[0] > st.ackermann(20)[1])

worst = 0.0
for want in [x * 0.5 for x in range(0, int(d["max_wheel_deg"] * 2) + 1)]:
    sv = st.servo_for_wheel(want)
    got = st.wheel_angle(sv)
    if got is not None:
        worst = max(worst, abs(abs(got) - want))
check("asking for a wheel angle gives that wheel angle", worst < 0.2,
      "worst error %.2f deg" % worst)
check("it will not ask the servo for more than it has",
      abs(st.servo_for_wheel(90)) <= st.servo_max + 0.01)
check("a stick at full deflection is full lock",
      abs(st.stick_to_wheel(1.0) - st.wheel_max) < 0.01)
check("turning left is a positive yaw rate", st.yaw_rate_dps(0.4, 20) > 0)
check("and turning right is negative", st.yaw_rate_dps(0.4, -20) < 0)
check("standing still it does not rotate", st.yaw_rate_dps(0.0, 20) == 0)

# ------------------------------------------------------------- the spray boom
print("\nthe spray boom")

from ar750.hw.boom import Boom                            # noqa: E402


class FakeState:
    estop = False
    spray_armed = True
    telemetry = type("t", (), {"tank_ml": 0.0, "tank_pct": 0.0})()

    def set(self, **kw):
        pass


boom = Boom(full, FakeState())
check("standing still is not a spray rate", boom.rate_l_per_ha(0.0) is None)
r1 = boom.rate_l_per_ha(0.2, ["centre"])
r2 = boom.rate_l_per_ha(0.4, ["centre"])
check("driving twice as fast halves the rate", abs(r1 - 2 * r2) < 1.0,
      "%.0f vs %.0f" % (r1, r2))
dd, note = boom.duty_for_rate(200, 0.35)
check("it works out a valve duty", 0 < dd <= 1.0, str(dd))
slow, note = boom.duty_for_rate(200, 0.10)
check("and warns when the duty gets too low to spray evenly",
      slow < boom.min_duty and "stripey" in note, note)
dd2, note2 = boom.duty_for_rate(99999, 0.35)
check("it says so when even wide open is not enough", dd2 == 1.0 and "slow down" in note2)
check("it can say what nozzle you should have bought",
      10 < boom.right_nozzle_ml_min(200, 0.35) < 200,
      "%.0f ml/min" % boom.right_nozzle_ml_min(200, 0.35))

ok, why = boom.can_spray(["centre"], 0.0)
check("it refuses to spray while standing still", not ok, why)
ok, why = boom.can_spray(["nowhere"], 0.3)
check("it refuses a boom section that does not exist", not ok, why)
FakeState.spray_armed = False
ok, why = boom.can_spray(["centre"], 0.3)
check("it refuses when the pump is not armed", not ok, why)
FakeState.spray_armed = True
FakeState.estop = True
ok, why = boom.can_spray(["centre"], 0.3)
check("and during an emergency stop", not ok, why)
FakeState.estop = False
check("the centre section is one nozzle", boom.nozzle_count(["centre"]) == 1)
check("a side section is two", boom.nozzle_count(["left"]) == 2)
check("all three sections is all five nozzles",
      boom.nozzle_count(["left", "centre", "right"]) == 5)

# ------------------------------------------------------------- the soil probe
print("\nthe soil probe")

from ar750.hw.probe import SoilProbe                      # noqa: E402

pr = SoilProbe(full, sim=True)
ok, msg = pr.deploy()
check("it can be sent down", ok and pr.state == "down", msg)
ok, msg = pr.retract()
check("and brought back up", ok and pr.state == "up", msg)
val, msg = pr.read_soil(lambda: 42.0)
check("a reading is taken with the spike in the ground", val == 42.0, msg)
check("and it comes back up afterwards", pr.state == "up")
check("it is never left down after a read", not pr.busy)

# ---------------------------------------------------------------- the battery
print("\nthe battery gauge knows which pack you fitted")

from ar750.hw.io import battery_percent, CHEM, SimSensors     # noqa: E402

check("a full 12 V lead acid brick reads full",
      battery_percent(12.72, 6, "lead") > 95,
      "%.0f%%" % battery_percent(12.72, 6, "lead"))
check("a flat one reads empty",
      battery_percent(11.6, 6, "lead") < 10,
      "%.0f%%" % battery_percent(11.6, 6, "lead"))
check("the lead acid gauge is not the lithium one",
      abs(battery_percent(12.72, 6, "lead")
          - battery_percent(12.72, 6, "lipo")) > 20)
check("a charged LiFePO4 pack reads full",
      battery_percent(14.4, 4, "lifepo4") > 95,
      "%.0f%%" % battery_percent(14.4, 4, "lifepo4"))
check("a charged 4S LiPo reads full",
      battery_percent(16.6, 4, "lipo") > 95,
      "%.0f%%" % battery_percent(16.6, 4, "lipo"))

# the simulated pack must start ABOVE the cut-out, or the rover never moves
_bat = cfg["safety"]["battery"]
_sim_v = SimSensors(cfg).battery_volts()
check("the simulated pack starts above the cut-out",
      _sim_v > float(_bat["stop_v"]),
      "%.2f V vs stop_v %.2f" % (_sim_v, _bat["stop_v"]))
check("and above the warning too",
      _sim_v > float(_bat["warn_v"]),
      "%.2f V vs warn_v %.2f" % (_sim_v, _bat["warn_v"]))
check("the config's chemistry is one the code knows",
      str(_bat.get("chemistry", "lead")).lower() in CHEM)


# ------------------------------------------------------ both motor drivers
print("\nthe motor driver, both kinds")

from ar750.hw.drive import Drive                          # noqa: E402
import copy                                               # noqa: E402

_dcfg = copy.deepcopy(cfg["drive"])

# --- the BTS7960 H bridge, on the car layout (axles plus a steering servo)
_dcfg["driver"] = "bts7960"
_dcfg["layout"] = "car"
_dcfg["hbridge"] = dict(_dcfg.get("hbridge", {}))
_dcfg["hbridge"]["min_duty"] = 0.0
hb = Drive(_dcfg, cfg["rover"], sim=True)
check("an H bridge needs no arming", hb.armed and hb.arm_seconds == 0.0)

hb.front.write_frac(0.0)
check("stopped means both pins low", hb.front.duty == 0.0)
hb.front.write_frac(0.6)
check("forward drives one pin", abs(hb.front.duty - 0.6) < 1e-6)
hb.front.write_frac(-0.6)
check("back drives the other one", abs(hb.front.duty + 0.6) < 1e-6)
hb.front.write_frac(2.0)
check("it cannot be asked for more than full", hb.front.duty == 1.0)
hb.front.off()
check("off coasts, it does not brake", hb.front.duty == 0.0)

# deadband compensation: a tiny ask must still clear the motor's stiction
_dcfg["hbridge"]["min_duty"] = 0.20
hb2 = Drive(_dcfg, cfg["rover"], sim=True)
hb2.front.write_frac(0.01)
check("min_duty lifts a small ask over the motor's stiction",
      hb2.front.duty >= 0.20, "%.3f" % hb2.front.duty)
hb2.front.write_frac(1.0)
check("min_duty does not cost you the top end",
      abs(hb2.front.duty - 1.0) < 1e-6)
hb2.front.write_frac(0.0)
check("zero is still a real zero", hb2.front.duty == 0.0)

# both axles always agree, whichever driver
hb.set_throttle(0.8)
for _ in range(60):
    hb.tick()
check("both axles still get the same command",
      hb.front.duty == hb.rear.duty)
snap = hb.snapshot()
check("the dashboard is told which driver is fitted",
      snap.get("driver") == "bts7960" and "front_duty" in snap)

# --- the ESC, still there for anyone who built it that way
_ecfg = copy.deepcopy(cfg["drive"])
_ecfg["driver"] = "esc"
_ecfg["layout"] = "car"
ec = Drive(_ecfg, cfg["rover"], sim=True)
check("an ESC still has to arm", ec.arm_seconds > 0)
ec.front.write_frac(0.0)
check("neutral is the middle of the pulse",
      ec.front.us == _ecfg["esc"]["neutral_us"])
ec.front.write_frac(1.0)
check("full forward is the top of the pulse",
      ec.front.us == _ecfg["esc"]["max_us"])
ec.front.write_frac(-1.0)
check("full back is the bottom of the pulse",
      ec.front.us == _ecfg["esc"]["min_us"])
check("the dashboard gets pulses for an ESC",
      ec.snapshot().get("driver") == "esc" and "front_us" in ec.snapshot())

# --- the L298N on a skid (tank style) rover: the small build
_scfg = copy.deepcopy(cfg["drive"])
_scfg["driver"] = "l298n"
_scfg["layout"] = "skid"
_scfg["hbridge"] = dict(_scfg.get("hbridge", {}))
_scfg["hbridge"]["min_duty"] = 0.0
_scfg["ramp_per_tick"] = 1.0
sk = Drive(_scfg, cfg["rover"], sim=True)
check("an L298N needs no arming either", sk.armed and sk.arm_seconds == 0.0)
sk.set_throttle(0.5); sk.set_turn(0.0); sk.tick()
check("straight ahead: both sides the same", sk.left_out == sk.right_out == 0.5,
      "L %.2f R %.2f" % (sk.left_out, sk.right_out))
sk.set_throttle(0.0); sk.set_turn(1.0)
for _ in range(4):
    sk.tick()
check("a pure turn spins it: the sides go opposite ways",
      sk.left_out > 0 > sk.right_out and abs(sk.left_out + sk.right_out) < 1e-9)
sk.set_throttle(1.0); sk.set_turn(1.0)
for _ in range(4):
    sk.tick()
check("flat out and turning, nothing is asked past full",
      max(abs(sk.left_out), abs(sk.right_out)) <= 1.0 and sk.left_out > sk.right_out)
sk.stop()
check("stop means both sides stop", sk.left_out == 0 and sk.right_out == 0)
check("the dashboard is told it is a skid rover",
      sk.snapshot().get("layout") == "skid" and "left_duty" in sk.snapshot())
_scfg["invert_left"] = True
sk2 = Drive(_scfg, cfg["rover"], sim=True)
sk2.set_throttle(0.5); sk2.tick()
check("invert_left flips only the left side's wires",
      sk2.front.duty < 0 < sk2.rear.duty, "%.2f %.2f" % (sk2.front.duty, sk2.rear.duty))
try:
    Drive(dict(_scfg, driver="esc"), cfg["rover"], sim=True)
    _bad_skid = False
except ValueError:
    _bad_skid = True
check("skid on an ESC is refused - it needs an H bridge", _bad_skid)

# a driver nobody has built should not silently do nothing
try:
    Drive({"driver": "nonsense"}, cfg["rover"], sim=True)
    _bad = False
except ValueError:
    _bad = True
check("a driver name it does not know is refused, not ignored", _bad)


# ------------------------------------------------------- nothing is a dead end
print("\nevery setting the page shows is actually read")

import subprocess                                       # noqa: E402
from ar750.core.settings import EDITABLE            # noqa: E402

src = subprocess.run(
    ["grep", "-rh", "--include=*.py", "-e", "", os.path.join(
        os.path.dirname(HERE), "ar750")],
    capture_output=True, text=True).stdout
dead = []
for key in EDITABLE:
    leaf = key.split(".")[-1]
    # it counts as used if something outside settings.py names it
    uses = [ln for ln in src.splitlines()
            if leaf in ln and "EDITABLE" not in ln and "HARD" not in ln]
    if len(uses) < 2:
        dead.append(key)
check("no setting on the page is ignored by the code", not dead, str(dead))

print("\n%d passed, %d failed\n" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
