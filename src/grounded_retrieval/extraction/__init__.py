"""Stage [2] — extract figures & tables as first-class units, with provenance."""

from .figures import extract_figures  # noqa: F401
from .tables import extract_tables  # noqa: F401

__all__ = ["extract_figures", "extract_tables"]
