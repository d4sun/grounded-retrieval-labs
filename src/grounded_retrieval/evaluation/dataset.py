"""Gold evaluation questions with page-level evidence labels.

Mirrors what DUDE / MP-DocVQA ship: a question, its expected modality, and the
``doc_id`` + evidence page(s) that contain the answer — the retrieval gold that makes
measuring recall@k possible without hand-labelling.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GoldQuestion:
    qid: str
    question: str
    answer_type: str                 # expected modality: text | figure | table
    doc_id: str
    evidence_pages: list[int]
    meta: dict[str, Any] = field(default_factory=dict)


def load_gold(path: str | Path) -> list[GoldQuestion]:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw["questions"] if isinstance(raw, dict) and "questions" in raw else raw
    return [GoldQuestion(**q) for q in items]


def save_gold(questions: list[GoldQuestion], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"questions": [asdict(q) for q in questions]}, indent=2),
                    encoding="utf-8")
