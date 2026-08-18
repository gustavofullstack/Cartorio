# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Backend API for **2º Serviço Notarial de Uberlândia** — a Brazilian notary public office. Multi-channel chatbot platform (WhatsApp / Telegram / Web) with **LGPD-by-design** compliance, immutable audit chain (SHA256 + HMAC), 3-layer PII scrubbing, and mandatory Human-in-the-Loop for all legal acts.

Production: `https://api.2notasudi.com.br` (FastAPI + 6 sibling services).

## Quick commands

All commands run from the repo root and delegate to `backend/Makefile` via the root `Makefile`:

```bash
make install           # cd backend && uv sync
make setup             # install + hint to copy backend/.env.example -> backend/.env
make dev               # uvicorn app.main:app --reload --port 8000
make test              # pytest with coverage gate ≥90% (dead_code_g8 runs separately)
make test-fast         # pytest without coverage (faster, dev loop)
make test-one TEST=test_audit.py::test_x  # single test
make lint              # ruff check + mypy app/ + secret scanner (gates: 0 errors)
make format            # ruff format + ruff check --fix
make qa                # lint + test (local quality gate)
make ci                # NOT an alias of qa — stricter: secrets-scan-strict + ruff format --check + lint + test + openapi-check + n8n-validate + coverage-gate + bare-exception
make pre-commit        # lint + fast test (run before pushing)
make clean             # remove __pycache__, .mypy_cache, .ruff_cache, .coverage
make shell             # open Python shell with backend context loaded
make status            # git status + last 5 commits + coverage summary
make openapi-check     # OpenAPI snapshot vs baseline (CI gate)
make n8n-validate      # validate N8N JSON workflows (9 rules)
make n8n-list          # list live N8N workflows (needs N8N_API_KEY, N8N_BASE_URL)
make n8n-export        # export all N8N workflows to infra/n8n-workflows/
make n8n-test          # E2E test all N8N workflows
```

Lint tools (`ruff`, `mypy`) live in optional extra `dev`. After a fresh clone or `uv lock` change:

```bash
cd backend && uv sync --extra dev
```

`make install` (`uv sync` without extras) can drop ruff/mypy from the venv. Symptom: `Failed to spawn: ruff`. Fix: `--extra dev`, never assume the venv is complete after lock update.

Single test without make:
```bash
cd backend && uv run pytest -v --no-cov tests/test_audit.py::test_x
```

## Stack & runtime

- **Python 3.11+** (`requires-python`; prod/README currently 3.12), managed with `uv` (no pip/poetry). Lockfile: `backend/uv.lock`
- **FastAPI 0.115** + **SQLAlchemy 2.0** (typed style: `Mapped[...]`, `mapped_column`) + **Pydantic v2**
- **PostgreSQL 16** (Supabase self-hosted) — schema via Alembic in `backend/alembic/`
- **Redis 8** (idempotency, rate limit, cache, locks)
- **Observability**: OpenTelemetry traces + Prometheus metrics + Sentry (with PII before_send scrubber)
- **MCP server** (`backend/mcp_server.py`) mounted at `/mcp` — protocol 2025-03-26. Tool inventory is in the file itself (grep `@mcp.tool(` for current count); do NOT hardcode a number — the inventory drifts

## High-level architecture

```
Evolution API ──► OpenClaw Gateway ──► N8N workflows ──► Cartório API ──► Supabase (PG)
  (WhatsApp)       (LLM router)        (orchestration)    (rules + audit)    + Redis
                                                                              │
                              Chatwoot ◄──── handoff ───── API ◄──── Telegram/Channel
```

**Multi-agent context** (`.harness/`): this is an **agents.md-compliant** project. Operational rules, security details, multi-agent delegation live in `.harness/AGENTS.md` (NOT in this file). The root `AGENTS.md` is the compact spec-compliant subset.

### Backend layout (`backend/app/`)

