# Chatwoot 3.x - Quick Reference (Cartorio)

> **5 endpoints + Agent Bot + webhooks para integracao bot + humano.**
> Versao: 3.x (2026-06-24)
> Base URL prod: `https://chat.2notasudi.com.br`
> Doc oficial: https://www.chatwoot.com/developers/api/

## Visao geral

Chatwoot e' um **CRM open-source** com suporte a multi-canal (WhatsApp, Telegram, Web, Email). Roda em Docker (`chatwoot/chatwoot:latest`). API REST compativel com multi-tenant.

**Por que usamos**: CRM completo (conversas, agentes, labels, Canned Responses), Agent Bot para pausar IA em qualquer conversa, self-hosted (LGPD).

## Autenticacao

Todas as requisicoes exigem header `api_access_token`:
```bash
curl -H "api_access_token: <TOKEN>" ...
```

- **User token**: para `/api/v1/accounts/...`
- **Platform token** (admin): para `/platform/api/v1/...`
- **Agent Bot token**: ao criar um bot, Chatwoot retorna `access_token`

## 5 Endpoints principais

### 1. POST /api/v1/accounts/{account_id}/conversations

Cria conversa.

```bash
curl -X POST "https://chat.2notasudi.com.br/api/v1/accounts/1/conversations" \
  -H "api_access_token: $CHATWOOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "5534988887777",
    "inbox_id": 2,
    "contact_id": 15,
    "status": "open",
    "message": {"content": "Ola!"}
  }'
```

**Response 200**:
```json
{"id": 123, "account_id": 1, "inbox_id": 2}
```

### 2. POST /api/v1/accounts/{account_id}/conversations/{id}/messages

Envia mensagem.

```bash
curl -X POST "https://chat.2notasudi.com.br/api/v1/accounts/1/conversations/123/messages" \
  -H "api_access_token: $CHATWOOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Sua certidao foi emitida!",
    "message_type": "outgoing",
    "private": false
  }'
```

**Response 200**:
```json
{"id": 456, "content": "Sua certidao foi emitida!", "message_type": 1, "conversation_id": 123}
```

### 3. GET /api/v1/accounts/{account_id}/conversations?status=open

Lista conversas.

```bash
curl "https://chat.2notasudi.com.br/api/v1/accounts/1/conversations?status=open&assignee_type=unassigned&page=1" \
  -H "api_access_token: $CHATWOOT_API_KEY"
```

**Response 200**:
```json
{"data": {"meta": {"all_count": 7}, "payload": [{"id": 1, "status": "open", "inbox_id": 2}]}}
```

### 4. POST /api/v1/accounts/{account_id}/conversations/{id}/toggle_status

Atualiza status (open/resolved/pending/snoozed).

```bash
curl -X POST "https://chat.2notasudi.com.br/api/v1/accounts/1/conversations/123/toggle_status" \
  -H "api_access_token: $CHATWOOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved"}'
```

### 5. POST /platform/api/v1/agent_bots

Cria Agent Bot (requer Platform token admin).

```bash
curl -X POST "https://chat.2notasudi.com.br/platform/api/v1/agent_bots" \
  -H "api_access_token: $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bot Cartorio",
    "outgoing_url": "https://api.2notasudi.com.br/integrations/agent/chatwoot-webhook",
    "account_id": 1
  }'
```

**Response**: `{id, name, outgoing_url, bot_type: "webhook", access_token: "GUARDAR"}`

## Conceitos-chave

### Agent Bot

Bot que aparece como agente no Chatwoot. Ao receber mensagem:
1. Chatwoot faz POST no `outgoing_url` com payload
2. Bot processa e responde via `access_token`
3. `bot_type: webhook` (default) ou `dialogflow`

**Cartorio**: Agent Bot = nosso AI Cartorio. Humano pode pausar/resumir bot.

### Webhook events

| Event | Quando |
|---|---|
| `message_created` | Msg nova (incoming + outgoing) |
| `conversation_status_changed` | open -> resolved etc |
| `conversation_created` | Nova conversa |
| `conversation_updated` | Editada |

### Inbox WhatsApp via Evolution API

Criar inbox tipo `api`:
```bash
curl -X POST "$BASE/api/v1/accounts/1/inboxes" \
  -H "api_access_token: $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "WhatsApp Cartorio",
    "channel": {
      "type": "api",
      "webhook_url": "https://whatsapp.2notasudi.com.br/webhook/chatwoot"
    }
  }'
```

`source_id` da conversa = numero do contato (ex: `5511999999999`).

### Custom Attributes

Definir em **Settings -> Custom Attributes**:
```bash
curl -X POST "$BASE/api/v1/accounts/1/conversations" \
  -d '{
    "source_id": "...",
    "custom_attributes": {
      "protocolo": "PROT-2026-000123",
      "tipo_certidao": "nascimento",
      "status_servico": "em_andamento"
    }
  }'
```

**Cartorio atributos recomendados**: `protocolo`, `tipo_certidao`, `status_servico`, `prioridade`.

## Pausar bot em uma conversa

1. UI Chatwoot: assign to me
2. Webhook `conversation_updated` (assignee_id mudou)
3. POST `/admin/agent/pause` (API backend)
4. Humano soltar -> POST `/admin/agent/resume`

## Cenarios de uso no Cartorio

| Fluxo | Endpoints |
|---|---|
| Cliente manda WhatsApp | Evolution -> Inbox API -> Conversa criada |
| Bot responde | API -> POST /conversations/{id}/messages |
| Humano assume | UI Chatwoot -> toggle pause |
| LGPD esqueci meu dado | DELETE /contacts/{id} |

## Troubleshooting

| Problema | Solucao |
|---|---|
| 401 Unauthorized | token invalido - gerar novo em Settings |
| 404 Conversation | conversa deletada ou ID errado |
| Agent Bot nao responde | outgoing_url com problema |
| Webhook nao dispara | verificar Settings > Integrations > Webhooks |

## Referencias

- Doc oficial: https://www.chatwoot.com/developers/api/
- GitHub: https://github.com/chatwoot/chatwoot
- Plataforma: https://chat.2notasudi.com.br
- Integracao: `backend/app/services/chatwoot_handoff.py`

Modified by ZCode/Mavis - 2026-06-24
