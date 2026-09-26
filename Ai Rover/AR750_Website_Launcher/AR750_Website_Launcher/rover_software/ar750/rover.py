"""The AR-750 itself. Owns the hardware, runs the control loop, holds the modes.

Control loop, 50 times a second:

  1. read the sensors
  2. check the safety rules, and stop everything if one is broken
  3. read the remote
  4. work out the mode
  5. in MANUAL  - the sticks drive the wheels and point the steering
     in AUTO    - the mission state machine drives
     in HOLD    - hold still, keep the telemetry alive
  6. push throttle out to both ESCs and the angle out to the steering servo

The remote always wins. Touch a stick in AUTO and it drops to MANUAL.

THE ONE THING TO KEEP IN MIND: this machine steers like a car. Throttle and
steering are two separate things, it cannot turn on the spot, and it needs
about 2.8 m to come round. Nothing here ever tries to make it pirouette.
"""
from __future__ import annotations

import math
import os
import threading
import time
from typing import Optional

import yaml

from .core.state import Mode, RoverState
from .core.settings import Settings
from .core.db import DB
from .core.notify import Notifier
from .hw.drive import Drive
from .hw.ackermann import Steering
from .hw.boom import Boom, SECTIONS
from .hw.probe import SoilProbe
from .hw.rc import RCReceiver
from .hw.io import Outputs, Analog, SimSensors, SoilSwitch, battery_percent
from .hw.camera import Camera
from .hw.encoders import Encoders
from .hw.imu import IMU
from .hw.rangefinder import RangeFinder
from .hw.servos import Servos
from .media.recorder import Recorder
from .ai.vision import RowFollower, Classifier, find_weed, ground_point
from .ai.mission import Mission

try:
    import cv2                                       # type: ignore
