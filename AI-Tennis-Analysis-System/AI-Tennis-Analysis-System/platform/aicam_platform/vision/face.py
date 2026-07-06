"""Face detection + recognition via InsightFace (SCRFD detector + ArcFace embeddings).

Enrollment: store L2-normalized 512-d embeddings per consented identity.
Recognition: cosine-similarity match against the gallery with a threshold, plus
multi-frame voting in the pipeline to cut false matches.

Privacy: only run recognition against ENROLLED, CONSENTED identities. Unknown faces
return label 'unknown' and are never silently identified. See docs/05.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class FaceMatch:
    subject_id: Optional[str]     # None / "unknown" if below threshold
    similarity: float
    bbox: tuple[float, float, float, float]
    embedding: np.ndarray


class FaceEngine:
    def __init__(self, model_name: str = "buffalo_l", ctx_id: int = -1,
                 det_size: int = 640, match_threshold: float = 0.45):
        self.model_name = model_name
        self.ctx_id = ctx_id            # -1 cpu, >=0 gpu
        self.det_size = det_size
        self.match_threshold = match_threshold
        self._app = None
        # gallery: subject_id -> list of normalized embeddings
        self.gallery: dict[str, list[np.ndarray]] = {}

    def _ensure(self):
        if self._app is None:
            from insightface.app import FaceAnalysis
            self._app = FaceAnalysis(name=self.model_name)
            self._app.prepare(ctx_id=self.ctx_id, det_size=(self.det_size, self.det_size))
        return self._app

    @staticmethod
    def _norm(v: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(v)
        return v / n if n > 0 else v

    def embed(self, frame: np.ndarray):
        """Return list of (bbox, normalized_embedding) for all faces in frame."""
        faces = self._ensure().get(frame)
        return [(tuple(f.bbox.tolist()), self._norm(f.normed_embedding if hasattr(f, "normed_embedding") else f.embedding)) for f in faces]

    def enroll(self, subject_id: str, frame: np.ndarray) -> bool:
        """Add the largest detected face in `frame` to the gallery for subject_id."""
        embs = self.embed(frame)
        if not embs:
            return False
        # largest bbox = closest/best face
        bbox, emb = max(embs, key=lambda e: (e[0][2]-e[0][0]) * (e[0][3]-e[0][1]))
        self.gallery.setdefault(subject_id, []).append(emb)
        return True

    def _match_one(self, emb: np.ndarray) -> tuple[Optional[str], float]:
        best_id, best_sim = None, -1.0
        for sid, embs in self.gallery.items():
            sim = max(float(np.dot(emb, e)) for e in embs)  # cosine (both normalized)
            if sim > best_sim:
                best_id, best_sim = sid, sim
        if best_sim >= self.match_threshold:
            return best_id, best_sim
        return "unknown", best_sim

    def recognize(self, frame: np.ndarray) -> list[FaceMatch]:
        out: list[FaceMatch] = []
        for bbox, emb in self.embed(frame):
            sid, sim = self._match_one(emb)
            out.append(FaceMatch(subject_id=sid, similarity=sim, bbox=bbox, embedding=emb))
        return out
