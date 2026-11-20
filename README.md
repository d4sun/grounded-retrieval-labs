# Grounded Retrieval Labs — Sub-Track 1A

**Rich Answers, Not Just Text: Multimodal Retrieval over Technical Manuals (free stack)**

Course 3 · Day 2 · Lab A — a reference implementation of the Lab A playbook.

When a **figure or table is the answer**, this system returns the **actual artefact with its
page/source citation** — not a prose paraphrase. Three non-negotiables are baked into every step:

1. **Route** each content type correctly (text / figure / table / scanned).
2. Make figures & tables **retrievable** via searchable text (captions, linearised tables, OCR).
3. Carry `document → page → figure/table id` **provenance** end to end, so an answer can show and
   cite the real thing.

The guiding idea is **retrieve-by-text, answer-with-artefact**: we index something searchable
(a caption, a linearised table, OCR text) but we *hand back* the original figure/table, linked by
provenance.

---

## Why this runs with no billing wall

Every model in the pipeline has a **free path** and an **offline fallback**, selected at runtime:

| Capability        | Preferred (free)                                  | Offline fallback (no network)                |
|-------------------|---------------------------------------------------|----------------------------------------------|
| PDF structure     | [Docling](https://github.com/DS4SD/docling)       | PyMuPDF text/line heuristics                 |
| Figure extraction | PyMuPDF `get_images` / region render              | (same — PyMuPDF is always local)             |
| Table extraction  | Camelot / pdfplumber                              | pdfplumber (pure-python) / text heuristic    |
| OCR               | Tesseract (`pytesseract`)                         | skipped with a logged warning + review flag  |
| Figure captioning | OpenRouter `:free` vision model                   | nearby-caption text / deterministic stub     |
| Text embeddings   | `BAAI/bge-small-en-v1.5` (local, free)            | deterministic hashing embedder               |
| Vector index      | FAISS                                             | NumPy brute-force index                      |
| Answer caption    | OpenRouter `:free` vision model                   | templated grounded caption                   |

This means `make smoke` runs the **entire** ingest → retrieve → answer → evaluate path with **no
API key, no dataset download, and no GPU** — on a tiny synthetic manual generated locally. Swap the
fallbacks for the real free models by installing the extras and setting `OPENROUTER_API_KEY`.

> **Privacy note (state this in the room):** free endpoints may log/train on inputs. Use the public
> datasets for the lab; never send confidential manuals to a free endpoint — for real data, set
> `enrichment.captioner.backend: local` / `offline` and `indexing.embedder.backend: local` so no
> bytes leave the machine.

---

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .                 # core: numpy, pdfplumber, pymupdf, pyyaml, rank-bm25
pip install -e ".[free]"         # add: sentence-transformers, faiss-cpu, openai, docling, camelot-py, pytesseract
# Tesseract binary (OCR) is a system package, e.g.  sudo apt-get install tesseract-ocr
```

The **core** install alone is enough to run the offline smoke test.

## Quickstart (offline, no key)

```bash
make smoke          # generate sample manual → ingest → query → evaluate, all offline
# equivalently:
python -m scripts.make_sample_corpus          # writes data/sample/*.pdf + gold questions
python -m scripts.run_ingest  --config config/default.yaml
python -m scripts.run_query   "relay control wiring"
python -m scripts.run_eval    --config config/default.yaml
```

## Upgrade to the real free stack

```bash
export OPENROUTER_API_KEY=sk-or-...           # free key from openrouter.ai → Keys
# edit config/default.yaml:
#   parsing.loader.backend:          docling
#   enrichment.captioner.backend:    openrouter
#   indexing.embedder.backend:       local        # bge-small-en-v1.5
#   indexing.index.backend:          faiss
python -m scripts.run_ingest --config config/default.yaml
```

Point ingest at a real corpus (an FAA handbook, iFixit guides, a DUDE/MP-DocVQA slice) by dropping
PDFs in `data/raw/` and setting `corpus.input_dir: data/raw`.

---

## Architecture

```
PDFs / scans ─▶ [1] Parse & route ─▶ [2] Extract figures & tables (provenance)
                                          │
                                          ▼
                      [3] Enrich: caption figures / linearise tables
                                          │
                                          ▼
          [4] Embed & index  text-chunks + figure-captions + table-text  (provenance in metadata)
                                          │
                                          ▼
                                 [5] Retrieve (by text)
                                          │
                                          ▼
      [6] Answer: decide text | figure | table ─▶ return the REAL artefact + page citation
                                          │
                                          ▼
                      [7] Evaluate retrieval BY TYPE + faithfulness
```

Each bracketed step maps to a package under `src/grounded_retrieval/`. See
[`docs/architecture.md`](docs/architecture.md) for the module map and
[`docs/milestone-checklist.md`](docs/milestone-checklist.md) for the lab's milestone checklist.

---

## Repository layout

```
src/grounded_retrieval/
  provenance.py        # doc→page→id dataclasses + Unit model (the backbone)
  config.py            # typed config loader (YAML + env)
  parsing/             # [1] docling/pymupdf loader, content router, OCR quality gate
  extraction/          # [2] figure crops + structured tables, each with provenance
  enrichment/          # [3] vision captioner (+cache) and table linearisation
  indexing/            # [4] embedder + vector index (FAISS / numpy)
  retrieval/           # [5] vector retriever + optional BM25 fusion
  answering/           # [6] answer-type router, artefact return, fail-closed
  evaluation/          # [7] recall@k, MRR, faithfulness — broken out by type
  pipeline.py          # wires [1]–[6] into ingest() and answer()
scripts/               # CLI entrypoints + synthetic corpus generator
tests/                 # pytest smoke + unit tests (run fully offline)
config/default.yaml    # one place to flip free ↔ offline backends
data/                  # raw/ (gitignored) and sample/ (synthetic, committed)
```

## Licence note

Code here is yours to use for the program. Dataset licences differ: FAA/NASA are public domain,
iFixit is **CC BY-NC-SA** (non-commercial), the DocVQA family is **research use** — fine for the
lab, verify before any product use.
