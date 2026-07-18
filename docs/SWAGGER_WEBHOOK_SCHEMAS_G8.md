# Webhook Receiver Schemas — Swagger Documentation (G8.17.T2)

**Task**: `G8.17.T2` — Documentar schemas de payload detalhados para todos os
webhooks no Swagger.

**Status**: ✅ Done (commit `32e0204` + `0af92a9`)

---

## Visão geral

Todos os 5+ webhooks receivers do backend agora têm schemas Pydantic v2
**completamente documentados** no `/openapi.json` (Swagger UI). Cada campo tem
uma `description` humanamente útil em PT-BR, exemplos de payload realistas,
e campos com PII são explicitamente marcados com `**LGPD PII**` para tools
de revisão automática.

## Webhooks cobertos

| Webhook | Path | Schema Pydantic | Tags OpenAPI |
|---------|------|-----------------|--------------|
| Telegram Bot API | `POST /api/v1/telegram/webhook` | `TelegramUpdate` | `telegram` |
| Evolution API (WhatsApp) | `POST /api/v1/whatsapp/webhook` | `EvolutionPayload` | `whatsapp` |
| Chatwoot CRM | `POST /api/v1/webhook/chatwoot` | `ChatwootWebhookModel` | `webhook` |
| Evolution (legacy path) | `POST /api/v1/webhook/evolution` | `EvolutionPayload` | `webhook` |
| N8N Error Workflow | `POST /api/v1/integrations/n8n/error` | `N8nErrorRequest` | `meta` |
| N8N Deletion Log | `POST /api/v1/integrations/n8n/deletion` | `N8nDeletionRequest` | `meta` |
| N8N Metrics Ingest | `POST /api/v1/integrations/n8n/metrics` | `N8nMetricsIngest` | `meta` |
| AlertManager default | `POST /api/v1/webhook/alertmanager` | `AlertManagerPayload` | `alertmanager` |
| AlertManager critical | `POST /api/v1/webhook/alertmanager/critical` | `AlertManagerPayload` | `alertmanager` |
| AlertManager DLQ | `POST /api/v1/webhook/alertmanager/dlq` | `AlertManagerPayload` | `alertmanager` |
| AlertManager LGPD | `POST /api/v1/webhook/alertmanager/lgpd` | `AlertManagerPayload` | `alertmanager` |
| AlertManager N8N | `POST /api/v1/webhook/alertmanager/n8n` | `AlertManagerPayload` | `alertmanager` |
| Supabase Outbox | `POST /api/v1/integrations/outbox/dispatch` | `OutboxDispatchRequest` | `meta` |

Total: **5 webhooks principais** (Telegram, Evolution, Chatwoot, N8N, AlertManager)
+ 1 derivado (Supabase Outbox).

## Arquivos criados / modificados

| Arquivo | Tipo | LOC | Conteúdo |
|---------|------|-----|----------|
| `backend/app/services/pii_marker.py` | novo | 119 | `PIIField`, `is_pii_field`, `collect_pii_paths` |
| `backend/app/schemas/webhook_payloads.py` | novo | 756 | Telegram/Evolution/N8N/Outbox + re-exports |
| `backend/app/schemas/webhook_alertmanager.py` | novo | 264 | AlertManager retro-documentado (G8.15.T2 enhance) |
| `backend/app/schemas/chatwoot_webhook.py` | modified | 199 | `Field(description=...)` em 100% dos campos |
| `backend/app/api/v1/alertmanager.py` | modified | -5/+3 | reusa schemas de `webhook_alertmanager` |
| `backend/app/api/v1/telegram.py` | modified | +60 | `openapi_extra` com 3 examples (text/cb/group) |
| `backend/app/api/v1/whatsapp.py` | modified | +50 | `openapi_extra` com 2 examples (nested/legacy) |
| `backend/app/api/v1/router.py` | modified | +50 | `Body(examples=)` webhook/evolution + chatwoot |
| `backend/app/middleware/openapi_enhancer.py` | modified | +50 | `_register_webhook_schemas` force-register |
| `backend/tests/test_webhook_schemas_g8.py` | novo | 619 | 18 tests cobrindo serialization, PII marker, OpenAPI |
| **TOTAL** | — | **~2.165** | — |

## LGPD: marker `**LGPD PII**`

Todo campo com dado pessoal recebe **automaticamente** o prefixo `**LGPD PII**`
na sua `description`. Isso permite que ferramentas externas (LGPD scanner,
OpenAPI lint, audit reviewers) detectem e filtrem/redatem PII sem precisar
introspecção manual.

