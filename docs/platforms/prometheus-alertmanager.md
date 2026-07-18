# Prometheus AlertManager — Cartório 2º Notas

Pipeline oficial de alertas Prometheus → Telegram (LGPD-safe).

Documentação canônica: [`../ALERTMANAGER_G8.md`](../ALERTMANAGER_G8.md).

## Quick reference

| Item | Valor |
|------|-------|
| Config canônica | `infra/observability/alertmanager.yml` |
| Script bridge | `scripts/alert_to_telegram.py` |
| Endpoint receiver | `POST /api/v1/webhook/alertmanager` |
| Default port (AlertManager) | 9093 (interno) |
| Telegram Bot API | `https://api.telegram.org/bot{token}/sendMessage` |

## LGPD gates aplicados

- `extra="forbid"` em todos os schemas Pydantic → rejeita payload não documentado.
- Scrubber PII (3 camadas) em summary/description/instance antes de enviar Telegram.
- Auto-purge em memória: payload não é persistido em DB, nem em log raw.

Modified by Gustavo Almeida — G8.15.T2.
