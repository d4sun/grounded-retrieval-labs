"""Vector index over mixed units (part of stage [4]).

One index over the three unit types — text chunks, figure captions, table text — each row
carrying its full provenance in metadata. ``faiss`` when available, else a NumPy
brute-force index (fine for the few-hundred-page lab corpus). Vectors are normalised, so
inner product is cosine similarity.

Persisted to ``index_dir`` as:
  units.jsonl   — every unit (provenance + artefact + search_text)
  vectors.npy   — the embedding matrix (row i ↔ unit i)
  meta.json     — backend, dim, embedder info
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..logging_utils import get_logger
from ..provenance import Unit, read_units_jsonl, write_units_jsonl
from .embedder import Embedder

log = get_logger("grounded_retrieval.indexing.index")


def _faiss_available() -> bool:
    try:
        import faiss  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class SearchHit:
    idx: int
    score: float


class VectorIndex:
    def __init__(self, backend: str = "auto", dim: int | None = None):
        self.backend = self._resolve(backend)
        self.dim = dim
        self.vectors: np.ndarray | None = None
        self.units: list[Unit] = []
        self._faiss = None
        self.meta: dict = {}

    @staticmethod
    def _resolve(backend: str) -> str:
        if backend == "auto":
            return "faiss" if _faiss_available() else "numpy"
        return backend

    # ------------------------------------------------------------------ #
    @classmethod
    def build(cls, units: list[Unit], embedder: Embedder, backend: str = "auto"
              ) -> "VectorIndex":
        texts = [u.search_text or "" for u in units]
        vectors = embedder.encode(texts)
        idx = cls(backend=backend, dim=embedder.dim)
        idx.vectors = vectors
        idx.units = list(units)
        idx.meta = {"embedder_backend": embedder.backend, "dim": embedder.dim,
                    "n_units": len(units)}
        idx._init_backend()
        log.info("built %s index: %d units, dim=%d", idx.backend, len(units), embedder.dim)
        return idx

    def _init_backend(self) -> None:
        if self.backend == "faiss" and self.vectors is not None and len(self.vectors):
            import faiss
            self._faiss = faiss.IndexFlatIP(self.vectors.shape[1])
            self._faiss.add(self.vectors)

    # ------------------------------------------------------------------ #
    def search(self, qvec: np.ndarray, k: int) -> list[SearchHit]:
        if self.vectors is None or len(self.vectors) == 0:
            return []
        q = qvec.reshape(1, -1).astype("float32")
        k = min(k, len(self.vectors))
        if self.backend == "faiss" and self._faiss is not None:
            scores, idxs = self._faiss.search(q, k)
            return [SearchHit(int(i), float(s)) for i, s in zip(idxs[0], scores[0]) if i >= 0]
        scores = (self.vectors @ q[0])
        top = np.argsort(-scores)[:k]
        return [SearchHit(int(i), float(scores[i])) for i in top]

    def unit(self, idx: int) -> Unit:
        return self.units[idx]

    # ------------------------------------------------------------------ #
    def save(self, index_dir: str | Path) -> None:
        d = Path(index_dir)
        d.mkdir(parents=True, exist_ok=True)
        write_units_jsonl(self.units, d / "units.jsonl")
        np.save(d / "vectors.npy", self.vectors if self.vectors is not None
                else np.zeros((0, self.dim or 0), dtype="float32"))
        (d / "meta.json").write_text(json.dumps(
            {"backend": self.backend, **self.meta}, indent=2), encoding="utf-8")
        log.info("saved index to %s", d)

    @classmethod
    def load(cls, index_dir: str | Path) -> "VectorIndex":
        d = Path(index_dir)
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        idx = cls(backend=meta.get("backend", "auto"), dim=meta.get("dim"))
        idx.units = read_units_jsonl(d / "units.jsonl")
        idx.vectors = np.load(d / "vectors.npy").astype("float32")
        idx.meta = meta
        idx._init_backend()
        return idx
