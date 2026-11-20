"""Query the index and print the artefact answer + citation.

    python -m scripts.run_query "relay control wiring diagram"
    python -m scripts.run_query --k 5 "torque spec for the main bus"
"""

from __future__ import annotations

import argparse

import scripts  # noqa: F401  (sys.path bootstrap)
from grounded_retrieval.config import load_config
from grounded_retrieval.logging_utils import setup_logging
from grounded_retrieval.pipeline import Pipeline


def _print_answer(ans) -> None:
    print(f"\nQ: {ans.query}")
    print(f"answer type: {ans.answer_type}   citation: {ans.citation or '—'}")
    if ans.answer_type == "none":
        print(f"  (abstained) {ans.reason}")
    elif ans.answer_type == "figure":
        print(f"  figure: {ans.artefact['image_path']}")
        print(f"  grounded caption: {ans.grounded_caption}")
    elif ans.answer_type == "table":
        print("  table rows:")
        for row in ans.artefact.get("cells", []):
            print("    | " + " | ".join(str(c) for c in row) + " |")
    else:
        text = ans.artefact.get("text", "")
        print(f"  text: {text[:400]}{'…' if len(text) > 400 else ''}")

    print("  supporting hits:")
    for h in ans.support[:5]:
        print(f"    [{h.rank}] {h.unit.unit_type.value:<6} {h.citation:<22} "
              f"score={h.score:.3f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="+", help="the question / query text")
    ap.add_argument("--config", default=None)
    ap.add_argument("--k", type=int, default=None, help="top-k")
    args = ap.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("logging.level", "INFO"))
    ans = Pipeline(cfg).answer(" ".join(args.query), k=args.k)
    _print_answer(ans)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
