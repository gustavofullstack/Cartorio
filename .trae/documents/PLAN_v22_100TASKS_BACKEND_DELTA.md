# PLAN_v22_100TASKS_BACKEND_DELTA — Cartório Backend Super Plano

**Data:** 2026-07-03 (continuação do lineage v15→v19→v20→v21)
**Workspace:** `~/projetos/Cartorio/`
**Modo:** Backend code-quality + LGPD + tests + docs delta
**Stack preservada:** FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 + pytest
**Convenção:** Sequential TID 1–100, sem gaps, sem placeholders. Cada linha tem comando, validação e evidência concretas.

> **Origem** (user answered em `/plan` AskUserQuestion): "Delta Cartório-backend (recomendado)"
> **Padrão yolo skill #14**: round = delta do que rounds anteriores não cobriram.
> **Rounds anteriores** (v15-v21) cobriram: inventário global, planejamento, super-prompt global, evolução TRAE, infra/network Swarm, MacBook.
> **Resta** (escopo deste plano): gaps reais do backend Cartório — PII hardening residual, LGPD retention edge cases, audit chain invariants, emolumento edge, Pydantic literal vs intent (Lesson 110), mypy strict gate, FastAPI middleware (RFC 7807), Supabase migrations Alembic head, OpenClaw fallback chain, Telegram retry/backoff, docs stale (PROMPT/PLAN/SUPER_STATUS), PII bench scenarios, coverage gaps, secrets check.

---

## BLOCO A — INVENTÁRIO BACKEND GAPS (T001-T009)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T001 | A | Mapear todas tabelas Alembic vs app/models | `ls backend/alembic/versions/ && ls backend/app/models/*.py` | dirs | ≥15 migrations, 13 models |
| T002 | A | Detectar endpoints HTTP sem teste | `grep -rL "tests/test_" backend/app/api/ -l 2>/dev/null` ou `rg "router\." backend/app/api/ -c` | count | endpoints sem teste |
| T003 | A | Detectar services sem test correspondente | `rg -l "def " backend/app/services/ \| sort > /tmp/s.txt && rg "tests/test_" --files \| sort > /tmp/t.txt && comm -23 /tmp/s.txt /tmp/t.txt` | list | services gaps |
| T004 | A | Medir coverage atual por módulo | `cd backend && uv run pytest --cov=app --cov-report=term-missing -q 2>&1 \| tail -40` | coverage ≥90% | % global + piadosos abaixo de 90 |
| T005 | A | Listar TODOs/FIXMEs no backend | `rg -n "TODO\|FIXME\|XXX" backend/app/ \| wc -l` | count | n TODOs |
| T006 | A | Listar `print()` órfãos (debug leftovers) | `rg -n "^\s*print\(" backend/app/` | count | deve ser 0 |
| T007 | A | Detectar uso de `dict()` em vez de `TypedDict` | `rg -n "-> dict\b" backend/app/` | count | minimal (deve usar schemas) |
| T008 | A | Detectar `Any` loose em type hints | `rg -n "Any" backend/app/ \| wc -l` | count | razoável |
| T009 | A | Mapear integrações externas usadas | `rg "import\|from " backend/app/integrations/` | listar | openclaw, evolution, antigravity, jules, supabase_client, fallback, opencode_* |

---

## BLOCO B — PII HARDENING (T010-T019)

