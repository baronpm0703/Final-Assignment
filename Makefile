.PHONY: install sync test test-unit test-integration lint format dev docker-up docker-down init-db ingest

UV ?= uv
PYTHON ?= $(UV) run python

install: sync

sync:
	$(UV) sync --extra dev

test:
	$(PYTHON) -m pytest

test-unit:
	$(PYTHON) -m pytest tests/unit

test-integration:
	$(PYTHON) -m pytest tests/integration

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

dev:
	$(PYTHON) -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker compose up -d postgres

docker-down:
	docker compose down

init-db:
	$(PYTHON) -m scripts.init_db

ingest:
	$(PYTHON) -m scripts.ingest_kb
