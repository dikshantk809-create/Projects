"""Unit tests for pure-python logic (no heavy deps needed)."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../platform")))

from app.services.productivity import DailyTotals, score, aggregate
from app.services.attendance import compute_work_seconds
from aicam_platform.common.geometry import Tripwire, point_in_polygon
from datetime import datetime, timedelta


def test_productivity_score_bounds():
    t = DailyTotals(working_sec=3600, idle_sec=0)
    assert score(t) == 100.0
    t2 = DailyTotals(idle_sec=3600)
    assert score(t2) == 0.0

def test_aggregate_counts():
    samples = [("working", 1.0)] * 100 + [("idle", 1.0)] * 50
    t = aggregate(samples, 1.0)
    assert t.working_sec == 100 and t.idle_sec == 50

def test_attendance_pairing():
    base = datetime(2026, 6, 19, 9, 0, 0)
    entries = [base, base + timedelta(hours=5)]
    exits = [base + timedelta(hours=4), base + timedelta(hours=8)]
    # 4h + 3h = 7h = 25200s
    assert compute_work_seconds(entries, exits) == 25200

def test_tripwire_crossing():
    w = Tripwire("e", (0.0, 0.5), (1.0, 0.5))
    assert w.update(1, (0.5, 0.2)) is None      # first sample
    assert w.update(1, (0.5, 0.8)) == "in"      # crossed downward

def test_point_in_polygon():
    sq = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert point_in_polygon((0.5, 0.5), sq)
    assert not point_in_polygon((1.5, 0.5), sq)
