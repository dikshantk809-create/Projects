"""
Explainer agent — turns model output + linguistic signals into a human-readable
justification. Uses a local LLM when available, otherwise a deterministic
template generator (so it always works offline).
"""
from __future__ import annotations

from typing import Any

from ..features import extract_signals
from ..llm import get_llm
from .base import AgentResult, BaseAgent


class ExplainerAgent(BaseAgent):
    name = "ExplainerAgent"
    role = "Explains WHY the verdict was reached using linguistic credibility signals."

    def _execute(self, context: dict[str, Any]) -> AgentResult:
        text = context.get("text", "")
        title = context.get("title", "")
        label_name = context.get("model_label_name", "REAL")
        confidence = context.get("model_confidence", 0.5)

        signals = extract_signals(f"{title}. {text}")
        context["signals"] = signals

        terms = context.get("indicative_terms", {})
        explanation = self._compose(label_name, confidence, signals, terms)
        context["explanation"] = explanation

        return AgentResult(
            agent=self.name,
            summary="Generated an explainable justification from credibility signals.",
            data={
                "risk_score": signals.risk_score,
                "explanation": explanation,
                "signals": signals.to_dict(),
                "backend": get_llm().backend_name(),
            },
        )

    # ------------------------------------------------------------------ #
    def _compose(self, label_name, confidence, signals, terms) -> str:
        """Prefer an LLM phrasing; fall back to a deterministic template."""
        evidence = self._evidence_bullets(signals, terms)
        llm = get_llm()
        if llm.available:
            prompt = (
                "You are explaining, in 3-4 neutral sentences, why a news article "
                f"was assessed as likely {label_name} (confidence {confidence:.0%}).\n"
                "Base your explanation ONLY on these detected signals:\n"
                f"{evidence}\n"
                "Do not invent facts. Be measured and educational."
            )
            out = llm.generate(prompt)
            if out:
                return out
        return self._template(label_name, confidence, signals, evidence)

    @staticmethod
    def _evidence_bullets(signals, terms) -> str:
        lines = []
        if signals.sensational_hits:
            lines.append(f"- sensational words: {', '.join(signals.sensational_hits[:6])}")
        if signals.clickbait_hits:
            lines.append(f"- clickbait phrasing: {', '.join(signals.clickbait_hits[:4])}")
        if signals.vague_sourcing_hits:
            lines.append(f"- vague sourcing: {', '.join(signals.vague_sourcing_hits[:4])}")
        if signals.credibility_marker_hits:
            lines.append(f"- credibility markers: {', '.join(signals.credibility_marker_hits[:4])}")
        lines.append(f"- exclamation marks: {signals.exclamation_count}, "
                     f"ALL-CAPS ratio: {signals.all_caps_ratio:.2f}")
        lines.append(f"- citations/quotes: {signals.quote_count}, "
                     f"named entities (approx): {signals.named_entity_estimate}, "
                     f"dates present: {signals.has_dates}")
        fake_terms = ", ".join(t for t, _ in terms.get("toward_fake", [])[:5]) or "none"
        real_terms = ", ".join(t for t, _ in terms.get("toward_real", [])[:5]) or "none"
        lines.append(f"- model's top FAKE-leaning terms: {fake_terms}")
        lines.append(f"- model's top REAL-leaning terms: {real_terms}")
        return "\n".join(lines)

    @staticmethod
    def _template(label_name, confidence, signals, evidence) -> str:
        if label_name == "FAKE":
            head = (
                f"This article is assessed as **likely FAKE** with "
                f"{confidence:.0%} confidence. The language shows several markers "
                "commonly associated with misinformation: "
            )
            cues = []
            if signals.sensational_hits:
                cues.append("sensational vocabulary")
            if signals.clickbait_hits:
                cues.append("clickbait phrasing")
            if signals.vague_sourcing_hits:
                cues.append("vague, unattributed sourcing")
            if signals.exclamation_count >= 2 or signals.all_caps_ratio > 0.05:
                cues.append("heavy emphasis (capitalisation/exclamation)")
            if not cues:
                cues.append("term patterns the model learned from labelled fake news")
            body = ", ".join(cues) + "."
            tail = (
                " Few verifiable details (named sources, dates, direct quotes) were "
                "detected, which lowers credibility. Treat the claims with caution "
                "and seek corroboration from established outlets."
            )
        else:
            head = (
                f"This article is assessed as **likely REAL** with "
                f"{confidence:.0%} confidence. The writing reads as measured and "
                "report-like: "
            )
            cues = []
            if signals.credibility_marker_hits:
                cues.append("explicit attribution to named sources")
            if signals.has_dates:
                cues.append("concrete dates")
            if signals.named_entity_estimate >= 3:
                cues.append("multiple named entities")
            if signals.quote_count:
                cues.append("direct quotations")
            if not cues:
                cues.append("neutral term patterns learned from labelled real news")
            body = ", ".join(cues) + "."
            tail = (
                " Sensational and clickbait markers were largely absent. As always, "
                "cross-checking with the original source is good practice."
            )
        return head + body + tail + f"\n\nDetected signals:\n{evidence}"
