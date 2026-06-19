"""Base abstractions for the multi-agent pipeline."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Standard envelope returned by every agent for traceability."""
    agent: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


class BaseAgent(ABC):
    """
    Minimal agent contract. Each agent has a name, a one-line role, and a
    `run(context)` method that reads/writes a shared context dict and returns
    an AgentResult. This mirrors lightweight agent frameworks (CrewAI/LangGraph)
    without external dependencies.
    """

    name: str = "agent"
    role: str = ""

    @abstractmethod
    def _execute(self, context: dict[str, Any]) -> AgentResult:
        ...

    def run(self, context: dict[str, Any]) -> AgentResult:
        t0 = time.time()
        result = self._execute(context)
        result.elapsed_ms = round((time.time() - t0) * 1000, 2)
        return result
