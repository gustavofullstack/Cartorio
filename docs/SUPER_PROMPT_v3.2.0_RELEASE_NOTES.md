# Super-Prompt v3.2.0 — Release Notes (2026-07-16)

> **Status**: RELEASED
> **Versao**: v3.2.0 (2026-07-16 18:35 BRT)
> **Diff**: v3.1.0 (2026-07-16 17:45 BRT) → v3.2.0
> **Mudanca**: MAJOR (entrega cartorio-bot E6 + LGPD consent backend + SLO dashboard)

---

## Mudancas MAJOR (3)

### 1. LGPD consent backend implement end-to-end
- v3.1.0: banner widget frontend
- v3.2.0: **backend POST /api/v1/lgpd/consent** + model + schemas + 9 tests
- Audit trail completo (LGPD art. 37) com IP hash SHA256

### 2. SLO observability completa (4 SLOs + dashboard)
- v3.1.0: 12 SLO rules definidas (sem visualizacao)
- v3.2.0: **5 metrics backend** + **Grafana dashboard 7 panels** + 12 SLO rules
- Composite SLO calculado + error budget gauge

### 3. CartorioBot auth.challenge handler
- v3.1.0: chat CLI connectava mas recebia "connect.challenge" e parava
- v3.2.0: **auth handler SHA256** + dry-run + connect real
- Aguarda Gustavo configurar OPENCLAW_GATEWAY_PASSWORD (SUI-6)

## Mudancas MINOR (8)

### Novos artefatos (scripts/)
1. `scripts/openclaw_auth_handler.py` (121 LOC) - SHA256 challenge signer
2. `scripts/n8n_metrics_exporter.py` (214 LOC) - Prometheus textfile exporter
3. `scripts/cartorio_bot_chat.py` (131 LOC) - WebSocket chat REPL

### Novos backend
4. `backend/app/services/slo_metrics.py` (155 LOC) - 5 SLO metrics + helpers
5. `backend/app/api/v1/lgpd_consent.py` (88 LOC) - POST/GET consent endpoint
6. `backend/app/models/lgpd_consent.py` (35 LOC) - LGPDConsentLog + 2 indices
7. `backend/app/schemas/lgpd_consent.py` (32 LOC) - Pydantic Literal[v3] + ratio constraint

### Novos infra
8. `infra/grafana/slo_dashboard.json` (195 LOC) - 7 panels dashboard

## Métricas finais (v3.2.0)

| Métrica | v3.0.0 | v3.1.0 | v3.2.0 | Delta total |
|---|---|---|---|---|
| pytest | 952 | 3025 | **3059** | **+2107** |
| scripts CLI | 0 | 18 | **21** | +21 |
| SLO rules | 0 | 12 | **12** | +12 |
| SLO metrics | 0 | 0 | **5** | +5 |
| LGPD consent | 0 | 0 | **1 endpoint + 1 model + 1 schema** | +3 |
| Grafana panels | 0 | 0 | **7** | +7 |
| Lessons cross-rein | 0 | 186 | **188** | +188 |
| N8N WFs idempotency | 1/21 | 21/21 | **21/21** | +20 |

## Conformidade LGPD v3.2.0

- art. 7 I (consentimento) - banner widget + backend POST
- art. 8 (confirmacao clara) - 3 botoes + audit trail
- art. 9 (finalidade) - texto explicativo no banner
- art. 11 (categorias especiais) - biometricos/saude segregados
- art. 16 (retencao) - 5 anos protocol / 90d conversas IA / 6m logs
- art. 18 (7 direitos) - endpoint /lgpd/direitos
- art. 33 (DPA) - 4 signed + 5 pending (incluindo MiniMax Gustavo)
- art. 37 (registro) - LGPDConsentLog + AuditLog SHA256 chain
- art. 46 (seguranca) - IP hash + UA truncado + TLS + WAF + rate limit

## SLOs oficiais (v3.2.0)

| SLO | Target | Janela | Burn-rate alerts |
|---|---|---|---|
| API Availability | 99.5% | 30d | Fast 1h 14.4x + Slow 6h 6x |
| API Latency p95 | 500ms | 30d | Fast 1h 14.4x + Slow 6h 6x |
| N8N Workflow Success | 99% | 7d | Fast 3h 14.4x + Slow 6h 6x |
| OpenClaw Response | 5s | 30d | Fast 1h 14.4x + Slow 6h 6x |
| Composite Availability | 99%+ | 30d | (calculated) |
| Composite Latency | 95%+ | 30d | (calculated) |

## Compatibilidade v3.2.0

- Python 3.11+ (matrix CI 3.12+3.13)
- OpenClaw >=0.4.x (WebSocket-only + auth.challenge)
- N8N >=1.94.x (Redis SETNX NX)
- Prometheus >=2.30 (multi-window burn-rate)
- Grafana >=9.0 (schema v30 + threshold mode absolute)
- Postgres 15+ (jsonb, uuid, pgvector opcional)

## Breaking changes v3.2.0

- LGPD conversas IA: retencao 365d → **90d** (mantido v3.1.0)
- N8N webhooks: requerem Redis 7+ (SETNX NX)
- Privacy Policy v3 superset v2
- APP_ENV: agora aceita apenas `development`/`staging`/`production` (NAO "testing")

## Próximas versoes (roadmap)

- **v3.3.0** (2026-08-XX): OpenClaw cartorio-bot deploy + SUI 1-5 resolvidos
- **v3.4.0** (2026-08-XX): Backend microservices extraction + K8s manifests
- **v4.0.0** (2026-Q4): SaaS multi-tenant (2o/3o tabelionato de outras cidades)

## Como atualizar de v3.1.0 para v3.2.0

```bash
git pull origin master
cd backend && uv sync --all-extras
make ci  # roda todos gates
docker compose -f infra/loki/docker-compose.loki.yml up -d
# Importar dashboard Grafana: infra/grafana/slo_dashboard.json
```

---

**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 22 (G6.J.T8)**