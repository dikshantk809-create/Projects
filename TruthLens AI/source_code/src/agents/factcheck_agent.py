"""
Fact-Check agent — Retrieval-Augmented Generation (RAG) step.

Retrieves the most relevant *verified reference statements* from the knowledge
base and reports how well the article aligns with them. This is the project's
RAG component: retrieve -> ground -> report.
"""
from __future__ import annotations

from typing import Any, Optional

from ..model import combine_fields
from ..retrieval import EvidenceRetriever
from .base import AgentResult, BaseAgent


class FactCheckAgent(BaseAgent):
    name = "FactCheckAgent"
    role = "Retrieves verified reference statements (RAG) to ground the verdict."

    def __init__(self, retriever: Optional[EvidenceRetriever] = None):
        self.retriever = retriever or EvidenceRetriever()

    def _execute(self, context: dict[str, Any]) -> AgentResult:
        query = combine_fields(context.get("title", ""), context.get("text", ""))
        evidence = self.retriever.retrieve(query)
        context["evidence"] = evidence
        context["retrieval_backend"] = self.retriever.backend

        top_score = evidence[0]["score"] if evidence else 0.0
        note = (
            "Retrieved verified context relevant to the article's topic; review the "
            "statements below to corroborate or challenge specific claims."
            if evidence else
            "No closely matching reference statements were found in the knowledge base."
        )

        return AgentResult(
            agent=self.name,
            summary=f"Retrieved {len(evidence)} reference statement(s) "
                    f"(top relevance={top_score:.2f}) via {self.retriever.backend}.",
            data={"evidence": evidence, "note": note,
                  "backend": self.retriever.backend},
        )
