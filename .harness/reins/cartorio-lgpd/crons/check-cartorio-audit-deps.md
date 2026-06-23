---
name: check-cartorio-audit-deps
schedule: 0 */4 * * *
session:
  mode: sessionId
  sessionId: mvs_f7a29511daec40b7995718801be1a2c5
report_to_root: false
---

cartorio-lgpd: re-checar se WF-NOVO-01/02/03 foram criados em infra/n8n-workflows/. Rodar: ls /Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/ | grep -i 'novo\|WF-NOVO'. Se sim, abrir docs/lgpd/AUDITORIA_BLOCKERS.md e auditar cada workflow (checklist ja preparado). Reportar ao parent mvs_46cbec32e75e4c1da56118564d200a68.

---
[self-reminder TTL] This reminder expires at 2026-07-07 13:56:59 (America/Sao_Paulo, UTC-3).
If `Date.now() > 1783443419668`, your first action MUST be to delete this reminder and exit silently:
`mavis cron delete users-gustavoalmeida-projetos-cartorio--cartorio-lgpd check-cartorio-audit-deps`

[gate-discipline] If your guard condition is not met (CI still running, MR not merged, no new evidence), wrap a one-line status in `<mavis-progress>...</mavis-progress>` and exit. The progress tag lets the user glance at "still waiting" without lighting up an unread notification. Do NOT send IMs and do NOT write plain replies on skip ticks.
