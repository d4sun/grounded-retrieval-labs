"""Grounded Retrieval — multimodal retrieval over technical manuals.

Retrieve-by-text, answer-with-artefact. See ``grounded_retrieval.pipeline`` for the
end-to-end entrypoints and ``grounded_retrieval.provenance`` for the data backbone.
"""

__version__ = "0.1.0"

from .config import Config, load_config  # noqa: F401
from .provenance import (  # noqa: F401
    BBox,
    Document,
    Page,
    Provenance,
    Unit,
    UnitType,
    doc_id_from_path,
    make_unit_id,
    read_units_jsonl,
    write_units_jsonl,
)

__all__ = [
    "__version__",
    "Config",
    "load_config",
    "BBox",
    "Document",
    "Page",
    "Provenance",
    "Unit",
    "UnitType",
    "doc_id_from_path",
    "make_unit_id",
    "read_units_jsonl",
    "write_units_jsonl",
]
