# Multimodal RAG System — Text, Image & Table Understanding

Ask questions about a PDF and get answers grounded in its contents — **with a
citation to the exact page for every claim**. The system understands not just
text but also **tables** and **images** (charts/diagrams are described by GPT-4o
vision so they become searchable). Retrieval is **hybrid**: semantic (FAISS) +
keyword (BM25), fused with Reciprocal Rank Fusion.

**Stack:** Python · LangChain · GPT-4o (vision) · FAISS · BM25 · FastAPI · React

---

## What it does

- **Multimodal ingestion.** A PDF is split into three kinds of searchable pieces:
  - **text** → cleaned and chunked with overlap
  - **tables** → detected per page and converted to Markdown the LLM can read
  - **images** → described by GPT-4o vision, so a chart's contents are searchable
- **Hybrid retrieval.** FAISS finds *semantically* similar chunks; BM25 catches
  *exact* keywords, names and numbers. **Reciprocal Rank Fusion (RRF)** merges the
  two rankings so the best of both rises to the top.
- **Grounded answers with citations.** GPT-4o answers using only the retrieved
  context and cites the blocks it used (`[1]`, `[2]`). If the answer isn't in the
  document, it says so instead of guessing — which keeps hallucinations low.
- **Multi-turn chat.** Follow-up questions remember the conversation.
- **React chat UI.** Upload a PDF, ask questions, and click any citation chip to
  see the exact source snippet.

## How it works (architecture)

```
  PDF ─▶ ingest.py ──────────────▶ chunks (text + tables + image captions)
              │                            │
              │ GPT-4o vision              ▼
              │ describes images    vectorstore.py
              │                     ├─ FAISS  (dense / semantic)
              │                     └─ BM25   (sparse / keyword)
              │                            │  Reciprocal Rank Fusion
              ▼                            ▼
        question ─▶ rag.py: retrieve top-k ─▶ GPT-4o answers WITH citations
                                                      ▲
                              main.py (FastAPI) ──────┘──▶ React chat UI
```

| File | Responsibility |
|------|----------------|
| `ingest.py` | PDF → text/table/image-caption Documents (GPT-4o vision) |
| `vectorstore.py` | Hybrid retriever: FAISS + BM25 fused with RRF |
| `rag.py` | Retrieve, then GPT-4o answers grounded in context with citations |
| `main.py` | FastAPI: `/ingest` and `/query` endpoints (CORS enabled) |
| `frontend/index.html` | React chat UI (single file, no build step) |
| `test_rag.py` | Offline tests (no API key needed) |

---

## Setup

```bash
git clone <your-repo-url>
cd multimodal-rag
pip install -r requirements.txt
cp .env.example .env        # then paste your OpenAI key into .env
```

## Run

**1. Start the API**

```bash
uvicorn main:app --reload
```

**2. Open the UI** — just open `frontend/index.html` in your browser
(or serve it: `python -m http.server 5500 --directory frontend`, then visit
`http://localhost:5500`).

Upload a PDF, wait for it to index, and start asking questions. Click a citation
chip under any answer to see the exact source text.

### API directly

```bash
# index a PDF
curl -F "file=@report.pdf" http://localhost:8000/ingest

# ask a question
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was total revenue in 2023?"}'
```

Response: `{ "answer": "...", "sources": [{ "n":1, "page":4, "type":"table", ... }] }`

---

## Tests

```bash
pip install pytest
pytest -q
```

The tests build a small PDF, extract it, and run the whole hybrid-retrieval
pipeline with **fake embeddings**, so they pass offline without any API key.

## Notes & possible improvements

- **Persist the index.** Right now the FAISS index lives in memory and is rebuilt
  per upload. `FAISS.save_local()` / `load_local()` would make it permanent.
- **Move history to Redis** for multi-user, multi-process deployments.
- **Tune RRF weights / k** per document type for better retrieval.
- **Measure quality honestly.** To claim an accuracy or hallucination number, build
  a small labelled Q&A set for your own document and score the answers against it.

## Security

The API accepts file uploads and calls external models. Add auth, file-size
limits, and rate limiting before exposing it publicly.