except Exception:                                    # pragma: no cover
    cv2 = None


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class Rover:
    def __init__(self, cfg_path: str = "ar750/config.yaml"):
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(cfg_path)))
        self.cfg = load_config(cfg_path)
        self.state = RoverState()

        def here(key, fallback):
            p = os.path.join(self.root, self.cfg["web"].get(key, fallback))
            os.makedirs(p, exist_ok=True)
            return p

        self.data_dir = here("data_dir", "data")
        self.photo_dir = here("photo_dir", "data/photos")
        self.video_dir = here("video_dir", "data/recordings")

        self.settings = Settings(self.cfg,
                                 os.path.join(self.data_dir, "settings.json"))
        self.settings.apply_to_config()
        self.settings.on_change(self._settings_changed)
        self.db = DB(os.path.join(self.data_dir, "ar750.db"))
        self.notify = Notifier(self.settings, self.state)

        force_sim = self.cfg["rover"].get("sim", "auto") is True

        # ---------------------------------------------------------- hardware
        self.drive_hw = Drive(self.cfg["drive"], self.cfg["rover"], sim=force_sim)
        self.steering = Steering(self.cfg["drive"]["steering"], self.cfg["rover"])
        self.boom = Boom(self.cfg, self.state, sim=force_sim)
        self.probe = SoilProbe(self.cfg, sim=force_sim)
        self.rc = RCReceiver(self.cfg["rc"], sim=force_sim)
        self.out = Outputs({}, self.cfg["lamps"], sim=force_sim)
        self.analog = Analog(self.cfg["sensors"], sim=force_sim)
        self.soil_switch = SoilSwitch(self.cfg["sensors"].get("soil", {}) or {},
                                      sim=force_sim)
        self.simsens = SimSensors(self.cfg)
        self.enc = Encoders(self.cfg["drive"], self.cfg["rover"], sim=force_sim)
        self.imu = IMU(self.cfg["sensors"], sim=force_sim)
        self.rangef = RangeFinder(self.cfg["sensors"], sim=force_sim)
        self.cam_front = Camera("front", self.cfg["cameras"]["front"], sim=force_sim)
        # the robotic arm and the servo that turns the camera
        self.servos = Servos(self.cfg.get("servos", {}), sim=force_sim,
                             store=os.path.join(self.data_dir, "arm_poses.json"))

        self.row = RowFollower(self.cfg["ai"].get("row", {}))
        self.classifier = Classifier(self.cfg["ai"], root=self.root)
        self.recorder = Recorder(self, self.video_dir)
        self.mission = Mission(self)

        # "simulation" on the website has to mean one thing only: the wheels
        # are NOT really driven. It used to mean "any part simulated", so a Pi
        # with its motor pins live but no ADC wired yet said "simulation"
        # while its wheels could move - the one mix-up that must not happen.
        # The parts that are still pretend are listed separately.
        self.state.sim = self.drive_hw.sim
        self.state.sim_parts = [name for name, part in (
            ("drive", self.drive_hw), ("boom", self.boom),
            ("soil probe", self.probe),
            ("battery, tank and soil readings (ADS1115)", self.analog))
            if part.sim and getattr(part, "enabled", True)]   # absent is not "simulated"
        self.sprayer = self.boom            # the website and the db call it this

        # ------------------------------------------------------------- loop
        self._run = True
        self._odo = {"x": 0.0, "y": 0.0, "hdg": 0.0, "d": 0.0}
        self.home = {"x": 0.0, "y": 0.0}
        self._last_cmd = time.time()
        self._last_web = time.time()
        self._t_prev = time.time()
        self._t_sample = 0.0
        self._t_range = 0.0
        self._t_prune = time.time()
        self._returning = False
        self._web_drive = {"throttle": 0.0, "steer": 0.0, "t": 0.0}
        self._speed_limit = float(self.settings.get("drive.speed_limit", 0.6))
        self.mode_refusal = ""
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        from .core.schedule import Patrols
        self.patrols = Patrols(self)

        if self.state.sim:
            self.state.say("AR-750 ready (simulation - the wheels are not driven)")
        else:
            self.state.say("AR-750 ready - the wheels are LIVE")
            if self.state.sim_parts:
                self.state.say("Still simulated: " + ", ".join(self.state.sim_parts),
                               "warn")
        d = self.steering.describe()
        if self.drive_hw.skid:
            self.state.say("Steering: tank style - left and right sides run apart, "
                           "so it can spin on the spot.")
        else:
            self.state.say("Steering: %.1f deg at the wheels, %.2f m turning circle. "
                           "It cannot turn on the spot."
                           % (d["max_wheel_deg"], d["turning_circle_mm"] / 1000.0))
        if not self.classifier.ready:
            self.state.say("AI model not loaded: %s" % self.classifier.reason, "warn")
        if self.probe.live:
            threading.Thread(target=self._home_probe, daemon=True).start()

    def _home_probe(self) -> None:
        time.sleep(1.0)
        ok, msg = self.probe.home()
        self.state.say("Soil probe: " + msg, "info" if ok else "warn")

    # ---------------------------------------------------------- settings
    def _settings_changed(self, changed: dict) -> None:
        self.settings.apply_to_config()
        if "drive.speed_limit" in changed:
            self.set_speed_limit(float(changed["drive.speed_limit"]))
        if "boom.tank_litres" in changed:
            self.boom.tank_ml = float(changed["boom.tank_litres"]) * 1000.0
        if "boom.ml_per_min_per_nozzle" in changed:
            self.boom.ml_per_min_per_nozzle = float(changed["boom.ml_per_min_per_nozzle"])
        self.state.say("Settings changed: %s" % ", ".join(sorted(changed)))

    # ============================================================ commands
    def set_mode(self, mode: str, autostart: bool = True) -> bool:
        self.mode_refusal = ""
        if self.state.estop and mode != Mode.IDLE:
            self.mode_refusal = "Clear the emergency stop first"
            return False
        if mode not in (Mode.IDLE, Mode.MANUAL, Mode.AUTO, Mode.HOLD):
            self.mode_refusal = "There is no mode called %s" % mode
            return False
        if mode == Mode.AUTO and self.cam_front.sim and not self.state.sim:
            # Auto steers by what the camera sees. With the camera down it
            # would be steering by the simulator's pretend crop row - on a
            # real rover, with real wheels. Never.
            self.mode_refusal = ("The camera is not working, and AI mode steers "
                                 "by the camera. Check its cable, then restart.")
            self.state.say("AI mode refused: " + self.mode_refusal, "warn")
            return False
        old = self.state.mode
        if old == Mode.AUTO and mode != Mode.AUTO:
            self.mission.stop("mode changed to %s" % mode)
        self.state.set(mode=mode)
        self.drive(0, 0)
        if mode == Mode.AUTO:
            # it follows the row with the camera, so the camera looks ahead
            for j in self.servos.joints.values():
                if j.group == "camera" and j.awake:
                    self.servos.set(j.name, j.park)
        self.state.say("Mode %s -> %s" % (old, mode))
        if mode == Mode.AUTO and not self.rangef.live:
            self.state.say("AI mode without a front distance sensor: it cannot see "
                           "what is in its way, so it is held to %d%% speed. Stay "
                           "close, STOP in hand." % round(self.auto_blind_cap * 100),
                           "warn")
        if autostart and mode == Mode.AUTO and not self.state.mission.get("running"):
            self.mission.start(0)
        return True

    def estop(self, reason: str = "button pressed") -> None:
        self.state.trip_estop(reason)
        self._halt()
        self.boom.all_off()
        self.out.all_off()
        self.drive_hw.centre_steering()
        self.servos.hold()            # the arm stops exactly where it is
        self.recorder.stop()
        threading.Thread(target=self.probe.retract, daemon=True).start()
        try:
            self.db.add_alert("error", "Emergency stop: %s" % reason)
        except Exception:
            pass
        self.notify.send("estop", "AR-750: EMERGENCY STOP - %s" % reason)

    def clear_estop(self) -> None:
        self.state.clear_estop()

    def _halt(self) -> None:
        """Stop the wheels AND tell the dashboard they stopped."""
        self.drive_hw.stop()
        if self.state.drive_throttle:
            self.state.set(drive_throttle=0.0)

    @property
    def auto_blind_cap(self) -> float:
        """How fast AI mode may go when nothing measures what is ahead."""
        return max(0.1, min(1.0, float(self.cfg["safety"].get(
            "auto_speed_without_range", 0.3))))

    def drive(self, throttle: float, steer: float) -> None:
        """throttle -1..1 both axles; steer -1..1 onto the steering angle -
        or, on a skid rover, onto how much faster one side runs."""
        t = max(-1.0, min(1.0, throttle)) * self._speed_limit
        limit = self._speed_limit
        if self.state.mode == Mode.AUTO and not self.rangef.live:
            # driving itself with no eyes for obstacles: slow, always
            limit = min(limit, self.auto_blind_cap)
            t = max(-limit, min(limit, t))
        if self.drive_hw.skid:
            st = max(-1.0, min(1.0, steer))
            self.state.set(drive_throttle=round(t, 3), steer_deg=0.0,
                           steer_stick=round(st, 3))
            if self.state.estop:
                self.drive_hw.stop()
            else:
                self.drive_hw.set_throttle(t)
                self.drive_hw.set_turn(st * limit)
            self._last_cmd = time.time()
            return
        wheel = self.steering.stick_to_wheel(steer)
        self.state.set(drive_throttle=round(t, 3),
                       steer_deg=round(wheel, 1),
                       steer_stick=round(max(-1.0, min(1.0, steer)), 3))
        if self.state.estop:
            self.drive_hw.stop()
        else:
            self.drive_hw.set_throttle(t)
            self.drive_hw.set_steer_deg(wheel, self.steering.wheel_max)
            self.drive_hw.write_servo(self.steering.servo_for_wheel(wheel))
        self._last_cmd = time.time()

    def web_drive(self, throttle: float, steer: float) -> None:
        self._web_drive = {"throttle": float(throttle), "steer": float(steer),
                           "t": time.time()}
        self._last_web = time.time()

    def set_speed_limit(self, frac: float) -> None:
        self._speed_limit = max(0.1, min(1.0, float(frac)))

    # ------------------------------------------------------- arm and camera
    def _servo_refusal(self, name: Optional[str] = None) -> str:
        if self.state.estop:
            return "Clear the emergency stop first"
        if self.state.mode == Mode.AUTO:
            j = self.servos.joints.get(name or "")
            if j is not None and j.group == "camera":
                return ("In Auto the camera has to look straight ahead - "
                        "it follows the row with it")
            return "The arm stays still while it drives itself"
        return ""

    def move_servo(self, name: str, deg: Optional[float] = None,
                   delta: Optional[float] = None):
        why = self._servo_refusal(name)
        if why:
            return False, why
        if delta is not None:
            return self.servos.nudge(name, float(delta))
        return self.servos.set(name, float(deg if deg is not None else 90))

    def servo_pose(self, pose: str):
        why = self._servo_refusal()
        if why:
            return False, why
        return self.servos.pose(pose)

    # ------------------------------------------------------------- spraying
    def spray_sections(self, sections, seconds: Optional[float] = None):
        """Open the named boom sections. With seconds, it is a timed band."""
        speed = abs(self.state.telemetry.speed_mps)
        if seconds:
            return self.boom.burst(list(sections), float(seconds), speed)
        return self.boom.open(list(sections), speed)

    def spray_stop(self):
        return self.boom.close()

    def set_spray_armed(self, on: bool) -> None:
        self.state.set(spray_armed=bool(on))
        if not on:
            self.boom.all_off()
        self.state.say("Spray %s" % ("ARMED" if on else "disarmed"),
                       "warn" if on else "info")

    def set_auto_spray(self, on: bool) -> None:
        self.state.set(auto_spray=bool(on))
        self.state.say("Auto spray %s" % ("on" if on else "off"), "warn")

    def set_lamps(self, on: bool) -> None:
        self.out.set("lamp_front", on)
        self.out.set("lamp_rear", on)
        self.state.set(lamps_on=bool(on))

    # ---------------------------------------------------------------- probe
    def probe_soil(self) -> Optional[float]:
        """Stop, put the spike in the ground, read it, pull it out again."""
        if self.probe.busy:
            return self.state.telemetry.soil_pct
        was = self.state.drive_throttle
        self._halt()

        def read():
            v = self.analog.soil_percent()
            # an invented reading only in the simulator, never on a real
            # rover that simply has no ADC
            if v is None and self.analog.sim and self.state.sim:
                v = self.simsens.soil_percent()
            return v

        if not self.probe.live and not self.state.sim:
            # no lead-screw probe on this rover: read what sensor there is
            val = read()
            if val is not None:
                self.state.telemetry.soil_pct = round(val, 1)
                self.state.say("Soil: %.0f%% moisture" % val)
                return val
            sw = self.soil_switch.read()
            if sw:
                self.state.telemetry.soil_state = sw
                self.state.say("Soil: %s (the sensor can only say wet or dry "
                               "without an ADC board)" % sw)
            else:
                self.state.say("No soil sensor is connected", "warn")
            return None
        val, msg = self.probe.read_soil(read)
        self.state.say("Soil probe: " + msg, "info" if val is not None else "warn")
        if val is not None:
            self.state.telemetry.soil_pct = round(val, 1)
        if was:
            self.drive_hw.set_throttle(was)
        return val

    def range_blocked(self) -> bool:
        if self.rangef.live:
            return self.rangef.blocked()
        cfg = self.cfg["sensors"].get("range_front", {})
        if not cfg.get("enabled"):
            return False
        d = self.state.telemetry.range_front_cm
        return d is not None and d < float(cfg.get("stop_cm", 60))

    def weed_target(self):
        """Where a weed is on the ground, from the front camera.

        The AR-750 has no arm, so nothing reaches out and pulls it. What this
        is for is deciding WHICH BOOM SECTION covers it.
        """
        img = self.cam_front.frame()
        if img is None:
            return None
        w = find_weed(img, self.cfg["ai"].get("row", {}))
        if not w:
            return None
        h, wd = img.shape[:2]
        spot = ground_point(w["cx"], w["cy"], wd, h, self.cfg["cameras"]["front"])
        if not spot:
            return None
        spot["section"] = self.section_for(spot["y_mm"])
        return spot

    def section_for(self, y_mm: float) -> str:
        """Which third of the boom covers a point this far off the centre line."""
        half = float(self.cfg["boom"].get("nozzle_spacing_mm", 140)) * 1.5
        if y_mm > half:
            return "left"
        if y_mm < -half:
            return "right"
        return "centre"

    def save_photo(self, img, plant_id: int) -> str:
        if img is None or cv2 is None:
            return ""
        name = "plant_%04d_%s.jpg" % (plant_id, time.strftime("%Y%m%d_%H%M%S"))
        path = os.path.join(self.photo_dir, name)
        try:
            cv2.imwrite(path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            return name
        except Exception:
            return ""

    # ------------------------------------------------------------ going home
    def mark_home(self) -> None:
        self.home = {"x": self._odo["x"], "y": self._odo["y"]}
        self.state.say("Marked this spot as home")

    def distance_home(self) -> float:
        return math.hypot(self._odo["x"] - self.home["x"],
                          self._odo["y"] - self.home["y"])

    def return_home(self) -> None:
        """Back the way it came, in reverse, wheels straight.

        Reversing is the only honest option: turning round needs 2.8 m, and if
        it had 2.8 m of headland it would not be stuck in the row in the first
        place. Without encoders this is dead reckoning and it gets you roughly
        back, not exactly.
        """
        if self._returning or self.state.estop:
            return
        self._returning = True
        self.state.say("Backing out of the row to where it started", "warn")
        self.state.mission["message"] = "Coming home, in reverse"

        def go():
            target = self.distance_home()
            start = self._odo["d"]
            self.drive_hw.write_servo(0.0)
            while (self._returning and not self.state.estop
                   and self._odo["d"] - start < target + 0.2):
                self.drive(-0.45, 0.0)
                time.sleep(0.05)
            self._halt()
            self._returning = False
            self.state.say("Back home, near enough")
            self.state.mission["message"] = "Home"

        threading.Thread(target=go, daemon=True).start()

    def stop_returning(self) -> None:
        self._returning = False

    def shutdown(self) -> None:
        self._run = False
        try:
            self.patrols.stop()
        except Exception:
            pass
        self.recorder.stop()
        try:
            self._thread.join(timeout=1.5)
        except Exception:
            pass
        # Each on its own: if pigpiod has already gone, the first pin command
        # raises, and one part failing to let go must not stop the rest -
        # least of all the database, which closing is what keeps it whole.
        for let_go in (self.boom.shutdown, self.probe.close,
                       self.drive_hw.release, self.out.close, self.rc.close,
                       self.cam_front.close, self.enc.close, self.imu.close,
                       self.rangef.close, self.servos.close,
                       self.soil_switch.close, self.db.close):
            try:
                let_go()
            except Exception:
                pass

    # =============================================================== loop
    def _loop(self) -> None:
        hz = float(self.cfg["safety"].get("loop_hz", 50))
        period = 1.0 / hz
        while self._run:
            t0 = time.time()
            try:
                self._read_sensors()
                self._safety()
                self._modes()
                self._drive_for_mode()
                self.drive_hw.tick()
                self.mission.tick()
                self._housekeeping()
            except ConnectionError as e:             # pragma: no cover
                # pigpiod went away under us (restarted or crashed). From
                # here every pin command fails, fifty times a second, while
                # the website goes on looking alive. So leave: systemd starts
                # the rover again in 5 s and it connects to pigpiod afresh -
                # or, if pigpiod stays down, comes up saying "simulation".
                # Without pigpiod nothing is pulsing the pins, so the ESCs
                # and valves already see "stop".
                self.state.say("lost pigpiod (%s) - restarting" % e, "error")
                print("lost the connection to pigpiod (%s) - exiting so "
                      "systemd starts the rover again" % e, flush=True)
                os._exit(3)
            except Exception as e:                   # pragma: no cover
                self.state.say("control loop error: %s" % e, "error")
                self._halt()
            dt = period - (time.time() - t0)
            if dt > 0:
                time.sleep(dt)

    # ---------------------------------------------------------- sensors
    def _read_sensors(self) -> None:
        t = self.state.telemetry
        now = time.time()
        dt = max(1e-3, now - self._t_prev)
        self._t_prev = now

        v = self.analog.battery_volts()
        t.battery_measured = v is not None
        if v is None:
            # a made-up pack: right for the simulator, and shown as "not
            # measured" on a real rover, where nothing is allowed to act on it
            v = self.simsens.battery_volts()
        t.battery_v = round(v, 2)
        _b = self.cfg["safety"]["battery"]
        t.battery_pct = round(battery_percent(
            v, int(_b.get("cells", 6)),
            str(_b.get("chemistry", "lead"))), 1)

        s = self.analog.soil_percent()
        if s is not None:
            t.soil_pct = round(s, 1)
        if self.soil_switch.live and now - getattr(self, "_t_soilsw", 0) > 1.0:
            self._t_soilsw = now
            t.soil_state = self.soil_switch.read()

        t.tank_ml = self.boom.remaining_ml()
        t.tank_pct = round(100.0 * t.tank_ml / max(1.0, self.boom.tank_ml), 1)

        if now - self._t_range > 0.2:
            self._t_range = now
            if self.rangef.live:
                t.range_front_cm = self.rangef.read()
            elif self.cfg["sensors"].get("range_front", {}).get("enabled"):
                t.range_front_cm = round(self.simsens.range_cm(), 1)

        imu = self.imu.read()
        if imu:
            t.tilt_deg = imu["tilt_deg"]

        # ---- where it is. An Ackermann rover turns because the wheels are
        # pointed, so the heading comes from speed and steering angle, not from
        # one wheel outrunning the other.
        vmax = float(self.cfg["rover"].get("max_speed_mps", 0.45))
        e = self.enc.read()
        if e:
            v_lin = (e["left_mps"] + e["right_mps"]) / 2.0
            dl = (e["left_m"] + e["right_m"]) / 2.0
        else:
            v_lin = self.drive_hw.throttle * vmax
            dl = v_lin * dt

        if imu:
            self._odo["hdg"] = imu["heading_deg"]
        elif self.drive_hw.skid:
            # a skid rover turns because one side outruns the other
            track = float(self.cfg["rover"].get("track_mm", 430)) / 1000.0
            dv = (self.drive_hw.left_out - self.drive_hw.right_out) * vmax
            yaw = math.degrees(dv / max(0.05, track))
            self._odo["hdg"] = (self._odo["hdg"] + yaw * dt) % 360.0
        else:
            yaw = self.steering.yaw_rate_dps(v_lin, self.state.steer_deg)
            self._odo["hdg"] = (self._odo["hdg"] + yaw * dt) % 360.0
        hr = math.radians(self._odo["hdg"])
        self._odo["x"] += dl * math.cos(hr)
        self._odo["y"] += dl * math.sin(hr)
        self._odo["d"] += abs(dl)

        t.speed_mps = round(v_lin, 3)
        t.heading_deg = round(self._odo["hdg"], 1)
        t.x_m = round(self._odo["x"], 3)
        t.y_m = round(self._odo["y"], 3)
        t.distance_m = round(self._odo["d"], 2)
        t.odometry_measured = bool(e)
        t.turn_radius_mm = self.steering.turn_radius(self.state.steer_deg)

        cur = self.analog.current_amps()
        if cur is not None:
            t.current_a = round(cur, 2)

        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                t.cpu_temp_c = round(int(f.read()) / 1000.0, 1)
        except Exception:
            t.cpu_temp_c = 45.0

        self.state.set(rc_live=self.rc.live, rc_channels=self.rc.snapshot())

    # ----------------------------------------------------------- safety
    def _safety(self) -> None:
        s = self.cfg["safety"]
        t = self.state.telemetry
        if self.state.estop:
            self._halt()
            return

        stop_v = float(self.settings.get("safety.battery.stop_v", 13.6))
        warn_v = float(self.settings.get("safety.battery.warn_v", 14.4))
        if not t.battery_measured and not self.state.sim:
            # no ADC on this rover: the battery number is invented, and an
            # invented number must never stop it or send it home
            stop_v = warn_v = -1.0
        if t.battery_v < stop_v:
            self.estop("battery too low: %.2f V" % t.battery_v)
            return
        if t.battery_v < warn_v:
            if not any("battery" in a.get("text", "") for a in self.state.alerts[:3]):
                self.state.add_alert("warn", "Battery low, %.2f V" % t.battery_v)
                self.db.add_alert("warn", "Battery low, %.2f V" % t.battery_v)
                self.notify.send("low_battery", "AR-750: battery low, %.2f V (%.0f%%)"
                                 % (t.battery_v, t.battery_pct), 900)
            home_at = int(self.settings.get("safety.return_home_pct", 25))
            if (home_at and t.battery_pct <= home_at and not self._returning
                    and self.state.mission.get("running")):
                if self.settings.get("drive.reverse_on_low_batt", True):
                    self.mission.stop("battery low, coming home")
                    self.return_home()
                else:
                    self.mission.stop("battery low, parked where it is")
                    self.state.add_alert("warn", "Battery at %.0f%%. Parked in "
                                         "the row." % t.battery_pct)

        tilt_max = float(self.settings.get("safety.tilt_stop_deg", 20))
        if self.imu.live and abs(t.tilt_deg) > tilt_max:
            self.estop("it is leaning %.0f degrees" % t.tilt_deg)
            return

        # a boom section open while it is not moving dumps the lot in one place
        if self.boom.pump_on and abs(t.speed_mps) < 0.01 and not self.probe.busy:
            self.boom.close()
            self.state.add_alert("warn", "Boom shut off: it stopped moving")

        if (self.state.mode == Mode.MANUAL
                and time.time() - self._last_cmd > float(s.get("command_timeout_s", 0.6))):
            self._halt()

    # ------------------------------------------------------------ modes
    def _modes(self) -> None:
        if self.state.estop or not self.rc.live:
            return
        sw = self.rc.switch3("mode")
        want = {-1: Mode.MANUAL, 0: Mode.HOLD, 1: Mode.AUTO}.get(sw, Mode.HOLD)

        stick = max(abs(self.rc.channel("throttle")), abs(self.rc.channel("steer")))
        if self.state.mode == Mode.AUTO and stick > 0.2:
            self.mission.stop("remote stick moved")
            self.state.set(mode=Mode.MANUAL)
            self.state.add_alert("info", "Remote took over, now in MANUAL")
            return
        if self._returning and stick > 0.2:
            self.stop_returning()
        if want != self.state.mode:
            self.set_mode(want)

        armed = self.rc.switch2("spray_arm")
        if armed != self.state.spray_armed:
            self.set_spray_armed(armed)

    def _drive_for_mode(self) -> None:
        m = self.state.mode
        if self._returning:
            return
        if self.state.estop or m in (Mode.IDLE, Mode.ESTOP, Mode.HOLD):
            self._halt()
            return
        if m == Mode.MANUAL:
            if self.rc.live:
                self.drive(self.rc.channel("throttle"), self.rc.channel("steer"))
                pr = self.rc.channel("probe")
                if pr > 0.5 and not self.probe.busy:
                    threading.Thread(target=self.probe_soil, daemon=True).start()
            else:
                w = self._web_drive
                if time.time() - w["t"] < 0.8:
                    self.drive(w["throttle"], w["steer"])
                else:
                    self._halt()

    def _housekeeping(self) -> None:
        now = time.time()
        if now - self._t_sample > 10.0:
            self._t_sample = now
            try:
                self.db.sample(self.state.telemetry)
            except Exception:
                pass
        if now - self._t_prune > 6 * 3600:
            self._t_prune = now
            try:
                keep = int(self.settings.get("record.keep_days", 30))
                self.db.prune(keep)
                self.recorder.prune(keep)
            except Exception:
                pass