Exemplo de output no Swagger UI:

```
text: string
  Texto plain-text da mensagem (LGPD PII: pode conter CPF/RG/nome).
  Max length: 4096
```

vs campo sem PII:

```
message_id: integer
  ID unico da mensagem dentro do chat.
  Greater than or equal to 1
```

### Helper: `collect_pii_paths(model)`

Coleta os paths JSON pointer-like dos campos PII de um schema. Útil para
popular a OpenAPI extension `x-pii-fields` em endpoints que recebem esse schema.

```python
from app.services.pii_marker import collect_pii_paths
from app.schemas.webhook_payloads import TelegramUpdate

paths = collect_pii_paths(TelegramUpdate)
# ['message', 'edited_message', 'callback_query']
```

### Helper: `PIIField(...)`

Wrapper sobre `pydantic.Field` que injeta `**LGPD PII**` no início da
description e adiciona `x-pii: True` no `json_schema_extra` (exportado como
OpenAPI extension para LGPD scanners).

```python
from app.services.pii_marker import PIIField
from typing import Annotated
from pydantic import BaseModel

class User(BaseModel):
    cpf: Annotated[str, PIIField(description="CPF do cliente (11 digits)")]
    name: Annotated[str, PIIField(description="Nome completo")]
```

## Exemplos curl copiáveis

### 1. Telegram webhook (3 examples: text/callback/group)

```bash
# Text message privado
curl -X POST 'https://api.2notasudi.com.br/api/v1/telegram/webhook' \
  -H 'Content-Type: application/json' \
  -H 'X-Telegram-Bot-Api-Secret-Token: $TELEGRAM_WEBHOOK_SECRET' \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 42,
      "date": 1721308800,
      "from": {"id": 987654321, "first_name": "Maria", "username": "mariacliente"},
      "chat": {"id": 987654321, "type": "private"},
      "text": "Quero agendar uma procuração amanhã"
    }
  }'

# Callback query (botão inline)
curl -X POST 'https://api.2notasudi.com.br/api/v1/telegram/webhook' \
  -H 'Content-Type: application/json' \
  -H 'X-Telegram-Bot-Api-Secret-Token: $TELEGRAM_WEBHOOK_SECRET' \
  -d '{
    "update_id": 123456790,
    "callback_query": {
      "id": "cb_abc123",
      "from": {"id": 987654321, "first_name": "Maria"},
      "chat_instance": "chat_inst_xyz",
      "data": "cmd:agendar",
      "message": {"message_id": 41, "date": 1721308500, "chat": {"id": 987654321, "type": "private"}}
    }
  }'

# Comando em grupo (supergroup)
curl -X POST 'https://api.2notasudi.com.br/api/v1/telegram/webhook' \
  -H 'Content-Type: application/json' \
  -H 'X-Telegram-Bot-Api-Secret-Token: $TELEGRAM_WEBHOOK_SECRET' \
  -d '{
    "update_id": 123456791,
    "message": {
      "message_id": 50,
      "date": 1721308900,
      "from": {"id": 111, "first_name": "João"},
      "chat": {"id": -1004331849032, "type": "supergroup", "title": "Clientes Cartório"},
      "text": "/menu"
    }
  }'
```

### 2. Evolution API (WhatsApp) — dual-format

```bash
# Formato nested moderno
curl -X POST 'https://api.2notasudi.com.br/api/v1/whatsapp/webhook' \
  -H 'Content-Type: application/json' \
  -H 'X-Hub-Signature-256: sha256=<HMAC>' \
  -d '{
    "event": "messages.upsert",
    "instance": "cartorio-2notas",
    "data": {
      "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": false, "id": "MSG_001"},
      "message": {"conversation": "Quanto custa autenticação?"},
      "messageType": "conversation",
      "pushName": "Maria Cliente"
    }
  }'

# Formato root-level legado
curl -X POST 'https://api.2notasudi.com.br/api/v1/whatsapp/webhook' \
  -H 'Content-Type: application/json' \
  -H 'X-Hub-Signature-256: sha256=<HMAC>' \
  -d '{
    "message": {"conversation": "Quero agendar"},
    "sender": "553499999999",
    "instance": "cartorio-2notas"
  }'
```

### 3. Chatwoot webhook

