"""Unit tests for text preprocessing."""
from src.preprocessing import clean_text, sentence_split, tokenize


def test_clean_text_lowercases_and_strips_punctuation():
    out = clean_text("BREAKING!! Visit https://x.com NOW!!!", remove_stopwords=False)
    assert "http" not in out
    assert "!" not in out
    assert out == out.lower()


def test_clean_text_removes_stopwords():
    out = clean_text("the economy is growing and the market is up")
    assert "the" not in out.split()
    assert "economy" in out


def test_clean_text_handles_empty_and_none():
    assert clean_text("") == ""
    assert clean_text(None) == ""          # type: ignore[arg-type]


def test_tokenize_counts_words():
    assert tokenize("Hello, world! Hello.") == ["hello", "world", "hello"]


def test_sentence_split():
    assert len(sentence_split("One sentence. Two sentences! Three?")) == 3
