"""
Optional Generative-AI text backend.

TruthLens uses a local LLM (via Ollama) to phrase its explanations in fluent
natural language WHEN one is available. Crucially, the system never depends on
it: if no LLM is reachable, callers fall back to a deterministic, template-based
generator (see agents/explainer_agent.py) so the GenAI output always renders
offline with no API key and no cost.

This mirrors a real production pattern: a cheap/local model with a guaranteed
fallback path, upgradable to a stronger model by changing one env var.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from . import config


class LLMClient:
    """Thin client around a local Ollama server with safe failure handling."""

    def __init__(
        self,
        host: str = config.OLLAMA_HOST,
        model: str = config.OLLAMA_MODEL,
        timeout: int = config.LLM_TIMEOUT_SECONDS,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._available: Optional[bool] = None

    # ------------------------------------------------------------------ #
    @property
    def available(self) -> bool:
        """Probe the local LLM server once and cache the result."""
        if self._available is None:
            self._available = self._probe()
        return self._available

    def _probe(self) -> bool:
        try:
            import requests

            r = requests.get(f"{self.host}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    def generate(self, prompt: str, system: str = "") -> Optional[str]:
        """
        Return generated text, or None if the LLM is unavailable / errors.
        Callers MUST handle the None case with a deterministic fallback.
        """
        if not self.available:
            return None
        try:
            import requests

            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system or "You are a careful, neutral media-literacy assistant.",
                "stream": False,
                "options": {"temperature": 0.3},
            }
            r = requests.post(
                f"{self.host}/api/generate", json=payload, timeout=self.timeout
            )
            if r.status_code == 200:
                return (r.json().get("response") or "").strip()
        except Exception:
            return None
        return None

    def backend_name(self) -> str:
        return f"Ollama · {self.model}" if self.available else "offline template generator"


@lru_cache(maxsize=1)
def get_llm() -> LLMClient:
    """Process-wide singleton so the availability probe runs only once."""
    return LLMClient()
