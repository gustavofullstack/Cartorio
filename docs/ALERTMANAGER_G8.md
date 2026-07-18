# AlertManager → Telegram (LGPD-safe) — G8.15.T2

Pipeline: **Prometheus → AlertManager → FastAPI webhook (`/api/v1/webhook/alertmanager/*`) → formatador LGPD-safe → Telegram Bot API → chat do escrevente**.

Implementação offline-friendly (não exige VPS/AlertManager live para validar):
- `infra/observability/alertmanager.yml` — config canônica do AlertManager (referência de produção).
- `scripts/alert_to_telegram.py` — script standalone (CLI, dry-run + apply) que faz exatamente o que o endpoint faz.
- `backend/app/api/v1/alertmanager.py` — endpoint FastAPI registrado em `api_router`, prefix `/webhook/alertmanager`.

## TL;DR — Setup em 1 página

1. Copiar config para a VPS:
   ```bash
   scp infra/observability/alertmanager.yml root@vps:/etc/alertmanager/alertmanager.yml
   ssh root@vps "docker restart alertmanager"
   ```
2. Configurar secrets (NUNCA commitados):
   ```bash
   mkdir -p /etc/alertmanager/secrets
   echo -n "$TELEGRAM_BOT_TOKEN" > /etc/alertmanager/secrets/telegram_bot_token
   echo -n "$TELEGRAM_CHAT_ID_P0" > /etc/alertmanager/secrets/telegram_grupo_pietra_chat_id
   chmod 600 /etc/alertmanager/secrets/*
   ```
3. Configurar DNS interno: `cartorio-api:8000` resolve para o serviço FastAPI no Docker Swarm.
4. Validar:
   ```bash
   curl -X POST https://api.2notasudi.com.br/api/v1/webhook/alertmanager \
        -H "Content-Type: application/json" \
        -d @sample-payload.json
   # Esperado: 202 Accepted
   ```

## Arquitetura

```
                    ┌──────────────────────────────────────────┐
                    │  Prometheus                              │
                    │  - Regras em /etc/prometheus/rules/      │
                    │  - Métricas: app_latency, dlq_depth,     │
                    │    error_rate, lgpd_*                    │
                    └────────────────┬─────────────────────────┘
                                     │ (push)
                                     ▼
                    ┌──────────────────────────────────────────┐
                    │  AlertManager                            │
                    │  - Config: infra/observability/          │
                    │    alertmanager.yml                      │
                    │  - Receivers: default | critical |       │
                    │    dlq | lgpd | n8n                      │
                    │  - Inhibit rules                         │
                    └────────────────┬─────────────────────────┘
                                     │ (webhook POST)
                                     ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  FastAPI backend — /api/v1/webhook/alertmanager/{route}     │
   │  1. Pydantic valida payload (extra=forbid)                  │
   │  2. HMAC optional (ALERTMANAGER_WEBHOOK_SECRET)             │
   │  3. Background task (NÃO bloqueia webhook)                  │
   │  4. Dedup via Redis SET NX TTL 60s (defesa em profundidade) │
   │  5. format_alert_message() — scrubber PII (3 camadas)       │
   │  6. httpx.AsyncClient POST → api.telegram.org               │
   │  7. AUTO-PURGE do payload (sem persistência)                │
   └────────────────┬────────────────────────────────────────────┘
                    │ (Bot API)
                    ▼
                    ┌──────────────────────────────────────────┐
                    │  Telegram do escrevente (chat privado    │
                    │  ou GRUPO PIETRA)                        │
                    │  - Mensagem LGPD-safe: só metadata       │
                    │  - Emojis: 🔴 P0 / ⚠️ P1 / ℹ️ P2        │
                    └──────────────────────────────────────────┘
```

## Receivers (severity → Telegram)

