# Monitoring Guide — Cartório Chatbot

> Guia operacional de monitoramento, alertas e observabilidade.
> Última atualização: 2026-06-26.

## TL;DR

Sistema de monitoramento em **3 camadas**:
1. **Sintético** (health checks 30s) — detecta DOWN
2. **Métricas** (Prometheus 15s) — detecta degradação
3. **Logs** (estruturados JSON) — investiga causa raiz

Dashboards: Grafana (a configurar) + `/api/v1/health/radar` (tempo real) + Chatwoot inbox (HITL).

---

## 1. Health Checks (Sintético)

### 1.1 Endpoints de Health

```bash
# Todos os 8 serviços (1 chamada)
curl -s https://api.2notasudi.com.br/api/v1/health/radar | jq

# Individual
curl -fsS https://api.2notasudi.com.br/health
curl -fsS https://flow.2notasudi.com.br/healthz
curl -fsS https://whatsapp.2notasudi.com.br/
curl -fsS https://chat.2notasudi.com.br/api/v1/accounts
curl -fsS https://supbase.2notasudi.com.br/auth/v1/health
curl -fsS https://agent.2notasudi.com.br/health

# Redis (via Tailscale)
ssh root@100.99.172.84 "redis-cli -p 1001 -a \$REDIS_AUTH PING"
```

### 1.2 Script Automatizado

```bash
# Local
./infra/monitoring/health_check_all.sh

# Output esperado
[OK] api.2notasudi.com.br → 200 (142ms)
[OK] flow.2notasudi.com.br → 200 (98ms)
[OK] whatsapp.2notasudi.com.br → 200 (87ms)
[OK] chat.2notasudi.com.br → 200 (201ms)
[OK] supbase.2notasudi.com.br → 200 (76ms)
[OK] agent.2notasudi.com.br → 200 (54ms)
[OK] redis → PONG (12ms)
[OK] easypanel.2notasudi.com.br → 200 (162ms)
```

### 1.3 Frequência

| Camada | Frequência | Ferramenta |
|--------|-----------|------------|
| **API radar** | 30s | N8N WF #11 (cron) |
| **Backup status** | 60min | N8N WF #21 (cron) |
| **Audit dead man's switch** | 60min | N8N WF #22 (cron) |
| **Audit verify diário** | 24h @ 03:30 | N8N WF #08 (cron) |
| **Stale detector** | 24h | N8N WF #23 (cron) |
| **Cleanup** | 24h @ 04:30 | N8N WF #24 (cron) |
| **Metrics collection** | 5min | N8N WF #25 (cron) |

---

## 2. Métricas (Prometheus)

### 2.1 Endpoints de Métricas

```bash
# API FastAPI
curl -fsS https://api.2notasudi.com.br/metrics

# N8N (interno)
ssh root@100.99.172.84 "curl -fsS http://n8n:5678/metrics"

# OpenClaw Gateway
curl -fsS https://agent.2notasudi.com.br/metrics
```

### 2.2 Métricas-Chave (SLO)

