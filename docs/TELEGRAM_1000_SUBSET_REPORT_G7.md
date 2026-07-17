# Telegram 1000-point subset check — G7.24.T2

**Generated**: 2026-07-17T11:57:18.809912+00:00
**Overall**: **OK** (exit `0`)
**Score**: 31/31 checks WORK

## Scope

Offline subset of `docs/GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md` + runbook:
- 7 comandos canônicos no source `telegram.py`
- Endpoints health/metrics/webhook/set-commands/debug
- Docs + scripts diagnose/setWebhook + testes pytest chave

**Does not** call Telegram API, prod webhook, or live VPS.

## By category

| Category | WORK | FAIL |
|----------|------|------|
| `artifact` | 15 | 0 |
| `command` | 7 | 0 |
| `doc_content` | 2 | 0 |
| `endpoint` | 6 | 0 |
| `test` | 1 | 0 |

## Checks

| Verdict | ID | Title | Detail |
|---------|----|-------|--------|
| **WORK** | `doc_guia_1000` | Guia validação 1000 pontos | docs/GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md |
| **WORK** | `doc_runbook_1000` | Runbook 1000 pontos (curl health/metrics) | docs/RUNBOOK_VALIDACAO_1000_PONTOS.md |
| **WORK** | `doc_guia_testes` | Guia 20 cenários E2E Telegram | docs/GUIA_TESTES_TELEGRAM.md |
| **WORK** | `doc_telegram_guide` | Telegram guide ops | docs/TELEGRAM_GUIDE.md |
| **WORK** | `doc_webhook_reregister` | Webhook re-register G7 | docs/TELEGRAM_WEBHOOK_REREGISTER_G7.md |
| **WORK** | `src_telegram_router` | Router FastAPI telegram.py | backend/app/api/v1/telegram.py |
| **WORK** | `script_diagnose` | Diagnose 1-command (score 7/7) | scripts/diagnose_vps_and_bot.sh |
| **WORK** | `script_set_webhook` | Helper setWebhook | scripts/telegram_set_webhook.py |
| **WORK** | `script_e2e_sh` | Shell E2E Telegram | scripts/test_telegram_e2e.sh |
| **WORK** | `test_commands` | Pytest comandos canônicos | backend/tests/test_telegram_commands.py |
| **WORK** | `test_webhook` | Pytest webhook | backend/tests/test_telegram_webhook.py |
| **WORK** | `test_webhook_e2e` | Pytest webhook e2e | backend/tests/test_telegram_webhook_e2e.py |
| **WORK** | `test_state_machine` | Pytest state machine | backend/tests/test_telegram_state_machine.py |
| **WORK** | `test_e2e` | Pytest telegram e2e | backend/tests/test_telegram_e2e.py |
| **WORK** | `test_send` | Pytest send helpers | backend/tests/test_telegram_send.py |
| **WORK** | `cmd:/start` | Handler /start | literal+branch OK |
| **WORK** | `cmd:/menu` | Handler /menu | literal+branch OK |
| **WORK** | `cmd:/agendar` | Handler /agendar | literal+branch OK |
| **WORK** | `cmd:/protocolo` | Handler /protocolo | literal+branch OK |
| **WORK** | `cmd:/humano` | Handler /humano | literal+branch OK |
| **WORK** | `cmd:/cancelar` | Handler /cancelar | literal+branch OK |
| **WORK** | `cmd:/lgpd` | Handler /lgpd | literal+branch OK |
| **WORK** | `ep:GET /health` | GET /health | router decorator found |
| **WORK** | `ep:GET /metrics` | GET /metrics | router decorator found |
| **WORK** | `ep:GET /webhook/info` | GET /webhook/info | router decorator found |
| **WORK** | `ep:POST /webhook` | POST /webhook | router decorator found |
| **WORK** | `ep:POST /set-commands` | POST /set-commands | router decorator found |
| **WORK** | `ep:GET /debug/last-updates` | GET /debug/last-updates | router decorator found |
| **WORK** | `guide:commands` | Guia lista 7 comandos | all 7 present |
| **WORK** | `runbook:endpoints` | Runbook cita health/metrics/webhook | ok |
| **WORK** | `test:commands_coverage` | test_telegram_commands cobre ≥6/7 comandos | 7/7 present: ['/start', '/menu', '/agendar', '/protocolo', '/humano', '/cancelar', '/lgpd'] |

## How to run

```bash
python3 scripts/telegram_1000_subset_check.py
python3 scripts/telegram_1000_subset_check.py --json
python3 scripts/telegram_1000_subset_check.py --report docs/TELEGRAM_1000_SUBSET_REPORT_G7.md
```

## Related

- `docs/GUIA_VALIDACAO_TELEGRAM_1000_PONTOS.md`
- `docs/RUNBOOK_VALIDACAO_1000_PONTOS.md`
- `scripts/diagnose_vps_and_bot.sh` (live score 7/7 — precisa rede)
- `scripts/g7_composite_gate.py` (composite local+prod HOLD)

---

Modified by Gustavo Almeida — G7 Wave 26 (G7.24.T2) auto-report
