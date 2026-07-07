.PHONY: install start test lint check format
.DEFAULT_GOAL := help

install:
	pip install -e .[dev]

start:
	@echo "Starting DEEP Server..."
	python interface/server.py

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

check:
	mypy core/ engine/ ai/ mcp_server/ interface/server.py || true

help:
	@echo "DEEP Commands:"
	@echo "  make install  - Install project and dev dependencies in editable mode"
	@echo "  make start    - Start the main DEEP server"
	@echo "  make test     - Run pytest"
	@echo "  make lint     - Run Ruff linter"
	@echo "  make format   - Format code with Ruff"
	@echo "  make check    - Run static type checking with Mypy"
