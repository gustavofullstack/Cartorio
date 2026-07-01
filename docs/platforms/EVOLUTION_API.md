# Evolution API v2.x - Quick Reference

> **5 endpoints + auth + webhooks para integracao WhatsApp Business.**
> Versao: 2.x (2026-06-24)
> Base URL prod: `https://whatsapp.2notasudi.com.br`
> Doc oficial: https://doc.evolution-api.com/v2/api-reference/

## Visao geral

Evolution API e' um **gateway WhatsApp Business** open-source. Roda em Docker (imagem `atendai/evolution-api:v2.x`). Suporta multi-instance, webhooks, REST API compativel com Baileys (lib Node.js WhatsApp Web).

**Por que usamos**: self-hosted (LGPD art. 33 - transferencia internacional), baixo custo, API REST simples, suporta multi-canal (WhatsApp, Telegram em breve).

## Autenticacao

Todas as requisicoes exigem header `apikey`:
```bash
curl -H "apikey: <AUTHENTICATION_API_KEY>" ...
```

- **Global key**: definida em `AUTHENTICATION.API_KEY.KEY` (env)
- **Per-instance key**: cada instance tem seu proprio `apikey` (token alternativo)
- Sem header -> `401 Unauthorized`

## 5 Endpoints principais (Cartorio usa esses)

### 1. POST /instance/create

Cria nova instancia WhatsApp.

```bash
curl -X POST "https://whatsapp.2notasudi.com.br/instance/create" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "cartorio-2notas",
    "qrcode": true,
    "integration": "WHATSAPP-BAILEYS"
  }'
```

**Response 201**:
```json
{
  "instance": {
    "instanceName": "cartorio-2notas",
    "instanceId": "abc-123",
    "status": "created",
    "serverUrl": "https://whatsapp.2notasudi.com.br",
    "apikey": "instance-specific-key",
    "ownerJid": null
  },
  "hash": {"apikey": "..."},
  "qrcode": {
    "pairingCode": "...",
    "code": "2@xxx",
    "base64": "iVBORw0KGgo...",
    "count": 0
  }
}
```

### 2. GET /instance/connect/{instance}

Retorna QR code (base64) para escanear com WhatsApp.

```bash
curl "https://whatsapp.2notasudi.com.br/instance/connect/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY"
```

**Response 200**:
```json
{
  "pairingCode": "ABCD1234",
  "code": "2@xxx",
  "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "count": 0
}
```

### 3. GET /instance/connectionState/{instance}

Status da conexao (open/close/connecting).

```bash
curl "https://whatsapp.2notasudi.com.br/instance/connectionState/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY"
```

**Response 200**:
```json
{
  "instance": {
    "instanceName": "cartorio-2notas",
    "state": "open"  // ou "close", "connecting"
  }
}
```

### 4. POST /message/sendText/{instance}

Envia mensagem de texto.

```bash
curl -X POST "https://whatsapp.2notasudi.com.br/message/sendText/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5534988887777",
    "text": "Ola! Sua certidao foi emitida.",
    "delay": 0
  }'
```

**Response 200**:
```json
{
  "key": {
    "remoteJid": "5534988887777@s.whatsapp.net",
    "fromMe": true,
    "id": "3EB0ABC123"
  },
  "message": {
    "extendedTextMessage": {
      "text": "Ola! Sua certidao foi emitida."
    }
  },
  "messageTimestamp": "1719227400"
}
```

### 5. POST /webhook/set/{instance}

Configura webhook para receber eventos.

```bash
curl -X POST "https://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
    "webhook_by_events": false,
    "webhook_base64": false,
    "events": [
      "MESSAGES_UPSERT",
      "CONNECTION_UPDATE",
      "MESSAGES_UPDATE"
    ]
  }'
```

**Response 200**:
```json
{
  "webhook": {
    "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE", "MESSAGES_UPDATE"],
    "byEvents": false,
    "base64": false
  }
}
```

### 6. POST /message/sendReaction/{instance}

Envia uma reação (emoji) a uma mensagem específica.

```bash
curl -X POST "https://whatsapp.2notasudi.com.br/message/sendReaction/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5534988887777",
    "reaction": "👍",
    "key": {
      "remoteJid": "5534988887777@s.whatsapp.net",
      "fromMe": false,
      "id": "3EB0ABC123"
    }
  }'
```

### 7. POST /message/sendPoll/{instance}

Envia uma enquete de escolha única ou múltipla.

```bash
curl -X POST "https://whatsapp.2notasudi.com.br/message/sendPoll/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5534988887777",
    "pollName": "Qual serviço deseja agendar?",
    "options": ["Abertura de Firma", "Procuração", "Escritura"],
    "selectableOptionsCount": 1
  }'
```

### 8. POST /message/sendMedia/{instance}

Envia mídias (imagens, vídeos, áudios ou documentos PDF) informando uma URL pública do arquivo.

```bash
curl -X POST "https://whatsapp.2notasudi.com.br/message/sendMedia/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5534988887777",
    "mediaMessage": {
      "mediatype": "document", // ou "image", "audio", "video"
      "fileName": "tabela_emolumentos.pdf",
      "media": "https://api.2notasudi.com.br/static/tabela.pdf",
      "caption": "Tabela de emolumentos oficial"
    }
  }'
```

## Webhook events (todos suportados)

| Event | Quando dispara |
|---|---|
| `MESSAGES_UPSERT` | Nova msg recebida OU enviada |
| `MESSAGES_UPDATE` | Msg editada |
| `MESSAGES_DELETE` | Msg apagada |
| `SEND_MESSAGE` | Msg enviada por nos |
| `CONNECTION_UPDATE` | Conexao WhatsApp mudou (open/close) |
| `CALL` | Chamada recebida |
| `CONTACTS_UPDATE` | Contato atualizado |
| `CHATS_UPDATE` | Chat atualizado |
| `CHATS_DELETE` | Chat apagado |
| `GROUPS_UPSERT` | Grupo criado/atualizado |
| `GROUP_UPDATE` | Grupo mudou |
| `GROUP_PARTICIPANTS_UPDATE` | Participante entrou/saiu |
| `PRESENCE_UPDATE` | Online/offline de contato |
| `TYPEING` | Usuario digitando |
| `NEW_JWT_TOKEN` | Token JWT novo |
| `LOGOUT_INSTANCE` | Logout feito |

## Rate limit

**Nao documentado oficialmente**. Recomendacao: usar retry com backoff em 429/5xx (ver `app/services/evolution_ingest.py`).

## Integracao com o Cartorio

| Componente | Como usa |
|---|---|
| **API Backend** | Recebe webhook em `/api/v1/webhook/evolution` (idempotente por message_id) |
| **N8N workflow #07** | Envia mensagens via Evolution (template marketing, lembretes) |
| **OpenClaw gateway** | NAO usa diretamente - passa pela API |
| **Chatwoot** | NAO usa Evolution direto - WhatsApp via Chatwoot (inbox separada) |

## Como adicionar nova instance

1. Chamar `POST /instance/create` (1)
2. Escanear QR code retornado (2)
3. Configurar webhook (5) apontando para API
4. Testar com `GET /instance/connectionState` (3)
5. Enviar msg de teste com `POST /message/sendText` (4)

## Referencias

- Doc oficial: https://doc.evolution-api.com/v2/api-reference/
- GitHub: https://github.com/EvolutionAPI/evolution-api
- Imagem Docker: `atendai/evolution-api:v2.x`
- Estado no projeto: `infra/` (config Easypanel)
- Integracao: `backend/app/services/evolution_ingest.py`

Modified by Gustavo Almeida - 2026-07-01
