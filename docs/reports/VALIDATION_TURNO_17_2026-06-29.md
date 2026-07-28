# Validation Report — Turno 17 (2026-06-29 ~11:42 BRT)

**Agent:** Braço Direito (Pietra / ZCode-M3)
**Trigger:** Master PROMPT v4.1.0 (revalidation 2026-06-29)
**Branch:** master @ commit `6d9ab69`
**Session goal:** "100% funcionando, integrado, testado, validado, documentado"

---

## TL;DR

Backend quality gates **VERDES**: pytest 1600 passed / coverage 90.28% / mypy 0 / ruff 0.
Infraestrutura **VERDE**: 8/8 serviços online (database, redis, n8n, openclaw,
evolution, chatwoot, supabase, opencode_go) — confirmado via
`/api/v1/health/integracoes` com `offline_count: 0` e via curl/SSH direto à VPS.

Cobertura subiu de 89.52% → 90.28% (gate `>=90%` agora passa, era -0.48pp
abaixo). 25 testes novos para `openclaw.py` (41% → 100%) e `fallback.py` (61% →
100%).

---

## Quality gates — PASSED

| Gate | Comando | Resultado | Threshold |
|---|---|---|---|
| pytest | `./scripts/run_tests_clean.sh --tb=short` | **1600 passed, 15 skipped** | all_passed |
| coverage | (idem, com cov-report) | **90.28%** | >= 90% |
| mypy | `.venv/bin/mypy app/` | **0 errors** (106 source files) | 0 |
| ruff | `.venv/bin/ruff check app/ tests/` | **All checks passed!** | 0 |
| git gates | `git push origin master` | **pushed 6d9ab69** | sem untracked |

**Antes do commit 6d9ab69:**
- pytest: 1547 passed
- coverage: **89.52%** (gate falhava por 0.48pp)
- mypy: 0 errors
- ruff: 0 errors

---

## Serviços — 8/8 ONLINE

Validado em 2026-06-29 11:42 BRT via:

```bash
curl -sS -m 8 -H "X-API-Key: $CARTORIO_API_KEY" \
  https://api.2notasudi.com.br/api/v1/health/integracoes
```

Resposta (verbatim):

```json
{
  "status": "green",
  "offline_count": 0,
  "integracoes": {
    "database":   { "status": "online", "latency_ms": 1,   "status_code": 200 },
    "redis":      { "status": "online", "latency_ms": 2,   "status_code": 200 },
    "n8n":        { "status": "online", "latency_ms": 6,   "status_code": 200 },
    "openclaw":   { "status": "online", "latency_ms": 6,   "status_code": 200 },
    "evolution":  { "status": "online", "latency_ms": 220, "status_code": 200 },
    "chatwoot":   { "status": "online", "latency_ms": 20,  "status_code": 200 },
    "supabase":   { "status": "online", "latency_ms": 16,  "status_code": 401 },
    "opencode_go":{ "status": "online", "latency_ms": 399, "status_code": 200 }
  }
}
```

| # | Serviço | URL | Status | Latência |
|---|---|---|---|---|
| 1 | API FastAPI | api.2notasudi.com.br | ✅ 200 ok v0.6.0 | 67ms |
| 2 | N8N | flow.2notasudi.com.br | ✅ 200 ok | 69ms |
| 3 | Supabase | supbase.2notasudi.com.br | ✅ 401 (auth required) | 65ms |
| 4 | Evolution API | whatsapp.2notasudi.com.br | ✅ 200 v2.3.7 | 329ms |
| 5 | Chatwoot | chat.2notasudi.com.br | ✅ 404 (endpoint ok, requer API key) | 74ms |
| 6 | Redis | 100.99.172.84:1001 | ✅ PONG | 1ms |
| 7 | OpenClaw | agent.2notasudi.com.br | ✅ 200 live | 73ms |
| 8 | Easypanel | easypanel.2notasudi.com.br | ✅ 200 | 71ms |

**VPS containers**: 27 running (`docker ps | wc -l = 27`)
- 2× cartorio_api (rolling deploy, gpe8cei9zt19... healthy, co11rqmh9n6... starting)
- cartorio_openclaw-gateway (2d healthy)
- cartorio_n8n + n8n-runner
- cartorio_evolution-api
- cartorio_chatwoot + sidekiq
- cartorio_redis + redis_dbgate + rediscommander
- 11× supabase-* (db, functions, kong, studio, storage, meta, analytics, supavisor, realtime, auth, vector, imgproxy)
- easypanel-traefik, easypanel, rest, vps_whoami

**N8N workflows**: 35 total, 34 active (matches PROMPT.json claim)

---

## Mudanças neste turno (commit 6d9ab69)

```
test(coverage): add openclaw + fallback unit tests to clear 90% gate
 3 files changed, 588 insertions(+)

 backend/scripts/run_tests_clean.sh  |  62 ++++++
 backend/tests/test_fallback.py      | 159 ++++++++++++++++
 backend/tests/test_openclaw_unit.py | 367 ++++++++++++++++++++++++++++++++++++
```

### `backend/scripts/run_tests_clean.sh` (novo)

Wrapper que faz `env -u` em 12 vars antes do pytest. Necessário porque
`tests/conftest.py` usa `os.environ.setdefault` que **NÃO sobrescreve** valor
já presente no shell. Em dev local o shell tem `AUDIT_HMAC_KEY=`,
`DATABASE_URL=`, `CARTORIO_API_KEY=`, `CHATWOOT_*`, `TELEGRAM_*` exportados
(vazamento de `.env` de prod via `~/.zshenv`/etc). Em CI limpo não precisa.

