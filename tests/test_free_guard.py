"""The free-tools guard: only free OpenRouter models are allowed by default."""

from __future__ import annotations

from pathlib import Path

from grounded_retrieval.config import load_config
from grounded_retrieval.enrichment import Captioner
from grounded_retrieval.free_guard import check_free_model, is_free_openrouter_model


def test_is_free_openrouter_model():
    assert is_free_openrouter_model("openrouter/free")
    assert is_free_openrouter_model("qwen/qwen2.5-vl-7b-instruct:free")
    assert is_free_openrouter_model("meta-llama/llama-3.2-11b-vision-instruct:free")
    assert not is_free_openrouter_model("openai/gpt-4o")        # paid
    assert not is_free_openrouter_model("qwen/qwen2.5-vl-72b-instruct")  # no :free tag
    assert not is_free_openrouter_model("")


def test_check_free_model_refuses_paid_when_free_only():
    assert check_free_model("openai/gpt-4o", free_only=True, where="t") is False
    assert check_free_model("x/y:free", free_only=True, where="t") is True
    # opt-out lets a paid model through (user's explicit choice)
    assert check_free_model("openai/gpt-4o", free_only=False, where="t") is True


def test_captioner_downgrades_paid_model_to_offline(tmp_path, monkeypatch):
    # pretend a key + the SDK are present so backend would resolve to openrouter
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setattr("grounded_retrieval.enrichment.captioner._openrouter_ready",
                        lambda: True)
    cfg = load_config(Path(__file__).resolve().parents[1] / "config" / "default.yaml")
    cfg.data["enrichment"]["captioner"]["cache_dir"] = str(tmp_path / "cap")
    cfg.data["enrichment"]["captioner"]["backend"] = "openrouter"
    cfg.data["enrichment"]["captioner"]["model"] = "openai/gpt-4o"   # paid slug

    cap = Captioner(cfg)
    assert cap.backend == "offline"          # free-only guard refused the paid model

    # with free_only disabled, the paid model is honoured
    cfg.data["enrichment"]["captioner"]["free_only"] = False
    assert Captioner(cfg).backend == "openrouter"
