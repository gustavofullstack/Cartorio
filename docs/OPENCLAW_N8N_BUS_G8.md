# Barramento OpenClaw ↔ N8N (G8.21.T2)

| Campo | Valor |
|-------|-------|
| **Task** | G8.21.T2 — barramento de mensageria assíncrona entre OpenClaw Gateway e N8N para jobs longos |
| **Wave pack** | **Wave 51** (2026-07-18) |
| **Rein** | `cartorio-n8n` |
| **Status** | Template + runbook + simulador offline. **Produção precisa de Redis + WebSocket real.** |
| **Constraint** | Acesso live a `openclaw.2notasudi.com.br` e `flow.2notasudi.com.br` **não disponível** nesta task. |

---

## 1. Problema

OpenClaw Gateway é o **LLM router** do stack (decide intenção, escolhe tool, gera resposta). N8N é o **orquestrador de workflows** (executa ações: emitir protocolo, abrir atendimento, notificar escrevente).

Quando uma decisão do OpenClaw dispara **workflow de longa duração** (orquestração multi-step, integração com Chatwoot, validação HITL), o caminho síncrono `/v1/chat`:

- bloqueia o canal WebSocket até a action chain terminar;
- perde contexto se o cliente desconectar no meio;
- não tem **persistência** se OpenClaw crashar antes do N8N confirmar;
- não tem **idempotência** — retry do N8N pode disparar o workflow 2x.

---

## 2. Pattern escolhido: WebSocket (push) + Redis Stream (jobs longos)

OpenClaw **emite decisões** via:

| Canal | Quando usar | Latência | Durabilidade |
|-------|-------------|----------|--------------|
| **WebSocket `/v1/stream`** | Real-time updates parciais (token a token, status de tool call) | <100ms | efêmero (drop on disconnect) |
| **Redis Stream `cartorio:openclaw:jobs`** | Job longo (workflow N8N multi-step) | <50ms enqueue | durável (MAXLEN ~ 10k, consumer group) |
| **POST `/v1/chat`** (legado) | Pedidos curtos, single-turn | síncrono | efêmero (404 histórico, ver fix) |

N8N **consome** via:

- **WebSocket listener Node** (`wss://agent.2notasudi.com.br/v1/stream`) — push imediato de eventos parciais;
- **Redis Stream consumer Node** (`XREADGROUP cartorio-n8n`) — jobs duráveis, at-least-once delivery.

---

## 3. Por que esse design

1. **Async first**: LLM pode levar 30–60s (Opus 4.5 / GPT-5.5). Push imediato de progresso parcial via WS mantém o canal "vivo"; a completion chega via Redis Stream event `job.done`.
2. **Persistência**: jobs longos sobrevivem a crash do OpenClaw (Redis Stream é append-only log).
3. **Idempotência**: cada job tem `job_id` UUID gerado pelo OpenClaw no submit. N8N faz `SETNX cartorio:openclaw:job:<id> -> ack` antes de processar; retries são seguros.
4. **LGPD-safe**: payload é **metadata only** (IDs, tipo de ação, hash de contexto). PII scrubbed **antes** do envelope — ver `app/services/pii.py` (3 camadas: Pydantic validator → Sentry `before_send` → log `MaskingFilter`).
5. **At-least-once + dead letter**: consumer group N8N usa XACK após processar; entries não-ACKadas após 24h vão pra DLQ via `outbox_message` (Lesson 213–215).
6. **Backpressure**: Redis Stream `MAXLEN ~ 10000` evita OOM; N8N ajusta `BLOCK 5000` no XREADGROUP.

---

## 4. Failure modes

| Cenário | Detecção | Recuperação |
|---------|----------|-------------|
| OpenClaw down antes do submit | N8N não vê `job.submitted` no WS | Health check OpenClaw no N8N cron; retry do cliente (WhatsApp/Telegram) reenvia via `/v1/chat` síncrono |
| OpenClaw down após submit (job na fila) | N8N polling via `XLEN cartorio:openclaw:jobs` | Jobs ficam na fila; N8N continua consumindo o backlog quando OpenClaw volta |
| N8N down | OpenClaw WS send falha; Redis Stream continua acumulando | OpenClaw retém no buffer local do agent; após N8N voltar, consumer group resync via `XREADGROUP 0` |
| WS connection drop | Heartbeat `ping/pong` 30s ausente | Redis Stream é source-of-truth; reconnect do WS N8N faz `XREADGROUP $` (pending entries) |
| Job travado (N8N processou, não ACKou) | `XPENDING cartorio:openclaw:jobs cartorio-n8n` mostra pending > 1h | Claim manual via `XCLAIM` ou DLQ automática após TTL |
| Duplicate delivery | Mesmo `job_id` chega 2x | N8N faz `SET cartorio:openclaw:job:<id> ack 1 NX EX 86400` antes de processar |
| PII no payload | `app.services.pii.scrub()` retorna masked | Job vai pra DLQ com `reason=pii_violation` (não processar) |