| Receiver | Severity | Repeat | LGPD | Descrição |
|----------|----------|--------|------|-----------|
| `cartorio-telegram-default` | qualquer (fallback) | 4h | ✅ scrubbed | Default — webhook `/webhook/alertmanager` |
| `cartorio-telegram-critical` | `severity=critical` | 1h | ✅ scrubbed | P0 — webhook `/webhook/alertmanager/critical` (sem dedup) |
| `cartorio-telegram-dlq` | `alertname=DLQOverflow` | — | ✅ scrubbed | DLQ — webhook `/webhook/alertmanager/dlq` (NO resolved) |
| `cartorio-telegram-lgpd` | `squad=cartorio-lgpd` | 12h | ✅ scrubbed | LGPD squad — webhook `/webhook/alertmanager/lgpd` |
| `cartorio-telegram-n8n` | `squad=cartorio-n8n` | 12h | ✅ scrubbed | N8N squad — webhook `/webhook/alertmanager/n8n` |

## LGPD — o que vai / o que NÃO vai pro Telegram

### ✅ Vai (metadata categórica)
- `alertname` (whitelist Pydantic — Pattern `^[a-zA-Z0-9_.-]+$`)
- `severity` (whitelist: `critical | warning | info`)
- `instance` (URL truncada, scrubbed se tiver PII)
- `squad` (whitelist: `cartorio-{dev,n8n,lgpd,data,front,sre}`)
- `status` (`firing | resolved`)
- `summary` — **SCRUBBED** (CPF/RG/email/telefone/protocolo → `[REDACTED]`)
- `description` — **SCRUBBED** (mesma lógica)
- `runbook_url` / `runbook` — URL externa, **SCRUBBED** se contiver PII

### ❌ NÃO vai (defense-in-depth em 3 camadas)
- Payload bruto AlertManager (auto-purge em memória após formatação)
- Labels não-canônicos (k8s_pod, container, etc — Pydantic `extra=forbid`)
- CPF, RG, email, telefone, PROT-XXXX-XXXXXX, ESCR-XXXXXX — substituídos por `[CPF_REDACTED]` etc.
- Mensagem inclui `<i>LGPD: CPF=1, EMAIL=2, ...</i>` apenas como AUDIT do que foi sanitizado.

### Camadas de proteção
1. **Camada 1 (input)**: Pydantic `extra="forbid"` rejeita campos não documentados no payload.
2. **Camada 2 (formatação)**: `_scrub_pii()` aplica regex em summary/description antes de montar a mensagem.
3. **Camada 3 (output)**: `_safe_str()` trunca e ainda aplica scrubber em qualquer label exposto.

Mesmo se uma camada falhar, as outras duas contêm o vazamento. Igual ao padrão PII já estabelecido em `app/services/pii.py`.

## Endpoints FastAPI

| Method | Path | Status | Notas |
|--------|------|--------|-------|
| POST | `/api/v1/webhook/alertmanager` | 202 | Default receiver (LGPD-safe, com dedup) |
| POST | `/api/v1/webhook/alertmanager/critical` | 202 | Critical P0 (sem dedup) |
| POST | `/api/v1/webhook/alertmanager/dlq` | 202 | DLQ Overflow (sem resolved) |
| POST | `/api/v1/webhook/alertmanager/lgpd` | 202 | Squad LGPD |
| POST | `/api/v1/webhook/alertmanager/n8n` | 202 | Squad N8N |

Resposta sempre 202 Accepted — webhook **NÃO bloqueia** AlertManager. Envio real ao Telegram acontece em BackgroundTask.

Resposta exemplo:
```json
{
  "status": "accepted",
  "receiver": "default",
  "alerts_received": 3,
  "alerts_critical": 1,
  "payload_status": "firing"
}
```

## Modo standalone (CLI)

Para testes locais sem precisar do AlertManager live:

