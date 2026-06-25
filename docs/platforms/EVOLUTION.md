# Evolution API — Cartório 2º Ofício

> **Gateway WhatsApp Business** (multi-instância, webhooks, REST sobre Baileys).
> Self-hosted (LGPD art. 33 — dado não sai do VPS). Container Docker:
> `cartorio_evolution-api.1.gze9s5djmxhxd1x96ht843oly` (imagem `evoapicloud/evolution-api:latest`).

## Status atual (2026-06-25 10:40 BRT)

| Campo | Valor |
|---|---|
| Container | `cartorio_evolution-api` (porta 8080) |
| Up time | 19h+ (healthy) |
| URL externa | `https://whatsapp.2notasudi.com.br` |
| Manager UI | `https://whatsapp.2notasudi.com.br/manager` |
| Versão | Evolution API v2.3.7 |
| API key global | `429683C4C977415CAAFCCE10F7D57E11` |
| Instância | `cartorio-2notas` (state=`close`, connectionStatus=`connecting`) |
| Webhook | `https://cartorio-n8n.dfgdxq.easypanel.host/webhook/evo-in` (5 eventos) |
| WhatsApp teste | TriQ Hub (conectado para testes) |
| DB | 37 tabelas (instance metadata + chats + messages + contatos) |
| Health | `GET /` → 200 OK (222ms via health/integracoes) |

## Arquitetura

```
WhatsApp (TriQ Hub / futuro número real)
    │
    ▼
Evolution API (gateway) ───→ N8N (evo-in workflow)
    │                              │
    │                         POST /api/v1/webhook/evolution
    │                              │
    │                         API FastAPI (HMAC + idempotência)
    │                              │
    │                         Supabase (webhook_events) + Redis (idempotency)
    │
    └──→ DB interno (37 tabelas: Instance, Chat, Message, Contact, Session, Baileys_*)
```

## Endpoints da API

### Instância

| Método | Path | Descrição |
|---|---|---|
| POST | `/instance/create` | Cria nova instância WhatsApp |
| POST | `/instance/connect/{instance}` | Retorna QR code (base64) para pareamento |
| GET | `/instance/connectionState/{instance}` | Status: `open` / `close` / `connecting` |
| DELETE | `/instance/delete/{instance}` | Remove instância e dados |
| GET | `/instance/fetchInstances` | Lista todas instâncias |

### Mensagens

| Método | Path | Descrição |
|---|---|---|
| POST | `/message/sendText/{instance}` | Envia mensagem de texto |
| POST | `/message/sendMedia/{instance}` | Envia mídia (imagem/áudio/video/documento) |
| POST | `/message/sendButtons/{instance}` | Envia botões interativos |
| POST | `/message/sendList/{instance}` | Envia lista de opções |

### Webhook

| Método | Path | Descrição |
|---|---|---|
| POST | `/webhook/set/{instance}` | Configura webhook de eventos |
| GET | `/webhook/find/{instance}` | Lista webhooks configurados |
| DELETE | `/webhook/clear/{instance}` | Remove webhooks |

### Eventos do Webhook

| Evento | Dispara quando | Ação no N8N |
|---|---|---|
| `MESSAGES_UPSERT` | Nova mensagem recebida | Processa mensagem → API |
| `MESSAGES_UPDATE` | Mensagem atualizada (lida, entregue) | Atualiza status |
| `CONNECTION_UPDATE` | Estado da conexão muda | Alerta se `close` |
| `QRCODE_UPDATED` | Novo QR gerado | Encaminha para admin |
| `MESSAGES_DELETE` | Mensagem apagada | Audit log |

## Webhook Flow

```
Evolution API → POST → N8N (evo-in)
                        → POST /api/v1/webhook/evolution (HMAC)
                        → Valida HMAC → Idempotência Redis → Processa → Audit log
```

**Auth**: header `apikey: $EVOLUTION_API_KEY` em todas as chamadas REST.

## Integrações

| Serviço | Tipo | Detalhes |
|---|---|---|
| **N8N** | Workflow | `infra/n8n-workflows/evo-in.json` (3 versões: template → header→credential → body simples) |
| **API FastAPI** | Endpoint | `POST /api/v1/webhook/evolution` (HMAC SHA256 + idempotência por `message_id`) |
| **Supabase** | DB | Tabela `webhook_events` (audit log) + `evolution_instance` (metadata) |
| **Redis** | Cache | Idempotency key SETNX 24h + rate-limit + métricas |
| **Chatwoot** | CRM | Inbox WhatsApp (independe do Evolution — via Baileys direto) |

## WhatsApp TriQ Hub (testes)

Uma conta WhatsApp da TriQ Hub está conectada para testes E2E.
O fluxo completo é:
1. Enviar mensagem para o número TriQ Hub
2. Evolution API recebe → webhook → N8N → API → resposta
3. Resposta volta pela cadeia inversa

**Instance state atual**: `close` (aguardando QR scan do número Business oficial)

## Troubleshooting

### Instance state=close
```bash
# Verificar estado
curl -s -H "apikey: $EVOLUTION_API_KEY" \
  https://whatsapp.2notasudi.com.br/instance/connectionState/cartorio-2notas
```
**Solução**: Gustavo escanear QR em `https://whatsapp.2notasudi.com.br/manager`

### Webhook não chegando no N8N
```bash
# Verificar webhook configurado
curl -s -H "apikey: $EVOLUTION_API_KEY" \
  https://whatsapp.2notasudi.com.br/webhook/find/cartorio-2notas
```
**Causa comum**: `WEBHOOK_GLOBAL_URL` vazio no container Evolution.
**Fix**: Usar `webhook/set/{instance}` por instância (não global).

### N8N restart loop
**Causa**: OOM (Out of Memory) — 7 containers em 2h.
**Fix pendente**: Aumentar memory limits no Easypanel.

### Health check
O monitoramento integrado verifica a cada 5min via systemd timer:
```
cartorio-evolution-health.timer → cartorio-evolution-health.service
```

## Referências

- Docker: `cartorio_evolution-api` (porta 8080, Traefik SSL)
- Workflow N8N: `infra/n8n-workflows/evo-in.json`
- Manager UI: `https://whatsapp.2notasudi.com.br/manager`
- Documentação oficial: `docs/platforms/EVOLUTION_API.md` (215 linhas)
- Config VPS: `/etc/easypanel/projects/cartorio/evolution-api/`
- Lesson 51: `N8N_BLOCK_ENV_ACCESS_IN_NODE` trap
