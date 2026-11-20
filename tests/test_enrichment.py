"""Stage [3] tests: captioning + linearisation make figures/tables retrievable."""

from __future__ import annotations

from pathlib import Path

from grounded_retrieval.config import load_config
from grounded_retrieval.enrichment import Captioner, linearise_table
from grounded_retrieval.extraction import extract_figures, extract_tables
from grounded_retrieval.parsing import parse_document
from grounded_retrieval.provenance import BBox, Provenance, Unit, UnitType
from tests._fixtures import make_test_pdf


def _ingest(tmp_path):
    cfg = load_config(Path(__file__).resolve().parents[1] / "config" / "default.yaml")
    cfg.data["corpus"]["work_dir"] = str(tmp_path / "artefacts")
    cfg.data["enrichment"]["captioner"]["cache_dir"] = str(tmp_path / "capcache")
    cfg.data["enrichment"]["captioner"]["backend"] = "offline"
    pdf = make_test_pdf(tmp_path / "manual.pdf")
    parsed, _ = parse_document(pdf, cfg)
    return cfg, parsed


def test_offline_captioner_fills_search_text(tmp_path):
    cfg, parsed = _ingest(tmp_path)
    figs = extract_figures(parsed, cfg)
    cap = Captioner(cfg)
    assert cap.backend == "offline"
    n = cap.caption_units(figs)
    assert n == 1
    f = figs[0]
    assert f.search_text != ""                         # now retrievable
    assert "figure" in f.search_text.lower()
    assert f.artefact["image_path"]                     # artefact untouched
    # caching: second pass is served from disk
    f.search_text = ""
    cap.caption_units(figs)
    assert figs[0].meta.get("caption_cached") is True


def test_linearise_normalises_and_keeps_caption():
    u = Unit(
        unit_type=UnitType.TABLE,
        provenance=Provenance("doc", 2, "doc-p2-tbl-00", BBox(0, 0, 1, 1)),
        artefact={"cells": [["Terminal", "Fault\ncode"], ["Main bus A", "E214\n-"]]},
        meta={"nearby_caption": "Table 4-1.  Bus   terminals."},
    )
    md = linearise_table(u, style="markdown")
    assert "Table 4-1. Bus terminals." in md            # caption normalised + kept
    assert "| Terminal | Fault code |" in md            # cell newline collapsed
    kv = linearise_table(u, style="kv")
    assert "Terminal=Main bus A" in kv
