# AGENTS.md

Bot WhatsApp/Telegram/Web para cartório com compliance LGPD, audit log imutável (hash chain + HMAC), PII scrubbing em 3 camadas e human-in-the-loop em toda ação jurídica.

Stack: FastAPI + SQLAlchemy 2.0 (este repo) + Supabase (Postgres + Storage) + n8n + Evolution API + OpenClaw + LiteLLM (Claude Opus 4.5 / GPT-5.5).

> **Para detalhes extensos** (security, workflow obrigatório, datasensitive, LGPD), ver `.harness/AGENTS.md`. Esta raiz é o spec-compliant agents.md; o `.harness/` é a versão operacional do time multi-agent.

## Setup commands

- Install deps: `cd backend && uv sync`
- Start dev:    `cd backend && uv run uvicorn app.main:app --reload --port 8000`
- Build:        `cd backend && uv build`                       # se aplicável
- Test:         `cd backend && pytest`                         # gate: coverage >= 90%
- Lint:         `cd backend && ruff check .`
- Format:       `cd backend && ruff format .`
- Typecheck:    `cd backend && mypy app/`                      # gate: 0 errors

## Project layout

- `backend/` — FastAPI + SQLAlchemy 2.0 + Pydantic v2. Lógica cartorária, audit chain, PII scrubber, emolumento. Pytest com coverage gate 90%.
- `backend/app/api/` — endpoints HTTP versionados (`/api/v1/...`)
- `backend/app/models/` — 5 tabelas core (cliente, conversa, protocolo, documento, emolumento) + `audit_log`
- `backend/app/services/` — `audit` (hash chain + HMAC), `pii` (scrubber), `emolumento` (regras estado MG)
- `backend/tests/` — pytest, gate coverage 90%
- `infra/n8n-workflows/` — JSON export dos workflows visuais
- `infra/supabase/` — `schema.sql` + migrations Alembic
- `scripts/` — utilitários de operação (deploy, backup, diagnose, lint-fix)
- `docs/ARCHITECTURE.md` — diagramas + decisões críticas
- `docs/ROADMAP.md` — 12 semanas (Fase 0 a 4). FONTE DA VERDADE para priorização
- `.harness/` — time multi-agent (Harness orquestrador + 3 reins) + standards + tasks

## Code style

- Python 3.11+, type hints obrigatórios em funções públicas
- Ruff: line-length 100, target py311. Rodar `ruff check .` + `ruff format .` antes do commit
- mypy strict em `app/`. Gate: 0 errors
- SQLAlchemy 2.0 typed style (`Mapped[...]`, `mapped_column`)
- Pydantic v2 models para entrada/saída HTTP. NUNCA retornar SQLAlchemy ORM direto
- Erros via exceptions tipadas (nunca raise genérico)
- Conventional Commits; mensagem termina com `Modified by Gustavo Almeida`

## Testing instructions

- Unit + integration em `backend/tests/`. Frameworks: pytest + pytest-asyncio + pytest-cov
- Coverage gate **>= 90%** (`pyproject.toml: addopts = --cov-fail-under=90`)
- Toda nova regra de emolumento tem teste com cenário nominal + 2-3 cenários de borda
- Toda mudança em `audit` ou `pii` precisa de teste que falha se a implementação regredir
- Rodar `pytest` local antes de commit. CI falha se coverage cair

## PR & commit conventions

- Branch from `master`; nunca push direto
- Conventional Commits: `feat:` / `fix:` / `docs:` / `test:` / `refactor:` / `chore:` / `perf:`
- Mensagem termina com `Modified by Gustavo Almeida`
- PR precisa de: build verde, coverage >= 90%, 1 review (revisor = outro rein)
- Mudança em `audit` ou `pii` exige review do `cartorio-lgpd`

## Security (NÃO PODE ERRAR)

- **Audit log tamper-evident**: append-only, SHA256 chain + HMAC. Edição retroativa invalida a cadeia.
- **PII scrubbing**: CPF/RG/telefone/email mascarados ANTES de ir pra LLM pública. 3 camadas: input / pre-LLM / output.
- **Human-in-the-loop**: bot NUNCA decide sozinho em isenção, urgência, validação jurídica, emissão de certidão/escritura.
- **LGPD by design**: soft delete, consentimento explícito, retenção configurável, DPO designado.
- **Secrets**: nunca commitar `.env`. Usar `backend/.env.example` como template.
- Qualquer dúvida: perguntar ao `cartorio-lgpd` antes de mexer.

## Team (delegação)

- **Backend FastAPI / SQLAlchemy / audit / PII** → `cartorio-dev`
- **Workflows n8n / Evolution API / OpenClaw / multi-canal / deploy** → `cartorio-n8n`
- **LGPD / RIPD / retenção / política privacidade / direito esquecimento** → `cartorio-lgpd`
- Mudança em `audit` ou `pii`: `cartorio-dev` implementa + `cartorio-lgpd` revisa + assina
- Mudança em workflow que toca PII: `cartorio-n8n` implementa + `cartorio-lgpd` revisa

Orquestração global vive em `.harness/agent.md` (Harness). Cada rein tem escopo próprio em `.harness/reins/<name>/agent.md`.

## Workflow obrigatório

Toda mudança (task, bug, refactor) segue o ciclo:

```
analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória
```

Pular etapa = bug. Especialmente em mudança de `audit` ou `pii`.

## Datasensitive

Este projeto lida com CPF, RG, protocolo jurídico, escritura. **Nenhum desses valores brutos pode sair do backend**. Ver `backend/app/services/pii.py` antes de qualquer integração nova com LLM ou storage externo.

## Integration & Verification Guidelines

- **Evolution API Webhooks**: Always parse inbound webhook requests to support both legacy root-level keys (`payload.get("message")`) and nested data keys (`payload.get("data", {}).get("message")`).
- **Test LLM Isolation**: Force environment variable overrides (`LLM_DEFAULT_PROVIDER="opencode_go"`) in `conftest.py` to prevent real LLM client network calls during local test runs.
- **Docker Swarm Port Handling**: When restarting Swarm services in `host` publishing mode, scale to `0` first, then scale back to `1` to avoid port conflict failures.
- **Chatwoot & Evolution Integration**: Always verify `CHATWOOT_ENABLED=true` is in the Evolution API service environment variables, create an API inbox in Chatwoot, and configure Evolution API using the generated `inboxId`.

## Padrão spec

Este arquivo segue o [agents.md](https://agents.md) spec — consumido por OpenCode, Codex, Cursor, Aider, Devin, Gemini CLI, etc. A versão estendida com security/standards operacionais vive em `.harness/AGENTS.md`.