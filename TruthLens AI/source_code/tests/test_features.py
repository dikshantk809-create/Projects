"""Unit tests for the explainable credibility-signal extractor."""
from src.features import extract_signals


def test_detects_sensational_and_clickbait():
    text = "SHOCKING!! You won't believe this secret. Sources say it's a hoax!!!"
    s = extract_signals(text)
    assert s.sensational_hits, "should flag sensational words"
    assert s.clickbait_hits, "should flag clickbait phrasing"
    assert s.exclamation_count >= 3
    assert s.risk_score > 0.4


def test_credible_text_scores_low_risk():
    text = ("According to the Reserve Bank, inflation rose 3 percent on March 14, "
            "2025. Data from the National Statistics Office confirmed the figure.")
    s = extract_signals(text)
    assert s.has_dates
    assert s.credibility_marker_hits
    assert s.risk_score < 0.4


def test_risk_score_is_bounded():
    s = extract_signals("SHOCKING " * 50 + "!!!!!!!!!!")
    assert 0.0 <= s.risk_score <= 1.0


def test_empty_input_is_safe():
    s = extract_signals("")
    assert s.word_count == 0
    assert 0.0 <= s.risk_score <= 1.0
