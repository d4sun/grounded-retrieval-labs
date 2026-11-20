"""Stage [2] tests: figures and tables become first-class units with provenance."""

from __future__ import annotations

from pathlib import Path

from grounded_retrieval.config import load_config
from grounded_retrieval.extraction import extract_figures, extract_tables
from grounded_retrieval.parsing import parse_document
from grounded_retrieval.provenance import UnitType
from tests._fixtures import make_test_pdf


def _ingest(tmp_path):
    cfg = load_config(Path(__file__).resolve().parents[1] / "config" / "default.yaml")
    # redirect work_dir into tmp so tests don't litter the repo
    cfg.data["corpus"]["work_dir"] = str(tmp_path / "artefacts")
    pdf = make_test_pdf(tmp_path / "manual.pdf")
    parsed, _ = parse_document(pdf, cfg)
    return cfg, parsed


def test_extract_figures_have_image_and_provenance(tmp_path):
    cfg, parsed = _ingest(tmp_path)
    figs = extract_figures(parsed, cfg)
    assert len(figs) == 1
    f = figs[0]
    assert f.unit_type is UnitType.FIGURE
    assert f.has_provenance and f.provenance.page == 2
    img = Path(f.artefact["image_path"])
    assert img.exists() and img.stat().st_size > 0        # the REAL artefact was written
    assert "figure" in f.meta["nearby_caption"].lower()   # caption carried for retrieval
    assert f.search_text == ""                            # enrichment fills this later


def test_extract_tables_preserve_structure(tmp_path):
    cfg, parsed = _ingest(tmp_path)
    tables = extract_tables(parsed, cfg)
    assert len(tables) == 1
    t = tables[0]
    assert t.unit_type is UnitType.TABLE
    assert t.has_provenance and t.provenance.page == 2
    cells = t.artefact["cells"]
    # Real PDF table extractors mangle spacing/newlines inside cells; what we assert is
    # that the STRUCTURE (grid shape + content) survived, not exact glyph spacing.
    header_norm = ["".join(c.split()).lower() for c in cells[0]]
    assert header_norm == ["terminal", "torque(in-lb)", "faultcode"]
    flat = " ".join(c for row in cells for c in row)
    assert "214" in flat and "215" in flat            # fault-code content preserved
    assert t.artefact["n_rows"] == 4 and t.artefact["n_cols"] == 3
