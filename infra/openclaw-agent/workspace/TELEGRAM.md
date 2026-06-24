# TELEGRAM.md - Bot Cartorio no Telegram

> **Configuracao do bot de teste do Cartorio no Telegram.**
> Bot: `@CartorioBot` (nome provisorio ate Gustavo registrar oficial)
> Token: `8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q`
> Status: **CONECTAR** (NÃO rotacionar token)

## Visao geral

O bot do Telegram e' o **canal de teste** do Cartorio. Ele esta conectado em:
- **OpenClaw Agent** (AI Cartorio)
- **API Backend** (FastAPI)
- **N8N** (workflows)
- **Chatwoot** (inbox)
- **Redis** (cache de conversa)
- **Supabase** (persist de mensagens)

## Setup do bot

### 1. Registrar bot no BotFather

Aconteceu em 2026-06-23 (Gustavo). Bot @CartorioBot criado. Token recebido e armazenado.

**NAO rotacionar** - Gustavo + ZCode sao unicos com acesso. Token nao tem risco.

### 2. Webhook URL

Telegram faz POST em:
```
https://api.2notasudi.com.br/api/v1/webhook/telegram
```

(NÃO é evolution - é endpoint dedicado Telegram)

### 3. Configurar webhook via curl

```bash
curl -X POST "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.2notasudi.com.br/api/v1/webhook/telegram",
    "allowed_updates": ["message", "edited_message", "callback_query"],
    "secret_token": "<HMAC-SHA256-shared-secret>"
  }'
```

### 4. Implementacao no backend (a fazer)

**Endpoint**: `POST /api/v1/webhook/telegram`

**Estrutura**:
1. Recebe update do Telegram
2. Valida `secret_token` (HMAC)
3. Extrai `message` (texto, chat_id, user_id)
4. PII scrub (camada 1)
5. Salva no Redis (contexto da conversa)
6. Chama OpenClaw (Agent AI)
7. PII scrub resposta (camada 3)
8. Envia resposta via Telegram API
9. Audit log (LGPD art. 37)

### 5. Schema Redis para contexto

```
cartorio:telegram:chat:{chat_id} -> Hash {
  user_id, first_name, last_msg_at, msg_count
}
TTL: 24h
```

## Telegram Bot API - Comandos uteis

### Enviar mensagem

```bash
curl -X POST "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 123456789,
    "text": "Ola! Bem-vindo ao Cartorio 2 Oficio de Notas de Uberlandia.",
    "parse_mode": "HTML"
  }'
```

### Responder callback (botao)

```bash
curl -X POST "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/answerCallbackQuery" \
  -H "Content-Type: application/json" \
  -d '{
    "callback_query_id": "abc123",
    "text": "Confirmado!",
    "show_alert": false
  }'
```

### Setar comandos do bot (menu)

```bash
curl -X POST "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/setMyCommands" \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {"command": "emolumento", "description": "Calcular custo de certidao"},
      {"command": "protocolo", "description": "Consultar status de protocolo"},
      {"command": "agendar", "description": "Ver horarios disponiveis"},
      {"command": "humano", "description": "Falar com escrevente"}
    ]
  }'
```

### Get updates (long polling - alternativa a webhook)

```bash
curl "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/getUpdates?timeout=30"
```

## Fluxo completo

```
[Telegram user]
   | mensagem
   v
[Telegram API] -> POST /api/v1/webhook/telegram (API backend)
   |
   | 1. Validar HMAC
   | 2. PII scrub (camada 1)
   | 3. Salvar no Redis
   v
[OpenClaw Agent] -> POST /api/v1/integrations/opencode/test (LLM)
   |
   | 4. PII scrub pre-LLM (camada 2)
   | 5. Chamada LLM
   v
[OpenCode-Go (deepseek-v4-flash)]
   |
   | 6. Resposta
   v
[API Backend]
   |
   | 7. PII scrub output (camada 3)
   | 8. Audit log
   | 9. POST sendMessage (Telegram API)
   v
[Telegram user]
```

## Troubleshooting

| Problema | Solucao |
|---|---|
| Bot nao responde | Verificar webhook: `curl .../getWebhookInfo` |
| 401 Unauthorized | Token invalido (NAO rotacionar - verificar config) |
| 400 Bad Request | Payload invalido (ver parse_mode, chat_id) |
| Rate limit (429) | Telegram limita 30 msg/sec globalmente, 1 msg/sec por chat |
| Timeout no webhook | Telegram espera 200 OK em <60s, nosso fluxo deve responder rapido |

## Teste rapido (sem webhook)

```bash
# Enviar msg ao bot via curl (bypass webhook)
curl -X POST "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/sendMessage" \
  -d "chat_id=SEU_CHAT_ID&text=Ola"

# Listar updates recebidos (para ver se webhook esta funcionando)
curl "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/getUpdates"
```

## LGPD Compliance

- **PII scrub 3 camadas** (input, pre-LLM, output) - mesmo que WhatsApp
- **Audit log** - toda msg registrada (LGPD art. 37)
- **Consent gate** - primeira msg pede consentimento LGPD
- **Retencao** - 365 dias (LGPD art. 16)
- **Direito ao esquecimento** - via API `/api/v1/lgpd/direito-esquecimento`

## Referencias

- Telegram Bot API: https://core.telegram.org/bots/api
- SetWebhook: https://core.telegram.org/bots/api#setwebhook
- Webhook spec: https://core.telegram.org/bots/webhooks
- Codigo fonte: `backend/app/api/v1/webhook/telegram.py` (a criar)
- LGPD: `docs/ripd.md` (mesmos principios)

Modified by ZCode/Mavis - 2026-06-24
