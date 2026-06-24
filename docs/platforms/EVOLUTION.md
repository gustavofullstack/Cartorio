# Evolution API — Cartório 2º Ofício

> **Gateway WhatsApp Business** (multi-instância, webhooks, REST Baileys).
> Self-hosted (LGPD art. 33). Imagem: `atendai/evolution-api:v2.x`.

## Status atual (2026-06-24)

| Campo | Valor |
|---|---|
| Container | `cartorio_evolution-api` |
| Up time | 16h (healthy) |
| URL pública | `https://whatsapp.2notasudi.com.br` (Traefik) |
| URL manager | `https://whatsapp.2notasudi.com.br/manager` |
| Versão | Evolution API v2.x |
| API key global | `429683C4C977415CAAFCCE10F7D57E11` |
| Instância | `cartorio-2notas` (`state=close`, `connectionStatus=connecting`) |
| Webhook | `https://flow.2notasudi.com.br/webhook/evo-in` (5 eventos) |
| DB | 37 tabelas (instance metadata + chats + messages) |
| Pendência | WhatsApp não pareado — escanear QR em `/manager` |

## Endpoints consumidos

| Método | Path | Auth | Descrição |
|---|---|---|---|
| POST | `/instance/create` | apikey | Cria instância WhatsApp |
| GET | `/instance/connect/{instance}` | apikey | Retorna QR code (base64) |
| GET | `/instance/connectionState/{instance}` | apikey | Status open/close/connecting |
| POST | `/message/sendText/{instance}` | apikey | Envia mensagem de texto |
| POST | `/webhook/set/{instance}` | apikey | Configura webhook de eventos |
| GET | `/webhook/find/{instance}` | apikey | Lista webhooks da instância |

**Auth**: header `apikey: $EVOLUTION_API_KEY` (todas as chamadas).

## Integrações ativas

- **N8N** → workflow `evo-in` (id `I4LkReuiurPBS9VN`) recebe webhooks (MESSAGES_UPSERT, MESSAGES_UPDATE, CONNECTION_UPDATE, QRCODE_UPDATED, MESSAGES_DELETE)
- **API FastAPI** → expõe `/api/v1/webhook/evolution` (HMAC + idempotência por message_id)
- **Chatwoot** → Inbox WhatsApp (independente, via Baileys direto, sem ponte Evolution)
- **OpenClaw** → NÃO usa Evolution direto (passa pela API)
- **Supabase** → tabela `evolution_instance` (metadata persistido)
- **Redis** → idempotency-key (SETNX 24h) + rate-limit + métricas

## Tabelas / Schemas / Workflows

- **DB Evolution** (Postgres interno): 37 tabelas (`Instance`, `Chat`, `Message`, `Contact`, `Webhook`, `Session`, `Baileys_*`)
- **N8N workflow** `evo-in.json` (em `infra/n8n-workflows/`) — 3 versões (template → header→credential → body simples)
- **DB cartorio**: tabela `evolution_instance` (Sprint 3 B0.2)
- **DB cartorio**: tabela `webhook_event` (audit log eventos Evolution)

## Problemas conhecidos + fixes aplicados

- **Instance `cartorio-2notas` state=close** → WhatsApp não pareado. Fix: escanear QR em `/manager` (pendente Gustavo)
- **N8N bloqueia `$env` em expressions** (`N8N_BLOCK_ENV_ACCESS_IN_NODE=true`) → usar credentials (id `ADNkyTP2e6uYskUZ` = `cartorio-api-key`)
- **E2E Evolution → N8N → API reporta "error" cosmetic** → API retorna 200 (logs confirmam). Fix: cosmetic no N8N
- **WEBHOOK_GLOBAL_URL vazio** no container Evolution → usar `webhook/set/{instance}` por instância
- **N8N restart loop silencioso** (7 containers em 2h) → OOM. Fix pendente: aumentar memory limits

## Próximas tasks (Squad B do plan 2026-06-24)

- **B01** Health-check + log últimas 100 mensagens
- **B02** Configurar 4 webhooks oficiais (upsert/update/connection/qrcode) com HMAC
- **B03** Retry+DLQ no consumer (3x backoff, persistente em outbox)
- **B04** send_message helper com idempotency-key (Redis SETNX 24h) + métricas
- **B05** Evolution client (httpx async) + tests
- **B06** Mapear eventos → filas N8N
- **B07** Validar 1 instância (cartorio-2notas) → mapping Chatwoot inbox
- **B08** Testar reconnect 5 cenários
- **B09** Documentação completa Evolution v2
- **B10** Postman collection completa

Ver plano completo: `.harness/reins/cartorio-dev/tasks/2026-06-24-plan.json` (Squad B).

