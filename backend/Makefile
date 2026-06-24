# Makefile backend - Python/FastAPI
# Use `make help` para ver alvos. Use `make <alvo>` para executar.

SHELL := /bin/bash
.DEFAULT_GOAL := help

GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
RESET  := \033[0m

.PHONY: help
help:
	@echo "$(GREEN)Cartorio Backend - Makefile$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' | sort

.PHONY: install
install:  ## uv sync - instala deps
	uv sync

.PHONY: lock
lock:  ## Atualiza uv.lock
	uv lock

.PHONY: dev
dev:  ## Uvicorn dev (hot reload)
	uv run uvicorn app.main:app --reload --port 8000

.PHONY: prod
prod:  ## Uvicorn prod (4 workers)
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

.PHONY: test
test:  ## Pytest com coverage
	uv run pytest --tb=short

.PHONY: test-fast
test-fast:  ## Pytest rapido sem coverage
	uv run pytest --tb=short -q --no-cov

.PHONY: test-cov
test-cov:  ## Pytest + gera HTML coverage report
	uv run pytest --cov=app --cov-report=html
	@echo "$(GREEN)Coverage HTML: backend/htmlcov/index.html$(RESET)"

.PHONY: test-one
test-one:  ## Roda 1 teste (uso: make test-one TEST=tests/test_pii.py::test_foo)
	uv run pytest -v --tb=short --no-cov $(TEST)

.PHONY: lint
lint:  ## Ruff check
	uv run ruff check .

.PHONY: lint-fix
lint-fix:  ## Ruff --fix + format
	uv run ruff check . --fix
	uv run ruff format .

.PHONY: format
format:  ## Ruff format
	uv run ruff format .

.PHONY: typecheck
typecheck:  ## Mypy strict
	uv run mypy app/

.PHONY: qa
qa:  ## Quality gate: lint + typecheck + test
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test

.PHONY: smoke
smoke:  ## Smoke test contra API local
	@echo "$(YELLOW)Smoke test: GET /health$(RESET)"
	@curl -s http://localhost:8000/health | python3 -m json.tool
	@echo "$(YELLOW)Smoke test: GET /ready$(RESET)"
	@curl -s http://localhost:8000/ready | python3 -m json.tool
	@echo "$(YELLOW)Smoke test: GET /api/v1/health/radar$(RESET)"
	@curl -s http://localhost:8000/api/v1/health/radar | python3 -m json.tool

.PHONY: mcp-server
mcp-server:  ## Inicia MCP server (FastMCP) - porta padrao 8765
	uv run python mcp_server.py

.PHONY: alembic-up
alembic-up:  ## Aplica migrations Alembic
	uv run alembic upgrade head

.PHONY: alembic-down
alembic-down:  ## Reverte 1 migration
	uv run alembic downgrade -1

.PHONY: alembic-history
alembic-history:  ## Mostra historico de migrations
	uv run alembic history --verbose

.PHONY: alembic-new
alembic-new:  ## Cria nova migration (uso: make alembic-new MSG="add table X")
	uv run alembic revision --autogenerate -m "$(MSG)"

.PHONY: shell
shell:  ## IPython com contexto carregado
	uv run ipython -i -c "from app.main import app; from app.db import SessionLocal; from app.config import settings; print('Contexto carregado: app, SessionLocal, settings')"

.PHONY: clean
clean:  ## Remove __pycache__, .mypy_cache, .ruff_cache, .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage
	rm -rf htmlcov/
	rm -f *.log
	@echo "$(GREEN)Cache limpo$(RESET)"

.PHONY: deps-list
deps-list:  ## Lista dependencias instaladas
	uv pip list

.PHONY: deps-tree
deps-tree:  ## Arvore de dependencias
	uv tree

.PHONY: audit
audit:  ## Verifica vulnerabilidades em deps
	uv pip install pip-audit
	uv run pip-audit
