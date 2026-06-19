"""Classifier agent — runs the interpretable ML model."""
from __future__ import annotations

from typing import Any

from .. import config
from ..model import predict_proba_fake, top_indicative_terms
from .base import AgentResult, BaseAgent


class ClassifierAgent(BaseAgent):
    name = "ClassifierAgent"
    role = "Predicts FAKE/REAL probability with the trained TF-IDF + LR model."

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def _execute(self, context: dict[str, Any]) -> AgentResult:
        title = context.get("title", "")
        text = context.get("text", "")

        p_fake = predict_proba_fake(self.pipeline, title, text)
        label = config.LABEL_FAKE if p_fake >= 0.5 else config.LABEL_REAL
        confidence = p_fake if label == config.LABEL_FAKE else (1 - p_fake)
        terms = top_indicative_terms(self.pipeline, title, text)

        context["model_label"] = label
        context["model_label_name"] = config.LABELS[label]
        context["p_fake"] = p_fake
        context["model_confidence"] = confidence
        context["indicative_terms"] = terms

        return AgentResult(
            agent=self.name,
            summary=(
                f"Model predicts {config.LABELS[label]} "
                f"(P(fake)={p_fake:.2f}, confidence={confidence:.2f})."
            ),
            data={"label": config.LABELS[label], "p_fake": round(p_fake, 4),
                  "indicative_terms": terms},
        )
