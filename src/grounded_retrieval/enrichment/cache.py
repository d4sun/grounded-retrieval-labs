"""A tiny content-addressed disk cache so captioning re-runs are free.

Keyed by a hash of (image bytes + model + prompt). Captions are the one place a free
vision endpoint gets hit, so caching them is the main cost control (playbook §4).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class CaptionCache:
    def __init__(self, cache_dir: str | Path):
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(image_bytes: bytes, model: str, prompt: str) -> str:
        h = hashlib.sha256()
        h.update(image_bytes)
        h.update(b"\x00")
        h.update(model.encode("utf-8"))
        h.update(b"\x00")
        h.update(prompt.encode("utf-8"))
        return h.hexdigest()

    def get(self, key: str) -> str | None:
        p = self.dir / f"{key}.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))["caption"]
            except Exception:
                return None
        return None

    def put(self, key: str, caption: str, meta: dict | None = None) -> None:
        p = self.dir / f"{key}.json"
        p.write_text(json.dumps({"caption": caption, "meta": meta or {}},
                                ensure_ascii=False), encoding="utf-8")
