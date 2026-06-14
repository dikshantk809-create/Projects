"""
WhatsApp message parser.

Turns free-text seller messages into a structured intent. Handles the
real-world formats from the spec without needing an LLM for the common
case (cheap, instant, deterministic). An LLM fallback can wrap this for
messages that don't match — but these patterns cover the 90% case.

Supported:
    "Dikshant 2L"                      -> total 2L (split as morning)
    "Dikshant 1.5 L"                   -> 1.5L
    "Dikshant Morning 1L Evening 1L"   -> M=1, E=1
    "Dikshant m 1 e 1"                 -> M=1, E=1
    "Dikshant evening 2"               -> E=2
    "Dikshant 1L @ 60"                 -> 1L at rate 60
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedEntry:
    customer_name: str
    morning_qty: float
    evening_qty: float
    rate: float | None
    raw: str

    @property
    def total_qty(self) -> float:
        return round(self.morning_qty + self.evening_qty, 2)


_NUM = r"(\d+(?:\.\d+)?)"
_RATE_RE = re.compile(rf"@\s*{_NUM}")
_MORNING_RE = re.compile(rf"(?:morning|subah|\bm\b)\s*{_NUM}\s*l?", re.I)
_EVENING_RE = re.compile(rf"(?:evening|shaam|\be\b)\s*{_NUM}\s*l?", re.I)
_QTY_RE = re.compile(rf"{_NUM}\s*l\b", re.I)
_BARE_QTY_RE = re.compile(rf"\b{_NUM}\b")


class ParseError(Exception):
    pass


def parse_message(text: str) -> ParsedEntry:
    original = text
    text = text.strip()
    if not text:
        raise ParseError("empty message")

    rate = None
    rm = _RATE_RE.search(text)
    if rm:
        rate = float(rm.group(1))
        text = _RATE_RE.sub("", text)

    morning = evening = 0.0
    matched_split = False

    mm = _MORNING_RE.search(text)
    if mm:
        morning = float(mm.group(1))
        matched_split = True
        text = _MORNING_RE.sub("", text)

    em = _EVENING_RE.search(text)
    if em:
        evening = float(em.group(1))
        matched_split = True
        text = _EVENING_RE.sub("", text)

    if not matched_split:
        q = _QTY_RE.search(text)
        if q:
            morning = float(q.group(1))
            text = _QTY_RE.sub("", text, count=1)
        else:
            q = _BARE_QTY_RE.search(text)
            if not q:
                raise ParseError(f"no quantity found in: {original!r}")
            morning = float(q.group(1))
            text = _BARE_QTY_RE.sub("", text, count=1)

    # Whatever non-numeric tokens remain are the customer name.
    name = re.sub(r"[^a-zA-Z\u0900-\u097F\s]", " ", text)
    name = " ".join(name.split()).strip()
    if not name:
        raise ParseError(f"no customer name found in: {original!r}")

    return ParsedEntry(
        customer_name=name,
        morning_qty=morning,
        evening_qty=evening,
        rate=rate,
        raw=original,
    )
