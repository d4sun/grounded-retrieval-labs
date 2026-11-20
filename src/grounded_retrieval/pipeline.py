"""End-to-end orchestration: wires stages [1]–[6] into ingest() and answer().

    pipe = Pipeline(load_config("config/default.yaml"))
    pipe.ingest()                       # parse -> extract -> enrich -> index (persisted)
    ans = pipe.answer("relay wiring")   # retrieve -> answer-with-artefact
"""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path

from .answering.answerer import Answer, Answerer
from .config import Config
from .enrichment.captioner import Captioner
from .enrichment.linearise import linearise_units
from .extraction.figures import extract_figures
from .extraction.tables import extract_tables
from .indexing.chunking import chunk_document
from .indexing.embedder import Embedder
from .indexing.index import VectorIndex
from .logging_utils import get_logger
from .parsing.router import ReviewFlag, parse_document, write_review_queue
from .provenance import Unit, UnitType
from .retrieval.retriever import Retriever

log = get_logger("grounded_retrieval.pipeline")


@dataclass
class IngestStats:
    docs: int = 0
    units: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    review_flags: int = 0
    captioned: int = 0
    linearised: int = 0
    index_dir: str = ""

    def summary(self) -> str:
        bt = ", ".join(f"{k}={v}" for k, v in sorted(self.by_type.items()))
        return (f"ingested {self.docs} doc(s): {self.units} units ({bt}); "
                f"captioned {self.captioned}, linearised {self.linearised}; "
                f"{self.review_flags} page(s) flagged for review; index -> {self.index_dir}")


class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.input_dir = cfg.resolve_path("corpus.input_dir", "data/sample")
        self.index_dir = cfg.resolve_path("corpus.index_dir", "data/index")
        self._embedder: Embedder | None = None

    @property
    def embedder(self) -> Embedder:
        if self._embedder is None:
            self._embedder = Embedder(self.cfg)
        return self._embedder

    # --- ingest [1]-[4] ------------------------------------------------ #
    def ingest(self) -> IngestStats:
        pdfs = sorted(glob.glob(str(self.input_dir / "*.pdf")))
        if not pdfs:
            raise FileNotFoundError(
                f"no PDFs in {self.input_dir}. Run `python -m scripts.make_sample_corpus` "
                f"or point corpus.input_dir at your corpus.")
        all_units: list[Unit] = []
        all_flags: list[ReviewFlag] = []
        for pdf in pdfs:
            parsed, flags = parse_document(pdf, self.cfg)
            units = (chunk_document(parsed, self.cfg)
                     + extract_figures(parsed, self.cfg)
                     + extract_tables(parsed, self.cfg))
            all_units.extend(units)
            all_flags.extend(flags)

        # [3] enrich
        captioned = Captioner(self.cfg).caption_units(all_units)
        linearised = linearise_units(all_units, self.cfg)

        # [3.3] provenance spot-check — fail loudly if any unit can't name its page
        self._provenance_spotcheck(all_units)

        # [4] embed & index
        backend = self.cfg.get("indexing.index.backend", "auto")
        index = VectorIndex.build(all_units, self.embedder, backend=backend)
        index.save(self.index_dir)
        write_review_queue(all_flags, self.index_dir / "review_queue.json")

        stats = IngestStats(
            docs=len(pdfs), units=len(all_units),
            by_type={t.value: sum(1 for u in all_units if u.unit_type is t)
                     for t in UnitType},
            review_flags=len(all_flags), captioned=captioned, linearised=linearised,
            index_dir=str(self.index_dir),
        )
        log.info(stats.summary())
        return stats

    def _provenance_spotcheck(self, units: list[Unit], sample: int = 5) -> None:
        missing = [u for u in units if not u.has_provenance]
        if missing:
            log.error("PROVENANCE FAILURE: %d/%d units cannot name their page — "
                      "everything downstream depends on this. First: %s",
                      len(missing), len(units), missing[0].unit_id)
            raise ValueError(f"{len(missing)} units lack resolvable provenance")
        for u in units[:sample]:
            log.info("provenance ok: %-26s -> %s", u.unit_id, u.citation())

    # --- serve [5]-[6] ------------------------------------------------- #
    def load_retriever(self) -> Retriever:
        if not (self.index_dir / "meta.json").exists():
            raise FileNotFoundError(f"no index at {self.index_dir}; run ingest() first")
        return Retriever.from_index_dir(self.index_dir, self.cfg)

    def answer(self, query: str, k: int | None = None) -> Answer:
        return Answerer(self.load_retriever(), self.cfg).answer(query, k=k)
