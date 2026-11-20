"""Prose chunking → TEXT units (part of stage [4]).

Chunk prose by page and structure into TEXT units carrying provenance. Tables and
figure-captions are *never* split — they're already whole units from extraction. A chunk
never spans pages, so every chunk keeps a single, resolvable page citation.
"""

from __future__ import annotations

import re

from ..config import Config
from ..parsing.base import ParsedDocument
from ..provenance import Provenance, Unit, UnitType, make_unit_id

_PARA = re.compile(r"\n\s*\n")


def _split_paragraphs(text: str) -> list[str]:
    parts = _PARA.split(text)
    return [" ".join(p.split()) for p in parts if p.strip()]


def _chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Greedy paragraph packing with character overlap between consecutive chunks."""
    paras = _split_paragraphs(text)
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if not cur:
            cur = p
        elif len(cur) + 1 + len(p) <= max_chars:
            cur += " " + p
        else:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap > 0 else ""
            cur = (tail + " " + p).strip() if tail else p
    if cur:
        chunks.append(cur)
    # hard-split any oversized single paragraph
    out: list[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            out.append(c)
        else:
            for i in range(0, len(c), max_chars - overlap):
                out.append(c[i:i + max_chars])
    return [c for c in out if c.strip()]


def chunk_document(parsed: ParsedDocument, cfg: Config) -> list[Unit]:
    max_chars = int(cfg.get("indexing.chunking.max_chars", 1200))
    overlap = int(cfg.get("indexing.chunking.overlap", 150))
    doc_id = parsed.document.doc_id
    units: list[Unit] = []
    for page in parsed.pages:
        text = page.full_text or "\n\n".join(b.text for b in page.text_blocks)
        if not text.strip():
            continue
        for local, chunk in enumerate(_chunk_text(text, max_chars, overlap)):
            uid = make_unit_id(doc_id, page.page, "txt", local)
            units.append(Unit(
                unit_type=UnitType.TEXT,
                provenance=Provenance(doc_id=doc_id, page=page.page, unit_id=uid,
                                      source_path=parsed.document.path),
                search_text=chunk,
                artefact={"text": chunk, "kind": "text"},
                meta={"ocr": page.meta.get("ocr")},
            ))
    return units
