# Grounded Retrieval — Lab A
.PHONY: help install install-free smoke sample ingest query eval test clean

help:
	@echo "make install       - core deps (offline smoke test works with just these)"
	@echo "make install-free  - add the real free stack (sentence-transformers, faiss, openai, docling...)"
	@echo "make smoke         - sample corpus -> ingest -> query -> eval, fully offline"
	@echo "make test          - run pytest"

install:
	pip install -e .

install-free:
	pip install -e ".[free]"

sample:
	python -m scripts.make_sample_corpus

ingest: sample
	python -m scripts.run_ingest --config config/default.yaml

query:
	python -m scripts.run_query "relay control wiring diagram"

eval:
	python -m scripts.run_eval --config config/default.yaml

smoke: ingest eval
	@echo "Smoke test complete."

test:
	pytest

clean:
	rm -rf data/index data/artefacts .cache caption_cache data/sample/*.pdf data/sample/gold_questions.json
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
