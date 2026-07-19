# Fallback Chain — Runtime Contract and Historical Scenarios

> **Versão**: 4.0 (2026-07-19)
> **Status**: contrato de runtime atualizado; cenários abaixo são históricos e
> precisam de revalidação antes de serem usados como procedimento operacional.

## Contrato vigente (fonte: `backend/app/config.py` e `fallback.py`)

O código atual usa uma cadeia configurável de **14 slots**, nesta ordem padrão:

`opencode_zen_account_1 → opencode_zen_account_2 → opencode_zen_account_3 → opencode_free_3 → opencode_free_1 → opencode_free_2 → opencode_go → openrouter → groq → mistral → google_ai_studio → openclaw → jules → antigravity`.

O circuit breaker é persistido no Redis e o cooldown padrão é de **300 segundos**.
A cadeia padrão mantém 14 providers upstream; a cadeia também aceita
explicitamente o provider local `cache` como último recurso. `cache` devolve uma
mensagem determinística de indisponibilidade, não consulta nem persiste as
mensagens recebidas, não depende de Redis e não toma decisões jurídicas. Ele
exige consentimento LGPD, assim como os demais caminhos. Providers Zen sem
credencial podem ser ignorados, mas providers não configurados continuam
fail-closed por contrato.

## 🎯 Visão Geral

O Cartório usa **fallback chain de 7 providers** para garantir 99.9% de disponibilidade. Quando um provider falha (5xx, timeout, 429), o sistema automaticamente tenta o próximo em <2s.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   FALLBACK CHAIN (chat_pipeline)                    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
              ┌─────────────────────────────────────┐
              │ 1. LiteLLM Proxy (PRIMARY)          │
              │    cartorio_litellm-app:4000        │
              │    model: opencode-free-1           │
              │    Latência: 4-10s · SLA: 99%       │
              └────────────┬────────────────────────┘
                           │ (5xx ou timeout > 15s)
                           ▼
              ┌─────────────────────────────────────┐
              │ 2. opencode_free_1 (nemotron)       │
              │    NVIDIA nemotron-3-ultra-free     │
              │    1M ctx · Latência: 2-4s          │
              └────────────┬────────────────────────┘
                           │ (429 rate limit)
                           ▼
              ┌─────────────────────────────────────┐
              │ 3. opencode_free_2 (mimo)           │
              │    Xiaomi mimo-v2.5-free            │
              │    1M ctx · Latência: 2-5s          │
              └────────────┬────────────────────────┘
                           │ (503 service unavailable)
                           ▼
              ┌─────────────────────────────────────┐
              │ 4. opencode_free_3 (deepseek)       │
              │    DeepSeek v4-flash-free           │
              │    1M ctx · Latência: 3-6s          │
              └────────────┬────────────────────────┘
                           │ (timeout > 10s)
                           ▼
              ┌─────────────────────────────────────┐
              │ 5. opencode_go (M3 via Zen)         │
              │    MiniMax-M3 via opencode.ai/zen  │
              │    32K ctx · Latência: 1-3s         │
              └────────────┬────────────────────────┘
                           │ (5xx)
                           ▼
              ┌─────────────────────────────────────┐
              │ 6. openclaw (local fallback)        │
              │    Container openclaw               │
              │    Sem rede · Latência: 5-15s       │
              └────────────┬────────────────────────┘
                           │ (Redis offline)
                           ▼
              ┌─────────────────────────────────────┐
              │ 7. Cache local (se configurado)     │
              │    Resposta determinística         │
              │    sem PII, sem decisão jurídica  │
              └─────────────────────────────────────┘
```

## 📋 Configuração LiteLLM

**Arquivo**: `infra/litellm/config.yaml`

```yaml
model_list:
  - model_name: opencode-free-1
    litellm_params:
      model: openai/nemotron-3-ultra-free
      api_base: https://integrate.api.nvidia.com/v1
      api_key: os.environ/OPENCODE_FREE_1_API_KEY

  - model_name: opencode-free-2
    litellm_params:
      model: openai/mimo-v2.5-free
      api_base: https://api.xiaomimimo.com/v1
      api_key: os.environ/OPENCODE_FREE_2_API_KEY

  - model_name: opencode-free-3
    litellm_params:
      model: openai/deepseek-v4-flash-free
      api_base: https://api.deepseek.com/v1
      api_key: os.environ/OPENCODE_FREE_3_API_KEY

  - model_name: opencode-go
    litellm_params:
      model: openai/minimax-m3
      api_base: https://opencode.ai/zen/v1
      api_key: os.environ/OPENCODE_GO_API_KEY

  - model_name: mistral-free
    litellm_params:
      model: openai/mistral-free
      api_base: https://api.mistral.ai/v1
      api_key: os.environ/MISTRAL_FREE_API_KEY

  - model_name: openrouter-free
    litellm_params:
      model: openrouter/free
      api_key: os.environ/OPENROUTER_API_KEY

  - model_name: gemini-free
    litellm_params:
      model: google/gemini-2.0-flash-exp
      api_key: os.environ/GEMINI_FREE_API_KEY

