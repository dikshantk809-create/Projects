"""
End-to-end tests for the agentic pipeline.

A small model is trained in-memory from the synthetic generator so the tests
are fast, deterministic and independent of any saved artifact.
"""
import pytest

from src.agents import AgentOrchestrator
from src.data_generator import build_dataset, build_knowledge_base
from src.model import build_pipeline, combine_fields
from src.retrieval import EvidenceRetriever


@pytest.fixture(scope="module")
def engine() -> AgentOrchestrator:
    df = build_dataset(n_per_class=300, seed=7)
    X = [combine_fields(t, x) for t, x in zip(df["title"], df["text"])]
    y = df["label"].astype(int).values
    pipe = build_pipeline().fit(X, y)
    retriever = EvidenceRetriever(build_knowledge_base())
    return AgentOrchestrator(pipeline=pipe, retriever=retriever)


def test_fake_article_flagged_fake(engine):
    fake = ("SHOCKING: They don't want you to know the secret miracle cure!! "
            "Sources say the mainstream media is hiding the explosive truth, "
            "share before it's deleted!!!")
    result = engine.analyze(text=fake)
    assert result["verdict"] == "FAKE"
    assert result["confidence"] >= 0.5
    assert result["signal_risk"] > 0.3


def test_real_article_flagged_real(engine):
    real = ("According to the Reserve Bank, the economy grew 4 percent in the last "
            "quarter, based on data collected over 12 months. Governor Lee said the "
            "committee would review the figures before the deadline.")
    result = engine.analyze(text=real)
    assert result["verdict"] == "REAL"


def test_result_contains_full_trace_and_evidence(engine):
    result = engine.analyze(text="The Health Ministry published a peer-reviewed report.")
    assert len(result["trace"]) == 3
    assert {s["agent"] for s in result["trace"]} == {
        "ClassifierAgent", "ExplainerAgent", "FactCheckAgent"
    }
    assert "explanation" in result and result["explanation"]
    assert isinstance(result["evidence"], list)


def test_empty_text_raises(engine):
    with pytest.raises(ValueError):
        engine.analyze(text="   ")