### `backend/tests/test_openclaw_unit.py` (novo, 17 testes)

Cobre `app/integrations/openclaw.py:chat()` e `chat_with_settings()`:

- base_url vazia / whitespace → CONFIG
- messages vazio → CONFIG
- consent não granted → LGPD_BLOCKED (LGPD art. 7 I)
- happy path 200 com JSON válido → ChatResponse com PII scrub
- HTTP 401 → HTTP_4XX
- HTTP 503 → HTTP_5XX
- httpx.TimeoutException → TIMEOUT
- httpx.ConnectError → NETWORK
- Response não-JSON → PARSE
- JSON sem `choices` → PARSE (estrutura inesperada)
- Output com PII → scrub + `output_pii_redacted_count > 0`
- Com db → registra audit log (`openclaw.chat`)
- Output PII + db → registra audit 2x (chat + `llm.output_scrubbed`)
- Audit log falha → swallowed (LGPD não-bloqueante)
- Rate limit + session_id + redis_url → chama `_check_rate_limit`
- `chat_with_settings` wrapper → usa settings

### `backend/tests/test_fallback.py` (estendido, +8 testes)

Cobre `app/integrations/fallback.py:chat_with_fallback()`:

- openclaw como primary → direto, sem fallback
- primary_provider desconhecido → CONFIG
- fallback_provider desconhecido → CONFIG no fallback
- opencode como fallback (caminho alternativo)
- LGPD_BLOCKED no primary → não faz fallback
- CONFIG no primary → não faz fallback
- Erro inesperado no fallback (RuntimeError) → NETWORK ChatError
- Sucesso no fallback + db → audit log `llm.fallback_triggered` com
  payload completo (primary_provider, fallback_provider, primary_error_kind,
  primary_error_msg, model_used)

---

## Lições aprendidas (registradas em `.brain/memory/2026-06-29.md`)

- **L186/187**: `conftest.py` usa `os.environ.setdefault` que **NÃO sobrescreve**
  valores já presentes no shell. Em dev local, vazamento de `.env` de prod via
  `~/.zshenv` faz com que `AUDIT_HMAC_KEY=` (vazio), `DATABASE_URL=postgres://...`,
  `TELEGRAM_WEBHOOK_SECRET=...`, etc. cheguem ao pytest antes do setdefault.
  Solução: `scripts/run_tests_clean.sh` com `env -u` em 12 vars. CI limpo
  não precisa.

- **L188**: Coverage gap era concentrada em 4 arquivos com httpx/serviços externos
  mockados incorretamente — `fallback.py` (61%), `openclaw.py` (41%),
  `integrations.py` (66%), `telegram.py` (68%). Resolvido com 25 testes novos
  cobrindo happy path + 4xx/5xx/timeout/network/parse + output PII scrubbing +
  audit log success/failure. Após: openclaw 100%, fallback 100%.

- **L189**: PROMPT.json v4.1.0 reporta 1543 testes / 90.18% cobertura (claim).
  Verificação real mostrou 89.52% — claim stale de 1 sprint atrás. Após este
  commit: 1600 / 90.28% real (gain de +57 testes, +0.76pp coverage).

---

## Compliance checklist

- [x] **mypy 0 errors** (gate)
- [x] **ruff 0 errors** (gate)
- [x] **pytest all_passed** (gate, 1600 passed)
- [x] **coverage >= 90%** (gate, 90.28%)
- [x] **commit Conventional Commits** (`test(coverage): add ...`)
- [x] **mensagem termina com "Modified by Gustavo Almeida"** (sob Gustavo Almeida via `git -c user.name`)
- [x] **branch master** (sem worktree, sem deletar)
- [x] **push após commit** (6d9ab69 → origin/master)
- [x] **8/8 serviços online** (verificado via `/api/v1/health/integracoes`)
- [x] **.env não commitado** (gitignored)
- [x] **memória atualizada** (`.brain/memory/2026-06-29.md` Timeline + Lições)
- [x] **workflow obrigatório completo**: analisar → testar → corrigir → melhorar
  → otimizar → documentar → comentar → salvar na memória

---

## Pendente (não bloqueante, próximas sprints)

Do PROMPT.json v4.1.0 `blockers_remaining`:

- **SUI1** DNS `chatwoot.2notasudi.com.br` A record (canônico `chat.` funciona)
- **SUI2** WhatsApp production QR scan (Gustavo no Evolution Manager)
- **SUI3** Chatwoot API key configuration
- **SUI4** OpenClaw LLM key (depende LGPD)
- **SUI6** Decisão DNS `supbase` typo → `supabase` canonical
- **P0-B1** Chatwoot restart loop memory limit 1G (ADR-015)
- **P0-B2** OpenClaw context overflow threshold (ADR-016)

Squad progress (PROMPT.json `squads_status`):

| Squad | Total | Done | % | Status |
|---|---|---|---|---|
| S0 Supabase Foundation | 10 | 10 | 100% | DONE |
| A API+DB Hardening | 13 | 1 | 8% | 12 pending |
| B N8N Polish | 8 | 4 | 50% | 4 pending |
| C Docs | 25 | 5 | 20% | 20 pending |
| D LGPD Compliance | 25 | 17 | 68% | 8 pending |
| E OpenClaw CartorioBot | 8 | 5 | 63% | 3 pending |
| H Chatwoot CRM | 8 | 8 | 100% | DONE |
| J Obs+CICD | 10 | 5 | 50% | 5 pending |
| BRAIN | 8 | 2 | 25% | 6 pending |
| DOCS Download | 5 | 5 | 100% | DONE |

---

## Modified by Gustavo Almeida