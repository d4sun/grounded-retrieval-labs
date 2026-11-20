"""Stage [2b] — extract tables as first-class units, preserving structure.

A table is kept as **structured rows/cols** (the artefact we return) plus a source-page
reference. Enrichment later produces a *linearised* search_text copy; the structure itself
is never flattened — flattening is the "table flattening" failure mode we engineer against.

Backends:
- ``pymupdf``  : use cells already found by ``find_tables`` during parsing (default/offline).
- ``camelot``  : re-detect with Camelot (lattice/stream) for tricky ruled tables.
- ``pdfplumber``: pdfplumber's table finder.
``auto`` uses parsing's cells when present, else tries pdfplumber.
"""

from __future__ import annotations

from ..config import Config
from ..logging_utils import get_logger
from ..parsing.base import ParsedDocument, TableRegion
from ..provenance import Provenance, Unit, UnitType, make_unit_id

log = get_logger("grounded_retrieval.extraction.tables")


def _clean(cells):
    """Normalise to list[list[str]], dropping fully-empty rows."""
    out = []
    for row in cells or []:
        norm = ["" if c is None else str(c).strip() for c in row]
        if any(norm):
            out.append(norm)
    return out


def _valid(cells, min_rows: int, min_cols: int) -> bool:
    if not cells or len(cells) < min_rows:
        return False
    width = max(len(r) for r in cells)
    return width >= min_cols


def extract_tables(parsed: ParsedDocument, cfg: Config) -> list[Unit]:
    backend = cfg.get("extraction.tables.backend", "auto")
    min_rows = int(cfg.get("extraction.tables.min_rows", 2))
    min_cols = int(cfg.get("extraction.tables.min_cols", 2))
    doc_id = parsed.document.doc_id
    units: list[Unit] = []

    for page in parsed.pages:
        local = 0
        regions = list(page.table_regions)

        # If parsing didn't find tables (or backend forces re-detection), try pdfplumber.
        need_detect = backend in ("pdfplumber", "camelot") or all(r.cells is None for r in regions)
        if need_detect:
            detected = _detect(parsed.document.path, page.page, backend)
            if detected:
                regions = detected

        for r in regions:
            cells = _clean(r.cells)
            if not _valid(cells, min_rows, min_cols):
                continue
            unit_id = make_unit_id(doc_id, page.page, "tbl", local)
            units.append(Unit(
                unit_type=UnitType.TABLE,
                provenance=Provenance(doc_id=doc_id, page=page.page, unit_id=unit_id,
                                      bbox=r.bbox, source_path=parsed.document.path),
                search_text="",  # filled by enrichment (linearisation)
                artefact={"cells": cells, "kind": "table", "n_rows": len(cells),
                          "n_cols": max(len(x) for x in cells)},
                meta={"nearby_caption": r.nearby_caption},
            ))
            local += 1
    log.info("tables: extracted %d from %s", len(units), doc_id)
    return units


def _detect(path: str, page_no: int, backend: str) -> list[TableRegion]:
    if backend == "camelot":
        try:
            return _camelot(path, page_no)
        except Exception as e:  # noqa: BLE001
            log.warning("camelot failed on p.%d (%s); trying pdfplumber", page_no, e)
    try:
        return _pdfplumber(path, page_no)
    except Exception as e:  # noqa: BLE001
        log.debug("pdfplumber table detect failed on p.%d: %s", page_no, e)
        return []


def _pdfplumber(path: str, page_no: int) -> list[TableRegion]:
    import pdfplumber

    out: list[TableRegion] = []
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_no - 1]
        for tbl in page.find_tables() or []:
            try:
                cells = tbl.extract()
            except Exception:
                cells = None
            bb = getattr(tbl, "bbox", None)
            from ..provenance import BBox
            bbox = BBox(*bb) if bb else None
            out.append(TableRegion(page=page_no, bbox=bbox, cells=cells))
    return out


def _camelot(path: str, page_no: int) -> list[TableRegion]:
    import camelot

    out: list[TableRegion] = []
    tables = camelot.read_pdf(path, pages=str(page_no), flavor="lattice")
    if tables.n == 0:
        tables = camelot.read_pdf(path, pages=str(page_no), flavor="stream")
    for t in tables:
        cells = t.df.values.tolist()
        out.append(TableRegion(page=page_no, bbox=None, cells=cells))
    return out
