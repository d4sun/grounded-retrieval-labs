"""The data backbone: documents, pages, and the retrievable ``Unit``.

Everything the system stores, searches, and hands back is a ``Unit`` that carries
``document -> page -> id`` provenance. This is what lets an answer *show and cite the
real figure/table* instead of paraphrasing it.

Design rule (the whole point of Lab A): a ``Unit`` with no resolvable page is
**not a valid sourced answer**. ``Unit.has_provenance`` is the gate the answering
layer checks before presenting anything as sourced.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable


class UnitType(str, enum.Enum):
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"


@dataclass(frozen=True)
class BBox:
    """Bounding box in PDF points, origin top-left."""

    x0: float
    y0: float
    x1: float
    y1: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)


@dataclass(frozen=True)
class Provenance:
    """`document -> page -> id`. The citation handle for a unit."""

    doc_id: str
    page: int                       # 1-indexed page number
    unit_id: str                    # stable id, unique within the corpus
    bbox: BBox | None = None
    source_path: str | None = None  # original PDF path, for display/debug

    def is_resolvable(self) -> bool:
        """True iff this provenance can name a concrete page of a concrete doc."""
        return bool(self.doc_id) and isinstance(self.page, int) and self.page >= 1

    def citation(self) -> str:
        """Human-facing citation string, e.g. 'amt_handbook p.212'."""
        return f"{self.doc_id} p.{self.page}"


@dataclass
class Document:
    doc_id: str
    path: str
    num_pages: int = 0
    title: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Page:
    doc_id: str
    page: int
    is_scanned: bool = False
    ocr_applied: bool = False
    ocr_passed_gate: bool | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Unit:
    """The atom of retrieval.

    ``search_text`` is what we embed/index (a prose chunk, a figure *caption*, or a
    *linearised* table). ``artefact`` is what we *return* (the text span itself, the
    path to the figure image, or the structured table rows). Keeping them separate is
    the "retrieve-by-text, answer-with-artefact" split.
    """

    unit_type: UnitType
    provenance: Provenance
    search_text: str = ""
    artefact: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    @property
    def unit_id(self) -> str:
        return self.provenance.unit_id

    @property
    def has_provenance(self) -> bool:
        return self.provenance.is_resolvable()

    def citation(self) -> str:
        return self.provenance.citation()

    # --- serialization (jsonl-friendly) -------------------------------- #
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["unit_type"] = self.unit_type.value
        # BBox inside provenance serialises as a dict via asdict; normalise None
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Unit":
        prov = d["provenance"]
        bbox = prov.get("bbox")
        provenance = Provenance(
            doc_id=prov["doc_id"],
            page=prov["page"],
            unit_id=prov["unit_id"],
            bbox=BBox(**bbox) if bbox else None,
            source_path=prov.get("source_path"),
        )
        return cls(
            unit_type=UnitType(d["unit_type"]),
            provenance=provenance,
            search_text=d.get("search_text", ""),
            artefact=d.get("artefact", {}) or {},
            meta=d.get("meta", {}) or {},
        )


# ---------------------------------------------------------------------- #
# id helpers
# ---------------------------------------------------------------------- #
def doc_id_from_path(path: str | Path) -> str:
    """Stable, readable doc id from a filename (stem, slugified)."""
    stem = Path(path).stem.lower()
    slug = "".join(c if c.isalnum() else "_" for c in stem).strip("_")
    return slug or hashlib.sha1(str(path).encode()).hexdigest()[:10]


def make_unit_id(doc_id: str, page: int, kind: str, local_index: int) -> str:
    """Deterministic unit id: e.g. 'amt_handbook-p212-fig-03'."""
    return f"{doc_id}-p{page}-{kind}-{local_index:02d}"


# ---------------------------------------------------------------------- #
# jsonl persistence for a corpus of units
# ---------------------------------------------------------------------- #
def write_units_jsonl(units: Iterable[Unit], path: str | Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for u in units:
            fh.write(json.dumps(u.to_dict(), ensure_ascii=False) + "\n")
            n += 1
    return n


def read_units_jsonl(path: str | Path) -> list[Unit]:
    path = Path(path)
    units: list[Unit] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                units.append(Unit.from_dict(json.loads(line)))
    return units
