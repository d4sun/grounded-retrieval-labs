"""Text embeddings (part of stage [4]).

- ``local``   : a sentence-transformers model (default ``BAAI/bge-small-en-v1.5``),
                free and private — the recommended path.
- ``hashing`` : a deterministic, dependency-free embedder (hashed word + char-trigram
                bag) so the smoke test runs with no model download. Weak but real: it
                captures lexical overlap, enough to exercise the whole pipeline.
- ``auto``    : local if sentence-transformers is importable, else hashing.

All vectors are L2-normalised so inner product == cosine similarity.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

from ..config import Config
from ..logging_utils import get_logger

log = get_logger("grounded_retrieval.indexing.embedder")

_TOKEN = re.compile(r"[a-z0-9]+")


def _sentence_transformers_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
        return True
    except Exception:
        return False


class Embedder:
    """Factory + thin wrapper. Use ``Embedder(cfg).encode([...])``."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.backend = self._resolve(cfg.get("indexing.embedder.backend", "auto"))
        self.normalize = bool(cfg.get("indexing.embedder.normalize", True))
        self.batch_size = int(cfg.get("indexing.embedder.batch_size", 32))
        self._impl: _BaseEmbedder
        if self.backend == "local":
            self._impl = _SentenceTransformerEmbedder(
                cfg.get("indexing.embedder.model", "BAAI/bge-small-en-v1.5"))
        else:
            self._impl = _HashingEmbedder(int(cfg.get("indexing.embedder.dim", 384)))
        self.dim = self._impl.dim
        log.info("embedder backend=%s dim=%d", self.backend, self.dim)

    @staticmethod
    def _resolve(backend: str) -> str:
        if backend == "auto":
            return "local" if _sentence_transformers_available() else "hashing"
        return backend

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype="float32")
        vecs = self._impl.encode(texts, self.batch_size).astype("float32")
        if self.normalize:
            vecs = _l2_normalize(vecs)
        return vecs


def _l2_normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


class _BaseEmbedder:
    dim: int

    def encode(self, texts: list[str], batch_size: int) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError


class _SentenceTransformerEmbedder(_BaseEmbedder):
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dim = int(self.model.get_sentence_embedding_dimension())

    def encode(self, texts: list[str], batch_size: int) -> np.ndarray:
        return np.asarray(self.model.encode(texts, batch_size=batch_size,
                                            show_progress_bar=False,
                                            normalize_embeddings=False))


class _HashingEmbedder(_BaseEmbedder):
    """Deterministic hashed bag-of-features. No training, no download, no network."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _features(self, text: str):
        text = text.lower()
        toks = _TOKEN.findall(text)
        feats: list[str] = list(toks)
        # char trigrams within tokens add sub-word signal (part numbers, codes)
        for t in toks:
            pad = f"#{t}#"
            for i in range(len(pad) - 2):
                feats.append(pad[i:i + 3])
        return feats

    def encode(self, texts: list[str], batch_size: int) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype="float32")
        for row, text in enumerate(texts):
            for feat in self._features(text):
                h = int.from_bytes(hashlib.md5(feat.encode()).digest()[:8], "little")
                idx = h % self.dim
                sign = 1.0 if (h >> 63) & 1 else -1.0
                out[row, idx] += sign
        return out
