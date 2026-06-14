"""
client_example.py
-----------------
A tiny client to test the streaming /chat endpoint.

Run the server first (uvicorn main:app --reload), then in another terminal:

    python client_example.py "Search the web for the latest news on AI, then summarise it"

It keeps the same session_id across messages, so the agent remembers context.
"""

import sys
import json
import requests

API = "http://localhost:8000/chat"


def chat(message: str, session_id: str | None = None) -> str:
    resp = requests.post(
        API,
        json={"message": message, "session_id": session_id},
        stream=True,
    )
    new_session = session_id
    print("Agent: ", end="", flush=True)
    for line in resp.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8")
        if not text.startswith("data: "):
            continue
        event = json.loads(text[len("data: "):])
        if event["type"] == "session":
            new_session = event["session_id"]
        elif event["type"] == "token":
            print(event["content"], end="", flush=True)
        elif event["type"] == "done":
            print()
    return new_session


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "What is 25 * 17, and what is the capital of Japan?"
    chat(msg)
