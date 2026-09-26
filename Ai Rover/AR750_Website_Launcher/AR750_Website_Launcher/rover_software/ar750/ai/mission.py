"""The autonomous job for a boom sprayer that steers like a car.

    FIND_ROW -> FOLLOW -> AT_PLANT -> DECIDE -> ACT -> MOVE_ON
                   ^                              |
                   +------------------------------+
                            |
                        ROW_END -> TURN (three point) -> FIND_ROW

Two things about the AR-750 shape this, and they are worth saying plainly:

**There is no arm.** Nothing reaches out, looks closely at a leaf, or pulls a
weed. The rover has one camera looking forward and a boom across its back. So
it decides from the driving camera as it approaches, and it treats the plant by
opening the right part of the boom as it passes over it. A weed gets logged and
photographed for you to pull by hand - the machine cannot do it and does not
pretend to.

**It cannot turn on the spot.** Full lock still needs a 2.8 m circle. At the
end of a row it does a three point turn: forward on full lock, reverse on
opposite lock, forward again. If it has room for a proper headland turn it
uses that instead, because a three point turn in soft soil is how you get
stuck.

Nothing here talks to hardware directly. It calls the Rover object, so the same
mission runs against real hardware or against the simulator.
"""
from __future__ import annotations

import os
import time
from typing import Optional

from ..core.state import Mode, PlantRecord
from . import treatment as tx
from .vision import find_weed


