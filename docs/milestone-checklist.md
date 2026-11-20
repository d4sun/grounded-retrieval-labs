# Milestone checklist (Lab A)

Maps the playbook's §8 checklist to where each item is implemented and how to verify it.

| # | Milestone | Where | Verify |
|---|-----------|-------|--------|
| 1 | Corpus loaded (eval set with evidence labels + one real manual) | `scripts/make_sample_corpus.py`, `corpus.input_dir` | `python -m scripts.make_sample_corpus` then check `data/sample/` |
| 2 | Content routed; scanned pages OCR'd behind a **quality gate** | `parsing/router.py`, `parsing/ocr.py` | OCR units carry `ocr.passed_gate`; failed pages → `review_queue.json` |
| 3 | Figures & tables extracted **with `doc→page→id` provenance** | `extraction/figures.py`, `extraction/tables.py` | every `Unit.provenance` resolves to a page; `run_ingest` prints a provenance spot-check |
| 4 | Figures captioned / tables linearised (free vision model, cached) | `enrichment/captioner.py`, `enrichment/linearise.py` | captions cached under `.cache/captions`; re-run is free |
| 5 | Mixed index built with provenance in metadata (local embeddings + FAISS) | `indexing/embedder.py`, `indexing/index.py` | `data/index/` holds vectors + `units.jsonl` with provenance |
| 6 | Retrieval returns units **with citations** | `retrieval/retriever.py` | `run_query` prints `doc p.N` for every hit |
| 7 | Answer step returns the **real figure/table + page**, not a paraphrase | `answering/answerer.py` | figure answers return the image path + page; fail-closed on missing provenance |
| 8 | Retrieval measured **by type**; baseline recorded; failure modes fixed | `evaluation/metrics.py`, `scripts/run_eval.py` | `run_eval` prints recall@k / MRR split by text/figure/table |

## Failure modes engineered against (playbook §9)

| Symptom | Fix in this repo |
|---------|------------------|
| scanned-text noise | OCR confidence + garbled-ratio gate (`parsing/ocr.py`); failures flagged for review |
| figure invisibility | figures made retrievable via captions (`enrichment/captioner.py`) |
| table flattening | structure preserved (`extraction/tables.py`); linearised copy is search-only |
| lost provenance | `doc→page→id` carried in `Provenance` on every `Unit`; fail-closed answering |
| caption–image drift | caption prompt pulls labels/part numbers; answer re-captions from the real image |
| vision-cost blowout | caption selectively (`max_figures`) + disk cache |
