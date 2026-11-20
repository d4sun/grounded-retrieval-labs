"""PyMuPDF loader — the always-available baseline.

PyMuPDF (``fitz``) is a core dependency, so this loader is the offline fallback for
``parsing.loader.backend: auto`` and the thing the smoke test actually runs. It finds:

- text blocks (and so detects **scanned** pages: no text layer + a big image),
- **figure regions** from embedded images (with their page rectangles + a nearby caption),
- **table regions** via ``page.find_tables()`` when available (PyMuPDF >= 1.23).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..logging_utils import get_logger
from ..provenance import BBox, Document, doc_id_from_path
from .base import FigureRegion, PageParse, ParsedDocument, TableRegion, TextBlock

log = get_logger("grounded_retrieval.parsing.pymupdf")

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24 preferred import name
    _HAS_FITZ = True
except Exception:  # pragma: no cover
    try:
        import fitz  # older PyMuPDF
        _HAS_FITZ = True
    except Exception:
        _HAS_FITZ = False


def available() -> bool:
    return _HAS_FITZ


def _caption_near(blocks: list[tuple], rect) -> str:
    """Heuristic: a short text block directly below a region, often starting
    'Figure'/'Fig'/'Table', is the caption."""
    best = ""
    best_gap = 1e9
    for b in blocks:
        # block = (x0, y0, x1, y1, text, block_no, block_type)
        x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
        if not isinstance(text, str) or not text.strip():
            continue
        below_gap = y0 - rect.y1
        if -5 <= below_gap <= 60 and x0 < rect.x1 and x1 > rect.x0:
            t = text.strip()
            score = below_gap
            if t[:6].lower().startswith(("figure", "fig", "table", "diag")):
                score -= 100
            if score < best_gap:
                best_gap = score
                best = " ".join(t.split())
    return best[:300]


def load(path: str | Path, max_pages: int | None = None) -> ParsedDocument:
    if not _HAS_FITZ:
        raise RuntimeError("PyMuPDF (fitz) is not installed")
    path = Path(path)
    doc_id = doc_id_from_path(path)
    pdf = fitz.open(path)
    num_pages = pdf.page_count if max_pages is None else min(pdf.page_count, max_pages)
    document = Document(doc_id=doc_id, path=str(path), num_pages=pdf.page_count,
                        title=pdf.metadata.get("title") or None)
    parsed = ParsedDocument(document=document)

    for pno in range(num_pages):
        page = pdf[pno]
        page_1 = pno + 1
        raw_text = page.get_text("text") or ""
        try:
            blocks = page.get_text("blocks")
        except Exception:
            blocks = []

        # --- figure regions from embedded images ---
        fig_regions: list[FigureRegion] = []
        try:
            images = page.get_images(full=True)
        except Exception:
            images = []
        page_area = float(page.rect.width * page.rect.height) or 1.0
        biggest_img_frac = 0.0
        for idx, img in enumerate(images):
            xref = img[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            rect = rects[0] if rects else None
            if rect is not None:
                frac = float(rect.width * rect.height) / page_area
                biggest_img_frac = max(biggest_img_frac, frac)
                bbox = BBox(rect.x0, rect.y0, rect.x1, rect.y1)
                caption = _caption_near(blocks, rect)
            else:
                bbox, caption = None, ""
            fig_regions.append(FigureRegion(page=page_1, bbox=bbox, xref=xref,
                                            nearby_caption=caption,
                                            meta={"image_index": idx}))

        # --- scanned detection: no text layer but a page-filling image ---
        is_scanned = (len(raw_text.strip()) < 10) and (biggest_img_frac > 0.6)

        # --- table regions via find_tables (if available) ---
        table_regions: list[TableRegion] = []
        finder = getattr(page, "find_tables", None)
        if callable(finder):
            try:
                tf = finder()
                for t in getattr(tf, "tables", []) or []:
                    try:
                        cells = t.extract()
                    except Exception:
                        cells = None
                    bb = getattr(t, "bbox", None)
                    bbox = BBox(*bb) if bb else None
                    cap = _caption_near(blocks, _RectLike(bb)) if bb else ""
                    table_regions.append(TableRegion(page=page_1, bbox=bbox,
                                                     cells=cells, nearby_caption=cap))
            except Exception as e:  # noqa: BLE001
                log.debug("find_tables failed on p.%d: %s", page_1, e)

        text_blocks = [
            TextBlock(page=page_1, text=b[4].strip(),
                      bbox=BBox(b[0], b[1], b[2], b[3]))
            for b in blocks if isinstance(b[4], str) and b[4].strip()
        ]

        parsed.pages.append(PageParse(
            page=page_1,
            is_scanned=is_scanned,
            full_text=raw_text,
            text_blocks=text_blocks,
            figure_regions=fig_regions,
            table_regions=table_regions,
            meta={"biggest_image_frac": round(biggest_img_frac, 3)},
        ))
    pdf.close()
    log.info("pymupdf: parsed %s (%d pages)", doc_id, len(parsed.pages))
    return parsed


class _RectLike:
    """Adapts a 4-tuple bbox to the .x0/.y0/.x1/.y1 interface _caption_near expects."""

    def __init__(self, bb: Any):
        self.x0, self.y0, self.x1, self.y1 = bb
