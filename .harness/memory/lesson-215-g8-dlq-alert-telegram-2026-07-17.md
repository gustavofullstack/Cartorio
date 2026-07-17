# Lesson 215 — G8.08.T3 DLQ alert Telegram (LGPD-safe) (2026-07-17)

Type: project + reference

## Contexto

DLQ pode acumular mensagens FAILED silenciosamente. Wave 31 A1 (lesson 214) entregou
expiração automática, mas **detecção proativa** ainda faltava. Escrevente precisa ser
notificado quando há falhas recorrentes para investigar (HITL preserva decisão humana).

Wave 31 A2 entrega script que:
1. Coleta métricas agregadas (count + max_age, SEM payload)
2. Compara com thresholds
3. Envia Telegram MarkdownV2 ao escrevente se violar

## Entrega (Wave 31 A2)

### `scripts/dlq_alert_telegram.py` (250 LOC)

API:
- `collect_metrics(db)` → `dict[queue, {pending, failed_1h, max_age_minutes}]`
- `build_alert_message(metrics, threshold_failed, threshold_pending)` → `str | None`
- `send_telegram(message, token, chat_id)` → `(bool, response)` (urllib nativo, sem deps)
- `main()` com exit codes:
  - 0 = tudo OK (no alert)
  - 1 = alerta detectado (dry-run OU enviado)
  - 2 = config faltando (TELEGRAM_BOT_TOKEN/CHAT_ID)
  - 3 = falha no envio Telegram

CLI:
```
python3 scripts/dlq_alert_telegram.py                    # dry-run, exit 1 se alerta
python3 scripts/dlq_alert_telegram.py --apply           # envia real Telegram
python3 scripts/dlq_alert_telegram.py --threshold-failed 50
```

Configuração via `.secrets/telegram.env` (já existe no projeto).

### `tests/test_dlq_alert_telegram_g8.py` — **18 PASSED em 0.97s**

| Classe | Testes | Cobre |
|--------|--------|-------|
| TestBuildAlertMessage | 5 | None OK + failed breach + pending breach + multi-queue + MarkdownV2 |
| TestLGPDCompliance | 3 | sem payload + sem dict syntax + sem nomes próprios |
| TestSendTelegram | 1 | missing token graceful fail |
| TestMain | 3 | dry-run trigger exit 1 + dry-run no-alert exit 0 + apply sem env exit 2 |
| TestScriptSurface | 6 | shebang + docstring + LGPD doc + Art.16/37/46 mention + dry-run default + argparse |

## Validação gates pós-wave

| Gate | Antes (lesson 214) | Depois (Wave 31 A2) |
|------|--------------------|---------------------|
| pytest | 3262 | **3280** (+18) |
| mypy strict | 0/156 | 0/156 |
| ruff | 0 | 0 |

## LGPD compliance details

1. **Mensagem NUNCA inclui payload** — testado em 3 camadas:
   - `test_message_does_not_contain_payload` (palavras-chave explícitas)
   - `test_message_only_contains_aggregates` (sem `{`/`}` que indicariam dict)
   - `test_message_no_human_readable_names` (sem nomes comuns)
2. **Coleta agrega** — só `count`, `max_age_minutes`, queue name
3. **Threshold-driven** — alerta só dispara em padrão anormal (>10 FAILED/h OU >100 PENDING)
4. **Cooldown** (parâmetro `DLQ_ALERT_COOLDOWN_MINUTES`) — evita alerta repetido
5. **Audit log** — implicitamente via execução cron (registrado em `/var/log/cron`)

## Cross-refs

- lesson-214 (G8.08.T1 DLQ expiration, Wave 31 A1)
- lesson-213 (G8.08.T2 DLQ encryption, Wave 30 A2)
- lesson-212 (G8.07.T1 MCP tests, Wave 30 A1)
- lesson-211 (mega-commit 148 untracked)
- LGPD Art.16 (eliminação) + Art.37 (registro de operações) + Art.46 (security)
- .secrets/telegram.env (já provisionado pelo G7)

## Próxima wave (Wave 32)

**G8.08.T4**: Testes de integração injetando falhas nas conexões externas para validar DLQ.
- Testa retry policy A12 (3 tentativas com backoff 1m/5m/15m)
- Testa fallback para FAILED após max attempts
- Testa recover após sucesso
- Pode usar mock httpx/respx para Evolution/Chatwoot/Telegram

Modified by Gustavo Almeida