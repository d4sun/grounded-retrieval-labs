"""Stage [2a] — extract figures as first-class units, with provenance.

For every figure region found in parsing, export the **cropped image file** and record
``doc -> page -> figure_id`` (+ bbox + any nearby caption). The resulting ``Unit`` has its
artefact populated (the image path) but an *empty* ``search_text`` — enrichment fills that
with a caption so the figure becomes retrievable.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..logging_utils import get_logger
from ..parsing.base import ParsedDocument
from ..provenance import Provenance, Unit, UnitType, make_unit_id

log = get_logger("grounded_retrieval.extraction.figures")


def _open(path: str):
    try:
        import pymupdf as fitz
    except Exception:
        import fitz
    return fitz.open(path)


def extract_figures(parsed: ParsedDocument, cfg: Config) -> list[Unit]:
    min_w = float(cfg.get("extraction.figures.min_width", 48))
    min_h = float(cfg.get("extraction.figures.min_height", 48))
    dpi = int(cfg.get("extraction.figures.render_dpi", 150))
    work_dir = cfg.resolve_path("corpus.work_dir", "data/artefacts") / parsed.document.doc_id / "figures"
    work_dir.mkdir(parents=True, exist_ok=True)

    doc_id = parsed.document.doc_id
    units: list[Unit] = []
    pdf = _open(parsed.document.path)
    try:
        for page in parsed.pages:
            local = 0
            fitz_page = pdf[page.page - 1]
            for fr in page.figure_regions:
                # size filter (skip rules/icons)
                if fr.bbox is not None:
                    w = fr.bbox.x1 - fr.bbox.x0
                    h = fr.bbox.y1 - fr.bbox.y0
                    if w < min_w or h < min_h:
                        continue
                img_path = work_dir / f"p{page.page:04d}-fig{local:02d}.png"
                written = _export_figure(pdf, fitz_page, fr, img_path, dpi)
                if written is None:
                    continue
                unit_id = make_unit_id(doc_id, page.page, "fig", local)
                units.append(Unit(
                    unit_type=UnitType.FIGURE,
                    provenance=Provenance(doc_id=doc_id, page=page.page, unit_id=unit_id,
                                          bbox=fr.bbox, source_path=parsed.document.path),
                    search_text="",  # filled by enrichment (captioning)
                    artefact={"image_path": str(written), "kind": "figure"},
                    meta={"nearby_caption": fr.nearby_caption, "xref": fr.xref},
                ))
                local += 1
    finally:
        pdf.close()
    log.info("figures: extracted %d from %s", len(units), doc_id)
    return units


def _export_figure(pdf, fitz_page, fr, out_path: Path, dpi: int) -> Path | None:
    """Prefer the original embedded raster (via xref); else render the bbox region.
    Returns the path actually written (extension may differ from out_path), or None."""
    # 1) embedded image bytes
    if fr.xref:
        try:
            info = pdf.extract_image(fr.xref)
            if info and info.get("image"):
                ext = info.get("ext", "png")
                real = out_path.with_suffix("." + ext)
                real.write_bytes(info["image"])
                if real.exists() and real.stat().st_size > 0:
                    return real
        except Exception as e:  # noqa: BLE001
            log.debug("extract_image xref=%s failed: %s", fr.xref, e)
    # 2) render the region
    try:
        clip = None
        if fr.bbox is not None:
            try:
                import pymupdf as fitz
            except Exception:
                import fitz
            clip = fitz.Rect(*fr.bbox.as_tuple())
        pix = fitz_page.get_pixmap(dpi=dpi, clip=clip)
        pix.save(out_path)
        return out_path if out_path.exists() and out_path.stat().st_size > 0 else None
    except Exception as e:  # noqa: BLE001
        log.debug("render figure failed: %s", e)
        return None
