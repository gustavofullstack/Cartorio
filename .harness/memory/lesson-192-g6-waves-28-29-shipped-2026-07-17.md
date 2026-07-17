# Lesson 192 — G6 Waves 28-29: 5 tasks shipped + cleanup (2026-07-17)
Type: project + reference

## Contexto

Gustavo pediu CONTINUE com 4 agents/squad em loop. Reality check (skill `prompt-cartorio` v3.0.0):

- Regra do projeto: 1-2 agents maximo em paralelo (proibido 3+)
- Loop Gustavo criou: 5 arquivos (lobechat monitors + super status v3.2 + memory)
- Estamos em CICLO G6 (pos-F6) — 27 waves ja entregues (wave 1-27 = 52 tasks DONE)

## Entregas Waves 28-29 (5 commits pushed, 5 G6 tasks DONE + 1 cleanup)

### Wave 28 — Fix N8N tests + materialized views + retention (1 commit, 3 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `819164d` | (cleanup) | feat(loop-gustavo): lobechat monitors + super status v3.2 |
| `ef7b2c1` | G6.A.T12 + G6.C.T12 | backend/app/services/materialized_views.py + scripts/lgpd_retention_job.py + fix tests N8N |

### Wave 29 — Composite SLO recording + cartorio-bot deploy (1 commit, 2 tasks)
| Commit | Task | Entrega |
|---|---|---|
| `b977814` | G6.D.T10 + G6.E.T12 | infra/prometheus/composite_slo_recording_rules.yml + scripts/cartorio_bot_deploy.py |

## Métricas finais sessão (waves 28-29 + cleanup)

| Métrica | Antes (wave 27) | Depois (wave 29) | Delta |
|---|---|---|---|
| pytest | 3110 (2 fail) | **3128** (0 fail) | **+18** |
| mypy | 0/154 files | **0/155 files** | +1 files ✅ |
| ruff | 0 | **0** | mantido |
| commits ahead origin | 0 | **0** (5 pushed hoje) | ✅ |
| scripts/ (CLI) | 25 | **27** | +2 |
| Materialized views SQL | 0 | **4** | +4 |
| Recording rules Prometheus | 0 | **10** | +10 |
| Lessons cross-rein | 191 | **192** | +1 |

## G6 consolidado (waves 1-29)

**57 G6 tasks DONE** em 29 waves + **12 lessons (181-192)** + 12 cleanup commits = **69 total commits**

| Squad | Tasks DONE |
|---|---|
| A (backend dev) | T1.1, T2-T12 (12 tasks) |
| B (N8N) | T1-T10 (10 tasks) |
| C (LGPD) | T2, T3, T5, T6, T7, T8, T9, T10, T11, T12 (10 tasks) |
| D (SRE/obs) | T1, T2, T3, T4, T5, T6, T7, T8, T9, T10 (10 tasks) |
| E (LLM/OpenClaw) | T6, T7, T8, T9, T10, T11, T12 (7 tasks) |
| J (CI/CD) | T5, T6, T7, T8 (4 tasks) |

## Lições aprendidas cross-project (Wave 28-29)

1. **httpx mock context manager**: patch `app.api.v1.n8n_metrics.httpx.Client` (NAO `httpx.Client.get`). Stack:
   ```python
   with patch("app.api.v1.n8n_metrics.httpx.Client") as mock_cls:
       mock_client = mock_cls.return_value.__enter__.return_value
       mock_client.get.return_value.status_code = 200
       mock_client.get.return_value.json.return_value = {...}
   ```

2. **N8N API timestamp formato**: ISO 8601 com timezone UTC (ex: `2026-07-17T11:30:00+00:00`). Para tests usar `datetime.now(timezone.utc).isoformat()`.

3. **Materialized views vs tabelas**: views materializadas sao cacheadas (refresh periodico). Otimas para queries LGPD DPO (count, join) que sao pesadas. CONCURRENTLY permite queries em paralelo durante refresh.

4. **LGPD retenção por entity**:
   - conversa_ia_log: 90d (IA conversas tem baixa retencao)
   - audit_log: 6m (LGPD art. 37 - hash chain preservado)
   - session_temp: 24h (sessoes efemeras)
   - LGPDConsentLog: 5 anos (manter - prova de consentimento)

5. **Composite SLO media geometrica ponderada (Google SRE cap. 5)**:
   - Composite = prod(SLI_i^w_i)
   - Pesos indicam criticidade (API 40%, Latency 30%, N8N 20%, OpenClaw 10%)
   - Mais sensivel a violacoes do que media aritmetica

6. **Burn-rate fast/slow windows**:
   - Fast (1h, 14.4x): budget exhausto em 2 dias. CRITICAL.
   - Slow (6h, 6x): budget exhausto em 5 dias. HIGH.
   - Multi-window burn-rate eh Google SRE best practice.

7. **Cartorio-bot deploy via SSH**: 4 steps (copy, write config, restart, health check). SSH key obrigatorio (skip dry-run check).

8. **Cartorio-bot openclaw.json**: agent com 6 tools (api/n8n/supabase/redis/chatwoot/evolution), 4 skills (certidoes/protocolos/atendimento/lgpd_consentimento), 3 mcp_servers (cartorio-mcp-cabuloso/sre/lgpd). Auth: challenge SHA256 (lesson 188).

## Refs

- Wave 28-29 commits: 819164d, ef7b2c1, b977814
- Artefatos novos: `backend/app/services/materialized_views.py`, `scripts/lgpd_retention_job.py`, `infra/prometheus/composite_slo_recording_rules.yml`, `scripts/cartorio_bot_deploy.py`

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
15. VPS_SSH_KEY para cartorio-bot deploy

**Total: 57 G6 tasks DONE em 29 waves**
**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-17 12:00 BRT**