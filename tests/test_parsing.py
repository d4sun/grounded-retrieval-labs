"""Stage [1] tests: parsing routes content types and carries page numbers."""

from __future__ import annotations

from pathlib import Path

from grounded_retrieval.config import load_config
from grounded_retrieval.parsing import parse_document
from grounded_retrieval.parsing.ocr import garbled_ratio
from tests._fixtures import make_test_pdf


def _cfg():
    return load_config(Path(__file__).resolve().parents[1] / "config" / "default.yaml")


def test_parse_routes_text_figure_table(tmp_path):
    pdf = make_test_pdf(tmp_path / "manual.pdf")
    parsed, flags = parse_document(pdf, _cfg())

    assert parsed.document.doc_id == "manual"
    assert len(parsed.pages) == 2

    p1, p2 = parsed.pages
    # page 1 is prose: no figures/tables
    assert not p1.is_scanned
    assert p1.figure_regions == []
    assert p1.table_regions == []
    assert "relay control" in p1.full_text.lower()

    # page 2 has a figure and a table, each on the right page
    assert len(p2.figure_regions) == 1
    assert p2.figure_regions[0].page == 2
    assert "figure" in p2.figure_regions[0].nearby_caption.lower()

    assert len(p2.table_regions) == 1
    assert p2.table_regions[0].page == 2
    assert p2.table_regions[0].cells is not None
    assert len(p2.table_regions[0].cells) == 4  # header + 3 rows

    # a clean digital PDF yields no OCR review flags
    assert flags == []


def test_garbled_ratio_gate():
    assert garbled_ratio("clean readable text") < 0.1
    assert garbled_ratio("@#$%^&*(){}<>~`") > 0.8
    assert garbled_ratio("") == 1.0
