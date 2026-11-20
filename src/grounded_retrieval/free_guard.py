"""Enforce the lab's cost posture: **free tools only**.

The whole pipeline is built on free/open components — the only place a *paid* resource
could sneak in is an OpenRouter model slug. OpenRouter marks free models with a ``:free``
suffix (and ``openrouter/free`` is the free auto-router). This guard makes "free" a
checked invariant instead of a convention: with ``free_only`` on (the default), a non-free
slug is refused and the caller falls back to the offline path rather than spending money.

Local/open-weight models (sentence-transformers, FAISS, Docling, Tesseract, PyMuPDF,
pdfplumber, Camelot, rank-bm25) are always free and need no check.
"""

from __future__ import annotations

from .logging_utils import get_logger

log = get_logger("grounded_retrieval.free_guard")


def is_free_openrouter_model(slug: str) -> bool:
    """True for OpenRouter models that cost nothing: the free auto-router or any
    slug tagged ``:free``."""
    if not slug:
        return False
    s = slug.strip().lower()
    return s == "openrouter/free" or s.endswith(":free")


def check_free_model(slug: str, *, free_only: bool, where: str) -> bool:
    """Return True if *slug* may be used. When free_only is set and the slug is not a
    free OpenRouter model, log a clear warning and return False so the caller can fall
    back to the offline path."""
    if not free_only:
        return True
    if is_free_openrouter_model(slug):
        return True
    log.warning(
        "free-only is on but %s model %r is not a free (':free') OpenRouter slug — "
        "refusing it and using the offline fallback. Set enrichment.captioner.free_only "
        "to false to allow paid models, or pick a ':free' slug / 'openrouter/free'.",
        where, slug,
    )
    return False
