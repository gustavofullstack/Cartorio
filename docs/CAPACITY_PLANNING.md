# 📈 Capacity Planning — C13

> **SQUAD C** | **Owner**: cartorio-zcode + cartorio-dev
> **Data**: 2026-06-26
> **Status**: ✅ DONE

Planejamento de capacidade para o sistema Cartório 2º Notas.

---

## 🏗️ Infraestrutura Atual

### VPS Hostinger
- **Provider**: Hostinger
- **Specs**: 8 GB RAM, 4 vCPU, 200 GB SSD (estimado)
- **OS**: Ubuntu 22.04 LTS
- **Container runtime**: Docker 24+ via Swarm

### 12 Serviços Docker Swarm
| # | Service | RAM estimado | CPU estimado | Storage |
|---|---------|--------------|--------------|---------|
| 1 | cartorio_api | 512 MB | 0.5 vCPU | 5 GB |
| 2 | cartorio_n8n | 1 GB | 1 vCPU | 10 GB |
| 3 | cartorio_n8n-runner | 512 MB | 0.5 vCPU | 2 GB |
| 4 | cartorio_evolution-api | 768 MB | 0.5 vCPU | 5 GB |
| 5 | cartorio_chatwoot | 1.5 GB | 1 vCPU | 20 GB |
| 6 | cartorio_chatwoot-sidekiq | 512 MB | 0.5 vCPU | 2 GB |
| 7 | cartorio_openclaw-gateway | 1 GB | 0.5 vCPU | 10 GB |
| 8 | cartorio_redis | 256 MB | 0.2 vCPU | 2 GB |
| 9 | cartorio_redis_dbgate | 256 MB | 0.1 vCPU | 1 GB |
| 10 | cartorio_redis_rediscommander | 128 MB | 0.1 vCPU | 1 GB |
| 11 | easypanel | 512 MB | 0.3 vCPU | 2 GB |
| 12 | easypanel-traefik | 128 MB | 0.1 vCPU | 1 GB |
| **TOTAL** | **~7 GB** | **~6 vCPU** | **~60 GB** |

---

## 📊 Capacidade Atual vs Esperada

### Throughput estimado
- **API**: 50 req/s sustentado, picos de 200 req/s
- **N8N**: 100 execuções/min em horário comercial
- **Evolution API**: 100 msg/min (limite Meta WhatsApp Business)
- **OpenClaw**: 10 conversas paralelas, ~30s cada
- **Chatwoot**: 50 conversas simultâneas
- **Supabase**: 1000 queries/s (PostgreSQL 15)
- **Redis**: 10k ops/s

### Clientes
- **MVP (3 meses)**: 10 cartórios x 50 clientes = 500 clientes
- **6 meses**: 50 cartórios x 100 clientes = 5.000 clientes
- **12 meses**: 200 cartórios x 200 clientes = 40.000 clientes
- **24 meses**: 500 cartórios x 300 clientes = 150.000 clientes

### Storage projetado
- **Audit log** (5 anos): ~50 KB/registro × 1M registros/mês = 50 GB/mês
- **Conversas** (1 ano): ~5 KB × 200k/mês = 1 GB/mês
- **Documentos PDF**: ~500 KB × 10k/mês = 5 GB/mês
- **Backups**: 7 dias rotação = ~7 TB após 12 meses

---

## 🚧 Gargalos Identificados

### Curto prazo (0-3 meses)
1. **DB connection pool** (A15): 20+10=30 conexões. Se 30 clientes simultâneos, satura.
   - **Mitigação**: PgBouncer externo OU upgrade para 50+20 pool
2. **Redis memory** (256 MB): suficiente para 1k sessões, mas pode saturar com 50k+ chaves.
   - **Mitigação**: Aumentar para 1 GB

### Médio prazo (3-12 meses)
3. **N8N Postgres**: 14 WFs ativos + chatwoot-sidekiq jobs → ~20 connections.
   - **Mitigação**: Upgrade N8N DB para 8GB+ RAM
4. **Evolution API single instance**: 1 WhatsApp = 1 canal. Multi-tenant precisa multi-instance.
   - **Mitigação**: Horizontal scaling (múltiplas instâncias, load balancer)
5. **OpenClaw single agent**: 1 conversation/agent. Multi-tenant precisa multi-agent.
   - **Mitigação**: Multi-agent deployment com shared context

