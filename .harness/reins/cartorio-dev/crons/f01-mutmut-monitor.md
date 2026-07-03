---
name: f01-mutmut-monitor
schedule: '*/3 * * * *'
session:
  mode: sessionId
  sessionId: mvs_0c10591ae9374031bfc7fe9ef1243b4a
report_to_root: false
---

Check mutmut baseline progress: ps aux | grep mutmut | grep -v grep | wc -1. If 0, finalize F01 baseline, write F01-mutation-testing.md, commit local. If still running, take snapshot and wait.

---
[self-reminder TTL] This reminder expires at 2026-07-16 21:15:45 (America/Sao_Paulo, UTC-3).
If `Date.now() > 1784247345957`, your first action MUST be to delete this reminder and exit silently:
`mavis cron delete users-gustavoalmeida-projetos-cartorio--cartorio-dev f01-mutmut-monitor`

[gate-discipline] If your guard condition is not met (CI still running, MR not merged, no new evidence), wrap a one-line status in `<mavis-progress>...</mavis-progress>` and exit. The progress tag lets the user glance at "still waiting" without lighting up an unread notification. Do NOT send IMs and do NOT write plain replies on skip ticks.