- **`api/`** — HTTP routers, versioned under `/api/v1/` (current) and `/api/v2/` (alpha, sunset 2027-12-31). Telegram + WhatsApp webhooks, Pietra REST, LGPD rights, auth, BRAIN, CNJ export all live here.
- **`models/`** — SQLAlchemy 2.0 typed models: `cliente`, `conversa`, `protocolo`, `documento`, `emolumento`, `agendamento`, `atendimento`, plus `audit_log` (tamper-evident), `webhook_event`, `outbox_message` (DLQ).
- **`services/`** — Business logic. **Critical ones**:
  - `audit.py` / `audit_create.py` / `audit_query.py` / `audit_context.py` — immutable hash chain (any change requires `cartorio-lgpd` review)
  - `pii.py` — 3-layer PII scrubbing (input / pre-LLM / output). See before touching any LLM call.
  - `emolumento.py` + `emolumento_real_djalma.py` — MG 2026 fee table (state-regulated; TJMG + TFJ + RECOMPE + ISSQN)
  - `cartorio_agent.py` — LLM agent with Redis circuit breaker (MiniMax → litellm → zen fallbacks). Never silent on timeout.
  - `pietra_*` — customer-facing agent: coleta, atendimento, memória (Redis 30min + Postgres), identity/outbound guards. Bot persona is **Pietra** (not Hermes/Claude/GPT).
  - `conhecimento_*` — BRAIN institutional corpus. New items start `PENDING_HUMAN_VALIDATION`; never auto-promote to PUBLISHED (HITL + `cartorio-lgpd`).
  - `evolution_ingest.py` + `api/v1/whatsapp.py` — Evolution webhook parse + sendText. Path that actually replies: `POST /api/v1/whatsapp/webhook`.
  - `lgpd_*` — LGPD Art. 18 rights (access, correction, anonymization, portability, erasure, opposition, non-automation)
  - `dlq.py` + `outbox_message` — Dead Letter Queue with 3x exp backoff (1m/5m/15m)
  - `rate_limit.py` + `rate_limit_by_key.py` — sliding window (60/min per IP), 3-tier by API key (N8N 600, DPO 60, default 30). Fail-open if Redis down.
  - `idempotency_store.py` — Redis SETNX with 24h TTL (webhook dedupe)
  - `log_masker.py` — log filter that strips PII
  - `sentry.py` — `before_send` scrubber for Sentry
  - `lgpd/` package — full compliance toolkit
- **`middleware/`** — Request context, idempotency, slow log, OpenAPI validation, version header, problem details (RFC 7807)
- **`mcp_server.py`** (repo root of `backend/`) — FastMCP sub-app mounted at `/mcp`

### Entry point

`backend/app/main.py` orchestrates everything:
1. **Lifespan** startup: OTel init → DB smoke test → `Base.metadata.create_all` → audit startup entry → spawns **dead man's switch loop** (audit integrity check every 15 min) and **LGPD retenção scheduler** (daily 03:00 BRT).
2. **Middleware chain** (order matters): RequestContext → Idempotency → RateLimitByKey → RateLimit → SlowLog → CORS.
3. **MCP sub-app** mounted at `/mcp` if `MCP_SERVER_ENABLED=true`.
4. Routers: `api_router` (includes Pietra under `/pietra`), `ws_router` (WebSocket atendimentos), `telegram_router`, `whatsapp_router`, `lgpd_router`, `lgpd_v2_router` (JWT+DPO), `ripd_router`, `brain_router`, `cnj_export_router`, `auth_login_router`, `bot_lgpd_router`, `api_v2_router`.

## Critical rules (cannot be skipped)

These come from `AGENTS.md` and `.harness/AGENTS.md`. Violating them is a P0 incident:

