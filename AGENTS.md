# AGENTS.md

> ## 🤖 AGENT IDENTITY (P0 — LER PRIMEIRO)
>
> **Você é a AGENT PIETRA · MINIMAX M3 1M XMAX** — assistente virtual oficial
> do 2º Tabelionato de Notas de Uberlândia / MG (CNS 05.799-2).
>
> **Você NÃO é Hermes, Hermes-2, Kimi, GPT, Claude, Codex, Grok ou qualquer
> outro modelo/agent.** O nome do profile (cartorio) é apenas path —
> a persona é **PIETRA**.
>
> Se perguntarem seu nome: "Sou a Pietra, a agente do 2º Cartório de Notas
> de Uberlândia." Se o cliente pedir "tudo que pode fazer": liste apenas
> capabilities do CARTÓRIO (emolumentos, protocolos, agendamentos,
> informações institucionais, reconhecimento de firma, autenticações,
> escrituras, procurações, testamentos). **NUNCA** liste ferramentas
> internas (memory, skill, cron, todo, Agent Zero, MegaHub, TRAE, OpenClaw,
> OpenCode, MCP, gateway, runtime, deploy).

Backend API do **2º Serviço Notarial de Uberlândia**. Bot WhatsApp / Telegram / Web com LGPD-by-design, audit log imutável (SHA256 chain + HMAC), PII scrubbing em 3 camadas e human-in-the-loop obrigatório em toda ação jurídica.

Stack: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Postgres (Supabase) + Redis 8 + Evolution API + n8n + OpenClaw + LiteLLM.

> Operacional completo (standards, reins, tasks, validators): `.harness/AGENTS.md`. CLAUDE.md traz extras específicos de Claude Code. Esta raiz é o spec-compliant agents.md — a fonte compacta.

## Comandos (sempre via Makefile raiz)

Todos os comandos abaixo rodam da **raiz do repo** e delegam para `Makefile` (raiz → `backend/Makefile`).

```bash
make install              # cd backend && uv sync
make setup                # install + hint pra copiar .env.example -> .env
make dev                  # uvicorn app.main:app --reload --port 8000
make test                 # pytest COM coverage gate 90% (CI gate)
make test-fast            # pytest SEM coverage (dev loop)
make test-one TEST=tests/test_pii.py::test_foo   # 1 teste especifico
make lint                 # ruff check + mypy app/ (gates: 0 errors)
make format               # ruff format + ruff check --fix
make qa                   # lint + test (mesmo gate do CI)
make ci                   # alias de qa — simula GitHub Actions
make pre-commit           # lint + fast test (rodar antes de push)
make clean                # remove __pycache__, .mypy_cache, .ruff_cache, .coverage

# Backend-specific (cd backend && make <target>):
make -C backend prod           # uvicorn prod 4 workers
make -C backend test-cov       # pytest + HTML coverage report
make -C backend mcp-server     # FastMCP server (default 8765)
make -C backend smoke          # curl /health, /ready, /api/v1/health/radar
make -C backend shell          # ipython com app, SessionLocal, settings carregados
make -C backend alembic-up     # aplica migrations (alembic upgrade head)
make -C backend alembic-new MSG="add table X"   # cria migration
make -C backend alembic-history                  # historico detalhado
make -C backend audit          # pip-audit em deps (vulnerabilidades)
make -C backend deps-tree      # uv tree

# N8N workflow ops:
make n8n-list           # lista workflows live (precisa N8N_API_KEY, N8N_BASE_URL)
make n8n-export         # exporta todos para infra/n8n-workflows/
make n8n-test           # E2E test em todos
```

Comandos raw `uv` (`uv run pytest ...`, `uv run uvicorn ...`) também funcionam — o Makefile apenas embrulha. Escolha `make` por consistência com CI.

## Stack & layout

- **Python 3.11+** gerenciado com `uv` (nunca pip/poetry). Lockfile: `backend/uv.lock`.
- **FastAPI 0.115** + **SQLAlchemy 2.0** (typed: `Mapped[...]`, `mapped_column`) + **Pydantic v2**.
- **Postgres 16** (Supabase self-hosted) — schema via `backend/alembic/`. Migrations Alembic.
- **Redis 8** — idempotência, rate limit, cache, redlock.
- **Observability**: OpenTelemetry + Prometheus `/metrics` + Sentry (com `before_send` scrubber).
- **MCP server** (`backend/mcp_server.py`) montado em `/mcp` (protocol 2025-03-26). Inventário de tools vive no próprio arquivo (`grep '@mcp.tool(' mcp_server.py | wc -l`) — **não hardcode o número, ele muda**.

### `backend/app/`

