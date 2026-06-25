# 📊 SLA — Service Level Agreements — C12

> **SQUAD C** | **Owner**: cartorio-zcode
> **Data**: 2026-06-26
> **Status**: ✅ DONE

Acordos de Nível de Serviço (SLAs) para o sistema Cartório 2º Notas.

---

## 🎯 SLAs por Serviço

### 1. API FastAPI (api.2notasudi.com.br)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.5% mensal | Health check a cada 5min |
| **Latência p50** | < 200ms | Métrica Prometheus |
| **Latência p95** | < 500ms | Métrica Prometheus |
| **Latência p99** | < 1500ms | Métrica Prometheus |
| **Error rate 5xx** | < 0.5% | Métrica Prometheus |
| **Rate limit** | 100 req/min/cliente | Redis-backed |
| **Throughput** | 50 req/s sustentado | Benchmarks |
| **Recovery RTO** | < 30min | Restart via Swarm |
| **Recovery RPO** | < 1h (backup incremental) | pg_basebackup 4x/dia |

**Endpoints críticos** (RTO < 5min):
- `/api/v1/health/*` — health checks
- `/api/v1/atendimento/*` — fluxo WhatsApp principal
- `/api/v1/protocolos/*` — LGPD compliance
- `/api/v1/webhooks/evolution` — entrada WhatsApp

### 2. N8N Workflow Engine (flow.2notasudi.com.br)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.0% mensal | N8N healthz |
| **Latência WF execução** | < 30s p95 | Métrica Prometheus `n8n_wf_latency_seconds` |
| **Workflow success rate** | > 99% | Métrica `n8n_wf_executions_total` |
| **Error handler latency** | < 5min | Workflow #00 dispatch |
| **Workflow #07** | Aguarda cred Evolution | Bloqueio SUI |

### 3. Supabase (supbase.2notasudi.com.br)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.0% mensal | Auth health endpoint |
| **Query p95** | < 100ms | pg_stat_statements |
| **Slow query log** | > 200ms | A16 slow_log middleware |
| **Backup success rate** | 100% (4x/dia) | Cron pg_basebackup |
| **Backup RPO** | < 6h | 4 backups/dia (00/06/12/18 UTC) |
| **Migration success** | 100% (alembic) | Pipeline CI |
| **DB connections** | < 30 (pool 20 + 10 overflow) | A15 /admin/pool |

### 4. Evolution API (whatsapp.2notasudi.com.br)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.0% mensal | GET / |
| **Webhook delivery** | 100% (com retry 3x) | B07 aplicado |
| **Webhook latency** | < 2s p95 | Métrica Prometheus |
| **Message throughput** | 100 msg/min | Limite Meta |
| **Instance recovery** | < 5min | Restart container |

**Bloqueio atual**: Instance `cartorio-2notas` em state=close — Gustavo precisa escanear QR.

### 5. OpenClaw Agent (agent.2notasudi.com.br)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.0% mensal | GET /health |
| **Context size** | 1M tokens (P0 fix) | models.json |
| **Response latency** | < 5s p95 | Métrica Prometheus |
| **Thinking mode** | Adaptive ON | agent.json |
| **Skills ativas** | 7 (saudacoes, protocolo, etc) | IDENTITY.md |

### 6. Chatwoot CRM (chat.2notasudi.com.br)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.0% mensal | GET /api/v1/accounts |
| **Sidekiq queue** | < 100 jobs | Redis-backed |
| **HITL response time** | < 5min | Atendente manual |
| **Message delivery** | 100% (sem perda) | Audit log |

### 7. Redis (cache + sessions)

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.5% mensal | PING |
| **Cache hit rate** | > 80% | INFO stats |
| **Session TTL** | 30min (configurável) | TTL keys |
| **Memory usage** | < 80% | INFO memory |

### 8. Easypanel + Traefik