1. **HITL mandatory**: protocolo always born as `DRAFT`. The escrevente (notary clerk) validates before processing. The bot must never decide alone on isenções, urgency, legal validation, or certidão/escritura emission.
2. **PII never leaves raw** (**DATASENSITIVE** — CPF/RG/protocolo/escritura): masked BEFORE any external LLM call or storage. 3 layers: Pydantic field validators → Sentry `before_send` → log `MaskingFilter`. See `backend/app/services/pii.py` BEFORE any new integration. Never echo a raw CPF back to the user, never log it, never send it to a public LLM.
3. **Audit log is append-only** with SHA256 chain + HMAC. Any retro edit invalidates the chain. Tests must fail if implementation regresses.
4. **Secrets never committed**: `.env` is gitignored. Templates: `backend/.env.example` (API) and root `.env.example`.
5. **No literal API key fallbacks**: `scripts/check_no_literal_keys.py` blocks `lin_api_*`, `sk-*`, `rnd_*`, `AQ.*`, `gAAAAA`, `ghp_*`, `xox*`, `AKIA*`, `AIza*` patterns. Opt-out: `# noqa: ALLOW_KEY_FALLBACK`.
6. **Conventional Commits** only: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `perf:` — commit message must end with `Modified by Gustavo Almeida`.
7. **Always branch from `master`**, never push direct. One PR review required; changes in `audit` or `pii` require `cartorio-lgpd` sign-off.

## Workflow obrigatório (do AGENTS.md)

Toda mudança (task, bug, refactor) segue o ciclo abaixo. Pular etapa = bug. Especialmente em mudança de `audit` ou `pii`:

```
analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória
```

Materializado em `.harness/agents/` (`01-analyze-agent.sh` ... `05-memory-agent.sh`). O ponto de "salvar na memória" escreve em `.harness/memory/MEMORY.md` (cross-rein) ou na sessão (ver "Session memory convention" abaixo).

## Multi-agent delegation

Reins under the Harness orquestrador (`.harness/agent.md`). When delegating, declare upfront which rein owns review. The 3 primary reins for backend work:

- **`cartorio-dev`** — backend FastAPI / SQLAlchemy / audit / PII
- **`cartorio-n8n`** — N8N workflows / Evolution API / OpenClaw / multi-canal / deploy (JSON exports in `infra/n8n-workflows/`)
- **`cartorio-lgpd`** — LGPD / RIPD / retenção / privacy policy / erasure rights

Full inventory of 9 reins in `.harness/reins/` (dev, n8n, lgpd, data, evolution, front, security, sre, watchdog). Each rein has its own `agent.md` defining scope.

## Testing

- **Framework**: `pytest` + `pytest-asyncio` + `pytest-cov`. Async mode auto.
- **Coverage gate**: `--cov-fail-under=90` (CI fails if it drops). Enforced in `backend/pyproject.toml`.
- **Markers**: `smoke` (needs `SMOKE_TARGET=prod`) and `integration` (needs VPS network) are excluded by default addopts.
- **Patterns**:
  - Emolumento changes need nominal scenario + 2-3 edge cases
  - Audit/PII changes need regression tests
  - Use `fakeredis` for Redis in tests
  - `LLM_DEFAULT_PROVIDER="opencode_go"` override in `conftest.py` to avoid real LLM calls
- **E2E** (Telegram webhook): 20 scenarios in `tests/smoke/`. Production webhook live-tested; see `docs/GUIA_TESTES_TELEGRAM.md`.

## Lint / typecheck / format

- **ruff**: line-length 100, target py311. `ruff check .` + `ruff format .`
- **mypy**: strict on `app/`. Gate: 0 errors. Slow → pre-push hook only, not pre-commit.
- **pre-commit**: install with `pip install pre-commit && pre-commit install`. Heavy hooks (mypy, pytest) are `manual` stage — run `pre-commit run --hook-stage manual --all-files` before push.

## Deploy & infra

