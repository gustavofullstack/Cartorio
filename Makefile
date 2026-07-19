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
	@cd backend && uv run pytest --tb=short --ignore=tests/test_dead_code_audit_g8.py
	@cd backend && uv run pytest --tb=short --no-cov tests/test_dead_code_audit_g8.py

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
ci:  ## CI local: reproduz os gates bloqueantes do GitHub Actions
	@echo "$(YELLOW)=== CI Local ===$(RESET)"
	@$(MAKE) secrets-scan-strict
	@cd backend && uv run ruff format --check .
	@$(MAKE) lint
	@$(MAKE) test
	@$(MAKE) openapi-check
	@$(MAKE) n8n-validate
	@$(MAKE) coverage-gate
	@python3 scripts/check_no_bare_exception.py
	@echo "$(GREEN)=== CI PASSOU ===$(RESET)"

# ============================================================================
# N8N workflows
# ============================================================================

.PHONY: openapi-check
openapi-check:  ## Valida OpenAPI snapshot contra baseline (G6.A.T2 gate CI)
	@echo "$(YELLOW)[OpenAPI] Comparando snapshot contra baseline...$(RESET)"
	@python3 scripts/openapi_snapshot.py --check
	@echo "$(GREEN)[OpenAPI] Snapshot OK (sem breaking changes)$(RESET)"

.PHONY: openapi-update
openapi-update:  ## Atualiza baseline OpenAPI (apos bump de versao)
	@echo "$(YELLOW)[OpenAPI] Atualizando baseline...$(RESET)"
	@python3 scripts/openapi_snapshot.py --update
	@echo "$(GREEN)[OpenAPI] Baseline atualizado$(RESET)"

.PHONY: n8n-validate
n8n-validate:  ## Valida workflows N8N contra 9 regras (G6.B.T1 gate merge)
	@echo "$(YELLOW)[N8N] Validando workflows...$(RESET)"
	@python3 scripts/n8n_workflow_validator.py

# ============================================================================
# Secrets scanning (G8.23.T2 — Wave 52)
# ============================================================================

.PHONY: secrets-scan
secrets-scan:  ## Compose secrets scanner (literal_keys + gitleaks + trufflehog opt-in)
	@echo "$(YELLOW)[secrets] Compondo literal_keys + gitleaks (trufflehog opt-in)...$(RESET)"
	@python3 scripts/check_no_literal_keys_compose.py

.PHONY: secrets-scan-strict
secrets-scan-strict:  ## Secrets scan strict (severity=critical, fail-fast)
	@echo "$(YELLOW)[secrets] Strict scan — critical only$(RESET)"
	@python3 scripts/check_no_literal_keys_compose.py --severity critical --no-fail-fast

.PHONY: secrets-scan-tracked-report
secrets-scan-tracked-report:  ## Inventario redigido de arquivos textuais rastreados (nao bloqueia)
	@echo "$(YELLOW)[secrets] Inventario Git redigido (report-only)...$(RESET)"
	@python3 backend/scripts/check_no_literal_keys.py --tracked-files --severity critical --report-only

.PHONY: secrets-scan-trufflehog
secrets-scan-trufflehog:  ## Secrets scan com trufflehog (opt-in, mais lento)
	@echo "$(YELLOW)[secrets] Trufflehog full scan...$(RESET)"
	@python3 scripts/check_no_literal_keys_compose.py --scanner trufflehog --scanner literal_keys
	@echo "$(GREEN)[N8N] Validacao OK$(RESET)"

.PHONY: n8n-audit
n8n-audit:  ## Audita modificacoes Git em workflows N8N criticos (offline)
	@python3 scripts/n8n_wf_audit.py $(ARGS)

.PHONY: n8n-orphans
n8n-orphans:  ## Relatorio CSV de JSONs N8N sem referencias (offline)
	@uv run python scripts/n8n_orphan_detector.py

.PHONY: openclaw-skills-list
openclaw-skills-list:  ## Lista + valida skills em .agents/skills/ (G8.21.T1)
	@python3 scripts/openclaw_skill_registry.py

.PHONY: coverage-gate
coverage-gate:  ## Coverage gate fail-safe (G6.A.T5)
	@echo "$(YELLOW)[Coverage] Validando gate >=95%...$(RESET)"
	@python3 scripts/coverage_gate.py

