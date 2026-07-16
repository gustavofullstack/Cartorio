# N8N Idempotency Injector - Dry Run

**Data**: 2026-07-16T17:04:29.122637+00:00
**Total sem idempotencia**: 20

## WFs pendentes

- `01-consulta-emolumento.json`
- `02-criar-protocolo.json`
- `04-boas-vindas-lgpd.json`
- `04-consulta-protocolo.json`
- `05-agendamento.json`
- `06-2-via-protocolo.json`
- `10-faq-bot.json`
- `11-monitor-cartorio.json`
- `12-chatbot-llm-end-to-end.json`
- `14-opencode-go-fallback.json`
- `16-prospeccao-enrichment.json`
- `23-lgpd-esqueci-v2.json`
- `26-alerta-critico.json`
- `27-welcome-first-time.json`
- `31-telegram-listener.json`
- `33-whatsapp-qr-scan-helper.json`
- `35-llm-fallback-3x.json`
- `36-chatwoot-telegram-sync.json`
- `evo-in.json`
- `lgpd-esqueci-fix.json`

## Para aplicar:

```bash
python3 scripts/n8n_idempotency_injector.py --apply
```
