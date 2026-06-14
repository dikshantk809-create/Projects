"""
memory.py
---------
Per-session conversation memory backed by Redis.

Why Redis and why per-session?
    Each chat session gets a unique session_id. We store that session's full
    message history under its own Redis key ("agent:session:<id>"). Because
    every session has a separate key, two users (or two parallel agent runs)
    can never see each other's messages — this is the "no context bleed"
    guarantee, and Redis lets many requests share this memory at once.
"""

import json
import os
from typing import List

import redis
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict


class RedisMemory:
    def __init__(self, url: str | None = None, ttl_seconds: int = 60 * 60 * 24):
        url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # decode_responses=True so we get/set normal strings, not bytes.
        self.client = redis.from_url(url, decode_responses=True)
        self.ttl = ttl_seconds  # sessions expire after 24h by default

    def _key(self, session_id: str) -> str:
        return f"agent:session:{session_id}"

    def load(self, session_id: str) -> List[BaseMessage]:
        """Load a session's message history (empty list if new session)."""
        raw = self.client.get(self._key(session_id))
        if not raw:
            return []
        return messages_from_dict(json.loads(raw))

    def save(self, session_id: str, messages: List[BaseMessage]) -> None:
        """Save the full message history for a session."""
        data = json.dumps(messages_to_dict(messages))
        self.client.set(self._key(session_id), data, ex=self.ttl)

    def clear(self, session_id: str) -> None:
        """Forget a session entirely."""
        self.client.delete(self._key(session_id))
