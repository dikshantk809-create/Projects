"""Write a throwaway config for the self test.

The test must not touch the database, photos or sign-in details you already
have, so it gets its own folder and its own port. Everything it writes lives
under rover_software/data_selftest and is deleted by the menu when the check finishes.
"""
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)          # tests/ lives inside rover_software
SRC = os.path.join(APP, "ar750", "config.yaml")
OUT = os.path.join(APP, "ar750", "_config_selftest.yaml")

with open(SRC, encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

cfg.setdefault("rover", {})["sim"] = True
web = cfg.setdefault("web", {})
web["port"] = 8091
web["host"] = "127.0.0.1"          # the test copy is not offered to the network
web["data_dir"] = "data_selftest"
web["photo_dir"] = "data_selftest/photos"
web["video_dir"] = "data_selftest/recordings"
web["log_dir"] = "data_selftest/logs"

with open(OUT, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)

print("wrote", OUT)
print("the test copy uses rover_software/data_selftest and port 8091")
print("your own data folder is not touched")
sys.exit(0)