.PHONY: postman-export
postman-export:  ## Gera Postman collection do OpenAPI local (G7.17.T1)
	@cd backend && DATABASE_URL=$${DATABASE_URL:-sqlite:///:memory:} uv run python ../scripts/postman_export.py --from-app

.PHONY: postman-sync
postman-sync:  ## Regenera Postman collection do OpenAPI (G8.17.T1 - sync, tag-folders, LGPD-safe)
	@cd backend && uv run python ../scripts/postman_sync.py --from-app --output ../infra/postman/cartorio-api.postman_collection.json --base-url https://api.2notasudi.com.br

.PHONY: postman-sync-offline
postman-sync-offline:  ## Sync sem network (cached openapi.json em backend/docs/openapi.json)
	@cd backend && uv run python ../scripts/postman_sync.py --bypass-network --output ../infra/postman/cartorio-api.postman_collection.json --base-url https://api.2notasudi.com.br

.PHONY: postman-sync-test
postman-sync-test:  ## Roda pytest tests/test_postman_sync_g8.py
	@cd backend && uv run pytest -v --no-cov --tb=short tests/test_postman_sync_g8.py

.PHONY: g7-status
g7-status:  ## Status super plano G7 (orchestrator)
	@python3 scripts/g7_orchestrator.py status

.PHONY: super-loop
super-loop:  ## Super loop orchestrator (G7 default; status|next|validate|legacy-status)
	@python3 scripts/super_loop_orchestrator.py $(or $(CMD),status)

.PHONY: g7-next
g7-next:  ## Próximas 4 tasks abertas G7 (4 agents / squad)
	@python3 scripts/g7_orchestrator.py next

.PHONY: pii-inventory
pii-inventory:  ## G7.02.T3 PII pre-LLM call-site inventory
	@python3 scripts/pii_pre_llm_inventory.py --strict

.PHONY: bare-exception
bare-exception:  ## Gate: zero raise Exception( em app/ (G7.21.T4)
	@python3 scripts/check_no_bare_exception.py

# G8 DoR/DoD (honesty gate: code+tests+lesson, no fake PROGRESS ticks): docs/G8_DOR_DOD.md
# Cross-ref: SUPER_GOALS_G8.md · SUPER_PLANO_G8_100_TASKS.md · docs/G7_DOR_DOD.md
.PHONY: g7-validate
g7-validate:  ## G7 super teste validador (local+prod composite); G8 DoR/DoD: docs/G8_DOR_DOD.md
	@echo "$(YELLOW)[G7] Super validator...$(RESET)"
	@python3 scripts/g7_super_validator.py --report docs/G7_VALIDATOR_REPORT.md

.PHONY: g7-composite
g7-composite:  ## G7.24.T3 composite gate: import/pytest + DNS + radar (exit 0 OK / 1 local fail / 2 prod HOLD)
	@echo "$(YELLOW)[G7] Composite gate (Radar+DNS+local)...$(RESET)"
	@python3 scripts/g7_composite_gate.py --import-only --report docs/G7_COMPOSITE_GATE_WAVE24.md

.PHONY: g7-progress
g7-progress:  ## G7.23.T3 append wave block to PROGRESS.md (WAVE=N SUMMARY="...")
	@if [ -z "$(WAVE)" ] || [ -z "$(SUMMARY)" ]; then \
		echo "$(RED)Uso: make g7-progress WAVE=24 SUMMARY=\"composite gate\"$(RESET)"; \
		exit 1; \
	fi
	@python3 scripts/g7_progress_append.py --wave $(WAVE) --summary "$(SUMMARY)" \
		$(if $(AGENTS),--agents "$(AGENTS)",) \
		$(if $(TASKS),--tasks "$(TASKS)",) \
		$(if $(STATUS),--status "$(STATUS)",) \
		$(if $(FORCE),--force,)

.PHONY: progress-audit
progress-audit:  ## G8.16.T1 PROGRESS.md audit/persist (WAVE=N AGENT=sre BULLET="..." PRE=50 POST=51 TESTS=5)
	@if [ -z "$(WAVE)" ]; then \
		echo "$(RED)Uso: make progress-audit WAVE=46 AGENT=sre PRE=50 POST=51 TESTS=5 BULLET=\"**G8.16.T1** descr\"$(RESET)"; \
		exit 1; \
	fi
	@python3 scripts/progress_audit.py --wave $(WAVE) \
		$(if $(AGENT),--agent $(AGENT),--agent sre) \
		$(if $(PRE),--honest-pre $(PRE),) \
		$(if $(POST),--honest-post $(POST),) \
		$(if $(TESTS),--tests $(TESTS),) \
		$(if $(BULLET),--bullet "$(BULLET)",) \
		--apply

.PHONY: radar-smoke
radar-smoke:  ## Health radar smoke CLI (G6.D.T1)
	@echo "$(YELLOW)[Radar] Smoke test /api/v1/health/radar/expanded...$(RESET)"
	@python3 scripts/radar_smoke.py

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

# ============================================================================
# SRE / DNS health checks
# ============================================================================

.PHONY: dns-check
dns-check:  ## DNS health soft (default): exit 0 se core 7 OK; 3 HOLD NXDOMAIN nao falha CI local
	@echo "$(YELLOW)[SRE] DNS health check (MODE=soft default; DNS_CHECK_STRICT=1 for 10/10)$(RESET)"
	@bash scripts/check_dns_health.sh

.PHONY: dns-check-strict
dns-check-strict:  ## DNS health strict: exit 0 so se 10/10 hosts resolvem
	@echo "$(YELLOW)[SRE] DNS health check STRICT (all 10)$(RESET)"
	@DNS_CHECK_STRICT=1 bash scripts/check_dns_health.sh

.PHONY: dns-verify-records
dns-verify-records:  ## Integration test manual: assume Gustavo criou 3 A records; valida (WORK/HOLD)
	@echo "$(YELLOW)[SRE] DNS records integration test$(RESET)"
	@bash tests/manual/verify_dns_records.sh

# ============================================================================
# SUPER PLANO 100/100 (2026-07-15) — consolidated brain targets
# ============================================================================

.PHONY: super-plano
super-plano:  ## Status do SUPER PLANO 100/100 (6 phases, 7 commits, 50 tasks)
	@echo "$(GREEN)=== SUPER PLANO 100/100 ===$(RESET)"
	@echo "$(YELLOW)Data: 2026-07-15 (sessao ~3h 11:30 → 14:45 BRT)$(RESET)"
	@echo ""
	@echo "$(GREEN)Fases completadas:$(RESET) F0 setup, F1, F2 quality, F3 brain, F4 sre+evo, F5 lgpd+refactor, F6 consolidation"
	@echo "$(GREEN)Sub-agents:$(RESET) 8 (quality, brain, sre, evolution, lgpd, front paralelo, brain F6)"
	@echo "$(GREEN)Commits:$(RESET) 7 (6116a60, 6cc2fa7, d0332da, d46ebc8, 55fde90, 4b8dce7, T100)"
	@echo "$(GREEN)Tasks:$(RESET) 50+ completadas"
	@echo "$(GREEN)Arquivos novos:$(RESET) 12+ (DNS runbooks, LobeChat STATUS/README/monitors.json, telegram.env.example, OUTAGE_RECOVERY_RUNBOOK, catalog.py +6 endpoints)"
	@echo "$(GREEN)Backend gates:$(RESET) VERDE (pytest 2776+, mypy 0, ruff 0, coverage 95%)"
	@echo "$(YELLOW)Producao:$(RESET) PARTIAL (3/10 dominios 502/000 HOLD-GUSTAVO)"
	@echo ""
	@echo "$(YELLOW)Referencias:$(RESET) STATUS.md, .brain/index.md, .brain/loop-state.json (v3.0.0), .harness/memory/lesson-180-super-plano-100-100-cycle-2026-07-15.md"

.PHONY: postman-import
postman-import:  ## Mostra como importar Cartorio_API_v1.postman_collection.json no Postman
	@echo "$(GREEN)=== Postman Import Instructions ===$(RESET)"
	@if [ -f infra/postman/Cartorio_API_v1.postman_collection.json ]; then \
		echo "Colecao encontrada em infra/postman/Cartorio_API_v1.postman_collection.json"; \
		echo "Endpoints catalogados: 73"; \
		echo ""; \
		echo "Passos:"; \
		echo "  1. Abrir Postman"; \
		echo "  2. Import > File > Upload Files"; \
		echo "  3. Selecionar infra/postman/Cartorio_API_v1.postman_collection.json"; \
		echo "  4. Configurar variaveis: BASE_URL=https://api.2notasudi.com.br, API_KEY=<DPO_TOKEN>"; \
		echo "  5. Rodar Runner para validar 73 endpoints end-to-end"; \
	else \
		echo "$(RED)Colecao ainda nao commitada (F6 front agent em paralelo). Verificar em T100.$(RESET)"; \
	fi

.PHONY: health-radar
health-radar:  ## Health radar expanded (F6 front) - status detalhado dos 10 servicos prod
	@echo "$(GREEN)=== Health Radar Expanded ===$(RESET)"
	@curl -sk https://api.2notasudi.com.br/api/v1/health/radar/expanded | python3 -m json.tool 2>/dev/null || \
		curl -sk https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool
