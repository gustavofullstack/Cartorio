# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Backend API for **2º Serviço Notarial de Uberlândia** — a Brazilian notary public office. Multi-channel chatbot platform (WhatsApp / Telegram / Web) with **LGPD-by-design** compliance, immutable audit chain (SHA256 + HMAC), 3-layer PII scrubbing, and mandatory Human-in-the-Loop for all legal acts.

Production: `https://api.2notasudi.com.br` (FastAPI + 6 sibling services).

## Quick commands

All commands run from the repo root and delegate to `backend/Makefile` via the root `Makefile`:

```bash
make install           # cd backend && uv sync
make dev               # uvicorn app.main:app --reload --port 8000
make test              # full pytest with coverage gate ≥90%
make test-fast         # pytest without coverage (faster, dev loop)
make test-one TEST=test_audit.py::test_x  # single test
make lint              # ruff check + mypy app/ (gates: 0 errors)
make format            # ruff format + ruff check --fix
make qa                # lint + test (full quality gate, same as CI)
make clean             # remove __pycache__, .mypy_cache, .ruff_cache, .coverage
```

Single test without make:
```bash
cd backend && uv run pytest -v --no-cov tests/test_audit.py::test_x
```

## Stack & runtime

- **Python 3.11+**, managed with `uv` (no pip/poetry). Lockfile: `backend/uv.lock`
- **FastAPI 0.115** + **SQLAlchemy 2.0** (typed style: `Mapped[...]`, `mapped_column`) + **Pydantic v2**
- **PostgreSQL 16** (Supabase self-hosted) — schema via Alembic in `backend/alembic/`
- **Redis 8** (idempotency, rate limit, cache, locks)
- **Observability**: OpenTelemetry traces + Prometheus metrics + Sentry (with PII before_send scrubber)
- **MCP server** (`backend/mcp_server.py`) mounted at `/mcp` — protocol 2025-03-26, 7 tools

## High-level architecture

```
Evolution API ──► OpenClaw Gateway ──► N8N workflows ──► Cartório API ──► Supabase (PG)
  (WhatsApp)       (LLM router)        (orchestration)    (rules + audit)    + Redis
                                                                              │
                              Chatwoot ◄──── handoff ───── API ◄──── Telegram/Channel
```

**Multi-agent context** (`.harness/`): this is an **agents.md-compliant** project. Operational rules, security details, multi-agent delegation live in `.harness/AGENTS.md` (NOT in this file). The root `AGENTS.md` is the compact spec-compliant subset.

### Backend layout (`backend/app/`)

- **`api/`** — HTTP routers, versioned under `/api/v1/` (current) and `/api/v2/` (alpha, sunset 2027-12-31). Telegram webhook, LGPD rights, auth, BRAIN tasks all live here.
- **`models/`** — SQLAlchemy 2.0 typed models: `cliente`, `conversa`, `protocolo`, `documento`, `emolumento`, `agendamento`, `atendimento`, plus `audit_log` (tamper-evident), `webhook_event`, `outbox_message` (DLQ).
- **`services/`** — Business logic. **Critical ones**:
  - `audit.py` / `audit_create.py` / `audit_query.py` / `audit_context.py` — immutable hash chain (any change requires `cartorio-lgpd` review)
  - `pii.py` — 3-layer PII scrubbing (input / pre-LLM / output). See before touching any LLM call.
  - `emolumento.py` — MG 2026 fee table calculation (state-regulated)
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
4. Routers: `api_router`, `ws_router` (WebSocket atendimentos), `telegram_router`, `lgpd_router`, `lgpd_v2_router` (JWT+DPO), `brain_router`, `auth_login_router`, `api_v2_router`.

## Critical rules (cannot be skipped)

These come from `AGENTS.md` and `.harness/AGENTS.md`. Violating them is a P0 incident:

1. **HITL mandatory**: protocolo always born as `DRAFT`. The escrevente (notary clerk) validates before processing. The bot must never decide alone on isenções, urgency, legal validation, or certidão/escritura emission.
2. **PII never leaves raw**: CPF/RG/phone/email masked BEFORE any external LLM call or storage. 3 layers: Pydantic field validators → Sentry `before_send` → log `MaskingFilter`. See `backend/app/services/pii.py` before any new integration.
3. **Audit log is append-only** with SHA256 chain + HMAC. Any retro edit invalidates the chain. Tests must fail if implementation regresses.
4. **Secrets never committed**: `.env` is gitignored. Template is `.env.example`.
5. **No literal API key fallbacks**: `scripts/check_no_literal_keys.py` blocks `lin_api_*`, `sk-*`, `rnd_*`, `AQ.*`, `gAAAAA`, `ghp_*`, `xox*`, `AKIA*`, `AIza*` patterns. Opt-out: `# noqa: ALLOW_KEY_FALLBACK`.
6. **Conventional Commits** only: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `perf:` — commit message must end with `Modified by Gustavo Almeida`.
7. **Always branch from `master`**, never push direct. One PR review required; changes in `audit` or `pii` require `cartorio-lgpd` sign-off.

## Multi-agent delegation

Three reins under the Harness orquestrador (`.harness/agent.md`):

- **`cartorio-dev`** — backend FastAPI / SQLAlchemy / audit / PII
- **`cartorio-n8n`** — N8N workflows / Evolution API / OpenClaw / multi-canal / deploy (JSON exports in `infra/n8n-workflows/`)
- **`cartorio-lgpd`** — LGPD / RIPD / retenção / privacy policy / erasure rights

When delegating a cross-cutting task, declare upfront which rein owns review.

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
- **MCP servers exposed** via `~/.mavis/mcp/clients/cartorio-mcp-config.json`: `n8n-mcp` (50 tools), `supabase-mcp` (30), `cartorio-api` (7), `easypanel-mcp` (57), `openclaw-mcp` (20).
- **Real-time protocol exchange**: WebSocket at `/ws/atendimentos`.
- **Backup**: `backend/scripts/` has backup/restore scripts; `infra/backup/` has cron jobs.
- **Monitoring**: Prometheus metrics at `/metrics`; Sentry for errors.

## Notable integration gotchas (from AGENTS.md)

- **Evolution API webhooks**: support BOTH legacy root-level (`payload.get("message")`) AND nested (`payload.get("data", {}).get("message")`) — both formats appear in the wild.
- **Chatwoot + Evolution**: set `CHATWOOT_ENABLED=true` in Evolution env; create API inbox in Chatwoot; configure Evolution with the generated `inboxId`.
- **Docker Swarm port reuse**: when restarting Swarm services in `host` publish mode, scale to `0` first then back to `1` to avoid port conflict errors.
- **Telegram `parse_mode=HTML`**: LLM output containing `<think>`/`<reasoning>` tags breaks `parse_mode=HTML` and causes silent 502. Wrap LLM response before sending, or use Markdown parse mode. (See `backend/app/api/v1/telegram.py` for the retry-with-backoff implemented 2026-07-01.)
- **N8N `/mcp-server/http`**: needs correct auth header — returns 401 if token/header is broken.
- **Chatwoot 4.x + AI Agents SDK**: requires `pgvector` extension in the Postgres database or Chatwoot crashloops on startup.

## Documentation map

- Root: `README.md` (production status), `AGENTS.md` (compact agent contract), `PROMPT.MD` / `PROMPT.json` (project briefings).
- `docs/ARCHITECTURE.md` — C4 diagrams + ADRs
- `docs/API.md` — 50+ endpoints with curl
- `docs/DB.md` — 20+ tables + ER
- `docs/DEPLOYMENT.md`, `docs/RUNBOOK_VPS.md` — ops
- `docs/LGPD.md`, `docs/CONTRIBUTING.md`
- `docs/platforms/` — vendor-specific runbooks (N8N, Chatwoot, Evolution, Supabase, Redis, Jules)
- `docs/adr/README.md` — 24+ ADRs
- `.harness/memory/MEMORY.md` — cross-session lessons (loaded each session)
- `.harness/STANDARDS.md` — code standards

## Session memory convention

Cross-session lessons live at `/Users/gustavoalmeida/.claude/projects/-Users-gustavoalmeida-projetos-Cartorio/memory/MEMORY.md`. Patterns:

- New lesson? Write a single `.md` file with YAML frontmatter (`name`, `description`, `type`) + add one-line entry to MEMORY.md index.
- Type values: `user`, `feedback`, `project`, `reference`. Use `[[name]]` links liberally.
- Update existing files rather than creating duplicates; delete memories that turned out wrong.
- Don't save what the repo already records (git history, code structure); save what's non-obvious.