- **Production**: EasyPanel + Docker Swarm. 6 SSL domains via Traefik reverse proxy.
- **Other services** (in production but separate repos/processes): N8N, Evolution API 2.3.7, Chatwoot 3.x, OpenClaw Gateway 0.4.x, Supabase.
- **MCP servers exposed** via `~/.mavis/mcp/clients/cartorio-mcp-config.json`: `n8n-mcp` (50 tools), `supabase-mcp` (30), `cartorio-api` (count in `backend/mcp_server.py` — see Stack section), `easypanel-mcp` (57), `openclaw-mcp` (20).
- **Real-time protocol exchange**: WebSocket at `/ws/atendimentos`.
- **Backup**: `backend/scripts/` has backup/restore scripts; `infra/backup/` has cron jobs.
- **Monitoring**: Prometheus metrics at `/metrics`; Sentry for errors.
- **Go-live checklist**: `.harness/SUI_CHECKLIST.md` — required reading before any prod deploy.

## Notable integration gotchas (from AGENTS.md + MEMORY)

- **Evolution API webhooks**: support BOTH legacy root-level (`payload.get("message")`) AND nested (`payload.get("data", {}).get("message")`) — both formats appear in the wild.
- **Evolution event names**: prod sends `MESSAGES_UPSERT` (uppercase, underscore). Compare case-insensitively and accept `.` or `_` (`is_messages_upsert_event()` in `evolution_ingest.py`). A case-sensitive `event != "messages.upsert"` silently drops all inbound WhatsApp.
- **WhatsApp LID `@lid`**: multi-device chats write to `NNN@lid`, not `5534...@s.whatsapp.net`. Reply on the **same JID**; converting to `@s.whatsapp.net` opens a parallel mute thread.
- **WhatsApp reply path**: `POST /api/v1/whatsapp/webhook` runs `sendText`. `POST /api/v1/webhook/evolution` is ingest-only (returns JSON, does not reply). Dual-auth: HMAC **or** timing-safe `X-Webhook-Secret` / `X-Evolution-Webhook-Secret` / `Authorization: Bearer` (Evolution Baileys does not sign the body).
- **radar `evolution=online` ≠ WhatsApp session connected**. Check `GET /api/v1/whatsapp/health` → `whatsapp_session: open|close|connecting`. Session `close` needs QR reconnect (SUI).
- **Chatwoot + Evolution**: set `CHATWOOT_ENABLED=true` in Evolution env; create API inbox in Chatwoot; configure Evolution with the generated `inboxId`.
- **Docker Swarm port reuse**: when restarting Swarm services in `host` publish mode, scale to `0` first then back to `1` to avoid port conflict errors.
- **Telegram `parse_mode=HTML`**: LLM output containing `<think>`/`<reasoning>` tags breaks `parse_mode=HTML` and causes silent 502. Wrap LLM response before sending, or use Markdown parse mode. (See `backend/app/api/v1/telegram.py` for the retry-with-backoff implemented 2026-07-01.)
- **N8N `/mcp-server/http`**: needs correct auth header — returns 401 if token/header is broken.
- **MCP `/mcp` is not Traefik-routed in prod** (Lesson 282). `app.mount("/mcp", ...)` exists, but `https://api.2notasudi.com.br/mcp` is 404. Do not assume external MCP clients can call `cartorio_calcular_emolumento`.
- **Chatwoot 4.x + AI Agents SDK**: requires `pgvector` extension in the Postgres database or Chatwoot crashloops on startup.
- **LLM isolation in tests**: `backend/tests/conftest.py` force-sets `LLM_DEFAULT_PROVIDER="opencode_go"` so the test suite never hits a real upstream LLM. If you swap providers, update `conftest.py` too — otherwise tests will silently call Claude/GPT.
- **Alembic revision IDs are unique**: never reuse an occupied `revision=` (Lesson 261). Collision creates multiple heads. Check `make -C backend alembic-history` / `alembic heads` before adding a migration. Current chain includes 0028–0032 + knowledge/CNJ/envelope files.
- **Pietra outbound**: never leak internal vocab (MCP, gateway, Hermes, OpenClaw) to customers. Identity guard + outbound sanitizer in `pietra_identity_guard.py` / `pietra_outbound_guard.py`. Never call the client "doutor/doutora" unless they asked. Institutional facts: `docs/DJALMA_CARTORIO_DOSSIER.md` (not memory files).

