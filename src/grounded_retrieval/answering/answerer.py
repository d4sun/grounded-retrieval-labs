"""Answer — return the artefact, not a paraphrase (stage [6]).

Given a query: retrieve, **decide the answer type** (text | figure | table) from the
top sourced hit, and return the **real artefact** with its page citation:

- figure answer → the actual figure image path + page (+ a one-line grounded caption),
- table answer  → the exact structured rows + page,
- text answer   → the text span + page.

**Fail closed** (``answering.fail_closed``): a retrieved unit with no resolvable
provenance is never presented as a sourced answer. If nothing sourced is retrieved, the
answer type is ``none`` with a reason — we would rather abstain than cite nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..config import Config
from ..logging_utils import get_logger
from ..provenance import UnitType
from ..retrieval.retriever import RetrievedUnit, Retriever

log = get_logger("grounded_retrieval.answering.answerer")


@dataclass
class Answer:
    query: str
    answer_type: str                 # text | figure | table | none
    citation: str | None = None
    artefact: dict[str, Any] = field(default_factory=dict)
    grounded_caption: str | None = None
    support: list[RetrievedUnit] = field(default_factory=list)
    reason: str = ""

    @property
    def is_sourced(self) -> bool:
        return self.answer_type != "none" and bool(self.citation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer_type": self.answer_type,
            "citation": self.citation,
            "artefact": self.artefact,
            "grounded_caption": self.grounded_caption,
            "reason": self.reason,
            "support": [
                {"unit_id": h.unit.unit_id, "type": h.unit.unit_type.value,
                 "citation": h.citation, "score": round(h.score, 4)}
                for h in self.support
            ],
        }


def _first_line(text: str, limit: int = 160) -> str:
    text = " ".join((text or "").split())
    m = re.split(r"(?<=[.!?])\s", text, maxsplit=1)
    line = m[0] if m else text
    return line[:limit].strip()


class Answerer:
    def __init__(self, retriever: Retriever, cfg: Config):
        self.retriever = retriever
        self.cfg = cfg
        self.fail_closed = bool(cfg.get("answering.fail_closed", True))
        self.k = int(cfg.get("retrieval.top_k", 8))

    def answer(self, query: str, k: int | None = None) -> Answer:
        hits = self.retriever.retrieve(query, k=k or self.k)
        # fail-closed: only units with a resolvable page may be a sourced answer
        sourced = [h for h in hits if h.unit.has_provenance] if self.fail_closed else hits
        dropped = len(hits) - len(sourced)
        if dropped:
            log.warning("fail-closed: dropped %d hit(s) lacking provenance", dropped)

        if not sourced:
            return Answer(query=query, answer_type="none", support=hits,
                          reason="no retrieved unit had resolvable provenance")

        top = sourced[0]
        unit = top.unit
        atype = unit.unit_type.value
        ans = Answer(query=query, answer_type=atype, citation=unit.citation(),
                     support=sourced, reason=f"top sourced hit is a {atype} unit")

        if unit.unit_type is UnitType.FIGURE:
            ans.artefact = {"kind": "figure",
                            "image_path": unit.artefact.get("image_path"),
                            "page": unit.provenance.page, "doc_id": unit.provenance.doc_id}
            ans.grounded_caption = self._grounded_caption(unit)
        elif unit.unit_type is UnitType.TABLE:
            ans.artefact = {"kind": "table", "cells": unit.artefact.get("cells"),
                            "page": unit.provenance.page, "doc_id": unit.provenance.doc_id}
        else:  # TEXT
            ans.artefact = {"kind": "text", "text": unit.artefact.get("text", unit.search_text),
                            "page": unit.provenance.page, "doc_id": unit.provenance.doc_id}
        return ans

    def _grounded_caption(self, unit) -> str:
        """One-line caption grounded in the real figure. The stored caption already came
        from the vision model when ingest used the OpenRouter backend, so we condense it
        rather than making a second API call; offline it uses the printed caption."""
        base = unit.search_text or unit.meta.get("nearby_caption", "") or "Figure"
        return f"{_first_line(base)} — {unit.citation()}"
