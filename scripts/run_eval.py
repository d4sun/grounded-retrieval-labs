"""Evaluate retrieval by type + a faithfulness spot-check.

    python -m scripts.run_eval --config config/default.yaml
    python -m scripts.run_eval --gold data/sample/gold_questions.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

import scripts  # noqa: F401  (sys.path bootstrap)
from grounded_retrieval.answering import Answerer
from grounded_retrieval.config import load_config
from grounded_retrieval.evaluation import (
    evaluate,
    faithfulness_spotcheck,
    format_report,
    load_gold,
)
from grounded_retrieval.logging_utils import setup_logging
from grounded_retrieval.pipeline import Pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--gold", default=None, help="gold questions json (default: input_dir/gold_questions.json)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("logging.level", "INFO"))

    gold_path = Path(args.gold) if args.gold else \
        cfg.resolve_path("corpus.input_dir", "data/sample") / "gold_questions.json"
    if not gold_path.exists():
        raise FileNotFoundError(f"gold questions not found: {gold_path}")
    gold = load_gold(gold_path)

    pipe = Pipeline(cfg)
    retriever = pipe.load_retriever()
    report = evaluate(retriever, gold,
                      k_values=cfg.get("evaluation.k_values", [1, 3, 5, 10]),
                      by_type=cfg.get("evaluation.by_type", True))
    print(format_report(report))
    print("\n--- baseline recorded (record these numbers BEFORE any tuning) ---")

    print("\nFaithfulness spot-check:")
    for c in faithfulness_spotcheck(Answerer(retriever, cfg), gold, n=min(5, len(gold))):
        mark = "ok " if c.page_in_evidence else "!! "
        print(f"  {mark}{c.qid} [{c.answered_type}] cite={c.citation or '—'} "
              f"{'' if c.page_in_evidence else '<- ' + c.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
