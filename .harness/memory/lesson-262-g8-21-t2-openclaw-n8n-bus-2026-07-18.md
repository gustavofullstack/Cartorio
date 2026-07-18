# Lesson 262 — G8.21.T2 barramento assíncrono OpenClaw ↔ N8N (2026-07-18)

## Contexto

OpenClaw Gateway é o LLM router; N8N é o orquestrador de workflows. A interface anterior era apenas o endpoint síncrono `POST /v1/chat`, que já teve bug de 404 histórico e não oferece:

- progresso em tempo real para chamadas de 30–60s (Opus 4.5 / GPT-5.5);
- persistência se OpenClaw crashar antes do N8N confirmar;
- idempotência — retry do N8N pode disparar workflow 2x;
- backpressure para surtos de jobs longos (workflows multi-step, Chatwoot handoff).

Acesso live a `openclaw.2notasudi.com.br` e `flow.2notasudi.com.br` estava **offline** durante a task. Por isso a entrega é template + runbook + simulador offline, não deploy em prod.

## Decisão

Foi criado `docs/OPENCLAW_N8N_BUS_G8.md` documentando o pattern **WebSocket push + Redis Stream durável**:

- OpenClaw emite em `wss://agent.2notasudi.com.br/v1/stream` (eventos parciais, <100ms) e `POST /v1/jobs` (job durável em `cartorio:openclaw:jobs`, enqueue <50ms);
- N8N consome via WebSocket listener node + Redis Stream consumer group `cartorio-n8n` (`XREADGROUP` + `XACK` + dedup por `SETNX cartorio:openclaw:job:<id>`);
- `cartorio:openclaw:jobs:dlq` (TTL 7 dias) absorve entries não-ACKadas ou que falham PII re-check;
- LGPD: payload passa por `scrub_payload` (proxy de `app.services.pii.scrub`) antes do envelope; entry do Stream só guarda metadata + `context_hash`.

Foi criado `scripts/openclaw_n8n_bus_sim.py`, simulador offline que substitui Redis Stream + WebSocket por `dict` + `asyncio.Queue`:

- `OpenClawN8NBus` com `submit/poll/mark_processing/mark_done/mark_failed/cancel/subscribe`;
- idempotência via `idempotency_key` opcional (N submits = 1 job);
- `subscribe()` async generator — cada consumer recebe sua própria queue; subscribers stuck são evictados silenciosamente se a queue encher (não bloqueia o bus);
- `asyncio.Lock` guarda o dict de jobs (submits concorrentes são safe);
- `max_len` trimming LRU-by-time (substitui `XADD MAXLEN ~ N`);
- CLI `--mode=demo|stress|chaos` para smoke offline (3 submits, 1000 jobs concorrentes, subscriber quebrado).

## Testes

`backend/tests/test_openclaw_n8n_bus_g8.py` cobre **18 cenários** (acima do mínimo de 6):

- lifecycle: submit/poll/mark_processing/mark_done/mark_failed/cancel
- fan-out: subscriber único + 5 subscribers paralelos
- concorrência: 50 submits preservam unicidade de UUIDs
- idempotência: mesma `idempotency_key` retorna mesmo `job_id` (3 submits = 1 job); keys diferentes produzem jobs distintos
- failure modes: subscriber não-responsivo não bloqueia os demais; submit após `close()` levanta `BusError`
- LGPD: payload é marcado `_scrubbed` pelo hook
- `max_len` trima os mais antigos quando estourar

Validação:

- `pytest tests/test_openclaw_n8n_bus_g8.py --no-cov -v`: **18 passed**;
- `python3 scripts/openclaw_n8n_bus_sim.py --mode=demo`: 9 eventos recebidos;
- `python3 scripts/openclaw_n8n_bus_sim.py --mode=stress --n=100`: 100k jobs/s in-memory;
- `python3 scripts/openclaw_n8n_bus_sim.py --mode=chaos`: subscriber quebrado não impede o healthy;
- `ruff check scripts/openclaw_n8n_bus_sim.py backend/tests/test_openclaw_n8n_bus_g8.py`: zero erros.

## LGPD

- Payload scrubbing stub (`scrub_payload`) substitui CPF/RG/protocolo por `sha256:...` antes de armazenar — implementação real delega para `app.services.pii.scrub` (3 camadas: Pydantic validator → Sentry `before_send` → log MaskingFilter).
- Stream entry não carrega payload completo: só `workflow`, `context_hash`, `payload_size`, `submitted_by`, `submitted_at`, `priority`. LGPD Art. 18 VI (eliminação) é atendida via `cancel()` enquanto o job está pending.
- Audit: cada submit vira `audit_log` entry (`action=openclaw.job.submit`, `metadata={job_id, workflow, context_hash}`); append-only + HMAC chain já cobertos por `app.services.audit*`.

## Failure modes documentados

| Cenário | Detecção | Recuperação |
|---------|----------|-------------|
| OpenClaw down | WS drop + health check | Jobs na fila; cliente retry reenvia via `/v1/chat` síncrono |
| N8N down | Redis Stream acumula | OpenClaw retém no buffer; consumer group resync após N8N voltar |
| WS drop | Heartbeat ping/pong 30s | Redis Stream é source-of-truth; reconnect com `XREADGROUP $` |
| Job travado | `XPENDING > 1h` | `XCLAIM` manual ou DLQ automática |
| Duplicate delivery | `SETNX` dedup key | N8N skip + XACK |
| PII no payload | `scrub_payload` falha | DLQ com `reason=pii_violation` |

## Constraint honored

- Sem branch criada (commit direto em master via `--no-verify`, conforme diretiva da task).
- `SUPER_PLANO_G8.md` e `PROGRESS.md` **não tocados**.
- Não rodou contra OpenClaw/N8N live (offline simulation apenas).
- Bus é offline sim — produção precisa de Redis Stream + WebSocket real.

## Próximos passos (não nesta task)

1. E2E live: deploy OpenClaw + N8N + Redis Stream + 50 jobs sintéticos (skill `openclaw_ws` já coberta em Lesson 198).
2. MCP tools: expor `cartorio_bus_submit` / `cartorio_bus_status` no `backend/mcp_server.py`.
3. Grafana dashboard `cartorio-bus.json` com `openclaw_bus_queue_depth` + `openclaw_bus_jobs_processed_total`.
4. HITL gate: jobs `emitir_protocolo` exigem aprovação escrevente via Chatwoot handoff (Lesson 160).

Modified by Gustavo Almeida + cartorio-n8n — G8.21.T2.