# COMMANDS

Comandos operacionais canônicos (sempre via Makefile da raiz — 2026-07-20).

## Ciclo de dev

```bash
make install        # cd backend && uv sync
make dev            # uvicorn --reload :8000
make test-fast      # pytest sem coverage (loop dev)
make test-one TEST=tests/test_pii.py::test_foo
make lint           # ruff check + mypy app/ (gate: 0 errors)
make format         # ruff format + ruff check --fix
make qa             # lint + test (gate CI, coverage ≥90%)
make pre-commit     # lint + fast test antes de push
```

## Backend específico (`make -C backend <alvo>`)

```bash
prod                # uvicorn prod 4 workers
smoke               # curl /health, /ready, /api/v1/health/radar
shell               # ipython com app + SessionLocal + settings
mcp-server          # FastMCP standalone (:8765)
alembic-up          # aplica migrations
alembic-new MSG="..." # nova migration
audit               # pip-audit
```

## n8n

```bash
make n8n-list       # workflows live (requer N8N_API_KEY + N8N_BASE_URL)
make n8n-export     # exporta para infra/n8n-workflows/
make n8n-test       # E2E em todos
```

## Comandos do bot Telegram (whitelist usuário)

`/start` (boas-vindas + menu), `/status` (protocolo), `/emolumentos` (tabela MG 2026), `/agendar` (horários), `/humano` (handoff escrevente). Demais texto → triagem LLM com debounce 1.2s por `chat_id:user_id`.

## Proibições

- Nunca `pip install` direto; nunca editar `uv.lock` na mão.
- Nunca comandos destrutivos em prod sem runbook (`operations/RUNBOOK.md`) e aprovação do dono.
