"""Generate the synthetic sample manual + gold questions (offline, no deps beyond core).

    python -m scripts.make_sample_corpus [--out data/sample]
"""

from __future__ import annotations

import argparse

import scripts  # noqa: F401  (sys.path bootstrap)
from grounded_retrieval.logging_utils import setup_logging
from grounded_retrieval.sample_corpus import build_sample_corpus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/sample", help="output directory")
    args = ap.parse_args()
    setup_logging("INFO")

    pdfs, gold = build_sample_corpus(args.out)
    print(f"wrote {len(pdfs)} PDF(s):")
    for p in pdfs:
        print(f"  {p}")
    print(f"gold questions: {gold}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
