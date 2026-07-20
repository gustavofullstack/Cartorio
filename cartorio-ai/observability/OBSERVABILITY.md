# OBSERVABILITY

Observabilidade do sistema (2026-07-20).

## Stack

- **Métricas**: Prometheus em `/metrics` (API) + radar agregado `/api/v1/health/radar`.
- **Tracing**: OpenTelemetry inicializado no lifespan; spans por request e por chamada LLM.
- **Logs**: estruturados com `RequestContext` (request_id); filtro `log_masker.py` strip PII em todos os handlers.
- **Erros**: Sentry com `before_send` scrubber — exceções nunca carregam PII.
- **Alertas**: AlertManager → Telegram do escrevente (sem PII no payload).

## Sinais-chave

| Sinal | Fonte | Limiar |
|---|---|---|
| Webhook Telegram 200/401/5xx | contador por resultado | 5xx = 0 (design); 401 > limiar → alerta |
| Latência webhook→resposta | histograma (inclui debounce 1.2s) | p95 monitorado |
| `response_sent=0` com tráfego | derivado | alerta imediato |
| Fallback LLM esgotado | contador por slot/provider | alerta + degradação amigável |
| Audit chain check | dead-man's-switch 15min | quebra = P0 |
| Slow requests | middleware SlowLog | log acima do budget |

## Regras LGPD em telemetria

- Labels de métricas nunca incluem `chat_id`, username, CPF ou protocolo.
- Traces carregam apenas IDs internos opacos.
- Dashboards e SLOs em `observability/DASHBOARDS.md` / `observability/SLO.md`.

## Verificação rápida

```bash
make -C backend smoke     # /health, /ready, radar
curl -s localhost:8000/metrics | head   # na VPS
```
