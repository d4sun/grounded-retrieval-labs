"""End-to-end smoke test: sample corpus -> ingest -> answer -> evaluate, fully offline."""

from __future__ import annotations

from pathlib import Path

from grounded_retrieval.config import load_config
from grounded_retrieval.evaluation import evaluate, load_gold
from grounded_retrieval.pipeline import Pipeline
from grounded_retrieval.sample_corpus import build_sample_corpus


def _cfg(tmp_path):
    cfg = load_config(Path(__file__).resolve().parents[1] / "config" / "default.yaml")
    # force offline/local-free backends and redirect all outputs into tmp
    cfg.data["corpus"]["input_dir"] = str(tmp_path / "sample")
    cfg.data["corpus"]["work_dir"] = str(tmp_path / "artefacts")
    cfg.data["corpus"]["index_dir"] = str(tmp_path / "index")
    cfg.data["enrichment"]["captioner"]["backend"] = "offline"
    cfg.data["enrichment"]["captioner"]["cache_dir"] = str(tmp_path / "cap")
    cfg.data["indexing"]["embedder"]["backend"] = "hashing"
    cfg.data["indexing"]["index"]["backend"] = "numpy"
    cfg.source_path = Path(__file__).resolve().parents[1] / "config" / "default.yaml"
    return cfg


def test_full_pipeline_offline(tmp_path):
    cfg = _cfg(tmp_path)
    build_sample_corpus(tmp_path / "sample")

    pipe = Pipeline(cfg)
    stats = pipe.ingest()
    assert stats.docs == 1
    assert stats.by_type["figure"] >= 2        # wiring diagram + exploded view
    assert stats.by_type["table"] >= 1
    assert stats.by_type["text"] >= 2
    assert stats.review_flags == 0             # clean digital PDF

    # a figure question returns the real image
    ans = pipe.answer("relay control wiring diagram")
    assert ans.answer_type == "figure"
    assert Path(ans.artefact["image_path"]).exists()
    assert ans.citation.startswith("amt_handbook_excerpt p.")

    # evaluation finds the evidence pages
    gold = load_gold(tmp_path / "sample" / "gold_questions.json")
    report = evaluate(pipe.load_retriever(), gold, k_values=[1, 3, 5], by_type=True)
    assert report["n"] == 5
    assert report["overall"]["recall_at"][5] >= 0.8    # most questions hit evidence in top-5
    assert set(report["by_type"]) == {"figure", "table", "text"}
