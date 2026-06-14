"""
main.py
-------
FastAPI service for the multimodal RAG system.

Endpoints:
    GET  /         -> health check (and whether a document is indexed)
    POST /ingest   -> upload a PDF; it gets parsed, embedded, and indexed
    POST /query    -> ask a question; returns an answer + source citations

State is kept in memory for simplicity: the current retriever and a short
per-session chat history. For production you'd persist the FAISS index to disk
and move history to Redis — see the README.
"""

import os
import shutil
import tempfile
from typing import Dict, List

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest import load_pdf
from vectorstore import build_retriever
from rag import answer

app = FastAPI(title="Multimodal RAG System")

# Allow the local React UI (different port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- simple in-memory state ---
STATE: Dict[str, object] = {"retriever": None}
HISTORY: Dict[str, List[str]] = {}


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


@app.get("/")
def root():
    return {"status": "ok", "index_ready": STATE["retriever"] is not None}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    # Save the uploaded PDF to a temporary file on disk.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        docs = load_pdf(tmp_path, caption_images=True)
        if not docs:
            return {"ok": False, "error": "No readable content found in the PDF."}

        STATE["retriever"] = build_retriever(docs)

        by_type: Dict[str, int] = {}
        for d in docs:
            by_type[d.metadata["type"]] = by_type.get(d.metadata["type"], 0) + 1

        return {
            "ok": True,
            "filename": file.filename,
            "chunks": len(docs),
            "by_type": by_type,
        }
    finally:
        os.unlink(tmp_path)


@app.post("/query")
def query(req: QueryRequest):
    if STATE["retriever"] is None:
        return {"ok": False, "error": "No document indexed yet. Upload a PDF first."}

    past = HISTORY.get(req.session_id, [])
    history_text = "\n".join(past[-6:])  # last few turns for follow-up questions

    ans, sources = answer(req.question, STATE["retriever"], history=history_text)

    past.append(f"User: {req.question}")
    past.append(f"Assistant: {ans}")
    HISTORY[req.session_id] = past

    return {"ok": True, "answer": ans, "sources": sources}
