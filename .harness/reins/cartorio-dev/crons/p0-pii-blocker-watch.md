---
name: p0-pii-blocker-watch
schedule: '*/5 * * * *'
session:
  mode: sessionId
  sessionId: mvs_de8510d1115e4b6fb731f9406295f038
report_to_root: false
---

Checar status do P0 interno: pytest quebrado em backend/tests/test_pii.py (5 tests failing, coverage 88.98% gate fail). Branch master tem modified tests/test_pii.py + modified backend/app/services/pii.py (NAO TOCAR). Aguardando decisao da Pietra: (A) rollback cartorio-lgpd pii.py, (B) cartorio-lgpd ajusta tests em paralelo, (C) ignoro gate, (D) outra. NAO fazer commit Phase 1 ate coverage >=90%.

---
[self-reminder TTL] This reminder expires at 2026-07-07 14:38:05 (America/Sao_Paulo, UTC-3).
If `Date.now() > 1783445885228`, your first action MUST be to delete this reminder and exit silently:
`mavis cron delete users-gustavoalmeida-projetos-cartorio--cartorio-dev p0-pii-blocker-watch`

[gate-discipline] If your guard condition is not met (CI still running, MR not merged, no new evidence), wrap a one-line status in `<mavis-progress>...</mavis-progress>` and exit. The progress tag lets the user glance at "still waiting" without lighting up an unread notification. Do NOT send IMs and do NOT write plain replies on skip ticks.
