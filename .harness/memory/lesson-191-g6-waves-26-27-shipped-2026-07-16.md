# Lesson 191 — G6 Waves 26-27: 4 tasks shipped + cleanup (2026-07-16)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0):

- Regra do projeto: 1-2 agents maximo em paralelo (proibido 3+)
- Loop Gustavo criou: 6 arquivos (router v3.2 + schemas init + workflows INDEX + memory)
- Estamos em CICLO G6 (pos-F6) — 25 waves ja entregues (wave 1-25 = 48 tasks DONE)

## Entregas Waves 26-27 (5 commits pushed, 4 G6 tasks DONE + 1 cleanup)

### Wave 26 — Dead man's switch + N8N retry policy (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `6203255` | (cleanup) | feat(loop-gustavo): router v3.2 + schemas init + N8N workflows index |
| `1e66e7b` | G6.A.T11 + G6.B.T10 | backend/app/api/v1/dead_mans_switch.py + scripts/n8n_retry_policy.py |

### Wave 27 — DSAR + SLO alertmanager routes (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `fc1697b` | G6.C.T11 + G6.D.T9 | backend/app/api/v1/lgpd_dsar.py + infra/alertmanager/slo_alerts_routes.yml |

## Métricas finais sessão (waves 26-27 + cleanup)

| Métrica | Antes (wave 25) | Depois (wave 27) | Delta |
|---|---|---|---|
| pytest | 3091 | **3110** | **+19** |
| mypy | 0/150 files | **0/154 files** | +4 files ✅ |
| ruff | 0 | **0** | mantido |
| commits ahead origin | 0 | **0** (5 pushed hoje) | ✅ |
| scripts/ (CLI) | 24 | **25** | +1 |
| Endpoints admin | 0 | **3 (DMS status/heartbeat/history)** | +3 |
| DSAR endpoint | 0 | **1 (POST + GET status)** | +1 |
| AlertManager routes | 0 | **11 SLO routes** | +11 |
| Lessons cross-rein | 190 | **191** | +1 |

## G6 consolidado (waves 1-27)

**52 G6 tasks DONE** em 27 waves + **11 lessons (181-191)** + 11 cleanup commits = **63 total commits**

| Squad | Tasks DONE |
|---|---|
| A (backend dev) | T1.1, T2-T11 (11 tasks) |
| B (N8N) | T1-T10 (10 tasks) |
| C (LGPD) | T2, T3, T5, T6, T7, T8, T9, T10, T11 (9 tasks) |
| D (SRE/obs) | T1, T2, T3, T4, T5, T6, T7, T8, T9 (9 tasks) |
| E (LLM/OpenClaw) | T6, T7, T8, T9, T10, T11 (6 tasks) |
| J (CI/CD) | T5, T6, T7, T8 (4 tasks) |

## Lições aprendidas cross-project (Wave 26-27)

1. **AuditService.log() signature real**: `AuditService.log(db, *, actor_id, action, resource, payload, actor_type="user", ip=None, user_agent=None, request_id=None, canal=None)`. NAO `entity/entity_id`. AuditLog columns: `resource` (NAO `entity`), `hash` (NAO `entry_hash`).

2. **LGPD DSAR workflow 15 dias**: LGPD art. 18 §5o garante prazo maximo 15 dias para resposta. Hash SHA256[:16] de PII (cpf/email/phone) garante LGPD-by-design sem armazenar PII cru.

3. **LGPD 7 direitos (art. 18)**: confirmacao, acesso, correcao, anonimizacao, portabilidade, eliminacao, compartilhamento. Enum literal garante validacao.

4. **AlertManager routes Google SRE**: 11 routes priorizadas por severidade (critical fast burn 1h, high slow burn 6h, medium composite drift). Receivers: pagerduty + 7 telegram + 1 email.

5. **SLO burn-rate alerts**: fast burn (1h, 14.4x rate) = budget exhausto em 2 dias. Slow burn (6h, 6x rate) = budget exhausto em 5 dias. Composite SLO = media ponderada de 4 SLIs.

6. **YAML vs Python docstring**: arquivos `.yml` devem ser YAML puro (sem `"""..."""` Python docstring no topo). Renomear backup antes de reescrever.

7. **N8N retry policy via API**: GET workflow + merge settings + PUT. Preserva outros campos (errorWorkflow, timezone, etc). maxTries=3 + wait=5000ms = SRE default.

8. **Dead man's switch LGPD art. 37**: detecta se API parou de escrever no audit log. Threshold 15min default. Endpoint admin permite inspecao + heartbeat manual.

## Refs

- Wave 26-27 commits: 6203255, 1e66e7b, fc1697b
- Artefatos novos: `backend/app/api/v1/dead_mans_switch.py`, `scripts/n8n_retry_policy.py`, `backend/app/api/v1/lgpd_dsar.py`, `infra/alertmanager/slo_alerts_routes.yml`
- Schemas: `backend/app/schemas/dead_mans_switch.py`, `backend/app/schemas/lgpd_dsar.py`
- Tests: `tests/test_dead_mans_switch_api.py` (8 tests)

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
13. ALERTMANAGER_WEBHOOK_URL para SLO routes
14. N8N_API_KEY para retry policy apply

**Total: 52 G6 tasks DONE em 27 waves**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 19:20 BRT**