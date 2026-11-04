# One command: make all
# It starts Postgres in Docker (unless one is already answering), loads data, builds dbt and exports.

-include .env
export PGHOST ?= localhost
export PGPORT ?= 5432
export PGUSER ?= econ
export PGPASSWORD ?= econ
export PGDATABASE ?= econ

VENV ?= .venv
PY := $(VENV)/bin/python
DBT := $(VENV)/bin/dbt --no-use-colors
DBT_ARGS := --project-dir transform --profiles-dir transform

.PHONY: all setup db db-down ingest ingest-full freshness build docs export dashboard test lint format clean

all: setup db ingest build export

$(VENV)/bin/activate: requirements.txt requirements-dev.txt
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip
	$(VENV)/bin/pip install -q -r requirements-dev.txt
	touch $(VENV)/bin/activate

setup: $(VENV)/bin/activate

db:
	@if pg_isready -q -h $(PGHOST) -p $(PGPORT) 2>/dev/null; then \
		echo "Postgres already running on $(PGHOST):$(PGPORT)"; \
	else \
		docker compose up -d --wait postgres; \
	fi

db-down:
	docker compose down

ingest:
	$(PY) -m ingest.main

ingest-full:
	$(PY) -m ingest.main --full

freshness:
	$(DBT) source freshness $(DBT_ARGS)

build:
	$(DBT) build $(DBT_ARGS)

docs:
	$(DBT) docs generate --static $(DBT_ARGS)
	mkdir -p docs/dbt
	cp transform/target/static_index.html docs/dbt/index.html

export:
	$(PY) -m scripts.export_marts

dashboard:
	@echo "Open http://localhost:8000"
	cd docs && ../$(PY) -m http.server 8000

test:
	$(VENV)/bin/pytest

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .
	$(VENV)/bin/sqlfluff lint transform

format:
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/sqlfluff fix transform

clean:
	rm -rf transform/target transform/logs .pytest_cache .ruff_cache docs/dbt