## Documentation map

- Root: `README.md` (production status), `AGENTS.md` (compact agent contract), `PROMPT.MD` / `PROMPT.json` (project briefings).
- `docs/ARCHITECTURE.md` — C4 diagrams + ADRs
- `docs/API.md` — 50+ endpoints with curl
- `docs/DB.md` — 20+ tables + ER
- `docs/DEPLOYMENT.md`, `docs/RUNBOOK_VPS.md` — ops
- `docs/LGPD.md`, `docs/CONTRIBUTING.md`
- `docs/BRAIN_PIPELINE_CONHECIMENTO.md` — institutional corpus ingest/classify/HITL
- `docs/DJALMA_CARTORIO_DOSSIER.md` — canonical institutional facts for Pietra
- `docs/platforms/` — vendor-specific runbooks (N8N, Chatwoot, Evolution, Supabase, Redis, Jules)
- `docs/adr/README.md` — 24+ ADRs
- `.harness/memory/MEMORY.md` — cross-session lessons (loaded each session)
- `.harness/STANDARDS.md` — code standards
- `cartorio-ai/` — agent identity/governance docs (not production code)
- `services/spectrum-gateway/` — TypeScript iMessage/Photon sidecar (Mac-local transport; backend stays on VPS)
- `.agents/skills/` — OpenClaw/agent skills (n8n, supabase, easypanel, VPS)

## PR requirements

`.github/pull_request_template.md` is the source of truth and is enforced. PRs without a complete checklist (quality gates, LGPD if applicable, tests, docs, rollback plan, reviewers) will be rejected. Key points:

- `make qa` must pass locally before opening the PR.
- Any PR touching `audit/`, `pii/`, `cliente/`, or `conversa/` requires `cartorio-lgpd` review + audit log entry.
- Tasks IDs follow `E_.S_.T_` pattern from `.harness/TASKS.md`.

## Session memory convention

Two distinct memory locations — don't conflate them:

**Project memory** (cross-rein lessons, committed): `.harness/memory/MEMORY.md`. Add an entry when a lesson generalizes across reins.

**Session memory** (per-user Claude Code memory, not in git): `/Users/gustavoalmeida/.claude/projects/-Users-gustavoalmeida-Projetos-Cartorio/memory/` on Gustavo's Mac. This Cursor/Linux checkout is `/config/workspace/Cartorio` — do **not** write session memory files into the git worktree. Add a one-file-per-fact with YAML frontmatter (`name`, `description`, `type` where type ∈ {user, feedback, project, reference}); reference index lives in `MEMORY.md` of that dir. Use `[[name]]` wikilinks liberally. Update existing files rather than creating duplicates; delete memories that turned out wrong. Don't save what the repo already records (git history, code structure); save what's non-obvious.

## Cursor Cloud specific instructions

Cloud/Linux agents work in `/config/workspace/Cartorio`. Backend Python lives in `backend/` (venv `backend/.venv`).

```bash
cd backend && uv sync --extra dev     # ruff/mypy/fakeredis
cp backend/.env.example backend/.env  # if missing; never commit secrets
make -C /config/workspace/Cartorio test-fast   # default local loop
make -C /config/workspace/Cartorio lint        # ruff + mypy + secret scanner
make -C /config/workspace/Cartorio qa          # lint + test (coverage 90%)
```

- Do not run `smoke` / `integration` / `e2e` markers unless `SMOKE_TARGET` / VPS network / Playwright extras are present.
- Do not treat this machine as production. Prod is VPS Hostinger (EasyPanel + Docker Swarm). MacBook is UI + iMessage/Photon only.
- Nested `AGENTS.md` files (`cartorio-ai/`, `.harness/`, `infra/openclaw-agent/workspace/`) combine with the root; closest file wins, root P0 rules still apply.