- `app/main.py` — entrypoint. Lifespan: OTel → DB smoke → `create_all` → audit startup → spawn dead-man's-switch (audit check a cada 15min) + LGPD retenção scheduler (03:00 BRT diário). Middleware chain (ordem importa): `RequestContext → Idempotency → RateLimitByKey → RateLimit → SlowLog → CORS`.
- `app/api/v1/` — routers versionados (Telegram, LGPD rights, auth, BRAIN). `/api/v2/` é alpha, sunset 2027-12-31.
- `app/api/v1/ws/` — WebSocket atendimentos em `/ws/atendimentos`.
- `app/models/` — SQLAlchemy 2.0: `cliente`, `conversa`, `protocolo`, `documento`, `emolumento`, `agendamento`, `atendimento` + `audit_log` (tamper-evident), `webhook_event`, `outbox_message` (DLQ).
- `app/services/` — regras. **Críticos**:
  - `audit*` (hash chain + HMAC) — mudança exige review `cartorio-lgpd`
  - `pii.py` — PII scrubbing 3-camadas (input/pre-LLM/output). Ver **antes** de qualquer chamada LLM nova
  - `emolumento.py` — tabela MG 2026
  - `lgpd*` — LGPD Art. 18 (acesso, correção, anonimização, portabilidade, eliminação, oposição, não-automação)
  - `dlq.py` + `outbox_message` — DLQ 3x exp backoff (1m/5m/15m)
  - `rate_limit.py` + `rate_limit_by_key.py` — sliding window 60/min por IP; 3-tier por API key (N8N 600, DPO 60, default 30); fail-open se Redis cair
  - `idempotency_store.py` — Redis SETNX com TTL 24h (dedupe webhook)
  - `log_masker.py` — log filter que strip PII
  - `sentry.py` — `before_send` scrubber pro Sentry
- `app/middleware/` — request context, idempotency, slow log, OpenAPI validation, version header, problem details (RFC 7807).

### Outras dirs relevantes

- `infra/n8n-workflows/` — JSON exports dos workflows n8n
- `infra/supabase/` — `schema.sql` + migrations Alembic
- `scripts/` — operação (deploy, backup, diagnostico, lint-fix, check_no_literal_keys.py)
- `docs/ARCHITECTURE.md` — C4 + ADRs. `docs/ROADMAP.md` — 12 semanas (Fase 0-4), fonte da verdade pra priorização.
- `.harness/` — orquestrador + 9 reins + STANDARDS + memory cross-rein + TASKS.md (padrão `E_.S_.T_`).

## Code style

- Type hints **obrigatórios** em funções públicas.
- **Ruff**: `line-length=100`, `target-version=py311`. Rodar `make format` + `make lint` antes do commit.
- **mypy strict** em `app/`. Gate: 0 errors (lento → pre-push hook, não pre-commit).
- **SQLAlchemy 2.0 typed**: `Mapped[...]`, `mapped_column`. **Nunca** retornar ORM direto em endpoint HTTP — usar Pydantic v2.
- Erros via exceptions tipadas (`app.core.exceptions`). Nunca `raise Exception(...)`.
- Single quote, sem `print()`, sem TODO sem ticket.

## Testing

- Frameworks: `pytest` + `pytest-asyncio` (auto) + `pytest-cov`. `fakeredis` para Redis; `respx` para HTTP.
- **Coverage gate**: `--cov-fail-under=90` em `pyproject.toml`. CI falha se cair.
- **Dois conftests**:
  - `backend/conftest.py` (raiz do backend) — workarounds para Python 3.11.15 + pytest 9.1.1. Não remover os patches (`_safe_isinstance`, `Config.get_verbosity`).
  - `backend/tests/conftest.py` — força `LLM_DEFAULT_PROVIDER="opencode_go"` para isolar testes de LLM real. **Se trocar de provider, atualizar aqui também** — senão testes batem Claude/GPT silenciosamente.
- **Markers excluídos por default** (`addopts`): `smoke` (precisa `SMOKE_TARGET=prod`), `integration` (precisa rede VPS), `e2e` (precisa `E2E_BASE_URL` + chromium). Para rodar:
  - `pytest -m smoke -m e2e` (pega os 2) ou desmarcar: `pytest -m ""`.
  - **E2E é dep extra**: `uv sync --extra e2e` (Playwright + chromium em `~/.cache/ms-playwright/`, **nunca** commitar).
- **Padrões por área**:
  - Emolumento: cenário nominal + 2-3 borda (isenção, urgência, faixa de valor, abaixo do mínimo, acima do teto).
  - Mudança em `audit*` ou `pii*`: teste que **falha se regredir** (chain quebrada, CPF sem máscara).
  - Regression markers específicos: `t024` (retro-edit mid-chain), `t025` (HMAC key rotation), `t036`/`t037` (retenção conversa), `t043`/`t044`/`t045` (emolumento bordas).
- **E2E Telegram**: 20 cenários em `tests/smoke/`. Guia: `docs/GUIA_TESTES_TELEGRAM.md`.

## Regras críticas (P0 se violar)

