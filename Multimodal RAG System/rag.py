"""
rag.py
------
The RAG answer step: retrieve the most relevant chunks, then ask GPT-4o to
answer using ONLY those chunks and cite its sources.

Grounding the model in retrieved text — and telling it to say "I don't know"
when the answer isn't there — is what keeps hallucinations low.
"""

import os
from typing import List, Tuple

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

SYSTEM = (
    "You answer questions using ONLY the provided context from a document. "
    "Each context block is numbered like [1], [2]. Cite the blocks you use with "
    "those numbers, e.g. 'Revenue grew 20% [2].' If the answer is not in the "
    "context, say you don't know — never make it up."
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        (
            "human",
            "Conversation so far:\n{history}\n\nContext:\n{context}\n\nQuestion: {question}",
        ),
    ]
)


def _format_context(docs: List[Document]) -> str:
    blocks = []
    for i, d in enumerate(docs, start=1):
        loc = (
            f"{d.metadata.get('source', '?')} "
            f"p.{d.metadata.get('page', '?')} "
            f"({d.metadata.get('type', 'text')})"
        )
        blocks.append(f"[{i}] (source: {loc})\n{d.page_content}")
    return "\n\n".join(blocks)


def answer(question: str, retriever, history: str = "") -> Tuple[str, List[dict]]:
    """Retrieve relevant chunks, then generate a grounded answer with citations."""
    docs = retriever.invoke(question)

    llm = ChatOpenAI(model=os.getenv("CHAT_MODEL", "gpt-4o"), temperature=0)
    chain = PROMPT | llm
    resp = chain.invoke(
        {
            "history": history or "(none)",
            "context": _format_context(docs),
            "question": question,
        }
    )

    sources = [
        {
            "n": i,
            "source": d.metadata.get("source"),
            "page": d.metadata.get("page"),
            "type": d.metadata.get("type"),
            "snippet": d.page_content[:200],
        }
        for i, d in enumerate(docs, start=1)
    ]
    return resp.content, sources
