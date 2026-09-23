.PHONY: help install-dev test lint format run venv

help:
	@echo "Makefile commands:"
	@echo "  make install-dev   # Install development dependencies (pytest, ruff)"
	@echo "  make test          # Run pytest"
	@echo "  make lint          # Run ruff lint checks"
	@echo "  make format        # Auto-format with ruff (safe)"
	@echo "  make run           # Start FastAPI app with uvicorn (if installed)"

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
