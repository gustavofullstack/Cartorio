# Troubleshooting — Bots (Telegram + WhatsApp)

> **Versão**: 3.0 (2026-07-09)
> **Owner**: Gustavo Almeida (debug) + 4 agents paralelos (fix)

## 📋 Cenários

1. [Bot não responde em 15s](#1-bot-não-responde-em-15s)
2. [LiteLLM DOWN (todos providers)](#2-litellm-down-todos-providers)
3. [Bot responde duplicado](#3-bot-responde-duplicado)
4. [Race condition typing + send](#4-race-condition-typing--send)
5. [Redis offline](#5-redis-offline)
6. [Audit log quebrado](#6-audit-log-quebrado)
7. [WhatsApp QR expirado](#7-whatsapp-qr-expirado)
8. [Consent WhatsApp não ativa](#8-consent-whatsapp-não-ativa)
9. [HITL Chatwoot offline](#9-hitl-chatwoot-offline)
10. [Circuit breaker travado OPEN](#10-circuit-breaker-travado-open)
11. [PII leak no output do LLM](#11-pii-leak-no-output-do-llm)
12. [Latência P95 > 15s](#12-latência-p95--15s)

## 1. Bot não responde em 15s

### Diagnóstico

```bash
# 1. Verificar webhook configurado
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"

# Esperado: {"url": "...", "pending_update_count": 0}

# 2. Verificar API online
curl -sS https://api.2notasudi.com.br/api/v1/health/integracoes | jq .

# Esperado: {"status": "ok", "integrations": {"telegram": "ok", "whatsapp": "ok", "llm": "ok", "redis": "ok"}}

# 3. Ver logs API
docker logs cartorio_api --since 2m 2>&1 | grep -E 'TG|telegram|webhook|LLM' | tail -20

# 4. Verificar LiteLLM proxy
curl -sS http://cartorio_litellm-app:4000/health/liveliness

# 5. Testar manualmente
CID=$(docker ps --filter 'name=^cartorio_api' --format '{{.ID}}' | head -1)
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"update_id":99999,"message":{"message_id":1,"date":0,"chat":{"id":6682284055,"type":"private"},"from":{"id":6682284055,"is_bot":false,"first_name":"G"},"text":"teste"}}' \
  https://api.2notasudi.com.br/api/v1/telegram/webhook

# Esperado: {"ok":true} em <1s (debounce 1.2s + LLM 4-8s + send 0.5s)
sleep 10
docker logs $CID --since 30s 2>&1 | grep -E 'sent=|provider='
```

### Causas Comuns

| Sintoma | Causa | Fix |
|---|---|---|
| `pending_update_count > 0` | Telegram não consegue entregar webhook | Verificar DNS + TLS |
| API 500 | Exceção não tratada | Ver logs stacktrace |
| API 200 mas `sent=False` | LLM/Evolution/Telegram falhou | Ver logs específicos |
| Nenhum log gerado | Background task morta | Restart API |
| LiteLLM 422 | Upstream NVIDIA/Xiaomi falhou | Fallback automático para opencode_free_1 |

## 2. LiteLLM DOWN (todos providers)

### Diagnóstico

```bash
# Verificar LiteLLM
curl -sS http://cartorio_litellm-app:4000/health/liveliness
# 200 = UP, connection refused = DOWN

# Verificar cada provider individualmente
curl -X POST http://cartorio_litellm-app:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"opencode-free-1","messages":[{"role":"user","content":"ping"}],"max_tokens":10}'
```

### Fallback Automático (já implementado)

```
1. LiteLLM UP → response em 4-10s
2. LiteLLM 5xx/timeout → opencode_free_1 (2-4s)
3. opencode_free_1 429 → opencode_free_2 (2-5s)
4. opencode_free_2 503 → opencode_free_3 (3-6s)
5. opencode_free_3 timeout → opencode_go (1-3s)
6. opencode_go 5xx → openclaw (5-15s)
7. openclaw fail → cache local "Sistema em manutenção"
```

**Bot auto-recupera**. Não requer intervenção manual.

### Fix Manual (se necessário)

```bash
# Restart LiteLLM
docker service update --force cartorio_litellm-app

# Verificar logs
docker service logs cartorio_litellm-app --tail 100

# Restart openclaw se também DOWN
docker service update --force cartorio_openclaw
```

## 3. Bot responde duplicado

### Causa

- Mesmo `update_id` ou `message_id` processado 2x (idempotência falhou)
- Race condition entre 2 webhooks simultâneos

### Diagnóstico

```bash
# Verificar idempotência Redis
docker exec cartorio_redis redis-cli KEYS "idem:*" | head -20
docker exec cartorio_redis redis-cli GET "idem:telegram:12345"

# Esperado: "1" (já processado)
# Se retorna nil = não foi gravado (bug)

# Ver logs
docker logs cartorio_api --since 1m 2>&1 | grep -E 'idem|duplicate'
```

### Fix

```python
# backend/app/services/chat_pipeline.py
async def check_idempotency(update_id: str, channel: Channel) -> bool:
    if not update_id:
        return False
    bus = get_bus()
    if not bus:
        return False
    key = f"idem:{channel.value}:{update_id}"
    is_new = await bus.client.set(key, "1", ex=IDEMPOTENCY_TTL_SEC, nx=True)
    return not bool(is_new)
```

**Verificar**:
- TTL = 600s (10min)
- Redis online (`redis-cli PING`)
- `nx=True` (atomic SETNX)

Se problema persiste: aumentar TTL para 3600s (1h).

## 4. Race condition typing + send

### Sintoma

Bot envia "typing" 30s+ sem enviar resposta. Cliente vê "Bot digitando..." infinito.

### Causa

`typing_loop` em background task não é cancelado quando `send_response()` termina (em alguns race conditions).

### Fix (já aplicado em `chat_pipeline.py`)

```python
async def typing_loop(adapter, recipient_id, stop_event, action="typing"):
    try:
        while not stop_event.is_set():
            await adapter.typing(recipient_id, action)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=TYPING_REFRESH_SEC)
                break
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        pass
    finally:
        await adapter.typing(recipient_id, "")  # SEMPRE cancela
```

**Garantias**:
1. `finally` sempre executa (mesmo com exceção)
2. `stop_event` setado antes de `send_response()` finalizar
3. `cancel_typing("")` enviado como última ação

### Diagnóstico

```bash
# Ver processos typing ativos
docker logs cartorio_api --since 1m 2>&1 | grep -E 'typing_loop|TYPING|stop_event'
```

## 5. Redis offline

### Sintoma

- Webhook retorna 500 (`redis.exceptions.ConnectionError`)
- Idempotência, rate limit, debounce falham

### Diagnóstico

```bash
docker exec cartorio_redis redis-cli PING
# Esperado: PONG

docker service logs cartorio_redis --tail 50
```

### Fix Imediato

```bash
# Force restart (atualiza DNS stale)
docker service update --force cartorio_redis

# Se OOM kill (lesson 127):
docker service update cartorio_redis --limit-memory 500M
docker service update cartorio_redis --args "--maxmemory 500mb --maxmemory-policy allkeys-lru"
```

### Fail-Open (já implementado)

Se Redis offline, **passa sem checagem** + log warning:

```python
async def check_idempotency(update_id: str, channel: Channel) -> bool:
    if not update_id:
        return False
    bus = get_bus()
    if not bus:  # Redis offline
        logger.warning("Redis offline, idempotência não verificada")
        return False  # sempre processa
    ...
```

**Trade-off**: risco de duplicação em caso de Redis offline. Aceitável (sistema degrada gracefully).

## 6. Audit log quebrado

### Sintoma

`POST /api/v1/audit/verify` retorna `ok=false`.

### Causa

- Hash chain corrompido (insert manual ou migration)
- HMAC key rotacionada

### Diagnóstico

```bash
curl -X POST https://api.2notasudi.com.br/api/v1/audit/verify \
  -H "X-API-Key: $ADMIN_API_KEY"
# {"ok": false, "broken_at": 12345}
```

### Fix

```bash
# 1. Identificar row problemática
psql -h cartorio_supabase -U postgres -d cartorio \
  -c "SELECT id, ts FROM audit_log WHERE id=12345;"

# 2. Verificar conteúdo
psql -h cartorio_supabase -U postgres -d cartorio \
  -c "SELECT payload, audit_hash FROM audit_log WHERE id=12345;"

# 3. Se tamper confirmado: investigar acesso, rotacionar AUDIT_KEY
# Se migration legítima: re-gerar hash chain a partir desse ponto
```

**Prevenção**: audit log INSERT-only (sem UPDATE/DELETE permission para usuário da app).

## 7. WhatsApp QR expirado

### Sintoma

Manager UI mostra QR mas celular não consegue scan (expirado).

### Causa

QR do WhatsApp Web expira em 60s.

### Fix

```bash
# Novo QR
curl http://localhost:8080/instance/connect/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" | jq -r '.qrcode'

# Escanear em < 60s
```

### Pairing Code (alternativa para corporativo)

```bash
curl -X POST http://localhost:8080/instance/pairingCode/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "5511999999999"}'
# Resposta: {"code": "ABCD-1234"}
# Inserir no WhatsApp → Configurações → Aparelhos conectados → Conectar com código
```

## 8. Consent WhatsApp não ativa

### Sintoma

Cliente responde "Aceito" mas bot não responde dúvidas.

### Diagnóstico

```bash
# Verificar se gravou no banco
docker exec cartorio_postgres psql -U postgres -d cartorio \
  -c "SELECT * FROM whatsapp_consent WHERE remote_jid='5511999999999@s.whatsapp.net';"

# Ver logs
docker logs cartorio_api --since 5m 2>&1 | grep -E 'whatsapp.*consent'
```

### Causas Comuns

| Sintoma | Causa | Fix |
|---|---|---|
| INSERT não aconteceu | Bot detectou comando errado | Conferir `detect_command("aceito")` |
| INSERT mas bot não responde | `consent_granted` flag não foi setada | Reiniciar bot / clear cache |
| Cliente digitou "aceito" com acento | `==` comparação exata falha | Usar `.lower().strip()` |

### Fix

```python
# whatsapp.py
async def whatsapp_consent_handler(remote_jid: str, text: str) -> bool:
    text_lower = text.lower().strip()
    if text_lower in ["1", "aceito", "aceitar", "sim", "ok"]:
        await db.execute(
            """INSERT INTO whatsapp_consent (remote_jid, granted_at)
               VALUES (:j, NOW())
               ON CONFLICT (remote_jid) DO UPDATE SET granted_at = NOW(), revoked_at = NULL""",
            {"j": remote_jid},
        )
        return True  # granted
    elif text_lower in ["2", "não aceito", "nao aceito", "não", "nao"]:
        return False  # denied → HITL
    return None  # resposta não reconhecida → re-perguntar
```

## 9. HITL Chatwoot offline

### Sintoma

`/humano` retorna erro ou timeout.

### Diagnóstico

```bash
curl -sS https://chatwoot.2notasudi.com.br/api/v1/accounts/1 \
  -H "api_access_token: $CHATWOOT_API_ACCESS_TOKEN"
```

### Fix

```bash
# Restart Chatwoot
docker service update --force cartorio_chatwoot-web
docker service update --force cartorio_chatwoot-sidekiq

# Se Postgres do Chatwoot offline:
docker service update --force cartorio_chatwoot-postgres

# Conferir inbox_id correto
curl -sS https://chatwoot.2notasudi.com.br/api/v1/accounts/1/inboxes \
  -H "api_access_token: $CHATWOOT_API_ACCESS_TOKEN" | jq '.[] | {id, name}'
```

### Fallback

Se Chatwoot offline, `/humano` envia email para `atendimento@cartorio2notas.com.br`.

## 10. Circuit breaker travado OPEN

### Sintoma

Provider marcado OPEN mas já está UP novamente. Sistema não tenta usar.

### Diagnóstico

```bash
# Ver estado
curl -sS http://cartorio_api:8000/metrics | grep circuit_state
# bot_circuit_state{provider="opencode_free_2"} 1  (OPEN)
```

### Fix

```bash
# Opção 1: aguardar 60s (auto-recovery para HALF_OPEN)
sleep 60
curl -sS http://cartorio_api:8000/metrics | grep circuit_state

# Opção 2: reset manual (admin)
curl -X POST http://cartorio_api:8000/admin/circuit/reset \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{"provider": "opencode_free_2"}'

# Opção 3: restart API (estado em memória)
docker service update --force cartorio_api
```

### Prevenção

Não abrir circuit prematuramente:
- `failure_threshold = 3` (3 falhas consecutivas)
- `recovery_timeout = 60s` (não 5min para cartório de baixo tráfego)

## 11. PII leak no output do LLM

### Sintoma

Resposta do bot contém CPF/RG/email que deveria estar redactado.

### Diagnóstico

```bash
# Ver logs
docker logs cartorio_api --since 1m 2>&1 | grep -E 'PII detected in output'

# Buscar output específico
docker logs cartorio_api --since 1h 2>&1 | grep '"scrubbed_text"' | grep -E 'cpf|rg|email'
```

### Causa

LLM alucinou e reproduziu PII do treino (raro mas possível).

### Fix Automático

```python
# chat_pipeline.py
async def process_message(msg):
    response = await call_llm_with_fallback(text)
    scrubbed, count = scrub_pii_3_layers(response)
    if count > 0:
        logger.warning("PII detectada no output do LLM", extra={"redaction_count": count})
        # Fail-safe: substitui resposta
        return OutboundMessage(
            text="🔒 Resposta automática pode ter conteúdo sensível. Vou transferir para humano.",
        )
        # Aciona HITL
        await create_handover(...)

    return OutboundMessage(text=scrubbed)
```

### Fix Manual (revisar prompt)

```python
# Reforçar no system prompt
SYSTEM_PROMPT = """Você é um assistente do Cartório 2º Notas.
NUNCA inclua dados pessoais (CPF, RG, email, telefone) na resposta.
Se o usuário fornecer dados pessoais, apenas confirme que foram recebidos
e NÃO os repita na resposta.

Responda sempre em português brasileiro, tom formal e respeitoso.
"""
```

## 12. Latência P95 > 15s

### Diagnóstico

```bash
# Ver métricas
curl -sS http://cartorio_api:8000/metrics | grep 'bot_latency_seconds{quantile="0.95"}'

# Grafana dashboard
open https://grafana.2notasudi.com.br/d/bot-latency
```

### Causas Comuns

| Causa | Latência típica | Fix |
|---|---|---|
| LiteLLM lento (queue NVIDIA) | 12-15s | Trocar para opencode_free_1 direto |
| OpenClaw local lento | 15-20s | Verificar CPU/MEM container |
| Redis lento (network) | +500ms | Verificar docker network |
| Evolution API lenta | +2s | Verificar latency para whatsapp.2notasudi.com.br |

### Fix Imediato

```bash
# Restart LiteLLM (limpa queue)
docker service update --force cartorio_litellm-app

# Se persistir: kill LiteLLM temporariamente (bot usa fallback opencode_free_1)
docker service scale cartorio_litellm-app=0

# Monitorar por 5 min
watch -n 30 'curl -sS http://cartorio_api:8000/metrics | grep "bot_latency_seconds{quantile="0.95""}'
```

### Fix Definitivo

Ajustar timeout no LiteLLM:
```yaml
# infra/litellm/config.yaml
router_settings:
  timeout: 10  # era 15s, reduzir para 10s (fallback mais rápido)
```

## 🆘 Escalation

Se nenhum dos procedimentos resolve:

1. **Coletar evidências**:
   ```bash
   docker logs cartorio_api --since 5m > /tmp/api_logs.txt
   docker logs cartorio_litellm-app --since 5m > /tmp/litellm_logs.txt
   curl -sS https://api.2notasudi.com.br/api/v1/health/integracoes | jq . > /tmp/health.json
   ```

2. **Notificar GRUPO Pietra (Telegram)** com attachment dos logs

3. **Abrir incidente** em `/incidents/` (template em [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md))

4. **Master Agent** (4 agents paralelos) assume debug

## 📚 Referências

- [`BOTS.md`](BOTS.md) — overview
- [`FALLBACK_CHAIN.md`](FALLBACK_CHAIN.md) — chain providers
- [`LGPD_BOTS.md`](LGPD_BOTS.md) — PII leak (item 11)
- [`EVOLUTION_API.md`](EVOLUTION_API.md) — WhatsApp (item 7)
- [`CHATWOOT_HANDOVER.md`](CHATWOOT_HANDOVER.md) — HITL (item 9)
- `backend/app/services/chat_pipeline.py` — código

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:39:30Z