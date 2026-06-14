"""
vectorstore.py
--------------
Hybrid retrieval = dense (FAISS) + sparse (BM25), merged with
Reciprocal Rank Fusion (RRF).

  - FAISS (dense) : embeds chunks into vectors, finds *semantically* similar
                    ones (good at meaning, e.g. "earnings" ~ "revenue").
  - BM25 (sparse) : classic keyword scoring (good at exact terms, names, numbers).
  - RRF           : each retriever returns a ranked list; RRF gives every doc a
                    score of 1/(c + rank) from each list and sums them, so docs
                    that rank high in EITHER method bubble to the top.

build_retriever takes an optional `embeddings` object. In the app it defaults to
OpenAI embeddings; tests pass in fake embeddings so they run without an API key.
"""

import os
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi


class HybridRetriever:
    """Dense (FAISS) + sparse (BM25) retrieval fused with RRF."""

    def __init__(self, docs: List[Document], embeddings: Embeddings, k: int = 4):
        self.docs = docs
        self.k = k
        # Dense index
        self.faiss = FAISS.from_documents(docs, embeddings)
        # Sparse index (BM25 over whitespace-tokenised lowercased text)
        self._tokenised = [d.page_content.lower().split() for d in docs]
        self.bm25 = BM25Okapi(self._tokenised)

    def _bm25_top(self, query: str, n: int) -> List[Document]:
        scores = self.bm25.get_scores(query.lower().split())
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.docs[i] for i in order[:n]]

    @staticmethod
    def _rrf(result_lists: List[List[Document]], c: int = 60) -> List[Document]:
        """Reciprocal Rank Fusion across several ranked result lists."""
        scores, lookup = {}, {}
        for results in result_lists:
            for rank, doc in enumerate(results):
                key = (
                    doc.metadata.get("source"),
                    doc.metadata.get("page"),
                    doc.page_content[:60],
                )
                scores[key] = scores.get(key, 0.0) + 1.0 / (c + rank)
                lookup[key] = doc
        ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
        return [lookup[k] for k in ranked]

    def invoke(self, query: str) -> List[Document]:
        """Return the top-k documents for a query (dense + sparse, fused)."""
        pool = self.k * 3
        dense = self.faiss.similarity_search(query, k=pool)
        sparse = self._bm25_top(query, pool)
        return self._rrf([dense, sparse])[: self.k]


def build_retriever(
    docs: List[Document],
    k: int = 4,
    embeddings: Optional[Embeddings] = None,
) -> HybridRetriever:
    """Build a hybrid retriever over the given documents."""
    if not docs:
        raise ValueError("No documents to index — ingest a PDF first.")
    embeddings = embeddings or OpenAIEmbeddings(
        model=os.getenv("EMBED_MODEL", "text-embedding-3-small")
    )
    return HybridRetriever(docs, embeddings, k=k)
