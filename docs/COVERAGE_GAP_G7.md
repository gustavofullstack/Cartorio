# Coverage Gap Report (G7.01.T2)

**Generated**: 2026-07-16T18:44:29.642832+00:00
**Threshold**: < 90.0%
**Modules below threshold**: 12

| % | Miss | Stmts | Module |
|---|------|-------|--------|
| 50.5 | 106 | 214 | `app/main.py` |
| 51.4 | 105 | 216 | `app/services/metrics.py` |
| 57.5 | 17 | 40 | `app/services/dead_mans_switch.py` |
| 57.7 | 137 | 324 | `app/api/v1/integrations.py` |
| 64.6 | 29 | 82 | `app/services/sentry.py` |
| 64.9 | 20 | 57 | `app/services/evolution_ingest.py` |
| 66.7 | 2 | 6 | `app/schemas/__init__.py` |
| 67.4 | 63 | 193 | `app/api/v1/health_radar_expanded.py` |
| 67.6 | 394 | 1216 | `app/api/v1/router.py` |
| 78.3 | 31 | 143 | `app/services/rate_limit_by_key.py` |
| 81.1 | 18 | 95 | `app/services/brain_sync.py` |
| 87.9 | 13 | 107 | `app/api/v1/lgpd_dpo_dashboard.py` |

## Prioridade de testes

1. `dead_mans_switch.py` / `evolution_ingest.py` — smaller, high leverage
2. `health_radar_expanded.py` — prod observability
3. `rate_limit_by_key.py` — security path
4. `main.py` / `router.py` — large; prefer route-level tests already exist

**Modified by Gustavo Almeida — G7 Wave 22**
