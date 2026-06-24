# Makefile raiz - Cartorio Chatbot
# Orquestra backend (Python/FastAPI) + N8N workflows + docs.
# Execute `make help` para ver todos os alvos.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Cores para output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
RESET  := \033[0m

.PHONY: help
help:  ## Mostra esta ajuda (alvos disponiveis)
	@echo "$(GREEN)Cartorio Chatbot - Makefile raiz$(RESET)"
	@echo ""
	@echo "$(YELLOW)Uso:$(RESET) make <alvo>"
	@echo ""
	@echo "$(YELLOW)Alvos principais:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}' | sort
	@echo ""
	@echo "$(YELLOW)Documentacao:$(RESET) docs/ARCHITECTURE.md, docs/ROADMAP.md, .harness/AGENTS.md"

# ============================================================================
# Backend (Python/FastAPI) - delega para backend/Makefile
# ============================================================================

.PHONY: install
install:  ## Instala dependencias do backend (uv sync)
	@echo "$(GREEN)[backend] uv sync$(RESET)"
	@cd backend && uv sync

.PHONY: test
test:  ## Roda pytest com coverage gate 90%
	@echo "$(GREEN)[backend] pytest$(RESET)"
	@cd backend && uv run pytest --tb=short

.PHONY: test-fast
test-fast:  ## Pytest rapido sem coverage (desenvolvimento)
	@echo "$(GREEN)[backend] pytest rapido (no cov)$(RESET)"
	@cd backend && uv run pytest --tb=short -q --no-cov

.PHONY: test-one
test-one:  ## Roda 1 teste especifico (uso: make test-one TEST=test_pii)
	@echo "$(GREEN)[backend] pytest 1 arquivo$(RESET)"
	@cd backend && uv run pytest -v --tb=short --no-cov $(TEST)

.PHONY: lint
lint:  ## Roda ruff (lint) + mypy (typecheck) no backend
	@echo "$(GREEN)[backend] ruff check$(RESET)"
	@cd backend && uv run ruff check .
	@echo "$(GREEN)[backend] mypy app/$(RESET)"
	@cd backend && uv run mypy app/

.PHONY: format
format:  ## Auto-format com ruff
	@echo "$(GREEN)[backend] ruff format$(RESET)"
	@cd backend && uv run ruff format .
	@echo "$(GREEN)[backend] ruff check --fix$(RESET)"
	@cd backend && uv run ruff check . --fix

.PHONY: dev
dev:  ## Sobe API em modo dev (port 8000)
	@echo "$(GREEN)[backend] uvicorn dev$(RESET)"
	@cd backend && uv run uvicorn app.main:app --reload --port 8000

.PHONY: shell
shell:  ## Abre shell Python com contexto do backend
	@cd backend && uv run python

# ============================================================================
# Quality gates (compostos)
# ============================================================================

.PHONY: qa
qa:  ## Quality gate completo: lint + typecheck + tests
	@echo "$(YELLOW)=== Quality Gate Completo ===$(RESET)"
	@$(MAKE) lint
	@$(MAKE) test
	@echo "$(GREEN)=== Quality Gate PASSOU ===$(RESET)"

.PHONY: ci
ci:  ## CI local: simula GitHub Actions (lint + test)
	@echo "$(YELLOW)=== CI Local ===$(RESET)"
	@$(MAKE) lint
	@$(MAKE) test
	@echo "$(GREEN)=== CI PASSOU ===$(RESET)"

# ============================================================================
# N8N workflows
# ============================================================================

.PHONY: n8n-list
n8n-list:  ## Lista workflows N8N (requer N8N_API_KEY)
	@echo "$(YELLOW)[N8N] Listando workflows via API...$(RESET)"
	@if [ -z "$$N8N_API_KEY" ]; then \
		echo "$(RED)Erro: N8N_API_KEY nao definida. Exporte: export N8N_API_KEY=...$(RESET)"; \
		exit 1; \
	fi
	@curl -s -H "X-N8N-API-KEY: $$N8N_API_KEY" "$$N8N_BASE_URL/api/v1/workflows?limit=100" | python3 -m json.tool | head -50

.PHONY: n8n-export
n8n-export:  ## Exporta todos os workflows N8N para infra/n8n-workflows/
	@echo "$(YELLOW)[N8N] Exportando workflows...$(RESET)"
	@if [ -z "$$N8N_API_KEY" ]; then \
		echo "$(RED)Erro: N8N_API_KEY nao definida$(RESET)"; \
		exit 1; \
	fi
	@python3 scripts/n8n_export_all.py

.PHONY: n8n-test
n8n-test:  ## Roda testes E2E de todos os workflows N8N
	@echo "$(YELLOW)[N8N] Testando workflows...$(RESET)"
	@python3 scripts/n8n_test_all.py

# ============================================================================
# Documentacao
# ============================================================================

.PHONY: docs-list
docs-list:  ## Lista arquivos de documentacao
	@find docs/ -name "*.md" -type f | sort | head -30
	@echo "..."
	@find docs/ -name "*.md" -type f | wc -l | xargs -I {} echo "Total: {} arquivos .md em docs/"

.PHONY: changelog
changelog:  ## Mostra ultimas 20 entradas do CHANGELOG
	@head -100 docs/CHANGELOG.md

# ============================================================================
# Utilitarios
# ============================================================================

.PHONY: clean
clean:  ## Remove cache Python (__pycache__, .mypy_cache, .ruff_cache, .coverage)
	@echo "$(YELLOW)Limpando cache...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -f backend/.coverage
	@rm -rf htmlcov/
	@echo "$(GREEN)Cache removido$(RESET)"

.PHONY: tree
tree:  ## Mostra estrutura do projeto (3 niveis)
	@tree -L 3 -I '__pycache__|*.pyc|.git|.venv|node_modules|.mypy_cache|.ruff_cache|.coverage|htmlcov' --dirsfirst

.PHONY: status
status:  ## Mostra status git + ultimos commits
	@echo "$(YELLOW)=== Git Status ===$(RESET)"
	@git status --short
	@echo ""
	@echo "$(YELLOW)=== Ultimos 5 commits ===$(RESET)"
	@git log --oneline -5
	@echo ""
	@echo "$(YELLOW)=== Cobertura ===$(RESET)"
	@cd backend && uv run pytest --no-cov -q 2>&1 | grep -E "passed|coverage" | tail -2

# ============================================================================
# Setup inicial
# ============================================================================

.PHONY: setup
setup: install  ## Setup completo do ambiente de desenvolvimento
	@echo "$(GREEN)Setup completo!$(RESET)"
	@echo "Proximos passos:"
	@echo "  1. cp backend/.env.example backend/.env (e preencher)"
	@echo "  2. make dev (sobe API na porta 8000)"
	@echo "  3. make test (valida que tudo funciona)"

.PHONY: pre-commit
pre-commit:  ## Pre-commit: lint + test rapido
	@$(MAKE) lint
	@cd backend && uv run pytest --tb=line -q --no-cov -x 2>&1 | tail -5
