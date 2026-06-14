"""
main.py
-------
The FastAPI web service that wraps the agent.

Endpoints:
    GET  /         -> health check
    POST /chat     -> send a message, stream the answer back token-by-token

Streaming: we use Server-Sent Events (SSE). As the LLM generates text, each
small chunk is pushed to the client immediately instead of waiting for the
whole answer. The browser/curl sees the answer appear live.

Memory: every request carries a session_id. We load that session's history
from Redis, run the agent, then save the updated history back. Different
session_ids stay completely isolated.
"""

import json
import uuid

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessageChunk

from agent import agent
from memory import RedisMemory

app = FastAPI(title="Autonomous AI Agent")
memory = RedisMemory()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/")
def root():
    return {"status": "ok", "service": "autonomous-ai-agent"}


@app.post("/chat")
def chat(req: ChatRequest):
    # New session id if the client didn't send one.
    session_id = req.session_id or str(uuid.uuid4())

    # 1. Load this session's history (isolation by session_id) and add the new msg.
    history = memory.load(session_id)
    history.append(HumanMessage(content=req.message))

    def event_stream():
        # First event: tell the client which session this is.
        yield _sse({"type": "session", "session_id": session_id})

        final_state = {"messages": history}

        # 2. Run the agent ONCE, asking for two stream modes at the same time:
        #    "messages" -> token-by-token LLM output (for live streaming)
        #    "values"   -> the full state after each step (to save to memory)
        for mode, data in agent.stream(
            {"messages": history},
            stream_mode=["messages", "values"],
        ):
            if mode == "messages":
                chunk, _meta = data
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield _sse({"type": "token", "content": chunk.content})
            elif mode == "values":
                final_state = data  # keep overwriting; last one is final

        # 3. Persist the full updated history for this session.
        memory.save(session_id, final_state["messages"])
        yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    """Format a dict as one Server-Sent Event line."""
    return f"data: {json.dumps(payload)}\n\n"