| Métrica | Target | Medição |
|---------|--------|---------|
| **Uptime** | 99.9% mensal | Easypanel health |
| **SSL renewal** | Automático (Let's Encrypt) | Traefik logs |
| **Container restart** | < 30s | Docker Swarm |

---

## 🚨 Acordos de Incidente

### Severidade P0 (Crítico — sistema DOWN)
- **Detecção**: < 5min (via health radar + alerta Telegram GRUPO PIETRA SQUAD)
- **Resposta**: < 15min (Gustavo + agent em alerta)
- **Resolução RTO**: < 1h
- **Comunicação**: Telegram DM + Squad grupo

### Severidade P1 (Alta — funcionalidade degradada)
- **Detecção**: < 15min
- **Resposta**: < 1h
- **Resolução RTO**: < 4h
- **Comunicação**: Squad grupo

### Severidade P2 (Média — feature impactada)
- **Detecção**: < 1h
- **Resposta**: < 4h
- **Resolução RTO**: < 1 dia
- **Comunicação**: Squad grupo (não-bloqueante)

### Severidade P3 (Baixa — cosmético)
- **Resposta**: < 1 semana
- **Resolução**: próximo sprint

---

## 📊 SLAs por Feature de Negócio

### Atendimento WhatsApp (fluxo principal)
- **Tempo até resposta inicial**: < 30s
- **Resolução completa**: < 24h úteis
- **HITL escalation**: < 15min em horário comercial
- **LGPD compliance**: 100% (todos os 6 direitos do titular)

### Consulta de Protocolo
- **Tempo de resposta**: < 2s
- **Disponibilidade**: 99% (8/8 serviços)
- **Audit trail**: 100% (LGPD art. 37 — 5 anos)

### Cálculo de Emolumentos
- **Tempo de resposta**: < 500ms
- **Precisão**: 100% (tabela oficial MG 2026)

### Agendamento
- **Slots disponíveis**: atualizado em tempo real
- **Confirmação**: < 1s
- **Notificação 24h antes**: automática (workflow N8N)

### Prospecção de Cartórios (feature)
- **Limite diário**: 10 mensagens/dia
- **Opt-out**: respeitado imediatamente
- **LGPD**: consent explícito obrigatório

---

## 📈 Monitoramento

### Ferramentas
- **Grafana**: dashboards em `infra/grafana/dashboards/`
  - cartorio-api-overview.json (uptime, audit, DB pool, clientes, protocolos)
  - cartorio-services-health.json (8 serviços)
- **Prometheus**: `/api/v1/metrics/prometheus`
- **Loki + Promtail**: log aggregation (C23)
- **Audit log**: `audit_log` table (LGPD art. 37)

### Alertas
- **Telegram GRUPO PIETRA SQUAD**: alertas operacionais
- **Telegram DM Gustavo**: alertas críticos
- **Email** (futuro): relatórios mensais

---

## 📋 Compliance LGPD (vinculado ao SLA)

| Direito do Titular | SLA Implementação | Status |
|--------------------|---------------------|--------|
| Acesso (art. 18, I) | < 24h resposta | D23 ✅ |
| Correção (art. 18, III) | < 7 dias | D24 ✅ |
| Portabilidade (art. 18, V) | Download imediato | D22 + D09 ✅ |
| Exclusão (art. 18, VI) | < 15 dias + anonimização 30d | D21 + D25 ✅ |
| Oposição | Resposta imediata | D11 ✅ |
| Não-automação (opt-out) | Imediato | D12 ✅ |
| **Audit log** | **5 anos retenção** | **D14 ✅** |
| **Consent explícito** | Antes de processar | **D04 ✅** |
| **Anonimização** | **Após 365d** | **D21 ✅** |

---

## 🔄 Revisão de SLA

- **Trimestral**: Gustavo revisa targets
- **Anual**: ajuste de metas baseado em crescimento
- **Após incidente**: postmortem + revisão de SLA

---

## 🔗 Links

- **Grafana**: https://[VPS-IP]:3000 (interno)
- **API Health Radar**: https://api.2notasudi.com.br/api/v1/health/radar
- **Postmortems**: `docs/POSTMORTEMS.md`
- **Capacity Planning**: `docs/CAPACITY_PLANNING.md`
- **Incident Response**: `docs/INCIDENT_RESPONSE.md`
- **Super Prompt v4.0.0**: PROMPT.MD (Bloco 15 — Testes e Validação)

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26
**Próxima revisão**: 2026-09-26 (trimestral)
**Status**: ✅ C12 SQUAD C DONE