class Mission:
    STEPS = ["idle", "find_row", "follow", "at_plant", "decide", "act",
             "act_wait", "move_on", "row_end", "turn", "done"]

    def __init__(self, rover):
        self.r = rover
        self.cfg = rover.cfg
        self.ai = rover.cfg.get("ai", {})
        self.state = rover.state
        self.step = "idle"
        self.t_step = time.time()
        self.plants_done = 0
        self.target = 0
        self.mission_id = 0
        self.row_no = 0
        self.plant_no = 0
        self.rows_done = 0
        self.dist_since_plant = 0.0
        self.dist_since_probe = 0
        self._last_x = 0.0
        self._last_y = 0.0
        self._sprayed_ml = 0.0
        self._problems = 0
        self._d_start = 0.0
        self._d_row = 0.0
        self._turn_dir = 1
        self._turn_phase = 0
        self._weed_at = None
        self._plan = None
        self._rec = None

    # ------------------------------------------------------------------ api
    def start(self, plants: int = 0, kind: str = "manual") -> None:
        if self.state.mission.get("running"):
            self.stop("restarted")
        self.target = int(plants or 0)
        self.plants_done = 0
        self.step = "find_row"
        self.t_step = time.time()
        self.row_no += 1
        self.plant_no = 0
        self.rows_done = 0
        self.dist_since_probe = 0
        self._sprayed_ml = 0.0
        self._problems = 0
        self._d_start = self.state.telemetry.distance_m
        self._d_row = self.state.telemetry.distance_m
        self._turn_phase = 0
        self._mark()
        self.r.mark_home()
        try:
            self.mission_id = self.r.db.start_mission(kind)
        except Exception:
            self.mission_id = 0
        self.r.recorder.start(self.mission_id)
        self.state.mission.update(
            running=True, step=self.step, plants_done=0, plants_target=self.target,
            sprayed_ml=0.0, row=self.row_no, mission_id=self.mission_id,
            rows_done=0, rows_target=int(self.ai.get("rows", 1) or 1),
            message="Looking for the crop row")
        self.state.say("AUTO started. Target %s plants"
                       % (self.target or "as many as it finds"), "info")

    def stop(self, why: str = "stopped") -> None:
        was = bool(self.state.mission.get("running"))
        self.step = "idle"
        self.r.drive(0, 0)
        self.r.spray_stop()
        # a question belongs to the run that asked it. Leaving it up means the
        # next run opens holding an answer for a plant it never looked at.
        if self.state.pending:
            self._finish_plant(self.state.pending.get("record"), "unanswered")
            self.state.set(pending=None)
        self.state.mission.update(running=False, step="idle", message=why)
        self.state.say("AUTO stopped: " + why, "warn")
        if not was:
            return
        self.r.recorder.stop()
        gone = self.state.telemetry.distance_m - self._d_start
        try:
            self.r.db.end_mission(self.mission_id, plants_checked=self.plants_done,
                                  problems=self._problems,
                                  sprayed_ml=round(self._sprayed_ml, 1),
                                  distance_m=round(gone, 2), note=why)
        except Exception:
            pass
        self.r.notify.send(
            "finish", "AR-750 finished: %d plants checked, %d needing attention, "
            "%.0f ml sprayed, %.1f m covered."
            % (self.plants_done, self._problems, self._sprayed_ml, gone), 60)

    def answer(self, approve: bool) -> None:
        p = self.state.pending
        if not p:
            return
        self.state.set(pending=None)
        if not approve:
            self.state.say("You declined: %s" % p.get("title", ""), "warn")
            self._finish_plant(p.get("record"), action="declined")
            self.step = "move_on"
            return
        self.state.say("You approved: %s" % p.get("title", ""), "info")
        self._do_action(p["plan"], p["record"], forced=True)
        self.step = "move_on"

    # ----------------------------------------------------------- main tick
    def tick(self) -> None:
        if not self.state.mission.get("running"):
            return
        if self.state.estop or self.state.mode != Mode.AUTO:
            return
        fn = getattr(self, "_s_" + self.step, None)
        if fn:
            fn()
        self.state.mission["step"] = self.step

    # ------------------------------------------------------------- states
    def _s_find_row(self) -> None:
        img = self.r.cam_front.frame()
        steer, conf, dbg = self.r.row.steer(img)
        if conf > 0.25:
            self._go("follow", "Following the row")
            return
        self.r.drive(0.22, 0.0)
        if time.time() - self.t_step > 12:
            self.r.drive(0, 0)
            self._go("row_end", "No crop row found. Parked, waiting for you.")
            self.state.add_alert("warn", "Could not find a crop row to follow")

    def _s_follow(self) -> None:
        img = self.r.cam_front.frame()
        steer, conf, dbg = self.r.row.steer(img)
        base = float(self.ai.get("row", {}).get("base_speed", 0.35))

        cap = float(self.ai.get("row_length_m", 0) or 0)
        if cap and self.state.telemetry.distance_m - self._d_row > cap:
            self.r.drive(0, 0)
            self.state.add_alert("warn", "Reached the %.0f m row limit" % cap)
            self._go("row_end", "Row limit reached")
            return

        if self.r.range_blocked():
            self.r.drive(0, 0)
            self.state.add_alert("warn", "Something is in the way, holding")
            self.state.mission["message"] = "Obstacle ahead, waiting"
            return

        if conf < 0.2:
            self.r.drive(0, 0)
            self._go("row_end", "Row has ended")
            return

        self.r.drive(base, steer * 0.6)
        self._accumulate()

        spacing_m = float(self.ai.get("plant_spacing_mm", 350)) / 1000.0
        if self.r.row.plant_ahead(img) and self.dist_since_plant > spacing_m * 0.6:
            self._go("at_plant", "Plant ahead")

    def _s_at_plant(self) -> None:
        """It keeps rolling. There is no arm to stop and poke with, and a boom
        sprayer that stops is a boom sprayer dumping chemical in one spot."""
        self.r.drive(float(self.ai.get("row", {}).get("base_speed", 0.35)) * 0.6, 0.0)
        if time.time() - self.t_step < float(self.ai.get("inspect_seconds", 1.5)):
            return
        self._go("decide", "Deciding what it needs")

    def _s_decide(self) -> None:
        img = self.r.cam_front.frame()
        label, conf = self.r.classifier.classify(img)
        if not self.r.classifier.ready:
            self.state.mission["message"] = ("No AI model loaded: %s"
                                             % self.r.classifier.reason)
            label, conf = "not_checked", 0.0

        floor = float(self.ai.get("min_confidence", 0.60))
        if conf < floor and label not in ("not_checked", "healthy"):
            self.state.mission["message"] = "Only %.0f%% sure, asking you" % (conf * 100)
            label = "unknown"

        soil = self.state.telemetry.soil_pct
        if label == "water_stress":
            self.state.mission["message"] = "Putting the probe in the soil"
            soil = self.r.probe_soil()

        plan = tx.plan(label, conf, soil,
                       float(self.ai.get("auto_spray_confidence", 0.85)))

        self.plant_no += 1
        plot = "r%dp%02d" % (self.row_no, self.plant_no)
        rec = PlantRecord(
            id=self.state.next_plant_id(), plot=plot,
            common_name=str(plan["common_name"]),
            time=time.time(), x_m=self.state.telemetry.x_m,
            y_m=self.state.telemetry.y_m, label=plan["label"],
            confidence=round(conf, 3), healthy=bool(plan["healthy"]),
            severity=str(plan["severity"]),
            treatment=("%s  %s" % (plan["product"], plan["dose"])).strip(),
            advice=str(plan["advice"]), soil_pct=soil)
        rec.photo = self.r.save_photo(img, rec.id)

        # a weed is still worth spotting - it just decides which part of the
        # boom to open, because nothing here can pull it out
        self._weed_at = None
        if plan["kind"] == "ok":
            spot = self.r.weed_target()
            if spot:
                self._weed_at = spot
                plan = tx.plan("weed", 0.9, soil)
                rec.label = plan["label"]
                rec.healthy = bool(plan["healthy"])
                rec.severity = str(plan["severity"])
                rec.advice = str(plan["advice"])

        try:
            rec.db_id = self.r.db.add_plant(rec.as_dict(), self.mission_id, plot)
        except Exception:
            rec.db_id = 0
        if not rec.healthy:
            self._problems += 1
            self.r.notify.send("problem", "AR-750 found %s on plant %s (%.0f%% sure). %s"
                               % (plan["common_name"], plot, rec.confidence * 100,
                                  plan["advice"][:160]), 90)
        try:
            before = self.r.db.plant_history(plot, 6)[1:]
            if before and not rec.healthy and before[0].get("label") == rec.label:
                self.state.say("Plant %s had %s last time too"
                               % (plot, rec.common_name or rec.label), "warn")
        except Exception:
            pass

        self.state.add_plant(rec)
        self._plan, self._rec = plan, rec
        self._go("act", plan["common_name"])

    def _s_act(self) -> None:
        plan, rec = self._plan, self._rec
        if plan is None:
            self._go("move_on", "")
            return

        if plan["action"] == "none":
            self._finish_plant(rec, "none")
            self._go("move_on", "Plant is fine")
            return

        # a weed cannot be pulled by this machine, so it is logged for you
        if plan["action"] == "weed_pull":
            rec.action = "marked_for_you"
            self._save(rec)
            self.state.add_alert("info", "Weed at plant %s - pull it by hand, "
                                 "the AR-750 has no gripper" % rec.plot, plant=rec.id)
            self._go("move_on", "Weed logged for you")
            return

        ask = (plan["action"] == "needs_you"
               or (plan["action"] == "spray" and not self.state.auto_spray))
        if ask:
            rec.action = "needs_you"
            self.state.set(pending={
                "title": "%s on plant %d" % (plan["common_name"], rec.id),
                "question": self._question(plan),
                "plan": plan, "record": rec.id, "photo": rec.photo,
                "time": time.time()})
            self.state.add_alert("warn", "Waiting for you: %s" % plan["common_name"],
                                 plant=rec.id)
            try:
                self.r.db.add_alert("warn", "Waiting for you: %s on plant %s"
                                    % (plan["common_name"], rec.plot), rec.db_id)
            except Exception:
                pass
            self.state.mission["message"] = "Waiting for your answer"
            self.step = "act_wait"
            return

        self._do_action(plan, rec.id)
        self._go("move_on", "Done with this plant")

    def _s_act_wait(self) -> None:
        """Waiting on you. It rolls to a stop, wheels straight, boom shut."""
        self.r.drive(0, 0)
        self.r.spray_stop()
        if self.state.pending is None:
            self.step = "move_on"

    def _s_move_on(self) -> None:
        self.plants_done += 1
        self.dist_since_plant = 0.0
        self.dist_since_probe += 1
        self.state.mission["plants_done"] = self.plants_done
        self._mark()

        every = int(self.cfg.get("probe", {}).get("every_n_plants", 10) or 0)
        if every and self.dist_since_probe >= every:
            self.dist_since_probe = 0
            self.r.probe_soil()

        if self.target and self.plants_done >= self.target:
            self._go("done", "Finished the target number of plants")
            self.stop("finished")
            return
        self._go("follow", "On to the next plant")

    def _s_row_end(self) -> None:
        self.r.drive(0, 0)
        self.r.spray_stop()
        want = int(self.ai.get("rows", 1) or 1)
        self.state.add_alert("info", "Row %d finished, %d plants checked so far"
                             % (self.rows_done + 1, self.plants_done))
        self.rows_done += 1
        self.state.mission["rows_done"] = self.rows_done
        if self.rows_done >= want:
            self.state.mission["message"] = ("Finished. %d rows, %d plants."
                                             % (self.rows_done, self.plants_done))
            self.stop("all rows finished")
            return
        self._turn_phase = 0
        gap = float(self.ai.get("row_gap_mm", 700)) / 1000.0
        circle = self.r.steering.turning_circle_mm() / 1000.0
        if gap >= circle:
            # there is room to just drive round: far kinder to soft soil than
            # shuffling back and forth
            self._turn_phase = 2
            self.state.say("Beds are %.1f m apart and it turns in %.1f m, so "
                           "it can loop round rather than shuffle" % (gap, circle))
        else:
            self.state.say("Beds are %.1f m apart but it needs %.1f m to turn, "
                           "so it will do a three point turn" % (gap, circle))
        self._go("turn", "Turning into row %d" % (self.rows_done + 1))

    def _s_turn(self) -> None:
        """A three point turn, because full lock still needs 2.8 metres.

        forward on full lock -> reverse on the other lock -> forward again.
        Each leg runs for a distance worked out from the turn radius, not for
        a guessed number of seconds, so it is at least repeatable. Without
        encoders it still drifts, and after two or three rows you will be
        straightening it by hand. That is the machine, not the code.
        """
        vmax = float(self.cfg["rover"]["max_speed_mps"])
        R = self.steering_radius_m()
        # each leg turns it through about 60 degrees
        leg_m = R * (60.0 * 3.14159 / 180.0)
        gone = self.state.telemetry.distance_m - self._leg_start()

        if self.r.range_blocked():
            self.r.drive(0, 0)
            self.state.mission["message"] = "Something in the way, waiting"
            return

        # phase 2 on its own is a plain loop round, used when the beds are far
        # enough apart. Phases 0, 1, 2 together are the three point turn.
        if self._turn_phase == 0:
            self.r.drive(0.4, 1.0 * self._turn_dir)
        elif self._turn_phase == 1:
            self.r.drive(-0.4, -1.0 * self._turn_dir)
        elif self._turn_phase == 2:
            self.r.drive(0.4, 1.0 * self._turn_dir)
        else:
            self.r.drive(0, 0)
            self.r.drive_hw.centre_steering()
            self._turn_dir *= -1
            self.plant_no = 0
            self.row_no += 1
            self._d_row = self.state.telemetry.distance_m
            self._go("find_row", "Looking for row %d" % (self.rows_done + 1))
            return

        if gone >= leg_m:
            self._turn_phase += 1
            self._leg_mark()
            self.state.mission["message"] = ("Three point turn, leg %d of 3"
                                             % min(3, self._turn_phase + 1))

    def _s_done(self) -> None:
        self.r.drive(0, 0)

    # -------------------------------------------------------------- helpers
    def steering_radius_m(self) -> float:
        r = self.r.steering.turn_radius(self.r.steering.wheel_max)
        return (r or 1200.0) / 1000.0

    def _leg_start(self) -> float:
        return getattr(self, "_leg_d", self.state.telemetry.distance_m)

    def _leg_mark(self) -> None:
        self._leg_d = self.state.telemetry.distance_m

    def _question(self, plan: dict) -> str:
        if plan["label"] == "not_checked":
            return ("There is no AI model loaded, so I did not check this "
                    "plant. The photo is saved. Mark it as seen?")
        if plan["kind"] == "unknown":
            return ("I am not sure what is wrong with this plant. Look at the "
                    "photo. Mark it as seen and carry on?")
        if plan["kind"] == "viral":
            return ("This looks like %s. No spray cures a virus. Pull the plant "
                    "out and bin it - by hand, this machine has no gripper."
                    % plan["common_name"])
        if plan["action"] in ("spray", "needs_you") and plan["product"]:
            sec = self._section()
            return ("Open the %s boom section over this plant with %s (%s)? "
                    "Do not pick the crop for %d days after."
                    % (sec, plan["product"], plan["dose"], plan["phi_days"]))
        return "Act on %s?" % plan["common_name"]

    def _section(self) -> str:
        if self._weed_at and self._weed_at.get("section"):
            return self._weed_at["section"]
        return "centre"

    def _save(self, rec) -> None:
        if rec is None or not getattr(rec, "db_id", 0):
            return
        try:
            self.r.db.update_plant(rec.db_id, action=rec.action,
                                   dose_ml=rec.dose_ml,
                                   sprayed=1 if rec.sprayed else 0)
        except Exception:
            pass

    def _do_action(self, plan: dict, rec_id, forced: bool = False) -> None:
        rec = self._find(rec_id)
        act = plan["action"]
        if act == "spray" or (forced and plan["spray_allowed"]):
            secs = float(self.cfg.get("boom", {}).get("band_seconds", 1.2))
            before = self.r.boom.used_ml
            ok, msg = self.r.spray_sections([self._section()], secs)
            used = self.r.boom.used_ml - before
            if ok:
                if rec:
                    rec.sprayed = True
                    rec.action = "sprayed"
                    rec.dose_ml = round(used, 1)
                self._sprayed_ml += used
                self.state.mission["sprayed_ml"] = round(self._sprayed_ml, 1)
                self.state.say("Sprayed the %s section over plant %s (%s)"
                               % (self._section(), rec_id, msg))
            else:
                if rec:
                    rec.action = "needs_you"
                self.state.add_alert("error", "Could not spray: " + msg)
        else:
            if rec:
                rec.action = "seen_by_you" if forced else "needs_you"
        self._save(rec)

    def _finish_plant(self, rec_id, action: str) -> None:
        rec = self._find(rec_id)
        if rec:
            rec.action = action
            self._save(rec)

    def _find(self, rec_id):
        if rec_id is None:
            return None
        if hasattr(rec_id, "id"):
            return rec_id
        for p in reversed(self.state.plants):
            if p.id == rec_id:
                return p
        return None

    def _go(self, step: str, message: str) -> None:
        self.step = step
        self.t_step = time.time()
        if step == "turn":
            self._leg_mark()
        if message:
            self.state.mission["message"] = message

    def _mark(self) -> None:
        self._last_x = self.state.telemetry.x_m
        self._last_y = self.state.telemetry.y_m

    def _accumulate(self) -> None:
        t = self.state.telemetry
        d = ((t.x_m - self._last_x) ** 2 + (t.y_m - self._last_y) ** 2) ** 0.5
        self.dist_since_plant += d
        self._last_x, self._last_y = t.x_m, t.y_m
