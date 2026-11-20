"""Lexical BM25 over unit search-texts (stage [5], optional fusion).

Exact identifiers — part numbers, fault codes — often need lexical matching that dense
vectors smear over. BM25 fused with the vector score recovers them (and sets up Lab B).
"""

from __future__ import annotations

import re

import numpy as np

from ..provenance import Unit

_TOKEN = re.compile(r"[a-z0-9][a-z0-9\-]*")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


class BM25Lexical:
    def __init__(self, units: list[Unit]):
        from rank_bm25 import BM25Okapi
        self.corpus_tokens = [tokenize(u.search_text) for u in units]
        # BM25Okapi needs at least one non-empty doc; guard empty corpora
        safe = [toks if toks else ["\x00"] for toks in self.corpus_tokens]
        self.bm25 = BM25Okapi(safe)
        self.n = len(units)

    def scores(self, query: str) -> np.ndarray:
        if self.n == 0:
            return np.zeros((0,), dtype="float32")
        q = tokenize(query)
        if not q:
            return np.zeros((self.n,), dtype="float32")
        return np.asarray(self.bm25.get_scores(q), dtype="float32")
