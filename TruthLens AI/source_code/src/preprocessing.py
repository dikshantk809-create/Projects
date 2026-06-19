"""
Text preprocessing utilities.

Deliberately dependency-free (pure standard library + regex) so the project
runs offline with no NLTK/spaCy model downloads. This keeps the live demo
bulletproof on any laptop.
"""
from __future__ import annotations

import re
import unicodedata

# Pre-compiled patterns (compiled once, reused) -----------------------------
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HTML_RE = re.compile(r"<[^>]+>")
_NON_ALPHANUM_RE = re.compile(r"[^a-z0-9\s']")
_MULTISPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-zA-Z']+")

# A small, curated English stop-word list (no external download required).
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "of", "this", "that", "these",
    "those", "i", "you", "he", "she", "it", "we", "they", "them", "his",
    "her", "its", "our", "their", "as", "so", "than", "too", "very", "can",
    "will", "just", "not", "no", "nor", "only", "own", "same", "such",
}


def normalize_unicode(text: str) -> str:
    """Normalise accented/again exotic characters to plain ASCII where possible."""
    if not text:
        return ""
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii", "ignore")
    )


def clean_text(text: str, remove_stopwords: bool = True) -> str:
    """
    Lower-case, strip URLs/HTML/punctuation and (optionally) stop-words.

    This is the canonical cleaner used to feed the TF-IDF vectorizer. It is
    intentionally lossy — the raw text is preserved separately for the
    linguistic-signal extractor used by the Explainer agent.
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    text = normalize_unicode(text).lower()
    text = _URL_RE.sub(" ", text)
    text = _HTML_RE.sub(" ", text)
    text = _NON_ALPHANUM_RE.sub(" ", text)
    text = _MULTISPACE_RE.sub(" ", text).strip()
    if remove_stopwords:
        text = " ".join(w for w in text.split() if w not in STOPWORDS and len(w) > 1)
    return text


def tokenize(text: str) -> list[str]:
    """Return lower-cased word tokens (no external tokenizer needed)."""
    return _WORD_RE.findall(text.lower())


def sentence_split(text: str) -> list[str]:
    """Lightweight sentence splitter for readability statistics."""
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]
