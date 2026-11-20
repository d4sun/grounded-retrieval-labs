"""Stage [3] — enrich: make figures & tables retrievable."""

from .cache import CaptionCache  # noqa: F401
from .captioner import Captioner  # noqa: F401
from .linearise import linearise_table, linearise_units  # noqa: F401

__all__ = ["CaptionCache", "Captioner", "linearise_table", "linearise_units"]
