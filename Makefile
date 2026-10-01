.PHONY: help install-dev test lint format run venv evaluate seed-policy seed-users seed-apps calibrate

help:
	@echo "Makefile commands:"
	@echo "  make install-dev   # Install development dependencies (pytest, ruff)"
	@echo "  make test          # Run pytest"
	@echo "  make lint          # Run ruff lint checks"
	@echo "  make format        # Auto-format with ruff (safe)"
	@echo "  make run           # Start FastAPI app with uvicorn (if installed)"
	@echo "  make evaluate      # Run 15-question evaluation harness"
	@echo "  make seed-policy   # Ingest trusted policy documents"
	@echo "  make seed-users    # Seed demo users"
	@echo "  make seed-apps     # Seed application packs"
	@echo "  make calibrate     # Calibrate retrieval thresholds"

install-dev:
	python -m pip install --upgrade pip setuptools wheel
	python -m pip install -r requirements-dev.txt

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .

run:
	# Run the FastAPI app (ensure dependencies installed)
	uvicorn src.application.api.main:app --reload --port ${PORT:=8000}

evaluate:
	LLM_PROVIDER=fake python -m src.cli evaluate

seed-policy:
	python -m src.cli seed-policy

seed-users:
	python -m src.cli seed-users

seed-apps:
	python -m src.cli seed-apps

calibrate:
	LLM_PROVIDER=fake python -m src.cli calibrate
