"""Typed-ish configuration loader.

Loads ``config/default.yaml`` (or any YAML), supports dotted lookups, and lets
environment variables override secrets (never put keys in the YAML).

    cfg = load_config("config/default.yaml")
    cfg.get("indexing.embedder.backend", "auto")
    cfg["retrieval"]["top_k"]
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - pyyaml is a core dep
    raise ImportError("pyyaml is required: pip install pyyaml") from exc

log = logging.getLogger("grounded_retrieval.config")

_MISSING = object()


@dataclass
class Config:
    """A thin wrapper over a nested config dict with dotted access."""

    data: dict = field(default_factory=dict)
    source_path: Path | None = None

    def get(self, dotted_key: str, default: Any = _MISSING) -> Any:
        node: Any = self.data
        for part in dotted_key.split("."):
            if isinstance(node, Mapping) and part in node:
                node = node[part]
            else:
                if default is _MISSING:
                    raise KeyError(f"config key not found: {dotted_key!r}")
                return default
        return node

    def section(self, dotted_key: str) -> "Config":
        node = self.get(dotted_key, {})
        if not isinstance(node, Mapping):
            raise KeyError(f"config section {dotted_key!r} is not a mapping")
        return Config(dict(node), self.source_path)

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __contains__(self, key: str) -> bool:
        return key in self.data

    # --- environment-backed secrets --------------------------------------
    @staticmethod
    def openrouter_api_key() -> str | None:
        return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")

    def resolve_path(self, dotted_key: str, default: str | None = None) -> Path:
        value = self.get(dotted_key, default)
        if value is None:
            raise KeyError(f"no path configured at {dotted_key!r}")
        p = Path(value)
        if not p.is_absolute() and self.source_path is not None:
            # paths in config are relative to the repo root (config file's parent's parent)
            root = self.source_path.resolve().parent.parent
            p = root / p
        return p


def load_config(path: str | os.PathLike | None = None) -> Config:
    """Load a YAML config. If *path* is None, fall back to config/default.yaml
    relative to the repository root."""
    if path is None:
        root = Path(__file__).resolve().parents[2]
        path = root / "config" / "default.yaml"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"config file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping, got {type(data).__name__}")
    log.debug("loaded config from %s", path)
    return Config(data, source_path=path)
