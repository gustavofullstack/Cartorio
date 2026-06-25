# Integration Guide — Cartório Chatbot

> Guia completo de integração com serviços externos.
> Última atualização: 2026-06-26.

## TL;DR

**Integrações ativas** (8 serviços):
1. Evolution API v2.3.7 (WhatsApp)
2. OpenClaw Gateway (Agent AI)
3. Chatwoot (CRM)
4. Supabase (DB + Auth + Storage)
5. Redis (Cache)
6. N8N (Workflows)
7. Telegram Bot (notificações)
8. Traefik (reverse proxy)

**Padrão de integração**: API-first + Webhook + Retry 3x exp backoff + X-Correlation-ID.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Evolution API (WhatsApp)](#2-evolution-api-whatsapp)
3. [OpenClaw Gateway (Agent AI)](#3-openclaw-gateway-agent-ai)
4. [Chatwoot (CRM)](#4-chatwoot-crm)
5. [Supabase (DB + Auth)](#5-supabase-db--auth)
6. [Redis (Cache)](#6-redis-cache)
7. [N8N (Workflows)](#7-n8n-workflows)
8. [Telegram Bot](#8-telegram-bot)
9. [Padrões de Integração](#9-padrões-de-integração)
10. [Adicionando Nova Integração](#10-adicionando-nova-integração)

---

## 1. Visão Geral

### 1.1 Mapa de Integrações

```
┌─────────────────────────────────────────┐
│ Cliente WhatsApp                        │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│ Evolution API v2.3.7                    │
│ whatsapp.2notasudi.com.br               │
└────────────┬────────────────────────────┘
             │ Webhook (MESSAGES_UPSERT)
             ▼
┌─────────────────────────────────────────┐
│ N8N Workflow Engine                     │
│ flow.2notasudi.com.br                   │
│ 34 WFs ativos                           │
└────────────┬────────────────────────────┘
             │ REST
             ▼
┌─────────────────────────────────────────┐
│ FastAPI v0.6.0                          │
│ api.2notasudi.com.br                    │
│ 58 endpoints                            │
└────┬────────┬────────┬────────┬─────────┘
     │        │        │        │
     ▼        ▼        ▼        ▼
┌─────┐  ┌──────┐ ┌───────┐ ┌──────────┐
│Supa │  │Redis │ │OpenClaw│ │ Chatwoot │
│base │  │      │ │Pietra  │ │   CRM    │
└─────┘  └──────┘ └───────┘ └──────────┘
```

### 1.2 Padrões Comuns

Todas as integrações seguem:

```
✅ API-first (REST ou WS)
✅ Autenticação (API Key, JWT, OAuth)
✅ Webhook para eventos assíncronos
✅ Retry 3x exp backoff (1s, 5s, 15s)
✅ Timeout (5s/10s)
✅ X-Correlation-ID em todas requests
✅ Logs JSON estruturados
✅ Métricas Prometheus (count, latency, errors)
✅ Circuit breaker (futuro)
✅ Health check periódico
```

---

## 2. Evolution API (WhatsApp)

### 2.1 Configuração

| Item | Valor |
|------|-------|
| **Versão** | v2.3.7 |
| **URL** | https://whatsapp.2notasudi.com.br |
| **Manager UI** | https://whatsapp.2notasudi.com.br/manager |
| **Instância** | `cartorio-2notas` |
| **API Key** | (em `/etc/easypanel/projects/cartorio/evolution-api/.env`) |
| **Webhook** | https://flow.2notasudi.com.br/webhook/evo-in |

### 2.2 Endpoints Principais

```bash
# Conectar instância (QR code)
POST /instance/connect/{instance_name}
# Response: { "code": "base64-qr-code", "base64": true }

# Status da conexão
GET /instance/connectionState/{instance_name}
# Response: { "instance": {...}, "state": "open" | "close" }

# Enviar mensagem de texto
POST /message/sendText/{instance_name}
Body: { "number": "5534999999999", "text": "Olá" }

# Enviar mídia
POST /message/sendMedia/{instance_name}
Body: { "number": "...", "mediatype": "image", "media": "url", "fileName": "doc.pdf" }

# Ver mensagens (apenas admin)
POST /chat/findMessages/{instance_name}
Body: { "where": { "key.remoteJid": "...s.whatsapp.net" } }
```

### 2.3 Webhook Configurado

```bash
# Setar webhook
POST /webhook/set/{instance_name}
{
  "url": "https://flow.2notasudi.com.br/webhook/evo-in",
  "enabled": true,
  "events": [
    "MESSAGES_UPSERT",     # Nova mensagem
    "MESSAGES_UPDATE",      # Status update (lida, entregue)
    "SEND_MESSAGE",         # Mensagem enviada
    "CONNECTION_UPDATE",    # Status da conexão
    "CALL"                  # Chamadas (futuro)
  ],
  "webhookByEvents": false,
  "webhookBase64": false
}
```

### 2.4 Integração com API (Backend)

```python
# backend/app/services/evolution.py
import httpx
from typing import Any

class EvolutionClient:
    def __init__(self):
        self.base_url = settings.evolution_url
        self.api_key = settings.evolution_api_key
        self.instance = "cartorio-2notas"
    
    async def send_text(
        self,
        number: str,
        text: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Envia mensagem de texto via WhatsApp."""
        headers = {
            "apikey": self.api_key,
            "X-Correlation-ID": correlation_id or str(uuid.uuid4()),
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers=headers,
                json={"number": number, "text": text},
            )
            response.raise_for_status()
            return response.json()
    
    async def get_connection_state(self) -> str:
        """Retorna 'open' ou 'close'."""
        headers = {"apikey": self.api_key}
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{self.base_url}/instance/connectionState/{self.instance}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()["instance"]["state"]
```

### 2.5 Troubleshooting

```bash
# Instance desconectada
curl -fsS "https://whatsapp.2notasudi.com.br/instance/connectionState/cartorio-2notas" \
  -H "apikey: $EVO_KEY"
# Se state=close: SUI Gustavo escanear QR

# Webhook não dispara
curl -fsS "https://whatsapp.2notasudi.com.br/webhook/find/cartorio-2notas" \
  -H "apikey: $EVO_KEY"

# Logs
ssh vps-cartorio "docker service logs cartorio_evolution-api --tail 100"
```

---

## 3. OpenClaw Gateway (Agent AI)

### 3.1 Configuração

| Item | Valor |
|------|-------|
| **URL** | https://agent.2notasudi.com.br |
| **Agent ID** | `main` |
| **Modelo** | `deepseek-v4-flash` (1M ctx) |
| **Provider** | OpenCode-Go |
| **Base URL** | https://opencode.ai/zen/go/v1 |
| **API Key** | `sk-xcRwExjQjqmlc5swP8umqK2YqWUfVt23H3Xl6dpd9TqEyi16ssJXzHeUFGNNIfsJ` |
| **Thinking** | Adaptive ON (10k tokens) |
| **Skills** | 7 ativas |

### 3.2 Endpoints

```bash
# Health
GET /health
# Response: {"ok": true, "status": "live"}

# Listar agents
GET /v1/agents

# WebSocket (USAR)
WS /v1/chat
# Frames:
# Send: {"message": "...", "session_id": "...", "cliente_id": "..."}
# Recv: {"response": "...", "thinking": "...", "tools_called": [...]}

# HTTP (404 - NÃO USAR)
POST /v1/chat  # gateway.http schema rejeitado
```

### 3.3 Integração via WebSocket (Backend)

```python
# backend/app/services/openclaw_client.py
import websockets
import json
import uuid

class OpenClawClient:
    def __init__(self):
        self.url = settings.openclaw_ws_url  # wss://agent.2notasudi.com.br/v1/chat
    
    async def chat(
        self,
        message: str,
        session_id: str,
        cliente_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        """Envia mensagem para o Agent AI via WebSocket."""
        cid = correlation_id or str(uuid.uuid4())
        
        payload = {
            "message": message,
            "session_id": session_id,
            "cliente_id": cliente_id,
            "correlation_id": cid,
        }
        
        async with websockets.connect(self.url, timeout=30.0) as ws:
            await ws.send(json.dumps(payload))
            
            # Resposta única
            response_str = await ws.recv()
            response = json.loads(response_str)
            
            return response
    
    async def stream_chat(self, message: str, session_id: str):
        """Stream de tokens (futuro)."""
        async with websockets.connect(self.url, timeout=30.0) as ws:
            await ws.send(json.dumps({
                "message": message,
                "session_id": session_id,
                "stream": True
            }))
            
            async for msg in ws:
                yield json.loads(msg)
```

### 3.4 Skills Configuradas

```json
// /home/node/.openclaw/agents/main/agent/agent.json
{
  "skills": [
    {
      "name": "saudacoes",
      "description": "Boas-vindas e identificação do cliente",
      "triggers": ["olá", "oi", "bom dia", "boa tarde"],
      "handler": "saudacoes_handler"
    },
    {
      "name": "protocolo-tracker",
      "description": "Consultar e criar protocolos",
      "triggers": ["protocolo", "andamento", "status"],
      "handler": "protocolo_handler"
    },
    {
      "name": "emolumento-calc",
      "description": "Calcular emolumentos MG 2026",
      "triggers": ["emolumento", "valor", "preço", "quanto custa"],
      "handler": "emolumento_handler"
    },
    {
      "name": "agendamento",
      "description": "Agendar atendimento presencial",
      "triggers": ["agendar", "horário", "marcar"],
      "handler": "agendamento_handler"
    },
    {
      "name": "segunda-via",
      "description": "Solicitar segunda via de documentos",
      "triggers": ["segunda via", "cópia", "2 via"],
      "handler": "segunda_via_handler"
    },
    {
      "name": "lgpd-consent",
      "description": "Coletar consentimento LGPD",
      "triggers": ["consentimento", "lgpd", "dados"],
      "handler": "lgpd_handler"
    },
    {
      "name": "handoff-humano",
      "description": "Transferir para atendente humano",
      "triggers": ["atendente", "humano", "pessoa"],
      "handler": "handoff_handler"
    }
  ]
}
```

### 3.5 Troubleshooting

```bash
# Agent não responde
curl -fsS https://agent.2notasudi.com.br/health

# Contexto limitado
ssh vps-cartorio "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/models.json | jq '.providers.opencode_go.models[0].contextWindow'"
# Esperado: 1048576 (1M)

# Thinking OFF
ssh vps-cartorio "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json | jq '.thinking.enabled'"
# Esperado: true
```

---

## 4. Chatwoot (CRM)

### 4.1 Configuração

| Item | Valor |
|------|-------|
| **URL** | https://chat.2notasudi.com.br |
| **Admin Email** | admin@2notasudi.com.br |
| **Access Token** | (em env) |
| **Inbox WhatsApp** | Conectada via Evolution API |
| **Bot Agent** | pietra@2notasudi.com.br (Pietra) |

### 4.2 Endpoints Principais

```bash
# Headers
Authorization: Bearer <access_token>
api_access_token: <access_token>

# Listar contas
GET /api/v1/accounts

# Listar conversas
GET /api/v1/accounts/{account_id}/conversations
Params: ?status=open&assignee_id=...

# Listar agentes
GET /api/v1/accounts/{account_id}/agents

# Criar agente
POST /api/v1/accounts/{account_id}/agents
{
  "name": "Pietra Cartório",
  "email": "pietra@2notasudi.com.br",
  "role": "agent"
}

# Atribuir conversa
POST /api/v1/accounts/{account_id}/conversations/{id}/assignments
{
  "assignee_id": <agent_id>
}

# Toggle HITL (pausar bot)
POST /api/v1/accounts/{account_id}/conversations/{id}/custom_attributes
{
  "custom_attributes": { "bot_paused": true }
}
```

### 4.3 Webhook

```bash
# Webhook para eventos
POST /api/v1/accounts/{account_id}/webhooks
{
  "url": "https://api.2notasudi.com.br/webhook/chatwoot",
  "subscriptions": [
    "conversation_created",
    "conversation_status_changed",
    "message_created",
    "message_updated"
  ]
}
```

### 4.4 HITL (Human In The Loop)

```python
# backend/app/services/chatwoot.py
class ChatwootClient:
    async def pause_bot(self, conversation_id: int):
        """Pausa o bot em uma conversa."""
        await self._update_custom_attribute(
            conversation_id,
            "bot_paused",
            True
        )
        
        # Notificar API para parar de responder
        await self.redis.setex(
            f"chatwoot:bot_paused:{conversation_id}",
            86400,  # 24h TTL
            "1"
        )
    
    async def resume_bot(self, conversation_id: int):
        """Retoma o bot."""
        await self._update_custom_attribute(
            conversation_id,
            "bot_paused",
            False
        )
        await self.redis.delete(f"chatwoot:bot_paused:{conversation_id}")
    
    async def is_bot_paused(self, conversation_id: int) -> bool:
        """Verifica se bot está pausado."""
        return await self.redis.exists(f"chatwoot:bot_paused:{conversation_id}") > 0
```

### 4.5 Canned Responses & Macros

**52 templates jurídicos** em `infra/chatwoot/canned_responses_juridicos.md`:
- Protocolos (criação, consulta, status)
- Emolumentos (cálculo, tabela MG 2026)
- Agendamentos (slots, confirmação)
- Notariais (escritura, procuração, reconhecimento)
- LGPD (consentimento, direitos)
- Atendimento (saudação, despedida)
- Agent AI (transferência, status)
- Stats (relatórios)
- Utilidades (horário, endereço)

**10 macros de handoff** em `infra/chatwoot/macros_handoff_humano.md`:
- 3 transferência
- 2 identificação
- 2 resumo
- 3 pausa HITL

---

## 5. Supabase (DB + Auth)

### 5.1 Configuração

| Item | Valor |
|------|-------|
| **URL** | https://supbase.2notasudi.com.br |
| **Studio** | https://supbase.2notasudi.com.br:3000 |
| **PostgREST** | /rest/v1/ |
| **Auth** | /auth/v1/ |
| **Storage** | /storage/v1/ |
| **Realtime** | /realtime/v1/ |
| **Functions** | /functions/v1/ |

### 5.2 PostgREST (API Automática)

```bash
# SELECT
GET /rest/v1/clientes?select=id,nome&cpf_hash=eq.abc123
Headers:
  apikey: $SUPABASE_ANON_KEY
  Authorization: Bearer $JWT

# INSERT
POST /rest/v1/clientes
Headers:
  apikey: $SERVICE_ROLE_KEY  # bypass RLS
  Content-Type: application/json
  Prefer: return=representation
Body: { "cpf_hash": "...", "nome": "..." }

# UPDATE
PATCH /rest/v1/clientes?id=eq.123
Headers:
  apikey: $SERVICE_ROLE_KEY
Body: { "nome": "Novo Nome" }

# DELETE
DELETE /rest/v1/clientes?id=eq.123
```

### 5.3 Auth (JWT)

```python
# Verificar JWT
from jose import jwt

def verify_supabase_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid token")

# Endpoint protegido
@router.get("/meus-dados")
async def meus_dados(authorization: str = Header(...)):
    user = verify_supabase_jwt(authorization.split()[1])
    return user
```

### 5.4 Storage

```python
# Upload
from supabase import create_client

supabase = create_client(settings.supabase_url, settings.supabase_service_key)

# Upload de PDF (segunda via)
with open("documento.pdf", "rb") as f:
    response = supabase.storage.from_("documentos").upload(
        path="cliente-123/doc.pdf",
        file=f,
        file_options={"content-type": "application/pdf"}
    )

# URL pública (signed - expira em 7 dias)
url = supabase.storage.from_("documentos").create_signed_url(
    "cliente-123/doc.pdf",
    604800  # 7 dias
)
```

### 5.5 Database Webhooks (Outbox Pattern)

```sql
-- Já configurado: 3 webhooks ativos
-- outbox → N8N (novo evento)
-- protocolos → N8N (novo protocolo)
-- consent → N8N (novo consentimento)

-- Criar novo webhook
SELECT supabase_functions.http_request(
  'https://flow.2notasudi.com.br/webhook/supabase-event',
  'POST',
  '{"Content-Type": "application/json"}',
  jsonb_build_object('event', 'novo', 'data', NEW)
);
```

---

## 6. Redis (Cache)

### 6.1 Configuração

| Item | Valor |
|------|-------|
| **Host** | 100.99.172.84:6379 (Tailscale) |
| **Auth** | @Techno832466 |
| **Max Memory** | 256MB |
| **DB** | 0 |
| **Eviction** | allkeys-lru |

### 6.2 Cliente Python

```python
# backend/app/services/redis_cache.py
from redis.asyncio import Redis

redis = Redis.from_url(
    "redis://:@Techno832466@100.99.172.84:6379/0",
    encoding="utf-8",
    decode_responses=True,
    max_connections=50,
)

# SET com TTL
await redis.setex("key", 3600, "value")

# GET
value = await redis.get("key")

# DELETE
await redis.delete("key")

# Pub/Sub
async def listener():
    pubsub = redis.pubsub()
    await pubsub.subscribe("canal_eventos")
    async for message in pubsub.listen():
        if message["type"] == "message":
            print(message["data"])
```

### 6.3 Padrões de Uso

```python
# 1. Cache de emolumento (24h)
async def get_emolumento(tipo: str) -> dict:
    key = f"emolumento:{tipo}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    
    # Cache miss: query DB
    data = await db.query(...)
    await redis.setex(key, 86400, json.dumps(data))
    return data

# 2. Sessão de usuário (30min)
async def set_session(phone: str, data: dict):
    await redis.setex(f"sess:{phone}", 1800, json.dumps(data))

# 3. Rate limiting
async def check_rate_limit(ip: str, limit: int = 100) -> bool:
    key = f"rate:{ip}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)  # 1 min
    return count <= limit

# 4. Distributed lock (Redlock E8.A20)
async def acquire_lock(resource: str, ttl: int = 10) -> bool:
    token = str(uuid.uuid4())
    result = await redis.set(
        f"lock:{resource}",
        token,
        nx=True,  # só se não existir
        ex=ttl
    )
    return result is not None
```

### 6.4 Health Check

```bash
ssh vps-cartorio "redis-cli -p 6379 -a \$REDIS_AUTH PING"
# PONG

# Stats
ssh vps-cartorio "redis-cli -p 6379 -a \$REDIS_AUTH INFO stats | grep keyspace"
# keyspace_hits:12345
# keyspace_misses:1234
```

---

## 7. N8N (Workflows)

### 7.1 Configuração

| Item | Valor |
|------|-------|
| **URL** | https://flow.2notasudi.com.br |
| **API Key** | (em env) |
| **MCP URL** | https://flow.2notasudi.com.br/mcp-server/http |
| **Database** | Postgres (próprio schema) |
| **Workflows Ativos** | 34 |

### 7.2 Endpoints API

```bash
# Headers
X-N8N-API-KEY: $N8N_KEY

# Listar workflows
GET /api/v1/workflows
Response: { "data": [...], "nextCursor": null }

# Workflow específico
GET /api/v1/workflows/{id}

# Ativar/Desativar
PATCH /api/v1/workflows/{id}
Body: { "active": true }

# Listar execuções
GET /api/v1/executions?workflowId={id}&limit=10
Response: { "data": [...], "nextCursor": null }

# Executar manualmente
POST /api/v1/workflows/{id}/execute
Body: {} (workflow data)

# Tags
GET /api/v1/tags
```

### 7.3 Webhook Pattern

```bash
# Webhook URL gerada automaticamente
# Formato: https://flow.2notasudi.com.br/webhook/{path}
# Path definido no node "Webhook" do workflow

# Testar
curl -X POST "https://flow.2notasudi.com.br/webhook/test-path" \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-123" \
  -d '{"key": "value"}'
```

### 7.4 Padrão de WF (B07-B10)

```yaml
Estrutura obrigatória:
  1. Sticky Note inicial:
     - Nome do WF
     - Propósito
     - Serviços usados
     - Última atualização
     
  2. Trigger (webhook, cron, queue)
  
  3. Error Handler conectado ao WF #00
  
  4. HTTP Request nodes:
     - Timeout: 5000ms (default) ou 10000ms (LLM/file)
     - Retry: 3x exponential backoff (1s, 5s, 15s)
     - Header: X-Correlation-ID
     - Continue on Fail: false (salvo quando explícito)
     
  5. Logs estruturados (B09):
     - correlation_id
     - timestamp
     - workflow_name
     - status
     
  6. Métricas Prometheus (B10):
     - n8n_wf_executions_total
     - n8n_wf_latency_seconds
```

### 7.5 MCP Tools N8N

```bash
# URL do MCP server
https://flow.2notasudi.com.br/mcp-server/http

# 30 tools disponíveis
# Listar via Claude/Antigravity:
- list_workflows
- get_workflow
- create_workflow
- update_workflow
- activate_workflow
- deactivate_workflow
- execute_workflow
- list_executions
- get_execution
- ...
```

---

## 8. Telegram Bot

### 8.1 Configuração

| Item | Valor |
|------|-------|
| **Bot** | @test_cartorio_bot |
| **Token** | 8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q |
| **Webhook** | https://api.2notasudi.com.br/webhook/telegram |
| **Uso** | Pré-teste (NÃO é canal oficial) |

### 8.2 Enviar Mensagem

```python
# backend/app/services/telegram.py
import httpx

class TelegramClient:
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
    ) -> dict:
        """Envia mensagem de texto."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def send_alert(
        self,
        level: str,  # P0, P1, P2, P3
        title: str,
        message: str,
        chat_id: int = 6682284055,  # Gustavo
    ):
        """Envia alerta formatado."""
        emoji = {
            "P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🔵"
        }
        
        text = f"""
{emoji.get(level, '⚪')} *{level} - {title}*

{message}

_Datetime: {datetime.now().isoformat()}_
        """
        return await self.send_message(chat_id, text)
```

### 8.3 Webhook

```python
@router.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Recebe updates do Telegram."""
    # Verificar signature
    # Processar mensagem
    # Enviar para OpenClaw
    # Responder
    return {"ok": True}
```

### 8.4 Comandos Customizados

```python
# /status
async def status_command(chat_id: int):
    health = await api.get_health_radar()
    text = f"""
*Status dos Serviços*

{health_summary}

_CPU: X%_
_Memory: Y%_
_Disk: Z%_
    """
    await telegram.send_message(chat_id, text)

# /backup
async def backup_command(chat_id: int):
    result = await api.trigger_backup()
    text = f"Backup iniciado: {result['id']}"
    await telegram.send_message(chat_id, text)

# /alertas
async def alertas_command(chat_id: int):
    # Listar últimos alertas
    ...
```

---

## 9. Padrões de Integração

### 9.1 Cliente HTTP Genérico

```python
# backend/app/services/http_client.py
import httpx
import uuid
from tenacity import retry, stop_after_attempt, wait_exponential

class HTTPClient:
    """Cliente HTTP padrão com retry, timeout e correlation ID."""
    
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20),
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15)
    )
    async def request(
        self,
        method: str,
        path: str,
        correlation_id: str | None = None,
        **kwargs,
    ) -> httpx.Response:
        cid = correlation_id or str(uuid.uuid4())
        
        headers = {
            "X-Correlation-ID": cid,
            "User-Agent": "cartorio-api/0.6.0",
            **kwargs.pop("headers", {}),
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = await self.client.request(
                method, path, headers=headers, **kwargs
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(
                "http_error",
                extra={
                    "correlation_id": cid,
                    "status": e.response.status_code,
                    "method": method,
                    "path": path,
                }
            )
            raise
        finally:
            metrics.http_request_duration.labels(
                method=method, path=path, status=response.status_code
            ).observe(time.time() - start)
```

### 9.2 Webhook Receiver

```python
# backend/app/api/v1/router.py
@router.post("/webhook/{source}")
async def receive_webhook(
    source: str,
    request: Request,
    x_signature: str | None = Header(None),
):
    """Recebe webhook de serviço externo."""
    body = await request.body()
    
    # 1. Verificar signature (HMAC)
    if x_signature:
        expected = hmac.new(
            settings.webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(x_signature, expected):
            raise HTTPException(401, "Invalid signature")
    
    # 2. Parsear payload
    payload = json.loads(body)
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    
    # 3. Salvar no DB (outbox pattern)
    async with get_db() as session:
        event = WebhookEvent(
            source=source,
            payload=payload,
            correlation_id=correlation_id,
        )
        session.add(event)
        await session.commit()
    
    # 4. Processar assincronamente (N8N pega via DB webhook)
    return {"status": "received", "correlation_id": correlation_id}
```

### 9.3 Health Check Padronizado

```python
# backend/app/services/health.py
class HealthCheck:
    def __init__(self, name: str, url: str, **kwargs):
        self.name = name
        self.url = url
        self.kwargs = kwargs
    
    async def check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.url, **self.kwargs)
                response.raise_for_status()
                return {
                    "name": self.name,
                    "status": "online",
                    "latency_ms": response.elapsed.total_seconds() * 1000,
                }
        except Exception as e:
            return {
                "name": self.name,
                "status": "offline",
                "error": str(e),
            }

# Uso
checks = [
    HealthCheck("api", "https://api.2notasudi.com.br/health"),
    HealthCheck("n8n", "https://flow.2notasudi.com.br/healthz"),
    HealthCheck("evolution", "https://whatsapp.2notasudi.com.br/"),
    HealthCheck("openclaw", "https://agent.2notasudi.com.br/health"),
    # ...
]

results = await asyncio.gather(*[c.check() for c in checks])
```

---

## 10. Adicionando Nova Integração

### 10.1 Checklist

```
□ Adicionar settings em backend/app/config.py
□ Criar client em backend/app/services/novo_servico.py
□ Adicionar health check em backend/app/services/health.py
□ Adicionar endpoint(s) em backend/app/api/v1/router.py
□ Criar testes em backend/tests/test_novo_servico.py
□ Adicionar métricas Prometheus
□ Adicionar logger estruturado
□ Documentar em docs/INTEGRATION_GUIDE.md
□ Adicionar runbook em docs/TROUBLESHOOTING.md
□ Adicionar secrets em Supabase Vault
□ Atualizar .env.example
□ Adicionar doc em docs/platforms/novo_servico.md
```

### 10.2 Template de Cliente

```python
# backend/app/services/novo_servico.py
import httpx
import uuid
from typing import Any

from app.config import settings
from app.logging import get_logger
from app.metrics import http_requests_total

logger = get_logger(__name__)


class NovoServicoClient:
    """Cliente para integração com Novo Serviço."""
    
    def __init__(self):
        self.base_url = settings.novo_servico_url
        self.api_key = settings.novo_servico_api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_keepalive_connections=20),
        )
    
    async def _request(
        self,
        method: str,
        path: str,
        correlation_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        cid = correlation_id or str(uuid.uuid4())
        
        try:
            response = await self.client.request(
                method,
                path,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Correlation-ID": cid,
                },
                **kwargs,
            )
            response.raise_for_status()
            
            http_requests_total.labels(
                service="novo_servico", method=method, status=response.status_code
            ).inc()
            
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "novo_servico_error",
                extra={
                    "correlation_id": cid,
                    "method": method,
                    "path": path,
                    "error": str(e),
                }
            )
            raise
    
    async def example_method(self, param: str) -> dict:
        """Exemplo de método."""
        return await self._request("GET", f"/example/{param}")
    
    async def health_check(self) -> bool:
        """Verifica se serviço está online."""
        try:
            await self._request("GET", "/health")
            return True
        except Exception:
            return False
```

### 10.3 Template de Teste

```python
# backend/tests/test_novo_servico.py
import pytest
from unittest.mock import AsyncMock, patch

from app.services.novo_servico import NovoServicoClient


@pytest.fixture
def client():
    return NovoServicoClient()


@pytest.mark.asyncio
async def test_example_method_success(client):
    """Testa método example_method."""
    with patch.object(client.client, 'request') as mock_request:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        result = await client.example_method("test")
        
        assert result == {"result": "ok"}
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_health_check_online(client):
    """Testa health check online."""
    with patch.object(client, '_request', new=AsyncMock(return_value=None)):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_offline(client):
    """Testa health check offline."""
    with patch.object(client, '_request', new=AsyncMock(side_effect=Exception)):
        result = await client.health_check()
        assert result is False
```

---

## Recursos

- **API Endpoints**: `/docs/API_ENDPOINTS_CATALOG.md`
- **Plataformas**: `/docs/platforms/`
- **Performance**: `/docs/PERFORMANCE_TUNING.md`
- **Security**: `/docs/SECURITY_HARDENING.md`
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md`
- **Monitoring**: `/docs/MONITORING_GUIDE.md`

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