```bash
# Dry-run: imprime a mensagem que SERIA enviada
python3 scripts/alert_to_telegram.py --input sample-payload.json

# Apply: envia Telegram real (requer TELEGRAM_BOT_TOKEN + chat_id)
python3 scripts/alert_to_telegram.py --input sample-payload.json --apply

# Via stdin (pipe do AlertManager)
curl -s http://alertmanager:9093/api/v1/alerts | python3 scripts/alert_to_telegram.py --apply

# Custom dedup window
python3 scripts/alert_to_telegram.py --input payload.json --dedup-window 300
```

## PromQL queries de exemplo (regras de alerta)

```yaml
# /etc/prometheus/rules/cartorio.yml
groups:
  - name: cartorio-app
    interval: 30s
    rules:
      # P0 — Error rate crítico
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
          squad: cartorio-sre
        annotations:
          summary: "Error rate > 5% por 2min"
          description: "Taxa de erros 5xx sustentada"
          runbook_url: "https://runbooks.2notasudi.com.br/high-error-rate"

      # P1 — DLQ overflow
      - alert: DLQOverflow
        expr: cartorio_dlq_pending > 100
        for: 5m
        labels:
          severity: warning
          squad: cartorio-sre
        annotations:
          summary: "DLQ com >100 mensagens pendentes"
          description: "Verificar consumers"

      # P1 — Latência alta
      - alert: HighLatencyP95
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 1.0
        for: 5m
        labels:
          severity: warning
          squad: cartorio-sre
        annotations:
          summary: "Latência p95 > 1s"

      # P0 — Backend down
      - alert: CartorioServiceDown5Min
        expr: up{job="cartorio-api"} == 0
        for: 5m
        labels:
          severity: critical
          squad: cartorio-sre
        annotations:
          summary: "cartorio-api offline > 5min"
```

## Testes (offline)

22 tests em `backend/tests/test_alert_to_telegram_g8.py` cobrem:

- **LGPD-safe formatting**: CPF/RG/email/telefone/PROTOCOL em labels → `[REDACTED]`
- **Pydantic strict**: extra=forbid rejeita payload com campos não documentados
- **Severity mapping**: critical/warning/info → emoji + tag P0/P1/P2
- **Dry-run**: CLI default NÃO chama Telegram Bot API
- **DedupCache**: janela de 60s suprime duplicatas
- **Endpoint FastAPI**: payload válido → 202; inválido → 422; campo extra → 422
- **YAML config**: estrutura válida, receivers canônicos presentes, severity routing

```bash
cd backend && uv run pytest tests/test_alert_to_telegram_g8.py --no-cov -v
# 22 passed in 0.48s
```

## LGPD-REVIEW gate (LGPD Art. 46)

Este pipeline foi desenhado com LGPD-by-design desde o início:
- Zero persistência de payload bruto (auto-purge em memória).
- Apenas metadata categórica chega ao Telegram.
- Qualquer label/annotation que contenha dado pessoal é REDACTED antes do envio.
- Audit de redactions fica no log da operação (não no Telegram) para SRE/DPO investigarem.

Revisão de sign-off `cartorio-lgpd` recomendada antes de ir para produção.

## Runbook de troubleshooting

| Sintoma | Causa provável | Fix |
|---------|----------------|-----|
| 401 no webhook | `ALERTMANAGER_WEBHOOK_SECRET` configurado mas faltou header | Enviar `X-AlertManager-Signature: <hmac>` |
| 422 no webhook | Payload não bate com Pydantic (extra field) | Conferir `infra/observability/alertmanager.yml` versão v4 |
| Telegram não recebe | `TELEGRAM_BOT_TOKEN` ou `TELEGRAM_CHAT_ID` faltando | Setar env vars no serviço cartorio-api |
| Mensagem duplicada | Dedup Redis caiu | Fail-open = envia duplicado. AlertManager `group_interval: 5m` já mitiga |
| `[CPF_REDACTED]` na mensagem | PII original foi sanitizado (LGPD OK) | Investigar origem do dado (annotation externa) |

Modified by Gustavo Almeida — G8.15.T2.