```bash
# conversation_status_changed (HITL close)
curl -X POST 'https://api.2notasudi.com.br/api/v1/webhook/chatwoot' \
  -H 'Content-Type: application/json' \
  -H 'X-Chatwoot-Signature: <HMAC>' \
  -d '{
    "event": "conversation_status_changed",
    "id": 42,
    "status": "resolved",
    "conversation": {"id": 42, "status": "resolved"},
    "assignee": {"id": 7, "name": "Escrevente"}
  }'

# message_created (nova mensagem)
curl -X POST 'https://api.2notasudi.com.br/api/v1/webhook/chatwoot' \
  -H 'Content-Type: application/json' \
  -H 'X-Chatwoot-Signature: <HMAC>' \
  -d '{
    "event": "message_created",
    "id": 99,
    "message_id": 999,
    "message_type": "incoming",
    "content": "Quero falar com um humano",
    "conversation": {"id": 42, "status": "open"}
  }'
```

### 4. N8N Error Workflow

```bash
curl -X POST 'https://api.2notasudi.com.br/api/v1/integrations/n8n/error' \
  -H 'Content-Type: application/json' \
  -H 'X-N8N-Signature: sha256=<HMAC>' \
  -d '{
    "workflow_name": "01 - Consulta Emolumento",
    "workflow_id": "wf_abc123",
    "execution_id": "exec_xyz789",
    "error_type": "http_5xx",
    "error": {"name": "HTTPError", "message": "Upstream timeout", "http_code": 504},
    "node": "HTTP Request",
    "timestamp": "2026-07-18T12:34:56Z"
  }'
```

### 5. AlertManager (P0 critical)

```bash
curl -X POST 'https://api.2notasudi.com.br/api/v1/webhook/alertmanager/critical' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: $CARTORIO_API_KEY' \
  -d '{
    "version": "4",
    "groupKey": "{}:{alertname=\"API5xxSpike\"}",
    "status": "firing",
    "receiver": "cartorio-telegram-critical",
    "groupLabels": {"alertname": "API5xxSpike"},
    "commonLabels": {"severity": "critical", "squad": "cartorio-sre"},
    "commonAnnotations": {"summary": "API 5xx rate=15%"},
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "API5xxSpike", "severity": "critical", "instance": "cartorio-api-1:8000", "squad": "cartorio-sre"},
      "annotations": {"summary": "API 5xx > 10%", "description": "Endpoint /api/v1/protocolo", "runbook_url": "https://runbooks.2notasudi.com.br/5xx"},
      "startsAt": "2026-07-18T12:00:00Z",
      "fingerprint": "abc123def456"
    }]
  }'
```

## Validação

| Check | Comando | Resultado |
|-------|---------|-----------|
| Schema imports | `python -c "from app.schemas.webhook_payloads import ..."` | OK |
| Lint | `uv run ruff check app/schemas/ app/api/v1/...` | 0 errors |
| Typecheck | `uv run mypy app/schemas/...` | 0 errors |
| Tests | `uv run pytest tests/test_webhook_schemas_g8.py --no-cov` | **18 passed** |
| Webhook tests (full) | `pytest tests/test_*webhook* tests/test_*alert* ...` | 95 passed |
| Full suite | `uv run pytest --no-cov` | **4028 passed**, 0 failed |
| OpenAPI spec | `curl https://api.2notasudi.com.br/openapi.json` | 18 webhook schemas com 100% descriptions |

## LGPD: lista de campos com PII por webhook

### TelegramUpdate
- `message.from` (TelegramUser.id, first_name, last_name, username)
- `message.sender_chat` (TelegramChat.id)
- `message.chat` (TelegramChat.id)
- `message.text` (texto plain)
- `message.caption` (legenda de mídia)
- `edited_message` (mesmos campos)
- `callback_query.from` (TelegramUser)
- `callback_query.message`

### EvolutionPayload
- `data` (contém key.remoteJid + message.conversation)
- `key` (root-level legado)
- `message` (root-level legado)
- `sender` (phone number)
- `push_name` (WhatsApp profile name)

### ChatwootWebhookModel
- `assignee.name` / `assignee.email` (HITL)
- `content` (mensagem do cliente)
- `sender` (dict com name/email/phone)

### N8nErrorRequest
- `error.message` (pode vazar paths/dados sensíveis em stack traces)

### AlertManagerPayload
- `alerts[].annotations.summary` / `description` (podem conter dados injetados por engano)

### OutboxDispatchRequest
- `recipient_id` (phone/email/chat_id)
- `content` (texto da mensagem)

## Modified by Gustavo Almeida

Commit:
- `32e0204` — wire webhook schemas nos endpoints + force-register no OpenAPI
- `0af92a9` — webhook schemas Pydantic + LGPD PII marker (initial)

Lesson: `.harness/memory/lesson-240-g8-17-t2-swagger-schemas-2026-07-18.md`
