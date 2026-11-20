"""Ingest a corpus into the index: parse -> extract -> enrich -> embed -> index.

    python -m scripts.run_ingest --config config/default.yaml
"""

from __future__ import annotations

import argparse

import scripts  # noqa: F401  (sys.path bootstrap)
from grounded_retrieval.config import load_config
from grounded_retrieval.logging_utils import setup_logging
from grounded_retrieval.pipeline import Pipeline
from grounded_retrieval.sample_corpus import build_sample_corpus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None, help="path to config YAML")
    ap.add_argument("--make-sample", action="store_true",
                    help="generate the synthetic sample corpus first if input_dir is empty")
    args = ap.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.get("logging.level", "INFO"))

    input_dir = cfg.resolve_path("corpus.input_dir", "data/sample")
    if args.make_sample or not list(input_dir.glob("*.pdf")):
        # convenience: make the sample so a fresh checkout ingests with one command
        build_sample_corpus(input_dir)

    stats = Pipeline(cfg).ingest()
    print(stats.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
