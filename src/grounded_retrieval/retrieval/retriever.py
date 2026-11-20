"""Retrieve (stage [5]).

``retrieve(query, k)`` returns the top-k units **with their provenance**. Pure vector
search by default; with ``retrieval.fusion.bm25`` on, vector and BM25 scores are each
min-max normalised and blended (``alpha`` on the vector side).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..config import Config
from ..logging_utils import get_logger
from ..indexing.embedder import Embedder
from ..indexing.index import VectorIndex
from ..provenance import Unit
from .bm25 import BM25Lexical

log = get_logger("grounded_retrieval.retrieval.retriever")


@dataclass
class RetrievedUnit:
    unit: Unit
    score: float
    rank: int
    vector_score: float = 0.0
    bm25_score: float = 0.0

    @property
    def citation(self) -> str:
        return self.unit.citation()


def _minmax(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


class Retriever:
    def __init__(self, index: VectorIndex, embedder: Embedder, cfg: Config):
        self.index = index
        self.embedder = embedder
        self.cfg = cfg
        self.top_k = int(cfg.get("retrieval.top_k", 8))
        self.use_bm25 = bool(cfg.get("retrieval.fusion.bm25", True))
        self.alpha = float(cfg.get("retrieval.fusion.alpha", 0.5))
        self._bm25 = BM25Lexical(index.units) if self.use_bm25 else None

    @classmethod
    def from_index_dir(cls, index_dir: str | Path, cfg: Config) -> "Retriever":
        index = VectorIndex.load(index_dir)
        embedder = Embedder(cfg)
        if embedder.dim != (index.meta.get("dim") or embedder.dim):
            log.warning("embedder dim %d != index dim %s; retrieval may be degraded",
                        embedder.dim, index.meta.get("dim"))
        return cls(index, embedder, cfg)

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedUnit]:
        k = k or self.top_k
        if self.index.vectors is None or len(self.index.vectors) == 0:
            return []
        qvec = self.embedder.encode([query])[0]

        if not self.use_bm25:
            hits = self.index.search(qvec, k)
            return [RetrievedUnit(self.index.unit(h.idx), h.score, r, vector_score=h.score)
                    for r, h in enumerate(hits)]

        # fused path: full score arrays (lab-scale corpus)
        vec = self.index.vectors @ qvec.astype("float32")
        bm = self._bm25.scores(query)
        vn, bn = _minmax(vec), _minmax(bm)
        fused = self.alpha * vn + (1.0 - self.alpha) * bn
        order = np.argsort(-fused)[:k]
        out: list[RetrievedUnit] = []
        for rank, i in enumerate(order):
            i = int(i)
            out.append(RetrievedUnit(
                unit=self.index.unit(i), score=float(fused[i]), rank=rank,
                vector_score=float(vec[i]), bm25_score=float(bm[i]),
            ))
        return out