router_settings:
  num_retries: 3
  timeout: 15
  allowed_fails: 3
  cooldown_time: 60
```

## ⚡ Circuit Breaker Pattern

### Implementação

**Arquivo**: `backend/app/integrations/fallback.py`

```python
class CircuitBreaker:
    """Circuit breaker per-provider (não global)."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at: float | None = None

    def record_success(self):
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.time()

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.opened_at > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True  # testa 1 request
            return False  # rejeita
        # HALF_OPEN
        return True
```

### Comportamento

```
Estado       Transição       Ação
─────────    ──────────      ───────────────────────────
CLOSED       → OPEN          3 falhas consecutivas
CLOSED       → CLOSED        sucesso
OPEN         → HALF_OPEN     após 60s
OPEN         → OPEN          request rejeitado (fail-fast)
HALF_OPEN    → CLOSED        sucesso
HALF_OPEN    → OPEN          falha (volta a contar 60s)
```

### Métricas

```
bot_circuit_state{provider="litellm"} 0        # CLOSED
bot_circuit_state{provider="opencode_free_1"} 0
bot_circuit_state{provider="opencode_free_2"} 1  # OPEN
bot_circuit_state{provider="opencode_free_3"} 2  # HALF_OPEN
```

## 🔄 Retry com Exponential Backoff

```python
async def call_with_retry(provider_fn, max_retries: int = 3):
    """Retry com backoff 1s → 2s → 4s."""
    delays = [1, 2, 4]
    last_error = None

    for attempt in range(max_retries):
        try:
            return await provider_fn()
        except (TimeoutError, httpx.HTTPStatusError) as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(delays[attempt])
                continue
            raise

    raise last_error
```

**Não retentar** em:
- 400 Bad Request (input inválido)
- 401 Unauthorized (token errado)
- 403 Forbidden (sem permissão)

**Retentar** em:
- 429 Too Many Requests (rate limit)
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout
- Timeout (> 15s)

## 📊 Métricas por Provider

### Counter

```
bot_llm_requests_total{provider="litellm",status="ok"} 1234
bot_llm_requests_total{provider="litellm",status="fallback"} 12
bot_llm_requests_total{provider="opencode_free_1",status="ok"} 45
bot_llm_requests_total{provider="opencode_free_1",status="error"} 3
```

### Histogram (latência)

```
bot_llm_latency_seconds{provider="litellm",quantile="0.5"} 5.2
bot_llm_latency_seconds{provider="litellm",quantile="0.95"} 9.8
bot_llm_latency_seconds{provider="litellm",quantile="0.99"} 14.5
bot_llm_latency_seconds{provider="opencode_free_1",quantile="0.95"} 3.2
```

### Gauge (circuit state)

```
bot_circuit_state{provider="litellm"} 0
bot_circuit_state{provider="opencode_free_1"} 0
```

## ✅ Validação E2E

### T31 — LiteLLM UP (response 4-10s)

```bash
# Test
CID=$(docker ps --filter 'name=^cartorio_api' --format '{{.ID}}' | head -1)
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"update_id":1,"message":{"message_id":1,"date":0,"chat":{"id":6682284055,"type":"private"},"from":{"id":6682284055,"is_bot":false,"first_name":"G"},"text":"oi"}}' \
  https://api.2notasudi.com.br/api/v1/telegram/webhook
sleep 12

# Expect: sent=True em ~10s usando LiteLLM → opencode-free-1
docker logs $CID --since 1m 2>&1 | grep -E 'provider=|sent='
# Esperado: provider=litellm:opencode-free-1 sent=True latency_ms=8234
```

### T32 — LiteLLM DOWN → opencode_free_1 (2-4s)

```bash
# Kill LiteLLM
docker service update --force cartorio_litellm-app  # (mas scale 0)
docker service scale cartorio_litellm-app=0

# Test
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"update_id":2,"message":{...}}' \
  https://api.2notasudi.com.br/api/v1/telegram/webhook
sleep 8

# Expect: sent=True em ~5s usando fallback opencode_free_1
docker logs $CID --since 1m 2>&1 | grep -E 'fallback|sent='
# Esperado: fallback=opencode_free_1 sent=True latency_ms=4200

# Restore
docker service scale cartorio_litellm-app=1
```

### T33 — opencode_free_1 429 → opencode_free_2

```bash
# Mock 429 no opencode_free_1 (não-trivial, requer mock no código OU falha real do provider)
# Alternativa: validar em staging via integration test
pytest tests/integration/test_fallback_chain.py::test_429_to_opencode_free_2 -v
```

### T34-T35 — opencode_free_2 503 + todos DOWN

```bash
# Similar ao T33, integration test
pytest tests/integration/test_fallback_chain.py -v

# Para "todos DOWN": derrubar todos containers
docker service scale cartorio_litellm-app=0
docker service scale cartorio_openclaw=0

# Para habilitar o último recurso local, inclua `cache` no final de
# LLM_FALLBACK_CHAIN. A resposta é determinística e não usa o conteúdo da
# requisição: "O atendimento automatizado está temporariamente indisponível..."
```

### T36 — Circuit Breaker

```bash
# Forçar 3 falhas em opencode_free_2 (mock 500)
for i in 1 2 3; do
  curl -X POST https://api.2notasudi.com.br/api/v1/test/fail-provider/opencode_free_2
done

# Verificar circuit OPEN
curl -sS http://cartorio_api:8000/metrics | grep circuit_state
# Esperado: bot_circuit_state{provider="opencode_free_2"} 1  (OPEN)
```

### T37 — Retry Exponential Backoff

```bash
# Integration test
pytest tests/integration/test_retry_backoff.py -v
# Verifica: 1ª tentativa em t=0, 2ª em t=1s, 3ª em t=3s
```

### T38 — Métricas por Provider

```bash
# Grafana: http://grafana.2notasudi.com.br/d/bot-llm
# Dashboard: Bot LLM Latency by Provider
# Mostra: p50/p95/p99 por provider + success rate
```

### T39 — Documentação ✅

Este arquivo.

### T40 — E2E Fallback Completo

```bash
# Validar LiteLLM→opencode→openclaw→cache (todos os 4 níveis)
pytest tests/e2e/test_fallback_complete.py -v

# Expect: 4 cenários, 4 providers testados, todos com fallback success
```

## 🔍 Logs Estruturados

```json
{
  "timestamp": "2026-07-09T16:30:00Z",
  "level": "INFO",
  "logger": "chat_pipeline",
  "msg": "LLM call fallback",
  "provider_primary": "litellm:opencode-free-1",
  "provider_fallback": "opencode_free_1:nemotron",
  "error_primary": "litellm.BadRequestError: upstream 422",
  "latency_ms_primary": 8234,
  "latency_ms_fallback": 2040,
  "circuit_state_primary": "CLOSED",
  "circuit_state_fallback": "CLOSED"
}
```

## 🛠️ Troubleshooting

### Todos providers DOWN

1. Verificar conectividade internet: `docker exec cartorio_api curl https://integrate.api.nvidia.com`
2. Verificar Redis: `docker exec cartorio_redis redis-cli PING`
3. Ver logs: `docker logs cartorio_api --since 5m 2>&1 | grep -E 'fallback|circuit'`
4. Fallback final opcional: adicione `cache` ao chain para retornar uma
   mensagem estática LGPD-safe sem depender de upstream ou Redis.

### Circuit OPEN travado

```bash
# Reset manual
curl -X POST http://cartorio_api:8000/admin/circuit/reset \
  -H "X-API-Key: $ADMIN_API_KEY"

# Ou aguardar 60s (auto-recovery)
```

Ver [`TROUBLESHOOTING_BOTS.md`](TROUBLESHOOTING_BOTS.md).

## 📚 Referências

- [`BOTS.md`](BOTS.md) — overview
- [`CHANGELOG_BOTS.md`](CHANGELOG_BOTS.md) — v1.0 → v2.0 → v3.0
- `backend/app/integrations/fallback.py` — código
- `infra/litellm/config.yaml` — config LiteLLM
- Lesson 128 (LiteLLM 422 → opencode_free_1 salvou)
- Lesson 142 (fallback chain validado 1x)
- Lesson 148 (circuit breaker pattern)

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:37:30Z
**Lesson**: 128, 142, 148