---

## 5. Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/v1/chat` | POST | Legado síncrono. Use só para single-turn. Resposta inclui `job_id` se workflow foi enfileirado. | `Authorization: Bearer <operator_token>` |
| `/v1/stream` | WS | Real-time events. Tipos: `token`, `tool_call`, `job.submitted`, `job.done`, `job.failed`, `error`. | Bearer in subprotocol header |
| `/v1/jobs` | POST | Submete job longo. Body: `{payload, idempotency_key?}`. Retorna `{job_id, status: "queued"}`. | Bearer |
| `/v1/jobs/{id}` | GET | Status do job. Retorna `{job_id, status, result?, error?, created_at, updated_at}`. | Bearer |
| `/v1/jobs/{id}` | DELETE | Cancela (se ainda pending). Idempotente. | Bearer |

### Schema de payload (POST `/v1/jobs`)

```json
{
  "payload": {
    "workflow": "cartorio.protocolo.emitir",
    "context": {
      "conversation_id": "uuid",
      "cliente_hash": "sha256:...",
      "intent": "emitir_protocolo"
    },
    "params": { "...": "..." }
  },
  "idempotency_key": "uuid-optional"
}
```

Resposta:
```json
{
  "job_id": "uuid",
  "status": "queued",
  "stream_id": "1234-0",
  "estimated_duration_s": 45
}
```

---

## 6. Modelo de dados (Redis Stream)

### Stream key
```
cartorio:openclaw:jobs
```

### Entry schema
```json
{
  "job_id": "uuid-v4",
  "workflow": "cartorio.protocolo.emitir",
  "context_hash": "sha256:abc...",
  "payload_size": 1024,
  "submitted_at": "2026-07-18T12:34:56Z",
  "submitted_by": "openclaw-agent-id",
  "priority": "normal"
}
```

### Consumer group
```
XGROUP CREATE cartorio:openclaw:jobs cartorio-n8n $ MKSTREAM
```

### DLQ
```
cartorio:openclaw:jobs:dlq  (TTL 7 dias, alert via Telegram)
```

---

## 7. N8N workflow template

**Nome**: `cartorio.openclaw.bus_consumer`  
**Trigger**: `Redis Trigger` node (consumer group `cartorio-n8n`)  
**Steps**:
1. SETNX dedup key (`cartorio:openclaw:job:<job_id>`)
2. If exists → ACK e fim (duplicate)
3. PII re-check (`scripts/pii.py scrub`) — se falhar, DLQ + ACK
4. Switch por `payload.workflow` → roteia para sub-workflow específico
5. Executa workflow
6. Publica `job.done` em `cartorio:openclaw:events` (pub/sub pra UI)
7. XACK entry

**Idempotência**: SETNX + job_id garante at-least-once sem duplicar side-effects.

---

## 8. OpenClaw agent config (E8)

JSON em `infra/openclaw/cartorio-bot.openclaw.json` (canônico). Adicionar:

```json
{
  "bus": {
    "stream_path": "cartorio:openclaw:jobs",
    "dlq_path": "cartorio:openclaw:jobs:dlq",
    "max_len": 10000,
    "consumer_group": "cartorio-n8n",
    "ws_endpoint": "wss://agent.2notasudi.com.br/v1/stream",
    "submit_endpoint": "https://agent.2notasudi.com.br/v1/jobs",
    "idempotency_ttl_s": 86400
  }
}
```

---

## 9. LGPD

