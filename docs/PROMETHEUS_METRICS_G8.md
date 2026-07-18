# Prometheus AI/LLM Instrumentation — G8.15.T1

> Adicionado em 2026-07-18 por **cartorio-sre** (reins DevOps/SRE) na tarefa
> **G8.15.T1** do SUPER_PLANO_G8_100_TASKS.md.
>
> Owner: `cartorio-sre` · Reviewer: `cartorio-lgpd` (mudanca toca LGPD: labels) · Reviewer: `cartorio-dev` (mudanca toca `app/services/metrics.py`).

## O que foi adicionado

Quatro metricas Prometheus + um decorator reutilizavel para instrumentar
todas as chamadas LLM/AI do backend Cartorio (MiniMax-M3, LiteLLM proxy,
OpenClaw, OpenCode-Go e cia).

### 1. Metricas (expostas em `GET /api/v1/metrics/prometheus`)

| Nome                                       | Tipo    | Labels                          | Descricao                                       |
|--------------------------------------------|---------|----------------------------------|--------------------------------------------------|
| `cartorio_llm_call_seconds`                | summary | `model`, `operation`             | Latencia por chamada LLM (`_count`, `_sum`).      |
| `cartorio_llm_calls_total`                 | counter | `model`, `operation`, `status`   | Total de chamadas: `success` \| `error` \| `timeout` \| `rate_limited`. |
| `cartorio_llm_tokens_total`                | counter | `model`, `direction`             | Tokens consumidos: `input` \| `output`. Cumulativo. |
| `cartorio_llm_errors_total`                | counter | `model`, `operation`, `error_type` | Erros por classe de excecao canonica.           |

**Histograma vs Summary**: a renderer interna do `MetricsStore` expoe
histograms como `summary` (count + sum). Isso eh suficiente para `rate()`
no PromQL — para percentis p95/p99 reais, ver "Limitacoes conhecidas" abaixo.

### 2. Decorator `@instrument_llm`

```python
from app.services.metrics import instrument_llm

# Captura latency + status + tokens (sync ou async)
@instrument_llm(model="opencode_go", operation="chat", extract_tokens=...)
async def chat_with_fallback(messages): ...

# Apenas latency + status (sem contagem de tokens)
@instrument_llm(model="MiniMax_direct", operation="chat")
async def _chat_completion(messages): ...
```

Captura automaticamente:
- **latencia** (`cartorio_llm_call_seconds{model, operation}`)
- **status** (`cartorio_llm_calls_total{model, operation, status}`)
- **tipo de erro** (`cartorio_llm_errors_total{model, operation, error_type}`)
- **tokens** (via callback `extract_tokens` opcional — `cartorio_llm_tokens_total{model, direction}`)

LGPD-safe por design: decorator **rejeita** em tempo de decoracao qualquer
`model` ou `operation` que nao esteja em whitelist canonica. Cardinalidade
explodiria se aceitasse strings dinamicas.

### 3. Callers instrumentados

| Arquivo                                          | Funcao                | Label aplicado                              |
|--------------------------------------------------|------------------------|----------------------------------------------|
| `app/integrations/fallback.py`                   | `chat_with_fallback`   | `model="multi_provider", operation="chat"`   |
| `app/services/cartorio_agent.py`                 | `_chat_completion`     | `model="MiniMax_direct", operation="chat"`   |

## LGPD-by-design (P0)

Nenhuma das 4 metricas aceita valores dinamicos em labels. Whitelist
canonica enforced em `_ALLOWED_LLM_MODELS` / `_ALLOWED_LLM_OPERATIONS` /
`_ALLOWED_LLM_ERROR_TYPES` (ver `app/services/metrics.py`).

| Label       | Whitelist (canonical values)                                                                                                                                                  |
|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `model`     | `opencode_go` \| `MiniMax_direct` \| `litellm` \| `openclaw` \| `cache` \| `multi_provider` \| `test`                                                                         |
| `operation` | `chat` \| `tool_use` \| `embedding` \| `tts` \| `fast_path` \| `test`                                                                                                          |
| `status`    | `success` \| `error` \| `timeout` \| `rate_limited`                                                                                                                            |
| `direction` | `input` \| `output`                                                                                                                                                            |
| `error_type` | `TimeoutException` \| `HTTP_4XX` \| `HTTP_5XX` \| `ChatError` \| `JSONDecodeError` \| `ValueError` \| `TypeError` \| `KeyError` \| `RuntimeError` \| `ConnectionError` \| `UnknownError` |

