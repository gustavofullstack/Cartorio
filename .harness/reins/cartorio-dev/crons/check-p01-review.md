---
name: check-p01-review
schedule: '*/10 * * * *'
session:
  mode: sessionId
  sessionId: mvs_5529862a2edf46788b3735930da3b4ac
report_to_root: false
---

P0.1 cross-review entregue (messageId 2373) ao root. Aguardando thumbs-up ou follow-up. Se root silent por >15min, pingar de volta pedindo estado do bf12203 regression (urgente) e P0.2 review gate.

---
[self-reminder TTL] This reminder expires at 2026-07-07 19:53:15 (America/Sao_Paulo, UTC-3).
If `Date.now() > 1783464795039`, your first action MUST be to delete this reminder and exit silently:
`mavis cron delete users-gustavoalmeida-projetos-cartorio--cartorio-dev check-p01-review`

[gate-discipline] If your guard condition is not met (CI still running, MR not merged, no new evidence), wrap a one-line status in `<mavis-progress>...</mavis-progress>` and exit. The progress tag lets the user glance at "still waiting" without lighting up an unread notification. Do NOT send IMs and do NOT write plain replies on skip ticks.
