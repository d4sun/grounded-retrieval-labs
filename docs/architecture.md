# Architecture & module map

`retrieve-by-text, answer-with-artefact`. The backbone is `provenance.Unit`: everything the system
stores, searches, and returns is a `Unit` carrying `doc → page → id` provenance.

## Data model (`provenance.py`)

- `Document` — one source PDF (id, path, page count).
- `Page` — a page within a document (number, whether it was scanned/OCR'd).
- `UnitType` — `TEXT | FIGURE | TABLE`.
- `Unit` — the atom of retrieval. Holds:
  - `provenance` (`doc_id`, `page`, `unit_id`, optional `bbox`),
  - `search_text` — what we embed/index (prose chunk, figure caption, linearised table),
  - `artefact` — what we *return* (text span, figure image path, structured table rows),
  - `meta` — captioning/OCR flags, nearby caption text, etc.

A `Unit` is **invalid for sourced answers** if its provenance can't name a page. Answering
fails closed on these (`answering.fail_closed`).

## Pipeline stages

| Stage | Package | Key entrypoint | Notes |
|-------|---------|----------------|-------|
| [1] Parse & route | `parsing/` | `router.parse_document()` | Docling (or PyMuPDF fallback) → text/figure/table regions + page numbers; scanned pages detected and sent to `ocr.ocr_page()` behind a quality gate |
| [2] Extract | `extraction/` | `figures.extract_figures()`, `tables.extract_tables()` | PyMuPDF figure crops; Camelot/pdfplumber tables preserving rows/cols; provenance stamped here |
| [3] Enrich | `enrichment/` | `captioner.caption_figure()`, `linearise.linearise_table()` | figure → searchable caption (cached); table → markdown/kv text, structure kept for the answer |
| [4] Index | `indexing/` | `embedder.Embedder`, `index.VectorIndex` | one index over text + figure-caption + table-text units; provenance in metadata |
| [5] Retrieve | `retrieval/` | `retriever.Retriever.retrieve()` | vector search, optional BM25 fusion for exact identifiers |
| [6] Answer | `answering/` | `answerer.Answerer.answer()` | decide text/figure/table, return the real artefact + citation, fail-closed |
| [7] Evaluate | `evaluation/` | `metrics.evaluate()` | recall@k, MRR, faithfulness — broken out by type |

`pipeline.py` wires [1]–[6]: `Pipeline.ingest()` builds the index; `Pipeline.answer()` serves a query.

## Backend selection

Every model-bearing stage resolves its backend at runtime (`auto`): it tries the free/local model
and falls back to a deterministic offline implementation, logging the choice. This keeps the smoke
test hermetic while letting the same code run the real stack when deps + keys are present.

```
Embedder(backend="auto")  ->  sentence-transformers if importable, else HashingEmbedder
VectorIndex(backend="auto") -> faiss if importable, else NumpyIndex
Captioner(backend="auto") -> OpenRouter if key present, else OfflineCaptioner
Loader(backend="auto")    -> docling if importable, else PyMuPDFLoader
```
