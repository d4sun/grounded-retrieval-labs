"""Stages [4]+[5] tests: build a mixed index and retrieve with provenance."""

from __future__ import annotations

from pathlib import Path

from grounded_retrieval.config import load_config
from grounded_retrieval.enrichment import Captioner, linearise_units
from grounded_retrieval.extraction import extract_figures, extract_tables
from grounded_retrieval.indexing import Embedder, VectorIndex, chunk_document
from grounded_retrieval.parsing import parse_document
from grounded_retrieval.provenance import UnitType
from grounded_retrieval.retrieval import Retriever
from tests._fixtures import make_test_pdf


def _build_units(tmp_path):
    cfg = load_config(Path(__file__).resolve().parents[1] / "config" / "default.yaml")
    cfg.data["corpus"]["work_dir"] = str(tmp_path / "artefacts")
    cfg.data["enrichment"]["captioner"]["cache_dir"] = str(tmp_path / "cap")
    cfg.data["enrichment"]["captioner"]["backend"] = "offline"
    cfg.data["indexing"]["embedder"]["backend"] = "hashing"
    pdf = make_test_pdf(tmp_path / "manual.pdf")
    parsed, _ = parse_document(pdf, cfg)
    figs = extract_figures(parsed, cfg)
    tables = extract_tables(parsed, cfg)
    Captioner(cfg).caption_units(figs)
    linearise_units(tables, cfg)
    texts = chunk_document(parsed, cfg)
    units = texts + figs + tables
    return cfg, units


def test_index_build_search_and_provenance(tmp_path):
    cfg, units = _build_units(tmp_path)
    # all three unit types present
    kinds = {u.unit_type for u in units}
    assert kinds == {UnitType.TEXT, UnitType.FIGURE, UnitType.TABLE}
    # every unit has resolvable provenance
    assert all(u.has_provenance for u in units)

    for backend in ("numpy", "faiss"):
        idx = VectorIndex.build(units, Embedder(cfg), backend=backend)
        r = Retriever(idx, Embedder(cfg), cfg)
        hits = r.retrieve("relay control wiring diagram", k=3)
        assert hits, f"no hits with backend {backend}"
        # the figure (its caption mentions the wiring diagram) should surface
        assert any(h.unit.unit_type is UnitType.FIGURE for h in hits)
        # every hit carries a citation
        assert all("p." in h.citation for h in hits)


def test_bm25_fusion_finds_exact_fault_code(tmp_path):
    cfg, units = _build_units(tmp_path)
    cfg.data["retrieval"]["fusion"]["bm25"] = True
    idx = VectorIndex.build(units, Embedder(cfg), backend="numpy")
    r = Retriever(idx, Embedder(cfg), cfg)
    hits = r.retrieve("E-214", k=3)
    # exact-identifier lexical match: top hit is prose text that literally contains the code
    top = hits[0]
    assert top.unit.unit_type is UnitType.TEXT
    assert "e-214" in top.unit.search_text.lower()


def test_bm25_ranks_rare_identifier():
    """BM25 scoring on a non-degenerate corpus: a rare code outranks common prose."""
    from grounded_retrieval.provenance import Provenance, Unit, UnitType as UT
    from grounded_retrieval.retrieval import BM25Lexical

    def txt(i, body):
        return Unit(UT.TEXT, Provenance("d", i, f"d-p{i}-txt-00"), search_text=body)

    corpus = [
        txt(1, "general maintenance of the electrical system and buses"),
        txt(2, "the master relay coil open fault is code E-214 on this bus"),
        txt(3, "routine inspection of lighting and avionics power"),
        txt(4, "torque the terminals and verify continuity across the relay"),
        txt(5, "battery and generator distribution to the avionics bus"),
    ]
    bm = BM25Lexical(corpus)
    scores = bm.scores("E-214")
    assert scores.argmax() == 1          # the doc with the rare code wins
    assert float(scores[1]) > 0


def test_index_save_load_roundtrip(tmp_path):
    cfg, units = _build_units(tmp_path)
    idx = VectorIndex.build(units, Embedder(cfg), backend="numpy")
    out = tmp_path / "index"
    idx.save(out)
    r = Retriever.from_index_dir(out, cfg)
    hits = r.retrieve("torque specification", k=2)
    assert hits and all(h.unit.has_provenance for h in hits)
