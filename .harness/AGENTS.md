# AGENTS.md — Cartorio Chatbot

Bot WhatsApp/Telegram/Web para cartorio com compliance LGPD, audit log imutavel (hash chain + HMAC), PII scrubbing em 3 camadas e human-in-the-loop em toda acao juridica.

Stack: FastAPI + SQLAlchemy 2.0 (este repo) + Supabase (Postgres + Storage) + n8n + Evolution API + OpenClaw + LiteLLM (Claude Opus 4.5 / GPT-5.5).

## Setup commands

- Install deps: `cd backend && uv sync`
- Start dev:    `cd backend && uv run uvicorn app.main:app --reload --port 8000`
- Test:         `cd backend && pytest`          (gate: coverage >= 90%)
- Lint:         `cd backend && ruff check .`
- Format:       `cd backend && ruff format .`
- Typecheck:    `cd backend && mypy app/`        (gate: 0 errors)

## Project layout

- `backend/` — FastAPI + SQLAlchemy 2.0 + Pydantic v2. Logica cartoraria, audit chain, PII scrubber, emolumento. Pytest com coverage gate 90%. NAO MEXER sem antes ler este AGENTS.md + `.harness/STANDARDS.md`.
- `backend/app/api/` — endpoints HTTP versionados (`/api/v1/...`)
- `backend/app/models/` — 5 tabelas core (cliente, conversa, protocolo, documento, emolumento) + `audit_log`
- `backend/app/services/` — `audit` (hash chain + HMAC), `pii` (scrubber), `emolumento` (regras estado MG)
- `backend/tests/` — pytest, gate coverage 90%
- `infra/n8n-workflows/` — JSON export dos workflows visuais
- `infra/supabase/` — `schema.sql` + migrations Alembic
- `docs/ARCHITECTURE.md` — diagramas + decisoes criticas (hash chain, HITL, snapshot emolumento)
- `docs/ROADMAP.md` — 12 semanas (Fase 0 a 4). FONTE DA VERDADE para priorizacao.
- `.harness/` — time de agents + standards + tasks. Veja `.harness/AGENTS.md`.

## Code style

- Python 3.11+, type hints obrigatorios em funcoes publicas
- Ruff: line-length 100, target py311. Rodar `ruff check .` + `ruff format .` antes do commit
- mypy strict em `app/`. Gate: 0 errors
- SQLAlchemy 2.0 typed style (`Mapped[...]`, `mapped_column`)
- Pydantic v2 models para entrada/saida HTTP. NUNCA retornar SQLAlchemy ORM direto
- Erros via `app.core.exceptions` (a definir) — nunca raise generico

## Testing instructions

- Unit + integration em `backend/tests/`. Frameworks: pytest + pytest-asyncio + pytest-cov
- Coverage gate **>= 90%** (`pyproject.toml: addopts = --cov-fail-under=90`)
- Toda nova regra de emolumento tem teste com cenario nominal + 2-3 cenarios de borda (isencao, urgencia, faixa de valor)
- Toda mudanca em `audit` ou `pii` precisa de teste que falha se a implementacao regredir (chain quebrada, CPF nao scrubbed)
- Rodar `pytest` local antes de commit. CI falha se coverage cair

## PR & commit conventions

- Branch from `master`; nunca push direto
- Conventional Commits: `feat:` / `fix:` / `docs:` / `test:` / `refactor:` / `chore:` / `perf:`
- Mensagem termina com `Modified by Gustavo Almeida`
- PR precisa de: build verde, coverage >= 90%, 1 review (revisor = outro rein)
- Mudanca em `audit` ou `pii` exige review do `cartorio-lgpd`

## Security (NAO PODE ERRAR)

- **Audit log tamper-evident**: append-only, SHA256 chain + HMAC. Edicao retroativa invalida a cadeia. Verificacao automatica diaria.
- **PII scrubbing**: CPF/RG/telefone/email mascarados ANTES de ir pra LLM publica. Logs guardam apenas hash + scrubbed text. 3 camadas: input / pre-LLM / output.
- **Human-in-the-loop**: bot NUNCA decide sozinho em isencao, urgencia, validacao juridica, emissao de certidao/escritura.
- **LGPD by design**: soft delete, consentimento explicito, retencao configuravel, DPO designado.
- **Secrets**: nunca commitar `.env`. Usar `backend/.env.example` como template.
- Qualquer duvida: perguntar ao `cartorio-lgpd` antes de mexer.

## Workflow obrigatorio

Toda mudanca (task, bug, refactor) segue o ciclo:

```
analisar -> testar -> corrigir -> melhorar -> otimizar -> documentar -> comentar -> salvar na memoria
```

Aplicacao pratica:

1. **analisar** — ler AGENTS.md, `.harness/STANDARDS.md`, ROADMAP, AGENT do rein responsavel
2. **testar** — rodar testes locais antes de mudar nada; ver linha de base de coverage
3. **corrigir** — implementar mudanca minima. TDD quando possivel (teste falhou -> implementa -> passa)
4. **melhorar** — refactor mantendo testes verdes. NUNCA pular etapa "melhorar"
5. **otimizar** — perf check (latencia, query N+1, cache Redis onde aplicavel)
6. **documentar** — atualizar AGENTS.md / STANDARDS.md / ROADMAP.md / docstring
7. **comentar** — Conventional Commits + PR description objetiva
8. **salvar na memoria** — se a licao for reutilizavel alem deste task, escrever em `.harness/memory/MEMORY.md` (criterio: passa no "vale pra outro projeto?" — se nao, fica no PR description)

Regra: pular etapa = bug. Especialmente em mudanca de `audit` ou `pii`.

## Roster (delegacao)

Quando uma task chega, decidir:

- **Backend FastAPI / SQLAlchemy / audit / PII** -> `cartorio-dev`
- **Workflows n8n / Evolution API / OpenClaw / multi-canal** -> `cartorio-n8n`
- **LGPD / RIPD / retencao / politica privacidade / direito esquecimento** -> `cartorio-lgpd`
- Mudanca em `audit` ou `pii`: `cartorio-dev` implementa + `cartorio-lgpd` revisa + assina
- Mudanca em workflow que toca PII: `cartorio-n8n` implementa + `cartorio-lgpd` revisa

Orquestracao global vive em `.harness/agent.md` (Harness). Cada rein tem escopo proprio em `.harness/reins/<name>/agent.md`.

## Datasensitive

Este projeto lida com CPF, RG, protocolo juridico, escritura. **Nenhum desses valores brutos pode sair do backend**. Ver `backend/app/services/pii.py` antes de qualquer integracao nova com LLM ou storage externo.
