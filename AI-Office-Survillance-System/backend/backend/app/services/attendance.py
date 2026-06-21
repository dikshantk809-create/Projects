"""Attendance derivation from entry/exit events → work hours."""
from __future__ import annotations
from datetime import datetime, date

def compute_work_seconds(entries: list[datetime], exits: list[datetime]) -> int:
    """Pair sorted entries/exits into intervals and sum durations."""
    entries = sorted(entries); exits = sorted(exits)
    total, i, j = 0, 0, 0
    open_t = None
    events = sorted([(t, "in") for t in entries] + [(t, "out") for t in exits])
    for ts, kind in events:
        if kind == "in" and open_t is None:
            open_t = ts
        elif kind == "out" and open_t is not None:
            total += int((ts - open_t).total_seconds()); open_t = None
    return total

def status_for(entry: datetime | None, start_hour: int = 9, grace_min: int = 15) -> str:
    if entry is None:
        return "absent"
    cutoff = entry.replace(hour=start_hour, minute=grace_min, second=0, microsecond=0)
    return "late" if entry > cutoff else "present"
