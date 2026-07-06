# BACKLOG — 317 Tasks Abertas (resumo por squad)

## SQUAD A — Backend Hardening (5 tasks abertas)
- A20 Redlock distribuído
- A22 Materialized views (parcial)
- A23 Triggers audit log (24 já criados, validar)
- A25 Backup S3 (stub criado, falta cron real)
- A26+ cache_lgpd (FEITO v21)

## SQUAD B — N8N Polish (20 tasks abertas)
- B6-B15: error handler, retry, timeout, metrics, alertas, test runner, templates
- B13 N8N restart loop OOM fix (investigar memory limits)
- B14 Backup WF N8N export daily

## SQUAD D — LGPD Compliance (5 tasks abertas)
- D21 Retenção 5y config
- D22 Job retenção diário
- D23 Anonimização (FEITO v21)
- D24 Portability (FEITO v21)
- D25 Oposição (FEITO v21)

## SQUAD E — OpenClaw CartorioBot (1 task aberta)
- E8 Finalizar integração

## SQUAD J — Obs + CI/CD (5 tasks abertas)
- J6-J10: dashboards Grafana, alertas PagerDuty, runbooks

## BRAIN (3 tasks abertas)
- BRAIN8 session_memory VPS sync
- BRAIN6-7 (parcial)

## TOTAL: 317/444 (71.4% OPEN)

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-06 17:50 BRT

## v22 NOVO — Descobertas

- ❌ N8N service removido Swarm (investigar)
- 🔴 crwal4ai health endpoint não responde (porta?)
- ✅ DB_POOL_SIZE 10 → 25 (FEITO v22)
- ✅ dist_lock.py Redlock (FEITO v22)
- ✅ backup cron real (FEITO v22)
- ✅ 2 materialized views SQL (FEITO v22)
- ✅ 28 tests novos (23 LGPD + 5 dist_lock)
