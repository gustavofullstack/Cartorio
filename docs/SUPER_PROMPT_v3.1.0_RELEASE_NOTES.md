# Super-Prompt v3.1.0 — Release Notes (2026-07-16)

> **Status**: RELEASED
> **Versao**: v3.1.0 (2026-07-16 17:45 BRT)
> **Diff**: v3.0.0 (2026-06-25) → v3.1.0
> **Mudanca**: MAJOR (atualizacao de metricas + squads estado real)

---

## Mudancas MAJOR (3)

### 1. Estado dos squads atualizado para ciclo G6 (pos-F6)
- v3.0.0 reportava 60% tasks done (60/100), 952 pytest
- v3.1.0 reporta **75% tasks done** (75+/100), **3025 pytest**, 0 mypy, 0 ruff

### 2. Squads E (OpenClaw) e J (CI/CD) agora IN PROGRESS com tarefas
- v3.0.0: E 7/8 DONE, J 5/10 IN PROGRESS
- v3.1.0: E 3 tasks G6 DONE (T6/T7/T8), J 2 tasks G6 DONE (T5/T6)

### 3. Novos SUI (Só Gustavo Resolve) - 10 items
v3.0.0 tinha 5 SUI; v3.1.0 tem 10 (DNS, env vars, OpenClaw deploy, DPA MiniMax, etc).

## Mudancas MINOR (12)

### Novos artefatos (scripts/)
1. `scripts/n8n_workflow_validator.py` (393 LOC) - 9 regras gate merge N8N
2. `scripts/radar_smoke.py` (153 LOC) - CLI health radar
3. `scripts/coverage_gate.py` (225 LOC) - fail-safe >=95%
4. `scripts/openapi_snapshot.py` (163 LOC) - 122 paths baseline
5. `scripts/backup_dryrun.py` (267 LOC) - SQLite restore simulado
6. `scripts/dpa_sign_flow.py` (293 LOC) - 9 DPAs tracker
7. `scripts/n8n_error_handler_audit.py` (114 LOC) - 27 WFs fix
8. `scripts/prometheus_alert_validator.py` (180 LOC) - 15 alerts + 3 LGPD
9. `scripts/secrets_scan.py` (210 LOC) - 11 patterns
10. `scripts/lgpd_data_inventory.py` (248 LOC) - 18 PII fields
11. `scripts/n8n_idempotency_audit.py` (191 LOC)
12. `scripts/n8n_idempotency_injector.py` (208 LOC) - 19 WFs SETNX
13. `scripts/n8n_health_check.py` (209 LOC) - per WF
14. `scripts/openclaw_health_check.py` (191 LOC) - 3 checks
15. `scripts/anpd_report.py` (222 LOC) - 8 secoes LGPD
16. `scripts/coverage_badge.py` (210 LOC) - 8 badges shields.io
17. `scripts/n8n_workflow_backup.py` (230 LOC) - tar.gz + SHA256
18. `scripts/cartorio_bot_chat.py` (131 LOC) - WebSocket CLI

### Novos docs
- `docs/openclaw/E6-cartorio-bot-spec.md` - 8 tools, 5 skills, 3 MCPs
- `docs/lgpd/CONSENT_BANNER_WIDGET.html` - banner LGPD para LobeChat
- `docs/lgpd/policy/D23-site-privacy-policy-v3.md` - 7 secoes NOVAS
- `docs/ANPD_READY_2026-07-16.md` - 5627 chars / 920 palavras
- `infra/alertmanager/alertmanager.yml` - 5 receivers Telegram
- `infra/loki/{loki-config,promtail-config}.yaml` + docker-compose
- `infra/prometheus/alerts.yml` - 15 alerts (3 LGPD novos)
- `infra/prometheus/slo_rules.yml` - 12 SLO rules
- `.github/workflows/deploy.yml` - 3 stages deploy
- `.pre-commit-config.yaml` - 7 hooks

### Updates
- `Makefile` - 5 novos alvos (openapi-check/n8n-validate/coverage-gate/radar-smoke/openapi-update)
- `infra/n8n-workflows/INDEX.md` - 37 WFs catalogados
- 19 N8N WFs ganharam Redis SETNX (G6.B.T6)
- 27 N8N WFs ganharam errorWorkflow (G6.B.T3)
- 3 Prometheus alerts novos (consent/backup/circuit-breaker)

## Refs principais

- Skills: `prompt-cartorio` v3.0.0, `using-mavis-cross-session`, `up-agent-corporation`
- Lessons cross-rein: 181 → **186** (+5)
- Memory: `.harness/memory/lesson-186-g6-waves-13-14-15-shipped-2026-07-16.md`

## Compatibilidade

- Backend Python 3.11+ (matrix CI 3.12+3.13)
- OpenClaw >=0.4.x (WebSocket-only)
- N8N >=1.94.x (Redis SETNX NX option)
- Prometheus >=2.30 (multi-window burn-rate)
- Postgres 15+ (jsonb, uuid, pgvector opcional)

## Breaking changes

- LGPD conversas IA: retencao reduzida de 365d → **90d** (G6.LGPD-2026)
- N8N webhooks: requerem Redis 7+ (SETNX NX)
- Privacy Policy v3 superset v2 (v2 mantida commitada para auditoria)

## Como atualizar

```bash
# 1. Pull latest
git pull origin master

# 2. Re-sync deps backend
cd backend && uv sync --all-extras

# 3. Rodar gates
make ci

# 4. Aplicar pre-commit
uv tool install pre-commit
pre-commit install

# 5. (opcional) Deploy Grafana/Loki/AlertManager
docker compose -f infra/loki/docker-compose.loki.yml up -d
```

## Próximas versoes

- **v3.2.0** (2026-08-XX): OpenClaw E6 cartorio-bot deploy completo + 5 SUI resolvidos
- **v3.3.0** (2026-09-XX): Backend microservices extraction + K8s manifests
- **v4.0.0** (2026-Q4): SaaS multi-tenant (2o/3o tabelionato de outras cidades)

---

**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 18 (G6.J.T7)**