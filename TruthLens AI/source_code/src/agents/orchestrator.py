"""
Agent orchestrator — the agentic control loop.

Coordinates the specialist agents in sequence and fuses their outputs into a
single grounded verdict:

    ClassifierAgent  ->  ExplainerAgent  ->  FactCheckAgent  ->  fuse()

Each agent writes to a shared context and emits a traceable AgentResult, so the
UI can visualise the full reasoning chain (the "agentic" view).
"""
from __future__ import annotations

import time
from typing import Any, Optional

from .. import config
from ..model import load_model
from ..retrieval import EvidenceRetriever
from .base import AgentResult
from .classifier_agent import ClassifierAgent
from .explainer_agent import ExplainerAgent
from .factcheck_agent import FactCheckAgent

# Fusion weights: the trained model is primary, linguistic signals corroborate.
W_MODEL = 0.70
W_SIGNALS = 0.30


class AgentOrchestrator:
    """High-level, reusable entry point used by the app and the tests."""

    def __init__(self, pipeline=None, retriever: Optional[EvidenceRetriever] = None):
        self.pipeline = pipeline or load_model()
        self.retriever = retriever or EvidenceRetriever()
        self.classifier = ClassifierAgent(self.pipeline)
        self.explainer = ExplainerAgent()
        self.factchecker = FactCheckAgent(self.retriever)

    # ------------------------------------------------------------------ #
    def analyze(self, text: str, title: str = "") -> dict[str, Any]:
        """Run the full agentic pipeline on one article and return the verdict."""
        if not text or not text.strip():
            raise ValueError("Article text is empty. Please provide content to analyse.")

        t0 = time.time()
        context: dict[str, Any] = {"title": title or "", "text": text}
        trace: list[AgentResult] = []

        for agent in (self.classifier, self.explainer, self.factchecker):
            trace.append(agent.run(context))

        verdict = self._fuse(context)
        verdict["trace"] = [
            {"agent": r.agent, "summary": r.summary, "elapsed_ms": r.elapsed_ms}
            for r in trace
        ]
        verdict["total_ms"] = round((time.time() - t0) * 1000, 2)
        verdict["llm_backend"] = trace[1].data.get("backend", "offline template generator")
        verdict["retrieval_backend"] = context.get("retrieval_backend", "unknown")
        return verdict

    # ------------------------------------------------------------------ #
    def _fuse(self, context: dict[str, Any]) -> dict[str, Any]:
        p_fake_model = float(context["p_fake"])
        risk = float(context["signals"].risk_score)
        fused_fake = W_MODEL * p_fake_model + W_SIGNALS * risk

        label = config.LABEL_FAKE if fused_fake >= 0.5 else config.LABEL_REAL
        label_name = config.LABELS[label]
        confidence = fused_fake if label == config.LABEL_FAKE else (1 - fused_fake)

        if confidence >= config.CONFIDENCE_HIGH:
            band = "High"
        elif confidence >= config.CONFIDENCE_MEDIUM:
            band = "Medium"
        else:
            band = "Low"

        recommendation = (
            "Likely misinformation — do not share without verifying against "
            "established, named sources."
            if label_name == "FAKE" else
            "Appears credible, but always confirm with the original source."
        )

        return {
            "verdict": label_name,
            "fused_fake_score": round(fused_fake, 4),
            "model_p_fake": round(p_fake_model, 4),
            "signal_risk": round(risk, 4),
            "confidence": round(confidence, 4),
            "confidence_band": band,
            "explanation": context.get("explanation", ""),
            "signals": context["signals"].to_dict(),
            "indicative_terms": context.get("indicative_terms", {}),
            "evidence": context.get("evidence", []),
            "recommendation": recommendation,
        }
