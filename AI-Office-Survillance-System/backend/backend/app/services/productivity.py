"""Productivity scoring from behavior samples.

IMPORTANT (ethics/legal): productivity scores are NOISY PROXIES. Use them as
aggregate, role-level trend signals — never as sole grounds for individual
disciplinary action. Weights are configurable per org policy.
"""
from __future__ import annotations
from dataclasses import dataclass

# default activity weights toward "productive time"
WEIGHTS = {
    "working": 1.0, "meeting": 0.9, "talking": 0.5, "walking": 0.3,
    "break": 0.0, "idle": 0.0, "phone": -0.2,
}

@dataclass
class DailyTotals:
    working_sec: int = 0
    idle_sec: int = 0
    phone_sec: int = 0
    meeting_sec: int = 0
    break_sec: int = 0
    talking_sec: int = 0
    walking_sec: int = 0

    @property
    def active_sec(self) -> int:
        return (self.working_sec + self.idle_sec + self.phone_sec +
                self.meeting_sec + self.talking_sec + self.walking_sec)

def score(t: DailyTotals) -> float:
    """0..100 weighted productive-time ratio (break time excluded from denominator)."""
    denom = max(1, t.active_sec)
    weighted = (
        t.working_sec * WEIGHTS["working"] + t.meeting_sec * WEIGHTS["meeting"] +
        t.talking_sec * WEIGHTS["talking"] + t.walking_sec * WEIGHTS["walking"] +
        t.phone_sec * WEIGHTS["phone"] + t.idle_sec * WEIGHTS["idle"]
    )
    return round(max(0.0, min(100.0, 100.0 * weighted / denom)), 1)

def aggregate(samples: list[tuple[str, float]], sample_period_s: float = 1.0) -> DailyTotals:
    """samples = [(activity, confidence), ...] sampled at sample_period_s."""
    t = DailyTotals()
    for activity, _conf in samples:
        sec = int(sample_period_s)
        if activity == "working": t.working_sec += sec
        elif activity == "idle": t.idle_sec += sec
        elif activity == "phone": t.phone_sec += sec
        elif activity == "meeting": t.meeting_sec += sec
        elif activity == "break": t.break_sec += sec
        elif activity == "talking": t.talking_sec += sec
        elif activity == "walking": t.walking_sec += sec
    return t
