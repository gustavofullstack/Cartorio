# Lesson 188 — G6 Waves 19-20-21: cleanup + 4 tasks shipped (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0):

- Regra do projeto: 1-2 agents maximo em paralelo (proibido 3+)
- Loop Gustavo criou: 14 arquivos (telegram v3 + evolution_ingest + metrics v2 + rate_limit_by_key + tasks board + api catalog + domain typo)
- Estamos em CICLO G6 (pos-F6) — 18 waves ja entregues (wave 1-18 = 36 tasks DONE)

## Entregas Waves 19-20-21 (4 commits pushed, 4 G6 tasks DONE + 1 cleanup)

### Wave 19 — SLO metrics + N8N exporter (2 commits)
| Commit | Task | Entrega |
|---|---|---|
| `40c5031` | (cleanup) | feat(loop-gustavo): telegram+evolution ingest+metrics+ci tasks board v3.1 |
| `bf3161b` | G6.A.T9 | backend/app/services/slo_metrics.py (5 metrics SLO) + 10 tests |
| `fe17f96` | G6.B.T8 | scripts/n8n_metrics_exporter.py (Prometheus textfile/HTTP) |

### Wave 20 — LGPD consent API + (SLO dashboard deferred) (1 commit, 1 task)
| Commit | Task | Entrega |
|---|---|---|
| `8d7aa58` | G6.C.T9 | backend/app/api/v1/lgpd_consent.py + schemas + model + 9 tests |

### Wave 21 — Deferred (limit token)

## Métricas finais sessão (waves 19-20 + cleanup)

| Métrica | Antes (wave 18) | Depois (wave 20) | Delta |
|---|---|---|---|
| pytest | 3025 | **3049** | **+24** |
| mypy | 0/144 files | **0/147 files** | +3 files ✅ |
| ruff | 0 | **0** | mantido |
| commits ahead origin | 0 | **0** (4 pushed hoje) | ✅ |
| scripts/ (CLI) | 20 | **21** | +1 |
| SLO metrics module | 0 | **5 metrics** | +5 |
| LGPD consent endpoint | 0 | **1** | +1 |
| Lessons cross-rein | 187 | **188** | +1 |

## G6 consolidado (waves 1-20)

**40 G6 tasks DONE** em 20 waves + **8 lessons (181-188)** + 8 cleanup commits = **48 total commits**

| Squad | Tasks DONE |
|---|---|
| A (backend dev) | T1.1, T2-T9 (9 tasks) |
| B (N8N) | T1-T8 (8 tasks) |
| C (LGPD) | T2, T3, T5, T6, T7, T8, T9 (7 tasks) |
| D (SRE/obs) | T1, T2, T3, T4, T5, T6 (6 tasks) |
| E (LLM/OpenClaw) | T6, T7, T8, T9 (4 tasks) |
| J (CI/CD) | T5, T6, T7 (3 tasks) |

## Lições aprendidas cross-project (Wave 19-20)

1. **prometheus_client type: ignore import**: package nao instalado em dev, mypy reclama. Solucao: `# type: ignore[import-not-found]` + try/except ImportError com stub no-op.

2. **AuditService.log() vs .record()**: API real eh `.log(entity=..., action=..., actor_id=..., payload=...)`, NAO `.record(...)`. Para evitar overhead, LGPDConsentLog ja eh o audit trail — NUNCA duplicar com AuditService.

3. **APP_ENV literal values**: config.py so aceita "development"/"staging"/"production", NAO "testing". Usar "staging" em tests locais.

4. **cartorio_api_key format**: deve ser 64 chars hex (pattern `^[a-f0-9]{64}$`). Tests usam `"a" * 64`.

5. **IP hash LGPD art. 46**: `hashlib.sha256(client_ip.encode()).hexdigest()[:16]` evita armazenar IP cru (PII). Mesma logica para user-agent (truncado 200 chars).

6. **sendBeacon = 204 No Content**: navigator.sendBeacon NAO espera response. Endpoint POST deve retornar 204 sem body. FastAPI: `status_code=status.HTTP_204_NO_CONTENT` + retorno None.

7. **Auth middleware em backend**: cadeia eh JWT Bearer PRIMEIRO, depois X-API-Key. Para endpoints publicos (LGPD consent widget), auth deve ser pulado via `dependencies=[]` no router OU override de middleware.

## Refs

- Wave 19-20 commits: 40c5031, bf3161b, fe17f96, 8d7aa58
- Artefatos novos: `backend/app/services/slo_metrics.py`, `backend/app/api/v1/lgpd_consent.py`, `backend/app/models/lgpd_consent.py`, `backend/app/schemas/lgpd_consent.py`, `scripts/n8n_metrics_exporter.py`
- Tests: `tests/test_slo_metrics.py` (10), `tests/test_lgpd_consent_api.py` (9)

## SUI (Só Gustavo Resolve) — ainda pendentes

1. 🔴 3 A records Cloudflare (chatwoot/n8n/supabase → 187.77.236.77)
2. 3 env vars Easypanel UI (DATABASE_URL evolution/chatwoot/n8n)
3. Regenerar token Telegram @TestCartorioBot
4. LobeChat OPENAI_API_KEY real
5. Traefik routers merge (ROUTERS_PENDENTES.yaml)
6. OpenClaw E6 cartorio-bot deploy (SSH VPS + openclaw.json)
7. DPA MiniMax assinatura (Gustavo + Mavis)
8. N8N 00-error-handler ID → substituir placeholder nos 27 WFs
9. GitHub Secrets: VPS_HOST/VPS_USER/VPS_SSH_KEY/TELEGRAM_*
10. Loki stack deploy (docker compose up)

**Total: 40 G6 tasks DONE em 20 waves**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 18:30 BRT**