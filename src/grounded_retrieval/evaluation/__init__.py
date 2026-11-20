"""Stage [7] — evaluate retrieval by type + faithfulness."""

from .dataset import GoldQuestion, load_gold, save_gold  # noqa: F401
from .metrics import (  # noqa: F401
    FaithfulnessCase,
    evaluate,
    faithfulness_spotcheck,
    format_report,
)

__all__ = [
    "GoldQuestion",
    "load_gold",
    "save_gold",
    "FaithfulnessCase",
    "evaluate",
    "faithfulness_spotcheck",
    "format_report",
]
