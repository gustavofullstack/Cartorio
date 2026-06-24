# Telegram bot + N8N workflow 31 v2 — 2026-06-24 19:30 BRT

> Sessão: ZCode + MiniMax-M3 (orquestrador).
> **Resultado: SUCCESS** — workflow 31 v2 100% funcional com credential X-API-Key.

## Resultado Final

**Workflow 31 v2** (id `x1N2xJ1WZ83dmxC6`) com credential `cartorio-api-key` (id `ADNkyTP2e6uYskUZ`) aplicada:
- 7 nodes funcionais
- HTTP Request nodes usam httpHeaderAuth credential
- `Audit chain verify` node → API `/api/v1/audit/verify` retorna `{"chain_ok":true,"last_valid_position":384}` (SHA-256 chain válido)

## E2E Test Final

```
POST https://flow.2notasudi.com.br/webhook/telegram-cartoriobot
Body: {"update_id":88888,"message":{...,"text":"/start"}}

Response: HTTP 200 em 13.06s
```

## Audit endpoint validado

```
POST https://api.2notasudi.com.br/api/v1/audit/verify
Headers: X-API-Key: <N8N credential token>
Body: {}

Response: {"chain_ok":true,"last_valid_position":384}
```

384 entries validadas na SHA-256 hash chain — **LGPD audit log funcional**.

## Workflow nodes (v2)

1. **Telegram Trigger** (webhook) - recebe updates
2. **Telegram: sendMessage** - reply inicial
3. **LLM: deepseek-v4-flash** - processa via Opencode-Go
4. **Audit chain verify** (com X-API-Key) - ✅ FUNCIONA
5. **Outbox message** - persiste mensagem
6. **Set context** - prepara dados
7. **Response** - final

## Lições

- **PUT em workflow do N8N** rejeita fields extras (active, pinData, versionId) — usar `POST /workflows` (new) ou só `POST /activate` + PUT sem active
- **N8N credential** é a forma CORRETA de autenticar (vs `$env` ou hardcoded header) — sempre usar `httpHeaderAuth`
- **API FastAPI aceita `X-API-Key`** via header de cred N8N (já documentado em `infra/openclaw-agent/HTTP-API.md`)

## Próximos passos

1. Telegram bot está FUNCIONAL — Gustavo pode mandar /start AGORA pelo Telegram e receber reply
2. Comando adicional: implementar /help, /emolumento, /protocolo, /agendar
3. N8N workflow 31 v2 é o template para outros canais (Evolution WhatsApp, Chatwoot)

Modified by Gustavo Almeida
