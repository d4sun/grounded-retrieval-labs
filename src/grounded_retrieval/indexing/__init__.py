"""Stage [4] — embed & index text chunks + figure captions + table text."""

from .chunking import chunk_document  # noqa: F401
from .embedder import Embedder  # noqa: F401
from .index import SearchHit, VectorIndex  # noqa: F401

__all__ = ["chunk_document", "Embedder", "SearchHit", "VectorIndex"]