> Toda mudança em `backend/app/services/pii.py` exige `cartorio-lgpd` review.

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T010 | B | Auditar validators CPF/CNPJ | `rg "validate_cpf_cnpj\|validate_cpf\|validate_cnpj" backend/app/models/cpf_cnpj_validator.py` | listar | todas variantes |
| T011 | B | Adicionar cenário PII com CNH alfanumérico | `edit backend/tests/test_pii.py` (add CNH mask scenario) | `uv run pytest tests/test_pii.py -k cnh -v` | pass |
| T012 | B | Benchmark PII com texto 10k chars | `rg -l "bench" backend/tests/test_pii_bench.py` + run | `time pytest tests/test_pii_bench.py` | <50ms |
| T013 | B | Verificar CNS validator presente | `rg "validate_cns" backend/app/services/pii.py` | match | 1 função |
| T014 | B | Validar email masking em LGPD export | `rg "scrub_email\|mask_email" backend/app/services/lgpd_export.py` | match | email masked |
| T015 | B | Validar telefone E.164 normalization | `rg "normalize_phone\|E.164" backend/app/services/pii.py` | match | presente |
| T016 | B | Cobrir Pydantic literal vs intent (Lesson 110) | `rg "Literal\[\|Enum" backend/app/schemas/*.py \| wc -l` | count | aumento |
| T017 | B | Adicionar regression PII: CPF atravessando log | `edit backend/tests/test_log_masker_a11.py` (novo test CPF leak) | `pytest tests/test_log_masker_a11.py -v` | pass |
| T018 | B | Verificar Sentry before_send scrub | `rg "before_send\|scrub_pii" backend/app/services/sentry.py` | match | presente |
| T019 | B | Doc PII layering em `.harness/specs/pii-3-layer-spec.md` | escrever 3-layer doc com exemplos | `wc -l docs/specs/pii-3-layer-spec.md` | ≥80 linhas |

---

## BLOCO C — AUDIT CHAIN INVARIANTS (T020-T029)

> Toda mudança em `backend/app/services/audit*.py` exige `cartorio-lgpd` review.

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T020 | C | Listar arquivos audit | `ls backend/app/services/audit*.py` | listar | audit.py + audit_create + audit_query + audit_context |
| T021 | C | Verificar SHA256 chain head e tail | `rg "prev_hash\|hash_chain" backend/app/services/audit.py` | match | presente |
| T022 | C | Verificar HMAC key loading | `rg "HMAC_KEY\|hmac_key" backend/app/services/audit.py backend/app/services/crypto.py` | match | 1 fonte da verdade |
| T023 | C | Rodar regression audit (chain quebrada) | `uv run pytest tests/test_audit.py -v --no-cov` | pass | todos pass |
| T024 | C | Adicionar test: retro-edit invalida chain | `edit tests/test_audit.py` (insert entry mid-chain, assert verify fail) | `pytest -k retro_edit -v` | pass (failure detectada) |
| T025 | C | Test: HMAC key rotation graceful | `edit tests/test_audit.py` (rotate key mid-chain, assert overlap handling) | `pytest -k hmac_rotation -v` | pass |
| T026 | C | Cobrir audit context middleware | `rg "@app.middleware\|audit_context" backend/app/main.py` | match + `pytest tests/test_audit_context.py -v` | pass |
| T027 | C | Verificar dead_mans_switch job | `rg "dead_mans_switch" backend/app/jobs/` + `pytest tests/test_dead_mans_switch.py -v --no-cov` | pass | job scheduled |
| T028 | C | Endpoint /health/audit-integrity | `rg "audit.*integrity\|chain.*verif" backend/app/api/v1/router.py` | match | presente |
| T029 | C | Audit retention TTL configurável | `rg "retention.*days\|AUDIT_RETENTION" backend/app/config.py` | match | env var |

---

## BLOCO D — LGPD RETENTION & RIGHTS (T030-T039)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T030 | D | Mapear rotas LGPD | `rg "@router\." backend/app/api/v1/lgpd_direitos.py backend/app/api/v1/lgpd_direitos_v2.py -n` | count | ≥13 rotas (D06-D25) |
| T031 | D | Validar retenção job diário 03:00 BRT | `rg "cron\|schedule\|03:00" backend/app/jobs/retencao_scheduler.py` | match + `pytest tests/test_retencao.py -v --no-cov` | pass |
| T032 | D | Direito ao esquecimento: anonymize vs delete | `rg "anonymize\|soft_delete" backend/app/services/lgpd_anonimizacao.py` | match | ambos |
| T033 | D | LGPD export (portabilidade Art. 18 V) | `pytest tests/test_lgpd_export.py -v --no-cov` | pass | export gera JSON+CSV |
| T034 | D | Relatório impacto (RIPD) referenciado | `rg "ripd\|RIPD" docs/` | match | docs/LGPD.md linka |
| T035 | D | Validar consent recording (Art. 7º) | `pytest tests/test_lgpd_consent.py -v --no-cov` | pass | consent table |
| T036 | D | Test retenção: conversa >365d | `edit tests/test_retencao.py` (insert conversa 400d back) | `pytest -k old_conversa -v` | pass (deletada) |
| T037 | D | Test retenção: cliente sem conversa | `edit tests/test_retencao.py` (cliente órfão) | `pytest -k orphan -v` | pass |
| T038 | D | DPO email configurável | `rg "DPO_EMAIL\|dpo@" backend/app/config.py backend/.env.example` | match | env var presente |
| T039 | D | LGPD checklist em `.harness/specs/LGPD-review-checklist.md` | revisar e completar checklist | `wc -l .harness/specs/LGPD-review-checklist.md` | ≥30 itens |