**NUNCA** colocar em label:
- CPF / RG / CNS / CNH / titulo de eleitor (PII)
- email / telefone (PII)
- numero de protocolo / escritura / certidao (PII juridico)
- session_id / request_id / actor_id (PII indireto + cardinalidade)
- conteudo da mensagem (PII + cardinalidade)
- API key / token (secret)

A funcao `_classify_error` retorna **apenas** nomes canonicos de classe
(`UnknownError` para qualquer classe fora da whitelist) — assim a mensagem
do erro (que pode conter PII ecoado pelo LLM) **nunca** vira label.

## PromQL examples

```promql
# Latencia media por modelo (5min window)
sum by (model) (rate(cartorio_llm_call_seconds_sum[5m]))
  /
sum by (model) (rate(cartorio_llm_call_seconds_count[5m]))

# Latencia p95 por modelo (aproximacao via summary; para p95 real precisa
# de histograma nativo com buckets — ver "Limitacoes conhecidas")
sum by (model, le) (rate(cartorio_llm_call_seconds_sum[5m]))
  /
sum by (model, le) (rate(cartorio_llm_call_seconds_count[5m]))

# Error rate por modelo
sum by (model) (rate(cartorio_llm_calls_total{status="error"}[5m]))
  /
sum by (model) (rate(cartorio_llm_calls_total[5m]))

# Tipos de erro mais frequentes (top 5)
topk(5, sum by (error_type) (rate(cartorio_llm_errors_total[5m])))

# Custo em tokens por modelo (input + output)
sum by (model) (rate(cartorio_llm_tokens_total[1h])) * 3600

# Burn-rate de tokens de output vs limite mensal (ex: 10M tokens/mes)
sum(rate(cartorio_llm_tokens_total{direction="output"}[30d])) * 30 * 86400
```

## Alertas sugeridos (G8.15.T2 proximo passo)

```yaml
# alerts/llm_high_error_rate.yml
- alert: CartorioLLMHighErrorRate
  expr: |
    sum by (model) (rate(cartorio_llm_calls_total{status="error"}[5m]))
      /
    sum by (model) (rate(cartorio_llm_calls_total[5m]))
      > 0.20
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "LLM {{ $labels.model }} com > 20% erros nos ultimos 5min"

# alerts/llm_high_latency.yml
- alert: CartorioLLMHighLatencyP95
  expr: |
    sum by (model) (rate(cartorio_llm_call_seconds_sum[5m]))
      /
    sum by (model) (rate(cartorio_llm_call_seconds_count[5m]))
      > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "LLM {{ $labels.model }} latencia media > 10s"
```

## Limitacoes conhecidas

1. **Histogram como Summary**: o `MetricsStore` interno expoe histogramas
   como `summary` (count + sum) por design — suficiente para `rate()`
   medio, mas **NAO permite calcular percentis reais (p95/p99)** no
   PromQL. Para resolver: migrar para `prometheus_client.Histogram`
   nativo com buckets (work separado; precisa adicionar dep).

2. **Token extraction opcional**: o decorator usa `extract_tokens`
   callback opcional. Em callers que NAO retornam um objeto com
   `tokens_in`/`tokens_out` (ex: `_chat_completion` em
   `cartorio_agent.py`), os tokens NAO sao contados — apenas latency +
   status. Refactor futuro pode expor `usage` em todos os retornos.

3. **Sem cold-start gauge de LLM**: diferente de `agent_latency_seconds`,
   `cartorio_llm_call_seconds` nao tem gauge separado. Use
   `cartorio_llm_calls_total` zerado para evitar no-data em Grafana.

## Onde mexer se voce quiser adicionar uma nova metrica

1. Adicione o helper em `app/services/metrics.py::MetricsStore`
   (padrao: `_make_metric_or_skip_test` + `inc_counter` ou
   `observe_histogram`).
2. Documente aqui nesta pagina (LGPD-safe labels enforced).
3. Adicione testes em `tests/test_metrics_llm_g8.py` (se for AI/LLM) ou
   `tests/test_metrics.py` (caso geral).
4. Review LGPD se a metrica toca dados sensiveis.

Modified by Gustavo Almeida (via cartorio-sre) — G8.15.T1 — 2026-07-18