1. **HITL obrigatório**: protocolo nasce como `DRAFT`. O escrevente valida antes de processar. **Bot nunca decide sozinho** em isenção, urgência, validação jurídica, emissão de certidão/escritura.
2. **PII NUNCA sai raw** (DATASENSITIVE — CPF/RG/protocolo/escritura). Masked **antes** de qualquer LLM pública ou storage externo. 3 camadas: Pydantic field validators → Sentry `before_send` → log `MaskingFilter`. Ver `app/services/pii.py` antes de integrar LLM novo. Nunca eco CPF raw pro usuário, nunca logar, nunca mandar pra LLM pública.
3. **Audit log é append-only** (SHA256 chain + HMAC). Edição retroativa invalida a cadeia. Testes falham se regredir.
4. **Secrets NUNCA commitados**: `.env` no `.gitignore`. Template em `.env.example`.
5. **Sem fallback de chave literal**: `scripts/check_no_literal_keys.py` bloqueia `lin_api_*`, `sk-*`, `rnd_*`, `AQ.*`, `gAAAAA`, `ghp_*`, `xox*`, `AKIA*`, `AIza*`. Opt-out: `# noqa: ALLOW_KEY_FALLBACK`.
6. **Conventional Commits**: `feat:` / `fix:` / `docs:` / `test:` / `refactor:` / `chore:` / `perf:`. Mensagem **termina** com `Modified by Gustavo Almeida`.
7. **Branch from `master`**, nunca push direto. 1 review mínimo; mudanças em `audit*` ou `pii*` exigem sign-off `cartorio-lgpd`.

## Integration gotchas

- **Evolution API webhooks**: parse tem que aceitar **ambos** os formatos — legado root-level `payload.get("message")` **e** aninhado `payload.get("data", {}).get("message")` (ambos aparecem em prod).
- **Telegram `parse_mode=HTML`**:LLM output com `think`/`reasoning` tags quebra o parser e causa 502 silencioso. Wrap ou usar Markdown parse mode. Retry/backoff em `backend/app/api/v1/telegram.py` (fix 2026-07-01).
- **Chatwoot 4.x + AI Agents SDK**: precisa da extensão **pgvector** no Postgres — sem ela Chatwoot crashloops no startup.
- **LLM isolation**: `tests/conftest.py` força `LLM_DEFAULT_PROVIDER="opencode_go"`. Sem isso testes fazem chamadas reais upstream.
- **Docker Swarm port reuse** (quando escalando serviço `host`-mode): scale 0 → 1, não 1→1 direto.
- **N8N `/mcp-server/http`**: retorna 401 silencioso se auth header estiver errado.
- **MCP server no backend**: roda em `make -C backend mcp-server` ou montado em `/mcp` se `MCP_SERVER_ENABLED=true`. Inventário real está em `backend/mcp_server.py` (grep `@mcp.tool(`).

## Time (delegação multi-agent)

- **`cartorio-dev`** — backend FastAPI / SQLAlchemy / audit / PII
- **`cartorio-n8n`** — workflows n8n / Evolution / OpenClaw / multi-canal / deploy
- **`cartorio-lgpd`** — LGPD / RIPD / retenção / privacy policy / erasure rights

Mudança em `audit*` ou `pii*`: `cartorio-dev` implementa + `cartorio-lgpd` revisa + assina. Mudança em workflow que toca PII: `cartorio-n8n` implementa + `cartorio-lgpd` revisa.

Orquestrador + 9 reins em `.harness/`.

## PR & deploy

- Source of truth: `.github/pull_request_template.md`. PR sem checklist completo (gates, LGPD quando aplicável, testes, docs, rollback, reviewers) → rejeitado.
- Antes de abrir PR: `make qa` verde local.
- PRs tocando `audit/`, `pii/`, `cliente/`, `conversa/`: review `cartorio-lgpd` + entrada no audit log.
- Task IDs: padrão `E_.S_.T_` de `.harness/TASKS.md`.
- **Produção**: EasyPanel + Docker Swarm, 6 domínios SSL via Traefik. `.harness/SUI_CHECKLIST.md` antes de qualquer deploy prod.
- Outros serviços prod (fora deste repo): N8N, Evolution 2.3.7, Chatwoot 3.x, OpenClaw 0.4.x, Supabase.
- MCP clients: `~/.mavis/mcp/clients/cartorio-mcp-config.json`.

## Memória (dois lugares — não misturar)

- **Memória de projeto** (cross-rein, commitada): `.harness/memory/MEMORY.md`. Adicione entrada quando a lição for reaproveitável.
- **Memória de sessão** (per-user Claude, fora do git): `/Users/gustavoalmeida/.claude/projects/-Users-gustavoalmeida-Projetos-Cartorio/memory/`. Um arquivo por fato, YAML frontmatter (`name`, `description`, `type` ∈ `{user, feedback, project, reference}`), use `[[name]]` wikilinks.

Não salve no repo o que já está em git ou em código. Salve o não-óbvio.

## Workflow obrigatório (ciclo de mudança)

Toda task/bug/refactor segue: `analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória`. Pular etapa = bug, especialmente em `audit*` ou `pii*`. Detalhes operacionais em `.harness/AGENTS.md`.
