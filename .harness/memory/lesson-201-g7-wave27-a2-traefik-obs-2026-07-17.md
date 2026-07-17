---
name: g7-wave27-a2-traefik-obs
description: Wave 27 cartorio-sre A2 — Traefik access-log backend debug, edge rate-limit optional HOLD, AlertManager Telegram live-fire docs, Loki/Promtail sample LogQL.
type: project
date: 2026-07-17
agent: cartorio-sre
wave: G7-W27
tags: [g7, sre, traefik, alertmanager, loki, promtail, rate-limit, observability]
---

# Lesson 201 — G7 Wave 27 A2 Traefik + Observability (2026-07-17)

## TL;DR

Shipped **agent-side** docs/scripts for four tasks (no prod mutate, no secrets):

| Task | Deliverable |
|------|-------------|
| G7.13.T2 | `docs/TRAEFIK_ACCESS_LOG_DEBUG_G7.md` + `scripts/traefik_access_log_parse.py` |
| G7.13.T4 | `infra/traefik/middleware-rate-limit-optional.yaml` + `docs/TRAEFIK_EDGE_RATE_LIMIT_G7.md` (HOLD deploy) |
| G7.18.T3 | `docs/ALERTMANAGER_TELEGRAM_G7.md` (HOLD secrets / live fire) |
| G7.18.T4 | `docs/LOKI_PROMTAIL_SAMPLE_QUERY_G7.md` + `scripts/loki_sample_query.sh` |

## Key lessons encoded

1. **Backend name first on 502** — `http-cartorio_<svc>-0@file` in Traefik access log means Traefik routed; fix upstream (Lesson 176), do not force Traefik first.
2. **Edge rate-limit ≠ app rate-limit** — Traefik is in-memory enforced; app Redis layers are fail-open. Edge is optional depth-in-defense; webhooks need high burst or no edge.
3. **AlertManager Telegram** already modeled with `bot_token_file` / `chat_id_file` — live fire via `POST /api/v2/alerts` + amtool routes test; tokens HOLD-GUSTAVO.
4. **Two Loki stacks in repo** (`infra/logging/` vs `infra/loki/`) — confirm which is live before trusting label names; Promtail batchwait can be 1m (slow “ingest?” false alarm).
5. **PII-safe LogQL** — prefer level/correlation_id; rare `pii-audit` query only for pipeline health, not public dashboards.

## Offline validation

```bash
python3 scripts/traefik_access_log_parse.py --demo
bash scripts/loki_sample_query.sh --list
bash scripts/loki_sample_query.sh --dry-run --query api-502
```

## HOLD-GUSTAVO

- Apply Traefik rate-limit middleware in prod
- Materialize AlertManager Telegram secrets + real live fire
- Confirm Loki/Promtail stack actually running on VPS

## Cross-refs

- Lesson 176 (502 recovery / backend name)
- `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`
- `infra/alertmanager/alertmanager.yml`
- `infra/firewall/traefik-middleware/cartorio-middlewares.yml` (FASE 2 HOLD sibling)

**Modified by Gustavo Almeida — G7 Wave 27 cartorio-sre**
