"""Tennis scoring state machine — the referee's rulebook.

Implements standard scoring: points (0/15/30/40/deuce/advantage), games (first to 6,
win by 2), 7-point tiebreak at 6-6, and best-of-3/5 sets. Pure logic, fully unit-tested.
Feed it point winners ('a'/'b'); it tracks the full match score and detects match end.
"""
from __future__ import annotations
from dataclasses import dataclass, field

POINTS = ["0", "15", "30", "40"]


@dataclass
class TennisMatch:
    best_of: int = 3                       # 3 or 5
    tiebreak_at: int = 6                   # games each → tiebreak
    # state
    p: list[int] = field(default_factory=lambda: [0, 0])   # current game points (index)
    games: list[int] = field(default_factory=lambda: [0, 0])
    sets: list[int] = field(default_factory=lambda: [0, 0])
    set_scores: list[tuple[int, int]] = field(default_factory=list)
    in_tiebreak: bool = False
    tb: list[int] = field(default_factory=lambda: [0, 0])
    server: int = 0                        # 0='a', 1='b'
    finished: bool = False
    winner: str | None = None

    # ---- public API ----
    def point(self, who: str) -> dict:
        """Award a point to 'a' or 'b'. Returns a summary dict with the new score."""
        if self.finished:
            return self.summary()
        i = 0 if who == "a" else 1
        if self.in_tiebreak:
            self._tiebreak_point(i)
        else:
            self._game_point(i)
        return self.summary()

    # ---- internals ----
    def _game_point(self, i: int):
        j = 1 - i
        # deuce / advantage handling
        if self.p[i] >= 3 and self.p[j] >= 3:
            if self.p[i] == self.p[j]:
                self.p[i] += 1                       # advantage i
            elif self.p[i] == self.p[j] + 1:
                self._win_game(i)                    # had advantage → game
            else:
                self.p[j] -= 1                       # back to deuce
        elif self.p[i] >= 3 and self.p[j] < 3:
            self._win_game(i)
        else:
            self.p[i] += 1

    def _win_game(self, i: int):
        self.games[i] += 1
        self.p = [0, 0]
        self.server = 1 - self.server
        # tiebreak trigger
        if self.games[0] == self.tiebreak_at and self.games[1] == self.tiebreak_at:
            self.in_tiebreak = True
            self.tb = [0, 0]
            return
        self._check_set(i)

    def _check_set(self, i: int):
        j = 1 - i
        if self.games[i] >= 6 and self.games[i] - self.games[j] >= 2:
            self._win_set(i)

    def _tiebreak_point(self, i: int):
        self.tb[i] += 1
        j = 1 - i
        if self.tb[i] >= 7 and self.tb[i] - self.tb[j] >= 2:
            self.games[i] += 1                       # 7-6 set
            self.in_tiebreak = False
            self._win_set(i)

    def _win_set(self, i: int):
        self.sets[i] += 1
        self.set_scores.append((self.games[0], self.games[1]))
        self.games = [0, 0]
        self.p = [0, 0]
        self.tb = [0, 0]
        needed = self.best_of // 2 + 1
        if self.sets[i] >= needed:
            self.finished = True
            self.winner = "a" if i == 0 else "b"

    def display_points(self) -> str:
        if self.in_tiebreak:
            return f"TB {self.tb[0]}-{self.tb[1]}"
        a, b = self.p
        if a >= 3 and b >= 3:
            if a == b: return "40-40 (deuce)"
            return "AD-40" if a > b else "40-AD"
        return f"{POINTS[min(a,3)]}-{POINTS[min(b,3)]}"

    def summary(self) -> dict:
        return {
            "points": self.display_points(),
            "games": list(self.games),
            "sets": list(self.sets),
            "set_scores": self.set_scores,
            "server": "a" if self.server == 0 else "b",
            "in_tiebreak": self.in_tiebreak,
            "finished": self.finished,
            "winner": self.winner,
        }
