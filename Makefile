.PHONY: install start test lint check format playbooks
.DEFAULT_GOAL := help

install:
	pip install -e .[dev]

start:
	@echo "Starting DEEP Server..."
	python interface/server.py

test:
	pytest

# Response playbooks. Not vendored — this is someone else's Apache-2.0 corpus
# (~800 procedures already mapped to ATT&CK, NIST CSF, ATLAS, D3FEND, AI RMF
# and F3), and DEEP indexes any directory in the same Anthropic-Skills layout.
# Point DEEP_PLAYBOOKS_DIR elsewhere to use your own.
PLAYBOOKS_REPO ?= https://github.com/mukul975/Anthropic-Cybersecurity-Skills.git
PLAYBOOKS_DIR  ?= data/playbooks

playbooks:
	@if [ -d "$(PLAYBOOKS_DIR)/.git" ]; then \
		echo "Updating playbooks in $(PLAYBOOKS_DIR)..."; \
		git -C "$(PLAYBOOKS_DIR)" pull --ff-only; \
	else \
		echo "Fetching playbooks into $(PLAYBOOKS_DIR)..."; \
		git clone --depth 1 "$(PLAYBOOKS_REPO)" "$(PLAYBOOKS_DIR)"; \
	fi
	@echo "Indexed on next start. Check with: curl -s localhost:5174/api/intel/playbooks/status"

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
	@echo "  make playbooks- Fetch/update the response-playbook corpus into data/"
	@echo "  make lint     - Run Ruff linter"
	@echo "  make format   - Format code with Ruff"
	@echo "  make check    - Run static type checking with Mypy"
