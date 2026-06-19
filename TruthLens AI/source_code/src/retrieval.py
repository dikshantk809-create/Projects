"""
Retrieval-Augmented (RAG) evidence retriever.

Powers the Fact-Check agent: given an article, it retrieves the most relevant
*verified reference statements* from the knowledge base.

Two backends, auto-selected at runtime:
  1. Dense  — sentence-transformers embeddings + FAISS  (used if installed)
  2. Sparse — TF-IDF + cosine similarity                (pure scikit-learn fallback)

The sparse fallback guarantees the RAG layer works offline with zero model
downloads, while the dense backend gives a stronger semantic match when the
optional extras are installed.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from . import config


class EvidenceRetriever:
    """Semantic retriever over the verified-statements knowledge base."""

    def __init__(self, knowledge_base: Optional[pd.DataFrame] = None):
        if knowledge_base is None:
            knowledge_base = self._load_kb()
        self.kb = knowledge_base.reset_index(drop=True)
        self.statements = self.kb["statement"].tolist()
        self.backend = "none"
        self._dense_model = None
        self._dense_index = None
        self._tfidf = None
        self._tfidf_matrix = None
        self._build_index()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_kb() -> pd.DataFrame:
        if config.KNOWLEDGE_BASE_CSV.exists():
            return pd.read_csv(config.KNOWLEDGE_BASE_CSV)
        # Fallback: build it on the fly
        from .data_generator import build_knowledge_base
        return build_knowledge_base()

    def _build_index(self) -> None:
        """Try the dense backend first; fall back to TF-IDF cosine."""
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            import faiss  # type: ignore

            self._dense_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
            emb = self._dense_model.encode(
                self.statements, normalize_embeddings=True, show_progress_bar=False
            ).astype("float32")
            index = faiss.IndexFlatIP(emb.shape[1])
            index.add(emb)
            self._dense_index = index
            self.backend = "dense (sentence-transformers + FAISS)"
        except Exception:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._tfidf = TfidfVectorizer(stop_words="english")
            self._tfidf_matrix = self._tfidf.fit_transform(self.statements)
            self.backend = "sparse (TF-IDF cosine)"

    # ------------------------------------------------------------------ #
    def retrieve(self, query: str, top_k: int = config.RETRIEVAL_TOP_K) -> list[dict]:
        """Return the top-k most relevant verified statements with scores."""
        query = (query or "").strip()
        if not query or not self.statements:
            return []
        top_k = min(top_k, len(self.statements))

        if self._dense_index is not None:
            q = self._dense_model.encode(
                [query], normalize_embeddings=True, show_progress_bar=False
            ).astype("float32")
            scores, idx = self._dense_index.search(q, top_k)
            pairs = list(zip(idx[0].tolist(), scores[0].tolist()))
        else:
            from sklearn.metrics.pairwise import linear_kernel

            qv = self._tfidf.transform([query])
            sims = linear_kernel(qv, self._tfidf_matrix).ravel()
            order = np.argsort(sims)[::-1][:top_k]
            pairs = [(int(i), float(sims[i])) for i in order]

        results = []
        for i, score in pairs:
            results.append(
                {
                    "statement": self.statements[i],
                    "topic": str(self.kb.iloc[i].get("topic", "general")),
                    "score": round(float(score), 4),
                }
            )
        return results