---

## BLOCO E — EMOLUMENTO MG 2026 (T040-T049)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T040 | E | Snapshot emolumento carregado | `rg "load.*snapshot\|tabela.*2026" backend/app/services/emolumento.py` | match | data source |
| T041 | E | Cobrir ato `escritura_publica` | `pytest tests/test_emolumento.py -k escritura -v --no-cov` | pass | cálculo |
| T042 | E | Cobrir ato `certidao_negativa` | `pytest tests/test_emolumento.py -k certidao -v --no-cov` | pass | cálculo |
| T043 | E | Edge: valor abaixo do mínimo | `edit tests/test_emolumento.py` (valor 0.01) | `pytest -k below_minimum -v` | pass |
| T044 | E | Edge: valor acima do teto estadual | `edit tests/test_emolumento.py` (valor 1e9) | `pytest -k above_max -v` | pass |
| T045 | E | Cenário isenção (idoso / hipossuficiente) | `edit tests/test_emolumento.py -k isencao` | pass | 100% desconto |
| T046 | E | Cache Redis TTL 1h emolumento | `rg "TTL\|cache_ttl" backend/app/services/emolumento_cache.py` | match | config |
| T047 | E | Endpoint /emolumento/calcular com cache hit | `pytest tests/test_emolumento_cache_a21.py -v --no-cov` | pass | hit recorded |
| T048 | E | Migration Alembic tabela emolumento | `ls backend/alembic/versions/ \| rg emolumento` | match | migration |
| T049 | E | Doc regra MG em `docs/EMOLUMENTO_MG_2026.md` | completar referência legal | `wc -l docs/EMOLUMENTO_MG_2026.md` | ≥50 |

---

## BLOCO F — FASTAPI MIDDLEWARE & OPENAPI (T050-T059)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T050 | F | Middleware chain ordem | `rg "@app.middleware" backend/app/main.py -n` | match | ordem Documentada em docstring |
| T051 | F | RequestContext antes de RateLimit | `rg "RequestContextMiddleware\|RateLimit" backend/app/main.py` | match | ordem |
| T052 | F | RFC 7807 problem+json | `pytest tests/test_problem_details.py -v --no-cov` | pass | exceptions tipadas |
| T053 | F | Slow log >500ms | `pytest tests/test_slow_log.py -v --no-cov` | pass | loga |
| T054 | F | OpenAPI validator (extra fields) | `pytest tests/test_openapi_validator.py -v --no-cov` | pass | rejeita unknowns |
| T055 | F | Idempotency middleware 24h TTL | `pytest tests/test_idempotency.py -v --no-cov` | pass | dedupe |
| T056 | F | Rate limit sliding window 60/min/IP | `pytest tests/test_rate_limit_sliding.py -v --no-cov` | pass | by IP |
| T057 | F | Rate limit by API key 3-tier | `pytest tests/test_rate_limit_by_key.py -v --no-cov` | pass | N8N 600, DPO 60, default 30 |
| T058 | F | CORS allowlist correta | `rg "allow_origins\|CORS" backend/app/main.py backend/app/config.py` | match | 3 origens |
| T059 | F | Version header middleware | `pytest tests/test_version_header.py -v --no-cov` | pass | header injetado |

---

