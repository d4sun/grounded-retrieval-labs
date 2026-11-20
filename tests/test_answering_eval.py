"""Stages [6]+[7] tests: artefact answers, fail-closed, and by-type metrics."""

from __future__ import annotations

from pathlib import Path

from grounded_retrieval.answering import Answerer
from grounded_retrieval.config import load_config
from grounded_retrieval.enrichment import Captioner, linearise_units
from grounded_retrieval.evaluation import (
    GoldQuestion,
    evaluate,
    faithfulness_spotcheck,
    format_report,
)
from grounded_retrieval.extraction import extract_figures, extract_tables
from grounded_retrieval.indexing import Embedder, VectorIndex, chunk_document
from grounded_retrieval.parsing import parse_document
from grounded_retrieval.provenance import BBox, Provenance, Unit, UnitType
from grounded_retrieval.retrieval import Retriever
from tests._fixtures import make_test_pdf


def _retriever(tmp_path):
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
    units = chunk_document(parsed, cfg) + figs + tables
    idx = VectorIndex.build(units, Embedder(cfg), backend="numpy")
    return cfg, Retriever(idx, Embedder(cfg), cfg)


def test_figure_answer_returns_real_image_and_citation(tmp_path):
    cfg, r = _retriever(tmp_path)
    ans = Answerer(r, cfg).answer("relay control wiring diagram")
    assert ans.answer_type == "figure"
    assert ans.is_sourced and ans.citation.startswith("manual p.")
    img = Path(ans.artefact["image_path"])
    assert img.exists()                                  # the REAL artefact, not prose
    assert ans.grounded_caption and "p." in ans.grounded_caption


def test_fail_closed_drops_unit_without_provenance(tmp_path):
    cfg, r = _retriever(tmp_path)
    # poison the corpus with a provenance-less unit that matches a unique query exactly,
    # so it would rank #1 — then rebuild the index/retriever cleanly around it.
    bad = Unit(UnitType.TEXT, Provenance(doc_id="", page=0, unit_id="bad"),
               search_text="zzzqqq unique poison token", artefact={"text": "x"})
    units = list(r.index.units) + [bad]
    idx = VectorIndex.build(units, Embedder(cfg), backend="numpy")
    r2 = Retriever(idx, Embedder(cfg), cfg)

    # without fail-closed the poison ranks first...
    assert r2.retrieve("zzzqqq unique poison token", k=1)[0].unit.unit_id == "bad"
    # ...but the answerer must never present it as a sourced answer
    ans = Answerer(r2, cfg).answer("zzzqqq unique poison token")
    assert all(h.unit.unit_id != "bad" for h in ans.support)
    assert not (ans.is_sourced and ans.citation == "")


def _gold():
    return [
        GoldQuestion("q1", "relay control wiring diagram", "figure", "manual", [2]),
        GoldQuestion("q2", "bus terminal torque fault codes table", "table", "manual", [2]),
        GoldQuestion("q3", "master relay fault code E-214", "text", "manual", [1, 2]),
    ]


def test_evaluate_by_type_and_faithfulness(tmp_path):
    cfg, r = _retriever(tmp_path)
    report = evaluate(r, _gold(), k_values=[1, 3, 5], by_type=True)
    assert report["n"] == 3
    assert set(report["by_type"]) == {"figure", "table", "text"}
    # recall@5 should find the evidence page for every question in this tiny corpus
    assert report["overall"]["recall_at"][5] == 1.0
    assert isinstance(format_report(report), str)

    cases = faithfulness_spotcheck(Answerer(r, cfg), _gold(), n=3)
    assert len(cases) == 3
    assert all(c.citation for c in cases if c.answered_type != "none")
