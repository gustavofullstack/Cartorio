# Evolution API v2 — Integration Reference

> **Version**: Evolution API v2.3.7 (Docker: `cartorio_evolution-api:8080`)
> **Date**: 2026-06-22
> **Sprint**: Sprint 1 — Cartório Chatbot

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Instance Management](#2-instance-management)
3. [Webhook Registration](#3-webhook-registration)
4. [Webhook Payload Format (Incoming)](#4-webhook-payload-format-incoming)
5. [Sending Messages (Outbound)](#5-sending-messages-outbound)
6. [Complete Webhook Events List](#6-complete-webhook-events-list)
7. [OpenClaw Gateway Integration](#7-openclaw-gateway-integration)
8. [n8n Integration](#8-n8n-integration)
9. [Environment Variables Reference](#9-environment-variables-reference)
10. [Cartório-Specific Configuration](#10-cartório-specific-configuration)

---

## 1. Authentication

Evolution API uses **two levels** of API keys, both passed in the `apikey` HTTP header.

### Global API Key (Admin)

- **Purpose**: Creating/deleting instances, system-wide management
- **Configured via**: `.env` → `AUTHENTICATION_API_KEY=your-global-key`
- **Used for**: `/instance/*` endpoints

### Instance Token (Per-Instance)

- **Purpose**: Sending messages, managing contacts, reading chats for a specific instance
- **Generated**: Automatically when instance is created, or set manually via `token` field
- **Used for**: `/message/*`, `/chat/*`, `/webhook/*` endpoints

### Header Format

```
apikey: YOUR_KEY_HERE
Content-Type: application/json
```

> [!IMPORTANT]
> Never use the Global API Key for message operations. Always use the Instance Token for day-to-day operations — this provides instance-level isolation and better security.

### For Cartório Project

| Key Type | Where Stored | Value |
|----------|-------------|-------|
| Global API Key | `AUTHENTICATION_API_KEY` in Evolution API `.env` | Set in Easypanel env |
| Instance Token | Returned on instance creation / set via `token` field | Store in Supabase `config` or `.env` |

---

## 2. Instance Management

### 2.1 Create Instance

Creates a new WhatsApp connection. Returns QR code for pairing.

**Endpoint**: `POST /instance/create`
**Auth**: Global API Key

#### Request

```bash
curl -X POST http://cartorio_evolution-api:8080/instance/create \
  -H "apikey: YOUR_GLOBAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "cartorio-whatsapp",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true,
    "token": "INSTANCE_SPECIFIC_TOKEN",
    "webhook": {
      "url": "https://cartorio-backend.dfgdxq.easypanel.host/api/v1/webhook/evolution",
      "byEvents": false,
      "base64": true,
      "headers": {
        "X-Webhook-Secret": "YOUR_WEBHOOK_SECRET"
      },
      "events": [
        "QRCODE_UPDATED",
        "MESSAGES_UPSERT",
        "MESSAGES_UPDATE",
        "CONNECTION_UPDATE",
        "SEND_MESSAGE"
      ]
    }
  }'
```

#### Request Body Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `instanceName` | string | ✅ | Unique identifier for the instance |
| `integration` | string | ❌ | `WHATSAPP-BAILEYS` (default), `WHATSAPP-BUSINESS`, `EVOLUTION` |
| `qrcode` | boolean | ❌ | If `true`, returns base64 QR code in response |
| `token` | string | ❌ | Custom instance token; auto-generated if omitted |
| `number` | string | ❌ | Phone number (E.164 format, e.g., `5531999999999`) |
| `webhook` | object | ❌ | Inline webhook config (can also be set later via `/webhook/set`) |
| `webhook.url` | string | ❌ | Destination URL for event delivery |
| `webhook.byEvents` | boolean | ❌ | If `true`, appends event name to URL path |
| `webhook.base64` | boolean | ❌ | If `true`, media content is sent as base64 in webhook payload |
| `webhook.headers` | object | ❌ | Custom headers sent with each webhook request |
| `webhook.events` | string[] | ❌ | List of events to subscribe to |

#### Response (Success — 201)

```json
{
  "instance": {
    "instanceName": "cartorio-whatsapp",
    "instanceId": "uuid-here",
    "status": "created"
  },
  "hash": {
    "apikey": "auto-generated-instance-token-uuid"
  },
  "qrcode": {
    "code": "2@abc123...",
    "base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
  }
}
```

> [!TIP]
> The `hash.apikey` is the Instance Token you'll use for sending messages. Save it!

### 2.2 List All Instances

**Endpoint**: `GET /instance/fetchInstances`
**Auth**: Global API Key

```bash
curl -X GET http://cartorio_evolution-api:8080/instance/fetchInstances \
  -H "apikey: YOUR_GLOBAL_API_KEY"
```

### 2.3 Check Connection Status

**Endpoint**: `GET /instance/connectionStatus/{instanceName}`
**Auth**: Global API Key or Instance Token

```bash
curl -X GET http://cartorio_evolution-api:8080/instance/connectionStatus/cartorio-whatsapp \
  -H "apikey: YOUR_API_KEY"
```

#### Response

```json
{
  "instance": {
    "instanceName": "cartorio-whatsapp",
    "state": "open"
  }
}
```

States: `open` (connected), `connecting`, `close` (disconnected)

### 2.4 Get QR Code (Reconnect)

**Endpoint**: `GET /instance/connect/{instanceName}`
**Auth**: Global API Key

```bash
curl -X GET http://cartorio_evolution-api:8080/instance/connect/cartorio-whatsapp \
  -H "apikey: YOUR_GLOBAL_API_KEY"
```

### 2.5 Delete Instance

**Endpoint**: `DELETE /instance/delete/{instanceName}`
**Auth**: Global API Key

```bash
curl -X DELETE http://cartorio_evolution-api:8080/instance/delete/cartorio-whatsapp \
  -H "apikey: YOUR_GLOBAL_API_KEY"
```

---

## 3. Webhook Registration

### 3.1 Set Webhook (Per-Instance)

**Endpoint**: `POST /webhook/set/{instanceName}`
**Auth**: Instance Token or Global API Key

```bash
curl -X POST http://cartorio_evolution-api:8080/webhook/set/cartorio-whatsapp \
  -H "apikey: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook": {
      "enabled": true,
      "url": "https://cartorio-backend.dfgdxq.easypanel.host/api/v1/webhook/evolution",
      "byEvents": false,
      "base64": false,
      "headers": {
        "X-Webhook-Secret": "your-shared-secret"
      },
      "events": [
        "MESSAGES_UPSERT",
        "MESSAGES_UPDATE",
        "CONNECTION_UPDATE",
        "SEND_MESSAGE"
      ]
    }
  }'
```

#### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable webhook delivery |
| `url` | string | — | HTTPS endpoint to receive events |
| `byEvents` | boolean | `false` | If `true`: `url/messages-upsert`, `url/connection-update`, etc. |
| `base64` | boolean | `false` | If `true`: media payloads include base64 data |
| `headers` | object | `{}` | Custom headers for authentication on your endpoint |
| `events` | string[] | all | Which events to subscribe to |

> [!WARNING]
> When `byEvents` is `true`, the event name is appended to the URL as a kebab-case path (e.g., `MESSAGES_UPSERT` → `/messages-upsert`). Your server must handle those specific routes.

### 3.2 Get Current Webhook Config

**Endpoint**: `GET /webhook/find/{instanceName}`
**Auth**: Instance Token or Global API Key

```bash
curl -X GET http://cartorio_evolution-api:8080/webhook/find/cartorio-whatsapp \
  -H "apikey: YOUR_API_KEY"
```

### 3.3 Global Webhook (via Environment)

Instead of per-instance configuration, set these in the Evolution API `.env`:

```env
WEBHOOK_GLOBAL_ENABLED=true
WEBHOOK_GLOBAL_URL=https://cartorio-backend.dfgdxq.easypanel.host/api/v1/webhook/evolution
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false
WEBHOOK_EVENTS=MESSAGES_UPSERT,MESSAGES_UPDATE,CONNECTION_UPDATE,SEND_MESSAGE
```

> [!NOTE]
> Global webhook applies to ALL instances. Per-instance webhook overrides global config for that instance.

---

## 4. Webhook Payload Format (Incoming)

All webhook payloads follow this top-level structure:

```json
{
  "event": "messages.upsert",
  "instance": "cartorio-whatsapp",
  "data": { ... },
  "destination": "https://your-webhook-url.com",
  "date_time": "2026-06-22T12:00:00.000Z",
  "server_url": "http://cartorio_evolution-api:8080",
  "apikey": "instance-token"
}
```

### 4.1 Text Message (Incoming)

```json
{
  "event": "messages.upsert",
  "instance": "cartorio-whatsapp",
  "data": {
    "key": {
      "remoteJid": "5531999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "BAE5A1B2C3D4E5F6"
    },
    "pushName": "João da Silva",
    "message": {
      "conversation": "Qual o status do protocolo 12345?"
    },
    "messageType": "conversation",
    "messageTimestamp": 1750600000
  }
}
```

#### Extracting text content:

Text can appear in multiple locations depending on the message type:

```python
# Python helper — extract text from any message variant
def extract_text(data: dict) -> str | None:
    msg = data.get("message", {})

    # Simple text message
    if "conversation" in msg:
        return msg["conversation"]

    # Extended text (messages with links, formatting, etc.)
    if "extendedTextMessage" in msg:
        return msg["extendedTextMessage"].get("text")

    # Image/video/document captions
    for media_key in ("imageMessage", "videoMessage", "documentMessage"):
        if media_key in msg:
            return msg[media_key].get("caption")

    return None
```

### 4.2 Image Message (Incoming)

```json
{
  "event": "messages.upsert",
  "instance": "cartorio-whatsapp",
  "data": {
    "key": {
      "remoteJid": "5531999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "BAE5XXXXXXXX"
    },
    "pushName": "Maria Souza",
    "message": {
      "imageMessage": {
        "url": "https://mmg.whatsapp.net/v/t62.XXXXX/...",
        "mimetype": "image/jpeg",
        "caption": "Documento de identidade",
        "fileSha256": "base64-sha256-hash",
        "fileLength": "125430",
        "height": 1200,
        "width": 800,
        "mediaKey": "base64-media-key",
        "directPath": "/v/t62.XXXXX/..."
      }
    },
    "messageType": "imageMessage",
    "messageTimestamp": 1750600100
  }
}
```

> [!NOTE]
> If `base64: true` was set in webhook config, the payload will include a `base64` field inside `imageMessage` with the full image data. Otherwise, you need to use the `url` + `mediaKey` to download the file.

### 4.3 Document Message (Incoming — PDF, DOCX, etc.)

```json
{
  "event": "messages.upsert",
  "instance": "cartorio-whatsapp",
  "data": {
    "key": {
      "remoteJid": "5531999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "BAE5YYYYYYYY"
    },
    "pushName": "Carlos Oliveira",
    "message": {
      "documentMessage": {
        "url": "https://mmg.whatsapp.net/v/t62.XXXXX/...",
        "mimetype": "application/pdf",
        "fileName": "escritura-compra-venda.pdf",
        "fileSha256": "base64-sha256-hash",
        "fileLength": "543210",
        "pageCount": 5,
        "mediaKey": "base64-media-key",
        "directPath": "/v/t62.XXXXX/..."
      }
    },
    "messageType": "documentMessage",
    "messageTimestamp": 1750600200
  }
}
```

### 4.4 Audio Message (Voice Note)

```json
{
  "event": "messages.upsert",
  "instance": "cartorio-whatsapp",
  "data": {
    "key": {
      "remoteJid": "5531999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "BAE5ZZZZZZZZ"
    },
    "pushName": "Ana Santos",
    "message": {
      "audioMessage": {
        "url": "https://mmg.whatsapp.net/v/t62.XXXXX/...",
        "mimetype": "audio/ogg; codecs=opus",
        "seconds": 15,
        "ptt": true,
        "mediaKey": "base64-media-key",
        "fileLength": "23456",
        "directPath": "/v/t62.XXXXX/..."
      }
    },
    "messageType": "audioMessage",
    "messageTimestamp": 1750600300
  }
}
```

### 4.5 Key Fields Reference

| Field | Location | Description |
|-------|----------|-------------|
| `event` | root | Event type: `messages.upsert`, `connection.update`, etc. |
| `instance` | root | Instance name that received the event |
| `data.key.remoteJid` | data | Sender's WhatsApp ID (`NUMBER@s.whatsapp.net`) |
| `data.key.fromMe` | data | `true` if sent by our instance, `false` if incoming |
| `data.key.id` | data | Unique message ID |
| `data.pushName` | data | Sender's display name on WhatsApp |
| `data.message` | data | Message content object (varies by type) |
| `data.messageType` | data | String: `conversation`, `imageMessage`, `documentMessage`, etc. |
| `data.messageTimestamp` | data | Unix timestamp of the message |

### 4.6 Connection Update Event

```json
{
  "event": "connection.update",
  "instance": "cartorio-whatsapp",
  "data": {
    "state": "open",
    "statusReason": 200
  }
}
```

States: `open`, `connecting`, `close`

---

## 5. Sending Messages (Outbound)

All send endpoints use the pattern:
```
POST /message/{action}/{instanceName}
```

Auth: **Instance Token** in `apikey` header.

### 5.1 Send Text Message

**Endpoint**: `POST /message/sendText/{instanceName}`

```bash
curl -X POST http://cartorio_evolution-api:8080/message/sendText/cartorio-whatsapp \
  -H "apikey: INSTANCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5531999999999",
    "text": "Olá! O status do seu protocolo 12345 é: Em andamento. Previsão de conclusão: 25/06/2026."
  }'
```

#### Request Body

```json
{
  "number": "5531999999999",
  "text": "Sua mensagem aqui"
}
```

#### Response (Success)

```json
{
  "key": {
    "remoteJid": "5531999999999@s.whatsapp.net",
    "fromMe": true,
    "id": "BAE5SENT0001"
  },
  "message": {
    "conversation": "Sua mensagem aqui"
  },
  "messageTimestamp": 1750601000,
  "status": "PENDING"
}
```

### 5.2 Send Image

**Endpoint**: `POST /message/sendMedia/{instanceName}`

#### Via URL

```json
{
  "number": "5531999999999",
  "mediatype": "image",
  "mimetype": "image/jpeg",
  "caption": "Comprovante de pagamento de emolumentos",
  "media": "https://cartorio-storage.supabase.co/storage/v1/object/public/docs/comprovante.jpg"
}
```

#### Via Base64

```json
{
  "number": "5531999999999",
  "mediatype": "image",
  "mimetype": "image/png",
  "caption": "QR Code para pagamento",
  "fileName": "qrcode-pagamento.png",
  "media": "iVBORw0KGgoAAAANSUhEUg..."
}
```

> [!IMPORTANT]
> When using base64, send only the raw base64 string. Do NOT include the `data:image/png;base64,` prefix — it will cause 400 errors.

### 5.3 Send Document (PDF)

**Endpoint**: `POST /message/sendMedia/{instanceName}`

```json
{
  "number": "5531999999999",
  "mediatype": "document",
  "mimetype": "application/pdf",
  "caption": "Certidão de matrícula atualizada",
  "fileName": "certidao-matricula-12345.pdf",
  "media": "https://cartorio-storage.supabase.co/storage/v1/object/public/docs/certidao.pdf"
}
```

### 5.4 Send Media Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `number` | string | ✅ | Recipient phone (E.164: `5531999999999`) |
| `mediatype` | string | ✅ | `image`, `video`, `audio`, `document` |
| `mimetype` | string | ✅ | MIME type: `image/jpeg`, `application/pdf`, etc. |
| `media` | string | ✅ | Public URL **or** raw base64 string |
| `caption` | string | ❌ | Text caption displayed with the media |
| `fileName` | string | ❌ | Filename visible to recipient (required for documents) |

### 5.5 Quick Reference — All Send Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/message/sendText/{instance}` | POST | Send text message |
| `/message/sendMedia/{instance}` | POST | Send image/document/video/audio via URL or base64 |
| `/message/sendWhatsAppAudio/{instance}` | POST | Send audio as voice note (ptt) |
| `/message/sendButtons/{instance}` | POST | Send interactive button message |
| `/message/sendList/{instance}` | POST | Send interactive list message |
| `/message/sendContact/{instance}` | POST | Send contact vCard |
| `/message/sendLocation/{instance}` | POST | Send location |
| `/message/sendReaction/{instance}` | POST | Send emoji reaction to a message |

---

## 6. Complete Webhook Events List

### Instance & Connection Events

| Event | Description |
|-------|-------------|
| `APPLICATION_STARTUP` | Application initialized |
| `INSTANCE_CREATE` | New instance created |
| `INSTANCE_DELETE` | Instance deleted |
| `REMOVE_INSTANCE` | Instance removed from system |
| `STATUS_INSTANCE` | Instance status update |
| `CONNECTION_UPDATE` | Connection state changed (open/close/connecting) |
| `QRCODE_UPDATED` | New QR code generated |
| `LOGOUT_INSTANCE` | Instance logged out |

### Message Events ⭐

| Event | Description |
|-------|-------------|
| `MESSAGES_UPSERT` | **New message received or sent** — primary event for chatbot |
| `MESSAGES_UPDATE` | Message status changed (delivered, read, played) |
| `MESSAGES_DELETE` | Message deleted |
| `MESSAGES_SET` | Initial message sync |
| `MESSAGES_EDITED` | Message content modified |
| `SEND_MESSAGE` | Message sent via API |
| `SEND_MESSAGE_UPDATE` | Sent message status updated |

### Chat, Contact, and Group Events

| Event | Description |
|-------|-------------|
| `CHATS_UPSERT` | Chat added/updated |
| `CHATS_UPDATE` | Chat info changed |
| `CHATS_DELETE` | Chat deleted |
| `CONTACTS_UPSERT` | Contact added/updated |
| `CONTACTS_UPDATE` | Contact info changed |
| `PRESENCE_UPDATE` | User online/offline status |
| `GROUPS_UPSERT` | Group added/updated |
| `GROUP_UPDATE` | Group settings changed |
| `GROUP_PARTICIPANTS_UPDATE` | Group members changed |
| `LABELS_EDIT` | Label created/modified/deleted |
| `LABELS_ASSOCIATION` | Label associated/removed |
| `CALL` | Call event (incoming/outgoing) |

### Events We Need for Cartório

```json
[
  "MESSAGES_UPSERT",
  "MESSAGES_UPDATE",
  "CONNECTION_UPDATE",
  "QRCODE_UPDATED",
  "SEND_MESSAGE"
]
```

---

## 7. OpenClaw Gateway Integration

### Architecture Understanding

OpenClaw and Evolution API are **separate, complementary systems**:

| Aspect | OpenClaw Gateway | Evolution API |
|--------|-----------------|---------------|
| **Role** | AI Agent runtime + multi-channel orchestrator | WhatsApp connection middleware (REST API) |
| **Protocol** | WebSocket (bidirectional, persistent) | REST + Webhooks (HTTP) |
| **Best For** | AI agent logic, context management | WhatsApp connectivity, message I/O |

### How They Connect in Cartório Architecture

```
WhatsApp User
     │
     ▼
┌─────────────────────┐
│  Evolution API      │  ← Manages WhatsApp session (QR code, Baileys)
│  (REST + Webhooks)  │
└─────────┬───────────┘
          │ Webhook POST (messages.upsert)
          ▼
┌─────────────────────┐
│  FastAPI Backend     │  ← Receives webhook, processes, calls LLM
│  (port 8000)        │
└─────────┬───────────┘
          │ WebSocket
          ▼
┌─────────────────────┐
│  OpenClaw Gateway   │  ← AI agent runtime, context, tools
│  (WSS)              │
└─────────────────────┘
```

### OpenClaw Gateway Protocol

- **Transport**: WebSocket (`wss://cartorio-openclaw-gateway.dfgdxq.easypanel.host`)
- **Frame Format**: JSON payloads in text WebSocket frames
- **Typed Schema**: All frames validated against JSON Schema (TypeBox)
- **Handshake**: First frame must be a `connect` message with role + scope

#### Connection Example

```json
// Client → Gateway: connect handshake
{
  "type": "connect",
  "role": "client",
  "scope": "agent",
  "metadata": {
    "source": "cartorio-backend",
    "version": "1.0.0"
  }
}

// Gateway → Client: connected acknowledgment
{
  "type": "connected",
  "sessionId": "uuid-session-id",
  "capabilities": ["agent", "presence", "health"]
}
```

#### Sending a message to OpenClaw agent

```json
// Client → Gateway: send message to agent
{
  "type": "send",
  "channel": "agent",
  "payload": {
    "text": "Qual o status do protocolo 12345?",
    "context": {
      "remoteJid": "5531999999999@s.whatsapp.net",
      "pushName": "João da Silva",
      "conversationId": "uuid-conversation"
    }
  }
}

// Gateway → Client: agent response
{
  "type": "message",
  "channel": "agent",
  "payload": {
    "text": "O protocolo 12345 está em andamento...",
    "tools_used": ["consultar_protocolo"],
    "confidence": 0.95
  }
}
```

### Integration Strategy for Cartório

**Option A (Recommended for Sprint 1)**: Direct FastAPI → LLM
- FastAPI receives Evolution webhook
- FastAPI calls LiteLLM directly
- FastAPI sends response via Evolution `/message/sendText`
- Simpler, fewer moving parts

**Option B (Sprint 3+)**: FastAPI → OpenClaw → LLM
- FastAPI receives Evolution webhook
- FastAPI connects to OpenClaw Gateway via WebSocket
- OpenClaw manages agent context, memory, tool execution
- Response flows back through FastAPI → Evolution
- More powerful for complex multi-tool agent scenarios

> [!TIP]
> Start with Option A for Sprint 1. OpenClaw adds value when you need persistent agent memory, tool orchestration, and multi-channel routing — plan this for Sprint 3.

---

## 8. n8n Integration

### 8.1 Community Node

There is an **Evolution API community node** for n8n:
- Install via n8n Settings → Community Nodes
- Package: `n8n-nodes-evolution-api` (or similar)
- Requires self-hosted n8n (does not work on n8n Cloud)

### 8.2 Webhook-Based Integration (Recommended)

For maximum flexibility, use n8n's native Webhook node:

#### Step 1: Create n8n Webhook Node

In n8n, create a workflow starting with a Webhook node:
- **Method**: POST
- **Path**: `/evolution/messages`
- **Full URL**: `https://cartorio-n8n.dfgdxq.easypanel.host/webhook/evolution/messages`

#### Step 2: Configure Evolution API Webhook

Point the Evolution API webhook to your n8n endpoint:

```bash
curl -X POST http://cartorio_evolution-api:8080/webhook/set/cartorio-whatsapp \
  -H "apikey: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook": {
      "enabled": true,
      "url": "https://cartorio-n8n.dfgdxq.easypanel.host/webhook/evolution/messages",
      "byEvents": false,
      "base64": false,
      "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
    }
  }'
```

#### Step 3: n8n Workflow Design

```
┌──────────────┐     ┌──────────────┐     ┌───────────────────┐
│ Webhook Node │ ──→ │ IF Node      │ ──→ │ HTTP Request Node │
│ (receive     │     │ (filter      │     │ (POST to FastAPI  │
│  Evolution   │     │  fromMe=false│     │  backend)         │
│  webhook)    │     │  + event=    │     │                   │
│              │     │  messages.   │     │                   │
│              │     │  upsert)     │     │                   │
└──────────────┘     └──────────────┘     └───────┬───────────┘
                                                   │
                                                   ▼
                     ┌──────────────┐     ┌───────────────────┐
                     │ HTTP Request │ ←── │ Process Response  │
                     │ (POST to     │     │ (format message   │
                     │  Evolution   │     │  for WhatsApp)    │
                     │  sendText)   │     │                   │
                     └──────────────┘     └───────────────────┘
```

#### n8n Workflow JSON (Reference)

```json
{
  "nodes": [
    {
      "name": "Evolution Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "evolution/messages",
        "responseMode": "lastNode"
      }
    },
    {
      "name": "Filter Incoming",
      "type": "n8n-nodes-base.if",
      "position": [450, 300],
      "parameters": {
        "conditions": {
          "boolean": [
            {
              "value1": "={{ $json.data.key.fromMe }}",
              "value2": false
            }
          ],
          "string": [
            {
              "value1": "={{ $json.event }}",
              "value2": "messages.upsert"
            }
          ]
        }
      }
    },
    {
      "name": "Call FastAPI Backend",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300],
      "parameters": {
        "url": "http://cartorio-backend:8000/api/v1/webhook/evolution",
        "method": "POST",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "body",
              "value": "={{ JSON.stringify($json) }}"
            }
          ]
        }
      }
    }
  ]
}
```

### 8.3 Environment Configuration for n8n

Set in n8n's environment or Easypanel:

```env
# Evolution API connection
EVOLUTION_API_URL=http://cartorio_evolution-api:8080
EVOLUTION_API_KEY=your-instance-token

# FastAPI Backend
BACKEND_URL=http://cartorio-backend:8000
```

### 8.4 n8n vs Direct Webhook Decision

| Approach | Pros | Cons |
|----------|------|------|
| **n8n in the middle** | Visual workflow editor, easy to add logic, logging | Extra hop, latency, another service to maintain |
| **Direct Evolution → FastAPI** | Simpler, faster (fewer hops), less infra | Harder to debug, need to build routing in code |

> [!IMPORTANT]
> **Recommendation for Cartório**: Use **Direct Evolution → FastAPI** for Sprint 1 (simpler, faster). Use n8n for administrative workflows (notifications, reports, monitoring) rather than the critical message path.

---

## 9. Environment Variables Reference

### Evolution API `.env`

```env
# Server
SERVER_URL=https://cartorio-evolution-api.dfgdxq.easypanel.host
SERVER_PORT=8080

# Authentication
AUTHENTICATION_TYPE=apikey
AUTHENTICATION_API_KEY=your-strong-global-api-key-here

# Database (Postgres)
DATABASE_PROVIDER=postgresql
DATABASE_CONNECTION_URI=postgresql://user:pass@cartorio_evolution-api-db:5432/evolution

# Webhook (Global defaults)
WEBHOOK_GLOBAL_ENABLED=true
WEBHOOK_GLOBAL_URL=http://cartorio-backend:8000/api/v1/webhook/evolution
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false
WEBHOOK_EVENTS=MESSAGES_UPSERT,MESSAGES_UPDATE,CONNECTION_UPDATE,SEND_MESSAGE

# Cache
CACHE_REDIS_ENABLED=true
CACHE_REDIS_URI=redis://cartorio_redis:6379

# Instance defaults
DEL_INSTANCE=false
CONFIG_SESSION_PHONE_CLIENT=Cartorio-Bot
CONFIG_SESSION_PHONE_NAME=Chrome
```

### FastAPI Backend `.env`

```env
# Evolution API
EVOLUTION_API_URL=http://cartorio_evolution-api:8080
EVOLUTION_API_GLOBAL_KEY=your-strong-global-api-key-here
EVOLUTION_API_INSTANCE_TOKEN=your-instance-token-here
EVOLUTION_API_INSTANCE_NAME=cartorio-whatsapp

# Webhook security
WEBHOOK_SECRET=your-webhook-verification-secret
```

---

## 10. Cartório-Specific Configuration

### Recommended Instance Setup

```bash
# 1. Create instance with webhook pointing to FastAPI
curl -X POST http://cartorio_evolution-api:8080/instance/create \
  -H "apikey: $EVOLUTION_GLOBAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "cartorio-whatsapp",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true,
    "webhook": {
      "url": "http://cartorio-backend:8000/api/v1/webhook/evolution",
      "byEvents": false,
      "base64": false,
      "events": [
        "MESSAGES_UPSERT",
        "MESSAGES_UPDATE",
        "CONNECTION_UPDATE",
        "QRCODE_UPDATED"
      ]
    }
  }'

# 2. Save the returned instance token
# Response: { "hash": { "apikey": "SAVE_THIS_TOKEN" } }

# 3. Scan QR code from response to connect WhatsApp

# 4. Verify connection
curl -X GET http://cartorio_evolution-api:8080/instance/connectionStatus/cartorio-whatsapp \
  -H "apikey: $EVOLUTION_GLOBAL_KEY"
```

### FastAPI Webhook Endpoint Design

```python
# backend/app/api/v1/webhook.py

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional

router = APIRouter()

@router.post("/webhook/evolution")
async def evolution_webhook(
    request: Request,
    x_webhook_secret: Optional[str] = Header(None)
):
    """
    Receives webhook events from Evolution API.
    Handles: MESSAGES_UPSERT, CONNECTION_UPDATE, etc.
    """
    # 1. Verify webhook secret
    if x_webhook_secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payload = await request.json()
    event = payload.get("event")
    instance = payload.get("instance")
    data = payload.get("data", {})

    # 2. Route by event type
    if event == "messages.upsert":
        return await handle_incoming_message(data)
    elif event == "connection.update":
        return await handle_connection_update(data)
    else:
        return {"status": "ignored", "event": event}


async def handle_incoming_message(data: dict):
    """Process incoming WhatsApp message."""
    key = data.get("key", {})
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", True)

    # Skip messages sent by us
    if from_me:
        return {"status": "skipped", "reason": "fromMe"}

    # Skip group messages (for now)
    if "@g.us" in remote_jid:
        return {"status": "skipped", "reason": "group"}

    # Extract phone number
    phone = remote_jid.replace("@s.whatsapp.net", "")

    # Extract message content
    message = data.get("message", {})
    push_name = data.get("pushName", "")

    # Determine message type and content
    if "conversation" in message:
        msg_type = "text"
        content = message["conversation"]
    elif "extendedTextMessage" in message:
        msg_type = "text"
        content = message["extendedTextMessage"]["text"]
    elif "imageMessage" in message:
        msg_type = "image"
        content = message["imageMessage"]
    elif "documentMessage" in message:
        msg_type = "document"
        content = message["documentMessage"]
    elif "audioMessage" in message:
        msg_type = "audio"
        content = message["audioMessage"]
    else:
        msg_type = "unknown"
        content = message

    # 3. Process through PII scrubber → LLM → Response
    # (Implementation in conversation service)

    return {
        "status": "processed",
        "phone": phone,
        "type": msg_type,
        "pushName": push_name
    }
```

### Response Helper (Sending via Evolution)

```python
# backend/app/services/whatsapp.py

import httpx
from app.core.config import settings

class WhatsAppService:
    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.instance = settings.EVOLUTION_API_INSTANCE_NAME
        self.headers = {
            "apikey": settings.EVOLUTION_API_INSTANCE_TOKEN,
            "Content-Type": "application/json"
        }

    async def send_text(self, phone: str, text: str) -> dict:
        """Send a text message via Evolution API."""
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {"number": phone, "text": text}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def send_document(self, phone: str, file_url: str,
                            filename: str, caption: str = "") -> dict:
        """Send a PDF document via Evolution API."""
        url = f"{self.base_url}/message/sendMedia/{self.instance}"
        payload = {
            "number": phone,
            "mediatype": "document",
            "mimetype": "application/pdf",
            "media": file_url,
            "fileName": filename,
            "caption": caption
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def send_image(self, phone: str, image_url: str,
                         caption: str = "") -> dict:
        """Send an image via Evolution API."""
        url = f"{self.base_url}/message/sendMedia/{self.instance}"
        payload = {
            "number": phone,
            "mediatype": "image",
            "mimetype": "image/jpeg",
            "media": image_url,
            "caption": caption
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
```

---

## Quick Reference Card

### Endpoints Summary

| Action | Method | Endpoint | Auth |
|--------|--------|----------|------|
| Create instance | POST | `/instance/create` | Global Key |
| List instances | GET | `/instance/fetchInstances` | Global Key |
| Connection status | GET | `/instance/connectionStatus/{name}` | Global/Instance |
| Get QR code | GET | `/instance/connect/{name}` | Global Key |
| Delete instance | DELETE | `/instance/delete/{name}` | Global Key |
| Set webhook | POST | `/webhook/set/{name}` | Instance Token |
| Get webhook | GET | `/webhook/find/{name}` | Instance Token |
| Send text | POST | `/message/sendText/{name}` | Instance Token |
| Send media | POST | `/message/sendMedia/{name}` | Instance Token |

### Internal Network (Docker)

| Service | Internal URL |
|---------|-------------|
| Evolution API | `http://cartorio_evolution-api:8080` |
| FastAPI Backend | `http://cartorio-backend:8000` |
| n8n | `http://cartorio-n8n:5678` |
| Postgres (Evolution) | `cartorio_evolution-api-db:5432` |
| Postgres (n8n) | `cartorio_n8n-db:5432` |

### External URLs (Easypanel)

| Service | External URL |
|---------|-------------|
| Evolution API | `https://cartorio-evolution-api.dfgdxq.easypanel.host` |
| n8n | `https://cartorio-n8n.dfgdxq.easypanel.host` |
| OpenClaw Gateway | `wss://cartorio-openclaw-gateway.dfgdxq.easypanel.host` |
| FastAPI Backend | `https://cartorio-backend.dfgdxq.easypanel.host` |
