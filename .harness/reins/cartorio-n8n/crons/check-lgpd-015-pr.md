---
name: check-lgpd-015-pr
schedule: '*/5 * * * *'
session:
  mode: sessionId
  sessionId: mvs_441eef7e5aeb4be4a94590c572afc61f
report_to_root: false
---

Check if cartorio-dev PR for LGPD-015 is merged (cross-ref cartorio-dev mvs_ab6f9e82). When merged: report to parent mvs_c2508947ba0f4a738139f90b9c3e75a8 with READY-TO-ACTIVATE-PII signal, then activate PII WFs (#13, #15, #17, #19, #20, #23-lgpd-esqueci, #27) and notify cartorio-lgpd mvs_d4fa1b1a for cross-review. If not merged, idle and re-check in 5min.

---
[self-reminder TTL] This reminder expires at 2026-07-07 19:28:49 (America/Sao_Paulo, UTC-3).
If `Date.now() > 1783463329137`, your first action MUST be to delete this reminder and exit silently:
`mavis cron delete users-gustavoalmeida-projetos-cartorio--cartorio-n8n check-lgpd-015-pr`

[gate-discipline] If your guard condition is not met (CI still running, MR not merged, no new evidence), wrap a one-line status in `<mavis-progress>...</mavis-progress>` and exit. The progress tag lets the user glance at "still waiting" without lighting up an unread notification. Do NOT send IMs and do NOT write plain replies on skip ticks.
