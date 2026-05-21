.PHONY: help install lint format test run celery-worker docker-up docker-down clean

PYTHON := python3
VENV := .venv

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Create venv & install deps
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

lint:  ## Lint with ruff
	$(VENV)/bin/ruff check src tests

format:  ## Format
	$(VENV)/bin/black src tests
	$(VENV)/bin/ruff check --fix src tests

test:  ## Run tests
	$(VENV)/bin/pytest -v

test-cov:  ## Tests with coverage
	$(VENV)/bin/pytest --cov=src/clinical_etl --cov-report=html --cov-report=term

run:  ## Run sample pipeline
	$(VENV)/bin/python -m clinical_etl.main run --source sample

demo-fhir:  ## Demo FHIR extraction against fixtures
	$(VENV)/bin/python -m clinical_etl.main demo-fhir --fixture data/sample/fhir_patient.json

celery-worker:  ## Start Celery worker
	$(VENV)/bin/celery -A clinical_etl.orchestration.tasks worker --loglevel=INFO

docker-up:
	docker compose up -d postgres redis elasticsearch azurite

docker-down:
	docker compose down -v

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