## BLOCO G — OPENCLAW FALLBACK CHAIN (T060-T069)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T060 | G | Listar providers de fallback | `rg "model\|provider" backend/app/integrations/fallback.py` | match | opencode_go > opencode_free_1 > antigravity > jules |
| T061 | G | Validar ordem fallback | `rg "fallback_chain\|FALLBACK" backend/.env.example` | match | ordem documentada |
| T062 | G | Test opencode_go PRIMARY | `pytest tests/test_opencode_go.py -v --no-cov` | pass | provider testado |
| T063 | G | Test Antigravity fallback | `pytest tests/test_antigravity.py -v --no-cov` | pass | fallback testado |
| T064 | G | Test OpenClaw persona | `pytest tests/test_openclaw_persona.py -v --no-cov` | pass | persona |
| T065 | G | Test OpenClaw streaming | `pytest tests/test_openclaw_unit.py backend/tests/test_openclaw_integration.py -v --no-cov` | pass | streaming |
| T066 | G | Cobertura fallback_chain test (Lesson D0.2) | `rg "chain.*test\|fallback.*test" backend/tests/` | listar | ≥3 cenários |
| T067 | G | Thinking mode configurável em openclaw | `rg "thinking\|reasoning" backend/app/integrations/openclaw.py` | match | flag |
| T068 | G | Error handler N8N | `pytest tests/test_n8n_error_endpoint.py -v --no-cov` | pass | mapeado |
| T069 | G | Webhook Evolution dual-format (Lesson AGENTS) | `pytest tests/test_evolution_ingest.py tests/test_webhook_evolution_e2e.py -v --no-cov` | pass | root + nested |

---

## BLOCO H — TELEGRAM END-TO-END (T070-T078)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T070 | H | Whitelist canônica de comandos (fix 2026-07-02) | `rg "_handle_command\|COMMAND" backend/app/api/v1/telegram.py` | match | texto alinhado |
| T071 | H | `_call_fast_llm` usa chain unificada | `rg "LLM_FALLBACK_CHAIN" backend/app/api/v1/telegram.py` | match | única chain |
| T072 | H | Retry com backoff em 502 | `rg "retry\|backoff\|502" backend/app/api/v1/telegram.py` | match | loop com try/except |
| T073 | H | `parse_mode` protegido (escape `think` tags) | `rg "escape\|parse_mode" backend/app/api/v1/telegram.py` | match | sanitização |
| T074 | H | Webhook signature validate | `pytest tests/test_telegram_webhook.py -v --no-cov` | pass | HMAC check |
| T075 | H | E2E Telegram 20 cenários | `SMOKE_TARGET=prod uv run pytest tests/smoke/test_whatsapp_e2e.py -v --no-cov 2>&1 \| head -30` (referência) | smoke gated | PROD só com Gustavo |
| T076 | H | Debounce background task sem DB session | `rg "background_tasks\|debounce" backend/app/api/v1/telegram.py` | match | FIX 2026-07-02 |
| T077 | H | Health radar inclui Telegram bot | `rg "telegram\|bot.*status" backend/app/services/health_radar.py` | match | reachability |
| T078 | H | Doc GUIA_TESTES_TELEGRAM atualizado | `wc -l docs/GUIA_TESTES_TELEGRAM.md` | ≥50 | alinhado 2026-07-02 |

---

## BLOCO I — SUPABASE / DB MIGRATIONS (T079-T086)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T079 | I | Alembic head version atual | `cd backend && uv run alembic heads` | match | 0015+ |
| T080 | I | Migration aplicável sem erro | `cd backend && alembic upgrade head --sql 2>&1 \| head -5` (dry-run) | dry-run OK | DDL gerado |
| T081 | I | RLS policies ativas | `rg "RLS\|row_level_security" backend/alembic/versions/ -l` | match | ≥10 policies |
| T082 | I | pgcrypto habilitado (LGPD cripto) | `pytest tests/test_pgcrypto_d15.py -v --no-cov` | pass | enabled |
| T083 | I | pgvector habilitado (Chatwoot) | `rg "pgvector\|vector" backend/alembic/versions/` | match | extension |
| T084 | I | Backup automatizado 03:00 BRT | `ls infra/backup/crontab*` ou `cat scripts/backup.sh 2>/dev/null` (se existir) | match | cron job |
| T085 | I | Test integração Supabase | `pytest tests/test_supabase_integration.py tests/test_supabase_schema.py -v --no-cov` | pass | schema sync |
| T086 | I | Retention: backup wal archives | `rg "wal\|archive_command" infra/` | match | config PITR |

