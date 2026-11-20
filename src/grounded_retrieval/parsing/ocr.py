"""OCR for scanned pages, behind a **quality gate**.

The playbook's rule: score OCR output (mean confidence / garbled-char ratio); pages that
fail are *flagged for review*, not silently indexed. Silent indexing of garbage OCR is a
classic source of "scanned-text noise" retrieval failures.

Backends: ``tesseract`` (pytesseract + the system binary) or ``off``. ``auto`` uses
Tesseract when both the python package and the binary are present, else turns OCR off
with a logged warning (the page is still routed, just flagged ``ocr_applied=False``).
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..logging_utils import get_logger

log = get_logger("grounded_retrieval.parsing.ocr")

_WORDLIKE = re.compile(r"[A-Za-z0-9]")


@dataclass
class OcrResult:
    text: str
    mean_confidence: float       # 0..100 (-1 if unknown)
    garbled_ratio: float         # fraction of non-wordlike, non-space chars
    passed_gate: bool
    applied: bool                # whether OCR actually ran
    reason: str = ""


def tesseract_available() -> bool:
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
        return True
    except Exception:
        return False


def resolve_backend(backend: str) -> str:
    if backend == "auto":
        return "tesseract" if tesseract_available() else "off"
    return backend


def garbled_ratio(text: str) -> float:
    if not text:
        return 1.0
    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return 1.0
    wordlike = sum(1 for c in non_space if _WORDLIKE.match(c))
    return 1.0 - wordlike / len(non_space)


def _quality_gate(text: str, mean_conf: float, min_conf: float, max_garbled: float
                  ) -> tuple[bool, str]:
    g = garbled_ratio(text)
    if not text.strip():
        return False, "empty OCR output"
    if mean_conf >= 0 and mean_conf < min_conf:
        return False, f"mean confidence {mean_conf:.1f} < {min_conf}"
    if g > max_garbled:
        return False, f"garbled ratio {g:.2f} > {max_garbled}"
    return True, "ok"


def ocr_page_image(image_path: str | Path, *, languages: str = "eng",
                   min_confidence: float = 55.0, max_garbled: float = 0.30
                   ) -> OcrResult:
    """Run Tesseract on a rendered page image and apply the quality gate."""
    import pytesseract
    from PIL import Image

    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, lang=languages,
                                     output_type=pytesseract.Output.DICT)
    words, confs = [], []
    for w, c in zip(data.get("text", []), data.get("conf", [])):
        if w and w.strip():
            words.append(w)
            try:
                cf = float(c)
            except (TypeError, ValueError):
                cf = -1.0
            if cf >= 0:
                confs.append(cf)
    text = " ".join(words)
    mean_conf = sum(confs) / len(confs) if confs else -1.0
    g = garbled_ratio(text)
    passed, reason = _quality_gate(text, mean_conf, min_confidence, max_garbled)
    if not passed:
        log.warning("OCR page flagged for review (%s): %s", reason, image_path)
    return OcrResult(text=text, mean_confidence=mean_conf, garbled_ratio=g,
                     passed_gate=passed, applied=True, reason=reason)


def skipped(reason: str) -> OcrResult:
    return OcrResult(text="", mean_confidence=-1.0, garbled_ratio=1.0,
                     passed_gate=False, applied=False, reason=reason)