- **Payload scrubbing**: todo `payload.context.*` passa por `app.services.pii.scrub()` antes do envelope. CPF/RG/protocolo saem como `sha256:...`.
- **Audit**: cada submit vira `audit_log` entry com `action=openclaw.job.submit`, `metadata={job_id, workflow, context_hash}`.
- **Retenção**: Stream `cartorio:openclaw:jobs` trimado por `MAXLEN ~ 10000` (24h típico); DLQ 7 dias; após isso, PII zero retido.
- **Direito de eliminação (Art. 18 VI)**: cliente pode pedir cancelamento de job em `pending`; jobs `processing`/`done` requerem workflow reverso manual.

---

## 10. Runbook

### Deploy (SUI)

```bash
# 1. Validar config OpenClaw agent
python3 -c "import json; d=json.load(open('infra/openclaw/cartorio-bot.openclaw.json')); assert d['bus']['stream_path']"

# 2. Aplicar schema Redis (idempotente)
ssh root@100.99.172.84 "docker exec cartorio-redis-1 redis-cli XINFO STREAM cartorio:openclaw:jobs || docker exec cartorio-redis-1 redis-cli XADD cartorio:openclaw:jobs '*' bootstrap 1"

# 3. Criar consumer group (se ainda não existe)
ssh root@100.99.172.84 "docker exec cartorio-redis-1 redis-cli XGROUP CREATE cartorio:openclaw:jobs cartorio-n8n \$ MKSTREAM"

# 4. Deploy workflow N8N
make n8n-export  # valida JSON contra live

# 5. Smoke test (offline primeiro!)
python3 scripts/openclaw_n8n_bus_sim.py --mode=demo
```

### Diagnóstico

```bash
# Profundidade da fila
ssh root@100.99.172.84 "docker exec cartorio-redis-1 redis-cli XLEN cartorio:openclaw:jobs"

# Pending (não-ACKados) por consumer
ssh root@100.99.172.84 "docker exec cartorio-redis-1 redis-cli XPENDING cartorio:openclaw:jobs cartorio-n8n"

# DLQ
ssh root@100.99.172.84 "docker exec cartorio-redis-1 redis-cli XLEN cartorio:openclaw:jobs:dlq"
```

### Rollback

1. N8N para de consumir: `XGROUP DELCONSUMER cartorio:openclaw:jobs cartorio-n8n`
2. OpenClaw volta a `/v1/chat` síncrono (degraded mode)
3. Drain manual da fila após investigação

---

## 11. Simulador offline

**Arquivo**: `scripts/openclaw_n8n_bus_sim.py`

Implementa `OpenClawN8NBus` in-memory com `asyncio.Queue` para fan-out. Substitui Redis Stream + WebSocket em testes. Usado por `backend/tests/test_openclaw_n8n_bus_g8.py`.

```bash
python3 scripts/openclaw_n8n_bus_sim.py --demo
```

Modos:
- `--mode=demo`: roda 3 submit + 3 subscribe concorrentes, valida fan-out
- `--mode=stress`: 1000 jobs concorrentes, mede throughput
- `--mode=chaos`: mata 1 subscriber no meio, valida recovery dos outros

---

## 12. Métricas (Prometheus)

| Métrica | Tipo | Labels |
|---------|------|--------|
| `openclaw_bus_jobs_submitted_total` | counter | `workflow`, `priority` |
| `openclaw_bus_jobs_processed_total` | counter | `workflow`, `status` |
| `openclaw_bus_jobs_dlq_total` | counter | `reason` |
| `openclaw_bus_queue_depth` | gauge | — |
| `openclaw_bus_ws_subscribers` | gauge | — |
| `openclaw_bus_job_duration_seconds` | histogram | `workflow`, `status` |

Alert: `openclaw_bus_queue_depth > 5000 por 5min` → Telegram DPO.

---

## 13. Próximos passos (não nesta task)

1. **E2E live**: deploy OpenClaw + N8N + Redis Stream; rodar 50 jobs sintéticos (Lesson 198 já cobriu skill `openclaw_ws`).
2. **MCP tools**: expor `cartorio_bus_submit` / `cartorio_bus_status` no `backend/mcp_server.py`.
3. **Observability**: integrar métricas no Grafana dashboard `cartorio-bus.json`.
4. **HITL gate**: jobs `emitir_protocolo` exigem aprovação escrevente via Chatwoot handoff (Lesson 160).

---

Modified by Gustavo Almeida + cartorio-n8n — G8.21.T2.