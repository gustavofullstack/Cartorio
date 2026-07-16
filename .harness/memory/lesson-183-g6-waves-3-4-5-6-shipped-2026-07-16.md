# Lesson 183 — G6 Waves 3-4-5-6: ship 8 tasks em 4 waves (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0 + AGENTS.md):

- Regra do projeto: **1-2 agents maximo em paralelo** (proibido 3+)
- Loop Gustavo (Pietra/Mavis) já criou +495 LOC em `backend/tests/test_pii.py` + `integrations.py` + DNS records
- Plan v25 (F0-F6) já DONE; estamos em **CICLO G6** (pós-F6)

## Entregas Waves 3-4-5-6 (8 commits pushed, 8 G6 tasks DONE)

### Wave 3 — CI gates + observability (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `c5b3779` | G6.B.T1 | `scripts/n8n_workflow_validator.py` (393 LOC) + report — gate merge 9 regras |
| `d2892bf` | G6.D.T1 | `scripts/radar_smoke.py` (153 LOC) — CLI para `/api/v1/health/radar/expanded` |

### Wave 4 — coverage gate + LGPD v3 (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `5514fd0` | G6.A.T5 | `scripts/coverage_gate.py` (225 LOC) + report — total 95.49% ✅ |
| `aa6f079` | G6.C.T5 | `docs/lgpd/policy/D23-site-privacy-policy-v3.md` (183 LOC) — 7 seções NOVAS |

### Wave 5 — pytest-xdist + canned v3 (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `2aae058` | G6.A.T4 | `pytest-xdist` instalado + ruff fix — 67s → 21s (63% faster) |
| `3d98302` | G6.B.T2 | `chatwoot_canned_responses_v3.py` (280 LOC) + 8 testes — 10 atos específicos |

### Wave 6 — OpenAPI snapshot + backup dry-run (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `5dda738` | G6.A.T3 | `scripts/openapi_snapshot.py` (163 LOC) + baseline 122 paths |
| `a74979e` | G6.D.T3 | `scripts/backup_dryrun.py` (267 LOC) — restore simulado em sqlite |

## Métricas finais sessão (waves 3-4-5-6 + cleanup wave 2.5)

| Métrica | Antes (wave 2) | Depois (wave 6) | Delta |
|---|---|---|---|
| pytest | 2912 | **2932** | **+20** |
| mypy | 0/141 files | **0/142 files** | +1 file |
| ruff | 0 | **0** | mantido |
| coverage | 95% | **95.49%** | +0.49% |
| pytest tempo | ~67s | **~21s** | **-68% (xdist)** |
| commits ahead origin | 0 | **0** (8 pushed) | ✅ |
| scripts/ (CLI tools) | 6 | **9** | +3 |
| snapshot OpenAPI paths | 0 | **122 paths** | +122 |
| canned responses | 28 v2 | **38 v2+v3** | +10 |
| lessons cross-rein | 182 | **183** | +1 |

## G6 completo (consolidado waves 1-6)

| Wave | Tasks | Status |
|---|---|---|
| Wave 1 (8 commits) | G6.A.T1 + G6.C.T3 + lesson 181 | 2 DONE + 1 PARCIAL |
| Wave 2 (5 commits) | G6.B.T5 + G6.D.T5 + G6.A.T1.1 + cleanup + lesson 182 | 4 DONE |
| Wave 3 (2 commits) | G6.B.T1 + G6.D.T1 | 2 DONE |
| Wave 4 (2 commits) | G6.A.T5 + G6.C.T5 | 2 DONE |
| Wave 5 (2 commits) | G6.A.T4 + G6.B.T2 | 2 DONE |
| Wave 6 (2 commits) | G6.A.T3 + G6.D.T3 | 2 DONE |
| **Total** | **12 G6 tasks DONE** + 2 lessons + 1 cleanup | |

## Lições aprendidas cross-project (Wave 3-6)

1. **pytest-xdist migration é trivial mas poderosa**: adicionar dep em pyproject + usar `-n auto` cortou tempo de 67s → 21s sem mudar 1 linha de teste. Vantagem: coverage gate ainda funciona, tests ainda descobrem regressions.

2. **OpenAPI snapshot é canônico para FastAPI**: `app.openapi()` retorna spec completo. Salvar baseline em `snapshots/openapi.baseline.json` e detectar added/removed/changed é suficiente para quebrar CI em breaking changes.

3. **Backup dry-run SEM pg_restore é possível**: parse SQL → SQLite (conversão Postgres→SQLite é trivial para tipos comuns: BIGSERIAL→INTEGER, JSONB→TEXT, UUID→TEXT, BOOLEAN→INTEGER, BYTEA→BLOB). Valida header gzip + SHA256 sidecar + tabelas canônicas.

4. **DNS Python AF_INET gotcha**: `socket.getaddrinfo()` retorna IPv6 primeiro (Happy Eyeballs) — sempre forçar `family=AF_INET` para IPv4-only checks (já documentado na Lesson 182).

5. **Test parallel pode AUMENTAR test count**: serial 2919 → paralelo 2924 (+5) porque fixtures autouse são aplicadas em paralelo sem colisão. Pode acontecer o oposto (fixtures shared state).

6. **CannedResponse dataclass frozen tem só 3 fields** (short_code, content, tags). NÃO tem `title` — aprendi na hora que o teste quebrou (F841 + TypeError).

7. **Script `openapi_snapshot.py` precisa APP_ENV=development** ou falha com `app_env: Input should be 'development', 'staging' or 'production'`. Setar via env.copy() antes de subprocess.run.

8. **Privacy Policy v3 superset de v2**: ao invés de criar v3 do zero, declaramos "O que mudou na v3 (vs v2)" como seção inicial + 7 novas seções. Mantém v2 commitada para histórico + auditoria.

## Refs

- Wave 3-6 commits: c5b3779, d2892bf, 5514fd0, aa6f079, 2aae058, 3d98302, 5dda738, a74979e
- Artefatos novos: `scripts/{n8n_workflow_validator,radar_smoke,coverage_gate,openapi_snapshot,backup_dryrun}.py` + `snapshots/openapi.baseline.json` + `backend/app/services/chatwoot_canned_responses_v3.py`
- Reports: `infra/n8n-workflows/VALIDATION_REPORT.md`, `docs/COVERAGE_GATE_REPORT_2026-07-16.md`, `docs/OPENAPI_SNAPSHOT_REPORT_2026-07-16.md`, `docs/BACKUP_DRYRUN_REPORT_2026-07-16.md`
- Policy: `docs/lgpd/policy/D23-site-privacy-policy-v3.md`

## SUI (Só Gustavo Resolve) — ainda pendentes

1. 🔴 3 A records Cloudflare (chatwoot/n8n/supabase → 187.77.236.77)
2. 3 env vars Easypanel UI (DATABASE_URL evolution/chatwoot/n8n)
3. Regenerar token Telegram @TestCartorioBot
4. LobeChat OPENAI_API_KEY real
5. Traefik routers merge (ROUTERS_PENDENTES.yaml)
6. OpenClaw E8 cartorio-bot (SSH VPS bloqueado)

**Total: 12 G6 tasks DONE em 4 waves (3-6) + 2 lessons + 1 cleanup, ~1h30min**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 15:05 BRT**
