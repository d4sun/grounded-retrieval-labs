"""Grounded Retrieval — multimodal retrieval over technical manuals.

Retrieve-by-text, answer-with-artefact. See ``grounded_retrieval.pipeline`` for the
end-to-end entrypoints and ``grounded_retrieval.provenance`` for the data backbone.
"""

__version__ = "0.1.0"

from .config import Config, load_config  # noqa: F401

__all__ = ["__version__", "Config", "load_config"]