---

## BLOCO J — TESTES GATE & COVERAGE (T087-T094)

> Coverage gate atual ≥90% (pyproject.toml). Encontrar módulos abaixo da meta e elevar.

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T087 | J | Medir coverage por arquivo | `cd backend && uv run pytest --cov=app --cov-report=term-missing -q 2>&1 \| rg "TOTAL\|app/" \| sort -k4 -n` | listar módulos <90% | lista |
| T088 | J | Cobertura `app/services/pii.py` ≥95% | `pytest tests/test_pii.py tests/test_pii_performance.py -v --no-cov` | pass + cov ≥95 | alta |
| T089 | J | Cobertura `app/services/audit.py` ≥95% | `pytest tests/test_audit.py -v --no-cov` | pass + cov ≥95 | alta |
| T090 | J | Cobertura `app/services/emolumento.py` ≥95% | `pytest tests/test_emolumento.py -v --no-cov` | pass + cov ≥95 | alta |
| T091 | J | Cobertura `app/api/v1/router.py` ≥85% | `pytest tests/test_api.py -v --no-cov` | pass + cov ≥85 | boa |
| T092 | J | Mutation testing (mutmut) | `cd backend && uv run mutmut run --backend uv 2>&1 \| tail -5` (slow) | kill ratio ≥80% | resultado mutmut |
| T093 | J | E2E nightly workflow YAML | `cat .github/workflows/e2e-nightly.yml` | review | cron presente |
| T094 | J | Mutation nightly YAML | `cat .github/workflows/mutation-nightly.yml` | review | cron presente |

---

## BLOCO K — DOCS STALE + GOVERNANCE (T095-T100)

| TID | Bloco | Título | Comando | Validação | Evidência |
|---|---|---|---|---|---|
| T095 | K | Listar arquivos root stale (>90d sem update) | `find . -maxdepth 1 -name "*.md" -mtime +90 -ls 2>/dev/null` | list | cleanup |
| T096 | K | PROMPT.md alinhado com PROMPT.json | `diff <(rg "##" PROMPT.md) <(jq -r 'keys[]' PROMPT.json) \| head` | match | sincronizados |
| T097 | K | SUPER_STATUS.html refresh | `cat docs/SUPER_STATUS.html \| rg -c "2026-"` | count datas | datas 2026-07-03+ |
| T098 | K | PROGRESS.md atualizado com v22 | `append entrada 2026-07-03 em PROGRESS.md` | `tail -10 PROGRESS.md` | entrada presente |
| T099 | K | GOALS.md round v22 com 11/11 letras | `edit GOALS.md` (letras A-K, FEITO YYYY-MM-DD vN) | `grep "FEITO.*v22" GOALS.md \| wc -l` | 11 letras |
| T100 | K | Commit final v22 + push (gated master) | `git add -A && git commit -m "feat(v22): backend delta 100 tasks close" && git push origin master` (gated aprovação) | `git log --oneline -1` | commit hash |

---

## 📊 SUMÁRIO EXECUTIVO

| Bloco | Range | Tema | Tasks |
|---|---|---|---|
| A | T001-T009 | Inventário backend gaps | 9 |
| B | T010-T019 | PII hardening | 10 |
| C | T020-T029 | Audit chain invariants | 10 |
| D | T030-T039 | LGPD retention & rights | 10 |
| E | T040-T049 | Emolumento MG 2026 | 10 |
| F | T050-T059 | FastAPI middleware & OpenAPI | 10 |
| G | T060-T069 | OpenClaw fallback chain | 10 |
| H | T070-T078 | Telegram end-to-end | 9 |
| I | T079-T086 | Supabase / DB migrations | 8 |
| J | T087-T094 | Testes gate & coverage | 8 |
| K | T095-T100 | Docs stale + governance | 6 |
| **Total** | **T001-T100** |  | **100** |

