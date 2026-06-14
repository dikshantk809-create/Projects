# Autonomous AI Agent with Tool Use & Memory

A multi-step AI agent built with **LangGraph** that decides on its own when to
search the web, run code, read/write files, and use other tools to complete a
task. It is served as a streaming **FastAPI** API, and each chat session keeps
its own memory in **Redis**, so parallel users never mix context.

**Stack:** Python · LangGraph · OpenAI API · FastAPI · Redis

---

## What it does

- **Multi-step reasoning.** The agent runs a loop — think → call a tool → look
  at the result → think again → answer — instead of replying in one shot.
- **10 built-in tools:** web search, Wikipedia, fetch URL, calculator, Python
  code execution, current date/time, word count, read file, write file, unit
  conversion. (Adding more is a few lines — see below.)
- **Streaming output.** Answers stream back token-by-token over Server-Sent
  Events, so the client shows text as it is generated.
- **Per-session memory via Redis.** Every session has its own Redis key, so two
  users (or two parallel runs) stay fully isolated — no context bleed.

## How it works (architecture)

The core is a small LangGraph state machine with two nodes:

```
        ┌─────────┐   asked for tools?    ┌─────────┐
START ─▶│  agent  │──────── yes ─────────▶│  tools  │
        │  (LLM)  │◀──────────────────────│  (run)  │
        └─────────┘     results back      └─────────┘
             │
             │ gave a final answer
             ▼
            END
```

- `agent` node = the LLM. It either answers, or returns one or more *tool calls*.
- `tools` node = runs the requested tools and feeds results back.
- A conditional edge (`tools_condition`) sends flow to `tools` when the LLM
  wants a tool, otherwise to `END`. That loop is what makes it an *agent*.

| File | Responsibility |
|------|----------------|
| `agent.py` | Builds the LangGraph graph (the agent loop) |
| `tools.py` | The 10 tools the agent can call |
| `memory.py` | Redis-backed per-session conversation history |
| `main.py` | FastAPI app + streaming `/chat` endpoint |
| `client_example.py` | A small client to test streaming from the terminal |

---

## Setup

**1. Clone and install**

```bash
git clone <your-repo-url>
cd autonomous-ai-agent
pip install -r requirements.txt
```

**2. Add your API key**

```bash
cp .env.example .env
# open .env and paste your OpenAI key
```

**3. Start Redis** (easiest way is Docker)

```bash
docker run -d -p 6379:6379 --name agent-redis redis
```

> No Docker? Install Redis locally, or use a free Redis Cloud URL and put it in
> `REDIS_URL` inside `.env`.

---

## Run

**Start the API server:**

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000/docs` to try it in the browser, or use the client:

```bash
python client_example.py "Search the web for today's top AI news and summarise it"
```

You can also test the agent directly, without the server:

```bash
python agent.py "What is 25 * 17, and who is the CEO of OpenAI?"
```

### API

`POST /chat`

```json
{ "message": "your question", "session_id": "optional-id" }
```

Returns a stream of Server-Sent Events:
`{"type":"session",...}` → many `{"type":"token","content":"..."}` → `{"type":"done"}`.
Send the same `session_id` again to continue the conversation with memory.

---

## Add your own tool

Tools are just functions with the `@tool` decorator. Add one in `tools.py`:

```python
@tool
def reverse_text(text: str) -> str:
    """Reverse a piece of text."""
    return text[::-1]
```

…then add it to the `ALL_TOOLS` list at the bottom. The LLM picks it up
automatically — no other changes needed.

## Possible improvements (good next steps)

- Trim or summarise long histories before sending them to the LLM (saves tokens).
- Add streaming of *tool steps* to the client, not just final tokens.
- Swap the simple `python_repl` for a sandboxed executor for safety.
- Add auth + rate limiting before deploying publicly.

## Note on security

`python_repl` and the file tools run on the host machine. That is fine for local
development and demos, but sandbox them before exposing this service publicly.