| Métrica | Label | Threshold Alerta |
|---------|-------|------------------|
| `api_requests_total` | status, method, path | error rate > 1% |
| `api_request_duration_seconds` | endpoint | p95 > 500ms |
| `n8n_wf_executions_total` | workflow, status | failure rate > 5% |
| `n8n_wf_latency_seconds` | workflow | p99 > 30s |
| `openclaw_ws_connections_active` | — | < 1 (sem clientes) |
| `openclaw_messages_total` | direction, status | error rate > 2% |
| `audit_log_size` | — | delta < 1/h (dead man's switch) |
| `redis_used_memory_bytes` | — | > 80% maxmemory |
| `supabase_connections_active` | db | > 80% max_connections |

### 2.3 Dashboard Grafana (JSON)

Localização: `infra/monitoring/grafana-dashboards/cartorio-overview.json`

Importar:
1. Grafana → Dashboards → Import
2. Upload JSON file
3. Selecionar Prometheus datasource
4. Save & View

Panels incluídos:
- Service health (8 panels)
- API p50/p95/p99 latency
- N8N WF success rate (34 WFs)
- OpenClaw message throughput
- Audit log velocity
- Backup status
- LGPD consent rate

---

## 3. Logs Estruturados

### 3.1 Formato

Todos os serviços emitem JSON estruturado:

```json
{
  "ts": "2026-06-26T17:30:00.123Z",
  "level": "INFO",
  "service": "api",
  "correlation_id": "abc-123-xyz",
  "method": "POST",
  "path": "/api/v1/atendimento",
  "status": 200,
  "duration_ms": 142,
  "user_id": "uuid",
  "ip": "187.77.236.77",
  "msg": "atendimento criado"
}
```

### 3.2 PII Scrub (LGPD)

**PIIs removidos antes de logar**:
- CPF, RG, CNH, passport
- Phone numbers
- Email addresses
- Cartório-specific data (CNS, hash cliente)

Implementado em `backend/app/middleware/pii_scrub.py` (Pydantic V2 + regex).

### 3.3 Agregação Loki (Futuro J08)

**Stack proposta**:
- Promtail → coletar logs
- Loki → armazenar
- Grafana → query/visualizar

Status: J08 PENDENTE (script de setup em `infra/logging/loki-stack.yml`).

---

## 4. Alertas (Telegram)

### 4.1 Níveis

| Nível | Cor | Ação |
|-------|-----|------|
| **P0** Critical | 🔴 Vermelho | Imediato (< 5min) — Gustavo + Equipe |
| **P1** High | 🟠 Laranja | < 30min — Equipe técnica |
| **P2** Medium | 🟡 Amarelo | < 2h — Backlog |
| **P3** Low | 🔵 Azul | Próximo expediente |

### 4.2 Configuração

Token Telegram: `8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q`
Bot: `@test_cartorio_bot`
Chat: Gustavo DM (6682284055) + Squad (-5006771024)

Webhook: `https://api.2notasudi.com.br/api/v1/alerts/telegram`

### 4.3 Templates de Alerta

```yaml
service_down:
  message: |
    🔴 CRÍTICO: {service} está DOWN
    Host: {host}
    Latência: {latency_ms}ms
    Última resposta OK: {last_ok}
    Ação: verificar /health/radar
    
high_error_rate:
  message: |
    🟠 ALERTA: {service} error rate = {rate}%
    Threshold: 1%
    Últimos 5min
    Logs: https://grafana.2notasudi.com.br/d/errors
    
backup_failed:
  message: |
    🔴 BACKUP FALHOU
    Tipo: {backup_type}
    Tamanho esperado: {expected_mb}MB
    Erro: {error_msg}
    Ação: verificar /var/log/backup.log
    
audit_dead_man:
  message: |
    🔴 AUDIT LOG PARADO
    Última inserção: {last_insert_age}h
    Threshold: 1h
    Ação: investigar /api/v1/admin/audit/health
```

### 4.4 Silêncio Programado

```bash
# Suprimir alertas por X minutos
curl -X POST https://api.2notasudi.com.br/api/v1/alerts/silence \
  -H "X-API-Key: $API_KEY" \
  -d '{"service":"api","duration_min":30,"reason":"deploy em progresso"}'
```

---

## 5. SLI / SLO

### 5.1 Definições (2026-Q2)

| Serviço | SLI | SLO Target | Error Budget (30d) |
|---------|-----|-----------|---------------------|
| **API** | availability (200 OK) | 99.5% | 3.6h |
| **API** | latency p95 < 500ms | 95% requests | 5% |
| **N8N** | WF success rate | 99% | 1% |
| **N8N** | WF latency p99 < 30s | 95% WFs | 5% |
| **OpenClaw** | WS connection success | 99% | 1% |
| **OpenClaw** | response time p95 < 5s | 95% messages | 5% |
| **Supabase** | query success rate | 99.9% | 0.1% |
| **Supabase** | query latency p95 < 200ms | 95% queries | 5% |
| **Redis** | PING success | 99.99% | 0.01% |
| **Backup** | daily backup success | 100% | 0% |

### 5.2 Error Budget Burn Rate

```promql
# Burn rate API (5min window)
(
  sum(rate(api_requests_total{status=~"5.."}[5m]))
  /
  sum(rate(api_requests_total[5m]))
) > (1 - 0.995) * 14.4  # 14.4x burn = 1h budget
```

### 5.3 Relatório Mensal

**Gerado automaticamente** em `infra/monitoring/slo-report.sh` (cron mensal 1º dia).

Output: `docs/architecture/slo-report-YYYY-MM.md`

---

## 6. Troubleshooting Rápido

### 6.1 Serviço DOWN

```bash
# 1. Verificar se container está UP
ssh root@100.99.172.84 "docker service ps cartorio_{service} --no-trunc"

# 2. Ver logs
ssh root@100.99.172.84 "docker service logs cartorio_{service} --tail 100"

# 3. Ver healthcheck
ssh root@100.99.172.84 "docker inspect $(docker ps -qf 'name=cartorio_{service}') --format '{{json .State.Health}}' | jq"

# 4. Restart se necessário
ssh root@100.99.172.84 "docker service update --force cartorio_{service}"

# 5. Verificar se voltou
sleep 30 && curl -fsS https://{service}.2notasudi.com.br/health
```

### 6.2 Erro 5xx persistente

```bash
# Ver últimas 50 requests com erro
curl -fsS "https://api.2notasudi.com.br/admin/slow-queries?status=5xx&limit=50" \
  -H "X-API-Key: $API_KEY"

# Ver audit_log do período
psql $SUPABASE_URL -c "SELECT * FROM audit_log WHERE created_at > NOW() - INTERVAL '1 hour' AND status >= 500 ORDER BY created_at DESC LIMIT 20"
```

### 6.3 Backup não rodou

```bash
# 1. Verificar cron
ssh root@100.99.172.84 "cat /etc/cron.d/cartorio-backup"

# 2. Rodar manualmente
ssh root@100.99.172.84 "/usr/local/bin/cartorio-backup.sh"

# 3. Verificar resultado
ssh root@100.99.172.84 "ls -lah /var/backups/cartorio/ | tail -10"

# 4. Validar
curl -fsS https://api.2notasudi.com.br/api/v1/health/backup -H "X-API-Key: $API_KEY"
```

### 6.4 OpenClaw sem responder

```bash
# 1. Verificar se está UP
curl -fsS https://agent.2notasudi.com.br/health

# 2. Se UP mas não responde, ver logs
ssh root@100.99.172.84 "docker service logs cartorio_openclaw-gateway --tail 100"

# 3. Verificar configuração
ssh root@100.99.172.84 "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json"

# 4. Restart
ssh root@100.99.172.84 "docker service update --force cartorio_openclaw-gateway"
```

---

## 7. Contatos

| Quem | Quando | Como |
|------|--------|------|
| **Gustavo (CEO)** | P0 | Telegram DM 6682284055 |
| **Squad Pietra** | P1+ | Telegram grupo -5006771024 |
| **DPO** | LGPD | dpo@2notasudi.com.br |
| **Hostinger Support** | VPS DOWN | portal.hostinger.com |
| **Cloudflare** | DNS | dashboard.cloudflare.com |

---

**Mantido por**: Pietra (orquestrador) + cartorio-dev (noturno)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
