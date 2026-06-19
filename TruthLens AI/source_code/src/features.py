"""
Linguistic credibility-signal extraction.

These hand-crafted features are NOT used to train the classifier — they power
the *Explainer agent*, giving a human-readable, model-agnostic justification
for every verdict. This is the explainability backbone of TruthLens and works
with zero external dependencies (so it never fails during a live demo).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from .preprocessing import sentence_split, tokenize

# --------------------------------------------------------------------------- #
# Lexicons of well-documented misinformation markers
# --------------------------------------------------------------------------- #
SENSATIONAL_WORDS = {
    "shocking", "shock", "bombshell", "explosive", "miracle", "secret",
    "secrets", "exposed", "destroyed", "slammed", "insane", "unbelievable",
    "you", "wont", "believe", "jaw-dropping", "terrifying", "horrifying",
    "stunning", "outrageous", "scandal", "banned", "forbidden", "cover-up",
    "conspiracy", "hoax", "wake", "sheeple", "mainstream",
}

CLICKBAIT_PHRASES = [
    "you won't believe", "you wont believe", "what happened next",
    "doctors hate", "they don't want you to know", "they dont want you to know",
    "this one trick", "will blow your mind", "the truth about",
    "number will shock you", "gone wrong", "must see", "before it's deleted",
    "share before", "wake up", "do your own research",
]

VAGUE_SOURCING = [
    "sources say", "people are saying", "many believe", "it is said",
    "reportedly", "rumours", "rumors", "anonymous source", "insiders claim",
    "some say", "allegedly", "word on the street", "experts claim",
    "studies show",  # without citation
]

# Markers that *raise* credibility
CREDIBILITY_MARKERS = [
    "according to", "said in a statement", "told reuters", "told the associated press",
    "data from", "published in the journal", "peer-reviewed", "press release",
    "spokesperson", "court documents", "official report",
]

_NUMBER_RE = re.compile(r"\b\d[\d,\.]*\b")
_QUOTE_RE = re.compile(r"[\"“”']{1}.+?[\"“”']{1}")
_DATE_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b"
    r"|\b\d{4}\b",
    re.IGNORECASE,
)
# crude proper-noun / named-entity proxy: capitalised word not at sentence start
_PROPER_NOUN_RE = re.compile(r"(?<!^)(?<![.!?]\s)\b[A-Z][a-z]{2,}\b")


@dataclass
class CredibilitySignals:
    """Structured, explainable signals extracted from a single article."""
    char_count: int
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    exclamation_count: int
    question_count: int
    all_caps_word_count: int
    all_caps_ratio: float
    sensational_hits: list[str]
    clickbait_hits: list[str]
    vague_sourcing_hits: list[str]
    credibility_marker_hits: list[str]
    number_count: int
    quote_count: int
    has_dates: bool
    named_entity_estimate: int
    risk_score: float          # 0 (credible) .. 1 (high misinformation risk)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _find_phrases(text_low: str, phrases: list[str]) -> list[str]:
    return [p for p in phrases if p in text_low]


def extract_signals(text: str) -> CredibilitySignals:
    """Compute the full set of linguistic credibility signals for `text`."""
    text = text or ""
    low = text.lower()
    tokens = tokenize(text)
    sentences = sentence_split(text)
    words = text.split()

    word_count = len(tokens)
    sentence_count = max(len(sentences), 1)
    all_caps = [w for w in words if len(w) >= 3 and w.isupper()]

    sensational = sorted({t for t in tokens if t in SENSATIONAL_WORDS})
    clickbait = _find_phrases(low, CLICKBAIT_PHRASES)
    vague = _find_phrases(low, VAGUE_SOURCING)
    credible = _find_phrases(low, CREDIBILITY_MARKERS)

    exclamation = text.count("!")
    question = text.count("?")
    all_caps_ratio = round(len(all_caps) / max(word_count, 1), 4)
    numbers = len(_NUMBER_RE.findall(text))
    quotes = len(_QUOTE_RE.findall(text))
    has_dates = bool(_DATE_RE.search(text))
    entities = len(set(_PROPER_NOUN_RE.findall(text)))

    # ------------------------------------------------------------------ #
    # Transparent, weighted risk score (explainable by construction)
    # ------------------------------------------------------------------ #
    risk = 0.0
    risk += min(len(sensational) * 0.08, 0.30)
    risk += min(len(clickbait) * 0.15, 0.30)
    risk += min(len(vague) * 0.10, 0.25)
    risk += min(exclamation * 0.04, 0.20)
    risk += min(all_caps_ratio * 1.5, 0.20)
    # Credibility markers reduce risk
    risk -= min(len(credible) * 0.10, 0.25)
    risk -= 0.05 if has_dates else 0.0
    risk -= min(entities * 0.01, 0.10)
    risk -= min(quotes * 0.03, 0.10)
    risk = round(min(max(risk, 0.0), 1.0), 4)

    return CredibilitySignals(
        char_count=len(text),
        word_count=word_count,
        sentence_count=sentence_count,
        avg_sentence_length=round(word_count / sentence_count, 2),
        exclamation_count=exclamation,
        question_count=question,
        all_caps_word_count=len(all_caps),
        all_caps_ratio=all_caps_ratio,
        sensational_hits=sensational,
        clickbait_hits=clickbait,
        vague_sourcing_hits=vague,
        credibility_marker_hits=credible,
        number_count=numbers,
        quote_count=quotes,
        has_dates=has_dates,
        named_entity_estimate=entities,
        risk_score=risk,
    )
