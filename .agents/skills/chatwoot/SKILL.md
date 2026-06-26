---
name: chatwoot
description: |
  Skill para interagir com o Chatwoot CRM via API REST e MCP.
  Use quando precisar: criar/listar conversas, enviar mensagens, criar contatos,
  gerenciar inboxes, labels, canned responses, macros, relatórios e handoff humano.
  URL: https://chat.2notasudi.com.br | Account ID: 1 | Telegram Inbox ID: 1
---

# Chatwoot CRM — Skill de Integração

## Acesso

| Item | Valor |
|------|-------|
| **URL Base** | `https://chat.2notasudi.com.br` |
| **API Token** | `d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3` |
| **Account ID** | `1` |
| **Telegram Inbox ID** | `1` (test_cartorio_bot) |
| **Header de Auth** | `api_access_token: <token>` |

## Endpoints Principais

### Conversas
```bash
# Listar todas as conversas
GET /api/v1/accounts/1/conversations?page=1&status=open

# Criar conversa
POST /api/v1/accounts/1/conversations
{
  "inbox_id": 1,
  "contact_id": 123,
  "additional_attributes": {}
}

# Enviar mensagem em conversa
POST /api/v1/accounts/1/conversations/{conv_id}/messages
{
  "content": "Olá, como posso ajudar?",
  "message_type": "outgoing",
  "content_type": "text"
}

# Pausar/retomar agent
PUT /api/v1/accounts/1/conversations/{conv_id}
{
  "status": "open",
  "assignee_id": null
}
```

### Contatos
```bash
# Buscar contato por telefone ou email
GET /api/v1/accounts/1/contacts/search?q=<phone_or_email>

# Criar contato
POST /api/v1/accounts/1/contacts
{
  "name": "Nome Cliente",
  "phone_number": "+5534999999999",
  "email": "cliente@email.com"
}
```

### Inboxes
```bash
# Listar inboxes
GET /api/v1/accounts/1/inboxes

# Inbox 1: test_cartorio_bot (Telegram)
# Inbox 2: WhatsApp (a criar via Evolution API)
```

### Canned Responses
```bash
# Listar respostas prontas
GET /api/v1/accounts/1/canned_responses

# Criar canned response
POST /api/v1/accounts/1/canned_responses
{
  "short_code": "emolumento_certidao",
  "content": "A certidão de casamento custa R$ 105,40. Prazo: 5 dias úteis."
}
```

## Exemplo de Handoff Humano

```python
# No webhook do N8N ou API, quando agent decide fazer handoff:
import httpx

async def handoff_para_humano(conversa_id: int, motivo: str) -> None:
    headers = {
        "api_access_token": "d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3"
    }
    # 1. Enviar mensagem para atendente
    await httpx.AsyncClient().post(
        f"https://chat.2notasudi.com.br/api/v1/accounts/1/conversations/{conversa_id}/messages",
        json={"content": f"[PIETRA] Transferindo para atendente: {motivo}", "message_type": "activity"},
        headers=headers
    )
    # 2. Marcar conversa para handoff (label)
    await httpx.AsyncClient().post(
        f"https://chat.2notasudi.com.br/api/v1/accounts/1/conversations/{conversa_id}/labels",
        json={"labels": ["handoff-pietra", "aguardando-humano"]},
        headers=headers
    )
```

## Integração via N8N

O workflow N8N `03 - Handoff Humano (Chatwoot v2)` usa os nodes:
- `@devlikeapro/n8n-nodes-chatwoot` para criar conversas
- HTTP Request para enviar mensagens
- Webhook para receber eventos do Chatwoot

## Variáveis de Ambiente Necessárias

```env
CHATWOOT_BASE_URL=https://chat.2notasudi.com.br
CHATWOOT_API_KEY=d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```

## Notas Importantes

- **Telegram já conectado** no Inbox 1 via `@CartorioAssistantBot`
- **WhatsApp será Inbox 2** via Evolution API (conectar após validação completa)
- **HITL**: Atendente pode pausar Pietra a qualquer momento via UI do Chatwoot
- **Sidekiq**: Background jobs rodam em container separado (`cartorio_chatwoot-sidekiq`)
- **RubyLLM warning**: Avisos de deprecação nas rails commands são inofensivos

## Teste Rápido

```bash
# Verificar API funcionando
curl -H "api_access_token: d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3" \
  https://chat.2notasudi.com.br/api/v1/accounts/1/conversations

# Listar inboxes
curl -H "api_access_token: d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3" \
  https://chat.2notasudi.com.br/api/v1/accounts/1/inboxes
```

## MCP Server & Client Integration

- **Chatwoot MCP Server**: Um servidor MCP customizado ou node MCP no N8N mapeia as operações do Chatwoot para os agents.
- **Tools MCP Disponíveis**:
  - `chatwoot_list_conversations(status: str)`: Lista conversas abertas.
  - `chatwoot_send_message(conv_id: int, text: str)`: Envia resposta ao cliente.
  - `chatwoot_toggle_agent(conv_id: int, paused: bool)`: Ativa/desativa Pietra (HITL).

