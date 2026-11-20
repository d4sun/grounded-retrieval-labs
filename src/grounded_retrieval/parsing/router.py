"""Parse & route — stage [1].

Picks a loader (Docling preferred, PyMuPDF fallback), then routes each page:

- pages with a text layer keep their extracted text,
- **scanned** (image-only) pages are rendered and sent through OCR behind a quality gate,
- pages whose OCR fails the gate are recorded in a **review queue** rather than indexed.

Returns the ``ParsedDocument`` plus a list of ``review_flags`` (one per failed page).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..config import Config
from ..logging_utils import get_logger
from . import docling_loader, ocr as ocr_mod, pymupdf_loader
from .base import ParsedDocument

log = get_logger("grounded_retrieval.parsing.router")


@dataclass
class ReviewFlag:
    doc_id: str
    page: int
    reason: str
    mean_confidence: float
    garbled_ratio: float


def resolve_loader(backend: str) -> str:
    if backend == "auto":
        return "docling" if docling_loader.available() else "pymupdf"
    return backend


def parse_document(path: str | Path, cfg: Config) -> tuple[ParsedDocument, list[ReviewFlag]]:
    max_pages = cfg.get("corpus.max_pages", None)
    loader_backend = resolve_loader(cfg.get("parsing.loader.backend", "auto"))

    if loader_backend == "docling":
        try:
            parsed = docling_loader.load(path, max_pages=max_pages)
        except Exception as e:  # noqa: BLE001
            log.warning("docling failed (%s); falling back to pymupdf", e)
            parsed = pymupdf_loader.load(path, max_pages=max_pages)
    else:
        parsed = pymupdf_loader.load(path, max_pages=max_pages)

    review_flags = _route_ocr(path, parsed, cfg)
    return parsed, review_flags


def _route_ocr(path: str | Path, parsed: ParsedDocument, cfg: Config) -> list[ReviewFlag]:
    ocr_backend = ocr_mod.resolve_backend(cfg.get("parsing.ocr.backend", "auto"))
    scanned_pages = [p for p in parsed.pages if p.is_scanned]
    flags: list[ReviewFlag] = []
    if not scanned_pages:
        return flags

    if ocr_backend == "off":
        for p in scanned_pages:
            p.meta["ocr"] = {"applied": False, "reason": "OCR backend off / tesseract unavailable"}
            flags.append(ReviewFlag(parsed.document.doc_id, p.page,
                                    "scanned page, OCR unavailable", -1.0, 1.0))
            log.warning("scanned p.%d but OCR unavailable -> review queue", p.page)
        return flags

    # render + OCR each scanned page (rendering uses PyMuPDF regardless of loader)
    try:
        import pymupdf as fitz
    except Exception:
        import fitz
    work_dir = cfg.resolve_path("corpus.work_dir", "data/artefacts") / parsed.document.doc_id / "ocr"
    work_dir.mkdir(parents=True, exist_ok=True)
    dpi = int(cfg.get("extraction.figures.render_dpi", 150))
    min_conf = float(cfg.get("parsing.ocr.min_mean_confidence", 55.0))
    max_garbled = float(cfg.get("parsing.ocr.max_garbled_ratio", 0.30))
    langs = cfg.get("parsing.ocr.languages", "eng")

    pdf = fitz.open(str(path))
    try:
        for p in scanned_pages:
            page = pdf[p.page - 1]
            pix = page.get_pixmap(dpi=dpi)
            img_path = work_dir / f"page-{p.page:04d}.png"
            pix.save(img_path)
            res = ocr_mod.ocr_page_image(img_path, languages=langs,
                                         min_confidence=min_conf, max_garbled=max_garbled)
            p.full_text = res.text
            p.meta["ocr"] = {
                "applied": res.applied, "passed_gate": res.passed_gate,
                "mean_confidence": res.mean_confidence, "garbled_ratio": res.garbled_ratio,
                "reason": res.reason, "image": str(img_path),
            }
            if not res.passed_gate:
                flags.append(ReviewFlag(parsed.document.doc_id, p.page, res.reason,
                                        res.mean_confidence, res.garbled_ratio))
    finally:
        pdf.close()
    return flags


def write_review_queue(flags: list[ReviewFlag], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump([f.__dict__ for f in flags], fh, indent=2)
    if flags:
        log.info("wrote %d review flags to %s", len(flags), path)
