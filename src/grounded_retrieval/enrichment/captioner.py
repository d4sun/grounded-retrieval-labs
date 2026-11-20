"""Stage [3a] — make figures retrievable by describing them.

Images don't retrieve well on their own; *a description of the image* is what makes it
findable. Each figure image is sent to a free OpenRouter vision model with a search-oriented
prompt, and the caption becomes the figure unit's ``search_text`` — linked to the original
image + page (the artefact and provenance are untouched).

Backends (``enrichment.captioner.backend``):
- ``openrouter`` : free ``:free`` vision model via the OpenAI SDK (OpenRouter base URL).
- ``offline``    : deterministic caption from the nearby caption text + page context.
- ``auto``       : openrouter if a key + the openai SDK are present, else offline.

Captions are cached (``cache.CaptionCache``) so re-runs cost nothing.
"""

from __future__ import annotations

import base64
from pathlib import Path

from ..config import Config
from ..logging_utils import get_logger
from ..provenance import Unit, UnitType
from .cache import CaptionCache

log = get_logger("grounded_retrieval.enrichment.captioner")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _openrouter_ready() -> bool:
    if not (Config.openrouter_api_key()):
        return False
    try:
        import openai  # noqa: F401
        return True
    except Exception:
        return False


class Captioner:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.model = cfg.get("enrichment.captioner.model", "openrouter/free")
        self.prompt = " ".join(
            str(cfg.get("enrichment.captioner.prompt",
                        "Describe this technical figure for search.")).split()
        )
        self.max_figures = cfg.get("enrichment.captioner.max_figures", None)
        self.backend = self._resolve(cfg.get("enrichment.captioner.backend", "auto"))
        cache_dir = cfg.get("enrichment.captioner.cache_dir", ".cache/captions")
        self.cache = CaptionCache(cache_dir)
        self._client = None
        log.info("captioner backend=%s model=%s", self.backend, self.model)

    @staticmethod
    def _resolve(backend: str) -> str:
        if backend == "auto":
            return "openrouter" if _openrouter_ready() else "offline"
        return backend

    # ------------------------------------------------------------------ #
    def caption_units(self, units: list[Unit]) -> int:
        """Caption every FIGURE unit in place. Returns how many were captioned."""
        figures = [u for u in units if u.unit_type is UnitType.FIGURE]
        if self.max_figures is not None:
            figures = figures[: int(self.max_figures)]
        n = 0
        for u in figures:
            caption = self.caption_figure(u)
            u.search_text = caption
            u.meta["caption_backend"] = self.backend
            n += 1
        log.info("captioned %d figures (backend=%s)", n, self.backend)
        return n

    def caption_figure(self, unit: Unit) -> str:
        img_path = unit.artefact.get("image_path")
        nearby = unit.meta.get("nearby_caption", "") or ""
        if not img_path or not Path(img_path).exists():
            return self._offline_text(unit, nearby)

        image_bytes = Path(img_path).read_bytes()
        key = CaptionCache.key(image_bytes, self.model if self.backend == "openrouter"
                               else "offline", self.prompt)
        cached = self.cache.get(key)
        if cached is not None:
            unit.meta["caption_cached"] = True
            return cached

        if self.backend == "openrouter":
            caption = self._openrouter_caption(image_bytes, Path(img_path).suffix)
            if not caption:  # fall back rather than fail the run
                caption = self._offline_text(unit, nearby)
        else:
            caption = self._offline_text(unit, nearby)

        self.cache.put(key, caption, meta={"backend": self.backend,
                                           "citation": unit.citation()})
        return caption

    # ------------------------------------------------------------------ #
    def _offline_text(self, unit: Unit, nearby: str) -> str:
        """Deterministic, network-free caption. Uses the nearby printed caption (the most
        reliable signal) plus page context so the figure is still retrievable."""
        bits = []
        if nearby:
            bits.append(nearby)
        bits.append(f"Technical figure on page {unit.provenance.page} of "
                    f"{unit.provenance.doc_id}.")
        return " ".join(bits).strip()

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=Config.openrouter_api_key(),
                                         base_url=OPENROUTER_BASE_URL)
        return self._client

    def _openrouter_caption(self, image_bytes: bytes, suffix: str) -> str:
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp"}.get(suffix.lower(), "image/png")
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"
        try:
            client = self._get_client()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }],
                max_tokens=180,
                temperature=0.2,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001
            log.warning("OpenRouter caption failed (%s); using offline fallback", e)
            return ""
