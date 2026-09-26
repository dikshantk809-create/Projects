"""Start the AR-750 and its website.

    python3 -m ar750.main                      # normal, on the Pi
    python3 -m ar750.main --sim                # force simulation anywhere
    python3 -m ar750.main --config other.yaml

Then open  http://<pi-address>:8080
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time

import uvicorn
import yaml

from .rover import Rover
from .web.server import build_app


def local_address() -> str:
    """The address to type into a phone on the same wifi."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))          # no packet is sent, it just picks a route
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "<this-pi's-address>"


def main() -> int:
    ap = argparse.ArgumentParser(description="AR-750 agricultural rover")
    ap.add_argument("--config", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.yaml"))
    ap.add_argument("--sim", action="store_true",
                    help="run everything in simulation, no hardware needed")
    ap.add_argument("--port", type=int, default=None)
    args = ap.parse_args()

    if args.sim:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
        cfg["rover"]["sim"] = True
        tmp = os.path.join(os.path.dirname(args.config), "_config_sim.yaml")
        with open(tmp, "w") as f:
            yaml.safe_dump(cfg, f)
        args.config = tmp

    rover = Rover(args.config)
    app = build_app(rover)
    rover.auth_is_fresh = rover.auth.is_first_run()

    port = args.port or int(rover.cfg["web"].get("port", 8080))
    host = rover.cfg["web"].get("host", "0.0.0.0")

    def bye(*_):
        print("\nstopping the rover...")
        rover.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, bye)
    signal.signal(signal.SIGTERM, bye)

    fitted = ", ".join(n for n, d in (("encoders", rover.enc), ("tilt", rover.imu),
                                      ("range", rover.rangef), ("probe", rover.probe),
                                      ("boom", rover.boom), ("drive", rover.drive_hw),
                                      ("arm and camera servos", rover.servos))
                       if d.live) or "none yet"
    steer = rover.steering.describe()
    print("=" * 66)
    print(" AR-750")
    print("  mode        :", "SIMULATION - the wheels are not driven" if rover.state.sim
          else "hardware - the wheels are LIVE")
    if rover.state.sim_parts and not rover.state.sim:
        print("  simulated   :", ", ".join(rover.state.sim_parts))
    print("  AI model    :", "ready" if rover.classifier.ready
          else "not loaded (%s)" % rover.classifier.reason)
    print("  remote      :", "live" if rover.rc.live else "not detected yet")
    print("  fitted      :", fitted)
    if rover.drive_hw.skid:
        print("  steering    : tank style (%s, left and right sides) - it can"
              " spin on the spot" % rover.drive_hw.driver.upper())
    else:
        print("  steering    : %.1f deg at the wheels, %.2f m turning circle"
              % (steer["max_wheel_deg"], steer["turning_circle_mm"] / 1000.0))
        print("                it steers like a car - it cannot turn on the spot")
    print("  website     : http://%s:%d" % (local_address(), port))
    if rover.auth_is_fresh:
        print()
        print("  FIRST TIME: sign in with   admin / agrirover")
        print("  It will make you change both straight away.")
    print("=" * 66)

    uvicorn.run(app, host=host, port=port, log_level="warning")
    rover.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
