"""Intermediate representation produced by a loader, consumed by extraction.

A loader's only job is **parse & route**: turn a PDF into, per page, its text blocks,
its *figure regions*, its *table regions*, and a flag for whether the page is scanned
(image-only). The heavier work — cropping figure images, pulling structured table rows —
is the extraction stage's job, driven by the regions found here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..provenance import BBox, Document


@dataclass
class TextBlock:
    page: int
    text: str
    bbox: BBox | None = None


@dataclass
class FigureRegion:
    """A detected figure/image on a page. ``xref`` is a PyMuPDF image reference when
    the figure is an embedded raster; otherwise the region is rendered from ``bbox``."""

    page: int
    bbox: BBox | None = None
    xref: int | None = None
    nearby_caption: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableRegion:
    """A detected table. ``cells`` may be pre-filled by loaders that can (PyMuPDF
    ``find_tables``); otherwise the extraction stage fills it."""

    page: int
    bbox: BBox | None = None
    cells: list[list[str]] | None = None
    nearby_caption: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class PageParse:
    page: int
    is_scanned: bool = False
    full_text: str = ""
    text_blocks: list[TextBlock] = field(default_factory=list)
    figure_regions: list[FigureRegion] = field(default_factory=list)
    table_regions: list[TableRegion] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    document: Document
    pages: list[PageParse] = field(default_factory=list)

    def page(self, n: int) -> PageParse | None:
        for p in self.pages:
            if p.page == n:
                return p
        return None
