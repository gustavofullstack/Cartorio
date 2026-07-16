# Lesson 190 — G6 Waves 24-25: 4 tasks shipped + cleanup (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0):

- Regra do projeto: 1-2 agents maximo em paralelo (proibido 3+)
- Loop Gustavo criou: 10 arquivos (lobechat agent import + integrations v3 + super status HTML + metrics v2 + 2 deletes)
- Estamos em CICLO G6 (pos-F6) — 23 waves ja entregues (wave 1-23 = 44 tasks DONE)

## Entregas Waves 24-25 (5 commits pushed, 4 G6 tasks DONE + 1 cleanup)

### Wave 24 — DPO dashboard + Prometheus SLO deploy (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `d63bacc` | (cleanup) | feat(loop-gustavo): lobechat agent import + integrations v3 + super status |
| `dfec69c` | G6.C.T10 + G6.D.T8 | docs/lgpd/dpo_dashboard.html (LGPD art. 41) + scripts/prometheus_slo_deploy.py |

### Wave 25 — N8N metrics endpoint + cartorio-bot E2E (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `2e8bf0c` | G6.B.T9 | backend/app/api/v1/n8n_metrics.py (Prometheus + summary) + 8 tests |
| `f95de9a` | G6.E.T11 | scripts/cartorio_bot_e2e_test.py (connect+auth+message+latency) |

## Métricas finais sessão (waves 24-25 + cleanup)

| Métrica | Antes (wave 23) | Depois (wave 25) | Delta |
|---|---|---|---|
| pytest | 3064 | **3091** | **+27** |
| mypy | 0/147 files | **0/150 files** | +3 files ✅ |
| ruff | 0 | **0** | mantido |
| commits ahead origin | 0 | **0** (5 pushed hoje) | ✅ |
| scripts/ (CLI) | 22 | **24** | +2 |
| N8N metrics endpoint | 0 | **1 (Prometheus+summary)** | +1 |
| CartorioBot E2E test | 0 | **1** | +1 |
| DPO dashboard frontend | 0 | **1** | +1 |
| Lessons cross-rein | 189 | **190** | +1 |

## G6 consolidado (waves 1-25)

**48 G6 tasks DONE** em 25 waves + **10 lessons (181-190)** + 10 cleanup commits = **58 total commits**

| Squad | Tasks DONE |
|---|---|
| A (backend dev) | T1.1, T2-T10 (10 tasks) |
| B (N8N) | T1-T9 (9 tasks) |
| C (LGPD) | T2, T3, T5, T6, T7, T8, T9, T10 (8 tasks) |
| D (SRE/obs) | T1, T2, T3, T4, T5, T6, T7, T8 (8 tasks) |
| E (LLM/OpenClaw) | T6, T7, T8, T9, T10, T11 (6 tasks) |
| J (CI/CD) | T5, T6, T7, T8 (4 tasks) |

## Lições aprendidas cross-project (Wave 24-25)

1. **FastAPI PlainTextResponse import lazy**: usar `__import__("fastapi.responses", fromlist=["PlainTextResponse"]).PlainTextResponse` para evitar import estatico (lazy load). Alternativa: `from fastapi.responses import PlainTextResponse` no topo.

2. **httpx mock context manager**: `with patch("httpx.Client.get")` funciona para mockar. Mock retorna `MagicMock` com `.status_code`, `.json()`, `.text`.

3. **DPO dashboard LGPD art. 41**: Encarregado de Dados (DPO) deve ter acesso a:
   - Metricas agregadas (sem PII raw)
   - Audit trail por cliente
   - Fila de retencao automatica
   - Direitos LGPD art. 18 (7 direitos)
   - Auth duplo: X-API-Key + Bearer JWT (claim dpo=True)

4. **Prometheus reload endpoint**: POST /-/reload (Prometheus 2.0+). Basic auth via `httpx.Client.post(url, auth=("admin", password))`. Health check GET /-/ready.

5. **OpenClaw WebSocket 1008 invalid request frame**: bot rejeita mensagem mal formada. E2E framework funcional, bot deploy pendente (SUI-6).

6. **Latency tracking time.monotonic()**: precisao microsegundos vs time.time() (afetado por NTP). Sempre usar monotonic para SLO.

7. **SLO burn check em CI**: --expect-timeout 10 falha build se latency > 10s. Implementa "fail fast" em pipelines.

## Refs

- Wave 24-25 commits: d63bacc, dfec69c, 2e8bf0c, f95de9a
- Artefatos novos: `docs/lgpd/dpo_dashboard.html`, `scripts/prometheus_slo_deploy.py`, `scripts/cartorio_bot_e2e_test.py`, `backend/app/api/v1/n8n_metrics.py`
- Tests: `tests/test_n8n_metrics.py` (8 tests)

## SUI (Só Gustavo Resolve) — ainda pendentes

1. 🔴 3 A records Cloudflare (chatwoot/n8n/supabase → 187.77.236.77)
2. 3 env vars Easypanel UI (DATABASE_URL evolution/chatwoot/n8n)
3. Regenerar token Telegram @TestCartorioBot
4. LobeChat OPENAI_API_KEY real
5. Traefik routers merge (ROUTERS_PENDENTES.yaml)
6. OpenClaw E6 cartorio-bot deploy (SSH VPS + openclaw.json + OPENCLAW_GATEWAY_PASSWORD)
7. DPA MiniMax assinatura (Gustavo + Mavis)
8. N8N 00-error-handler ID → substituir placeholder nos 27 WFs
9. GitHub Secrets (VPS/TELEGRAM)
10. Loki stack deploy + Grafana dashboard import
11. AWS creds para S3 backup
12. PROMETHEUS_PASSWORD para SLO reload script

**Total: 48 G6 tasks DONE em 25 waves**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 19:00 BRT**