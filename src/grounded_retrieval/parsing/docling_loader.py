"""Docling loader — the preferred (free, open) structural parser.

Docling (IBM, MIT) gives figures, tables, layout, and reading order in one pass, which
is most of the routing for free. It's an optional/heavy dependency, so this module
imports it lazily and the router falls back to PyMuPDF when it isn't installed.

Docling's API has moved across versions; this adapter targets the ``DocumentConverter``
interface and degrades gracefully (it extracts what it can and leaves the rest to the
PyMuPDF-based figure/table extractors downstream).
"""

from __future__ import annotations

from pathlib import Path

from ..logging_utils import get_logger
from ..provenance import BBox, Document, doc_id_from_path
from .base import FigureRegion, PageParse, ParsedDocument, TableRegion, TextBlock

log = get_logger("grounded_retrieval.parsing.docling")


def available() -> bool:
    try:
        import docling  # noqa: F401
        return True
    except Exception:
        return False


def _bbox_from_prov(item) -> BBox | None:
    try:
        prov = item.prov[0]
        bb = prov.bbox
        return BBox(float(bb.l), float(bb.t), float(bb.r), float(bb.b))
    except Exception:
        return None


def _page_of(item) -> int | None:
    try:
        return int(item.prov[0].page_no)
    except Exception:
        return None


def load(path: str | Path, max_pages: int | None = None) -> ParsedDocument:
    """Parse with Docling. Raises if docling isn't importable (router guards this)."""
    from docling.document_converter import DocumentConverter  # lazy

    path = Path(path)
    doc_id = doc_id_from_path(path)
    converter = DocumentConverter()
    result = converter.convert(str(path))
    dl = result.document

    # page count
    try:
        num_pages = len(dl.pages)
    except Exception:
        num_pages = 0
    document = Document(doc_id=doc_id, path=str(path), num_pages=num_pages)
    parsed = ParsedDocument(document=document)

    pages: dict[int, PageParse] = {}

    def page_obj(n: int) -> PageParse:
        if n not in pages:
            pages[n] = PageParse(page=n)
        return pages[n]

    # texts
    for item in getattr(dl, "texts", []) or []:
        pno = _page_of(item)
        if pno is None:
            continue
        if max_pages and pno > max_pages:
            continue
        txt = getattr(item, "text", "") or ""
        if txt.strip():
            pp = page_obj(pno)
            pp.text_blocks.append(TextBlock(page=pno, text=txt.strip(),
                                            bbox=_bbox_from_prov(item)))
            pp.full_text += txt.strip() + "\n"

    # pictures / figures
    for item in getattr(dl, "pictures", []) or []:
        pno = _page_of(item)
        if pno is None or (max_pages and pno > max_pages):
            continue
        cap = ""
        try:
            cap = item.caption_text(dl) or ""
        except Exception:
            cap = ""
        page_obj(pno).figure_regions.append(
            FigureRegion(page=pno, bbox=_bbox_from_prov(item), nearby_caption=cap,
                         meta={"source": "docling"})
        )

    # tables
    for item in getattr(dl, "tables", []) or []:
        pno = _page_of(item)
        if pno is None or (max_pages and pno > max_pages):
            continue
        cells = None
        try:
            df = item.export_to_dataframe()
            cells = [list(map(str, df.columns))] + df.astype(str).values.tolist()
        except Exception:
            cells = None
        cap = ""
        try:
            cap = item.caption_text(dl) or ""
        except Exception:
            pass
        page_obj(pno).table_regions.append(
            TableRegion(page=pno, bbox=_bbox_from_prov(item), cells=cells,
                        nearby_caption=cap, meta={"source": "docling"})
        )

    for n in sorted(pages):
        parsed.pages.append(pages[n])
    log.info("docling: parsed %s (%d pages)", doc_id, len(parsed.pages))
    return parsed