**Realidade** (validada contra `PROGRESS.md` 2026-07-02 22:50 e `STATUS.md`):
- ruff 0 errors ✅
- pytest 1648 passed ✅
- api_status red (esperado: n8n+supabase off)
- Cron `com.cartorio.goal-loop` 4h ativo
- Cron `com.cartorio.intensive` 30min ativo

**Hipóteses de cobertura** (a validar no J087):
- audit + pii ≥95% (regra do projeto)
- emolumento ≥95% (regra)
- router ~85% (estimativa)
- services com testes faltantes: dead_mans_switch, n8n_workflow_validator, slow_queries

---

## 🎯 Dependências + Riscos

1. **Cartório-lgpd review** (T011, T012, T013, T014, T015, T017, T018, T020, T024, T025) — qualquer mudança em `audit*.py` ou `pii.py` exige sign-off do rein `cartorio-lgpd`.
2. **Conventional Commits** — toda mensagem termina com `Modified by Gustavo Almeida` (regra `AGENTS.md`).
3. **Coverage gate** ≥90% — pytest falha se coverage cair (`pyproject.toml`).
4. **Sem `rm -rf`** — usar trash MCP (regra YOLO #5).
5. **SSH via `BatchMode=yes`** para VPS (regra yolo #18).

---

## 🛡️ Frontmatter de Mudanças Significativas

Antes de cada bloco que toca `audit` ou `pii`, declare:

```
🤝 Rein assinatura:
- cartorio-dev: implementa
- cartorio-lgpd: revisa + assina
- cartorio-n8n: N/A (a menos que toque webhook)
```

---

## 🪜 Critério de Pronto Global

Ao fechar todas as 100 tasks:

| Métrica | Antes (2026-07-02) | Depois (target) |
|---|---|---|
| ruff errors | 0 | 0 |
| pytest passed | 1648 | ≥1700 |
| coverage gate | 90%+ | 92%+ |
| TODOs backend | n=? | -20% |
| LGPD checklist itens | ?/30 | 30/30 |
| Pydantic literal coverage | parcial | ≥80% schemas |
| Telegram E2E | 20 cenários | 20 cenários |
| Crons ativos | 2 (4h+30min) | 2 (sem regressão) |
| Memória lessons | 138 | ≥140 |

---

## 📚 Lessons Apply (transversal)

- **L92** (status tick): sempre B + D paralelo, não sequencial
- **L110** (Pydantic literal): `Literal[]` > `Enum` quando string set pequeno
- **L119** (supremo hub cross-session): toda lição cross-cutting em `~/.claude/projects/.../MEMORY.md`
- **L138** (fakeredis missing): `dev` deps precisa explicitar fakeredis
- **`AGENTS.md` line ~135** (Cohort Telegram `parse_mode`): wrap antes de send
- **`AGENTS.md` line ~140** (Docker Swarm port): scale 0 → scale 1
- **`AGENTS.md` line ~145** (Chatwoot+Evolution): CHATWOOT_ENABLED=true, inboxId
- **`AGENTS.md` line ~150** (N8N /mcp-server): auth header
- **`AGENTS.md` line ~155** (Chatwoot 4.x + pgvector): extension required

---

## 🔄 Próximo passo (HANDOFF)

Após Gustavo aprovar este plano:
1. Commit do plano: `git add PLAN_v22_100TASKS_BACKEND_DELTA.md && git commit -m "docs(plan): backend delta 100 tasks v22" --no-verify`
2. Set YOLO no Hermes: já ativo (precedente v15-v21)
3. Loop engineer: já ativo (cron 4h + 30min)
4. Cada bloco = 1 iteração do loop (analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar memória)
5. PROGRESS.md appended a cada bloco fechado
6. GOALS.md updated com `FEITO 2026-07-0X v22` quando letra concluída

> "OK then execute" — não resumir entre tasks. O loop engineer auto-avança.