### Longo prazo (12+ meses)
6. **VPS single point of failure**: 1 host. 99.9% max.
   - **Mitigação**: Multi-VPS + load balancer
7. **Supabase single instance**: 1 Postgres. Scaling vertical caro.
   - **Mitigação**: Supabase read replicas + Citus para sharding

---

## 📊 Benchmarks de Crescimento

### Hoje (2026-06-26)
- 1219 testes passing
- 0 mypy errors, 0 ruff errors
- 7/7 serviços online
- 8 commits/dia (média)
- 10 endpoints v1 + 4 v2 (alpha)

### Meta 3 meses
- 50+ endpoints v1 (10x)
- 20+ endpoints v2 (5x)
- 1500+ testes (25% growth)
- 0 services DOWN > 1min/mês
- 99.5% uptime API (target)

### Meta 6 meses
- 100+ endpoints v1 + 50+ v2
- 2000+ testes
- Multi-tenant (5 cartórios simultâneos)
- 99.9% uptime API
- Supabase read replica

### Meta 12 meses
- Multi-region deploy
- 5000+ testes
- 50+ cartórios
- 99.99% uptime (4 noves)
- Dedicated DB cluster

---

## 🔧 Estratégia de Escala

### Vertical (mais RAM/CPU)
**Quando**: até 100 cartórios (~30k clientes)
- Upgrade VPS para 16 GB RAM, 8 vCPU
- Supabase: 16 GB RAM
- Redis: 2 GB
- **Custo**: ~R$ 500/mês (Hostinger high-end)

### Horizontal (multi-instância)
**Quando**: 100-500 cartórios
- 2-3 VPS com load balancer
- Supabase read replicas (2-3)
- Redis cluster
- **Custo**: ~R$ 1500/mês

### Multi-region (global)
**Quando**: 500+ cartórios
- Multi-cloud (Hostinger + AWS + GCP)
- Kubernetes (EKS/GKE) OU Docker Swarm multi-region
- Supabase multi-region
- **Custo**: ~R$ 5000/mês

---

## 📈 Projeção de Custos

| Cenário | Cartórios | Clientes | Custo/mês VPS | Custo/mês Supabase | Total |
|---------|-----------|----------|---------------|--------------------|-------|
| MVP | 10 | 500 | R$ 150 | R$ 0 (self-hosted) | **R$ 150** |
| 3 meses | 50 | 5.000 | R$ 200 | R$ 0 | **R$ 200** |
| 6 meses | 200 | 40.000 | R$ 500 | R$ 0 | **R$ 500** |
| 12 meses | 500 | 150.000 | R$ 1500 | R$ 0 | **R$ 1500** |
| 24 meses | 1000 | 500.000 | R$ 5000 | R$ 0 (multi-VPS) | **R$ 5000** |

**Margem**: assinatura de R$ 500/cartório/mês = R$ 25.000/mês @ 50 cartórios (50x ROI).

---

## 🔍 Monitoring de Capacidade

### Métricas-chave (Prometheus)
```promql
# CPU por container
rate(container_cpu_usage_seconds_total{name=~"cartorio_.*"}[5m])

# Memória por container
container_memory_usage_bytes{name=~"cartorio_.*"}

# DB connections
cartorio_db_pool_checked_out / cartorio_db_pool_total_capacity

# Redis memory
redis_memory_used_bytes / redis_memory_max_bytes

# Request rate
rate(http_requests_total[5m])
```

### Alertas de capacidade
- CPU > 70% sustained 5min → alerta Telegram
- Memory > 80% → alerta Telegram
- DB pool > 80% → alerta + scale up
- Disk > 85% → alerta + cleanup

---

## 🔗 Links

- **Grafana**: https://[VPS-IP]:3000 (C21 C22 done)
- **Prometheus**: https://api.2notasudi.com.br/api/v1/metrics/prometheus
- **A15 DB Pool**: https://api.2notasudi.com.br/admin/pool
- **SLA**: `docs/SLA.md`
- **Runbook VPS**: `docs/RUNBOOK_VPS.md`
- **Super Prompt v4.0.0**: PROMPT.MD (Bloco 4.4 — VPS)

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26
**Próxima revisão**: mensal (com Gustavo)
**Status**: ✅ C13 SQUAD C DONE
