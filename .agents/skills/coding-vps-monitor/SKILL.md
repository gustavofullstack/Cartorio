---
name: coding-vps-monitor
description: Como monitorar o coding-vps_apenas_para_auxilio (89 serviços). Docker stats, port scan, health checks, Prometheus queries, Sentry, Grafana.
type: agent
created: 2026-07-08
squad: 3
---

# coding-vps-monitor

Skill que ensina o agente a **observar a saúde** do VPS `100.99.172.84` (89 serviços Docker Swarm) usando o MCP orchestrator e ferramentas nativas.

## Quando usar

- Você precisa **investigar lentidão** ou **queda** em um serviço.
- Você quer **rodar health check** geral de todos os serviços.
- Você precisa **extrair métricas** Prometheus ou **ver issues Sentry** recentes.
- Você quer **descobrir qual porta** um serviço está usando.

## Comandos essenciais

### Health check geral (executa em todos os 89 serviços)

```bash
python3 scripts/coding_vps_mcp_orchestrator.py call health_check_all
```

Retorna JSON com `healthy` / `unhealthy` por serviço. Para análise rápida:
```bash
python3 scripts/coding_vps_mcp_orchestrator.py call health_check_all | jq '.results[] | select(.healthy==false)'
```

### Docker stats em tempo real

```bash
python3 scripts/coding_vps_mcp_orchestrator.py call docker_stats
```

Retorna CPU%, MEM%, NET I/O por container. Para top-10 por memória:
```bash
python3 scripts/coding_vps_mcp_orchestrator.py call docker_stats | jq 'sort_by(.mem_usage) | reverse | .[0:10]'
```

### Port scan

```bash
# Scan uma porta específica
python3 scripts/coding_vps_mcp_orchestrator.py call port_scan 100.99.172.84 8100

# Scan range
python3 scripts/coding_vps_mcp_orchestrator.py call port_scan 100.99.172.84 8001-8010
```

### Service logs (tail -100)

```bash
python3 scripts/coding_vps_mcp_orchestrator.py call service_logs openclaw 200
```

### Tailscale mesh status

```bash
# Ver status completo da mesh
python3 scripts/coding_vps_mcp_orchestrator.py call tailscale_status

# Listar devices (quem está conectado)
python3 scripts/coding_vps_mcp_orchestrator.py call tailscale_list_devices

# Pingar peer específico
python3 scripts/coding_vps_mcp_orchestrator.py call tailscale_ping 100.99.172.84
```

## Métricas Prometheus

```bash
# CPU usage por container
python3 scripts/coding_vps_mcp_orchestrator.py call prometheus_query \
  'rate(container_cpu_usage_seconds_total{name!=""}[5m])'

# Memória usada por container
python3 scripts/coding_vps_mcp_orchestrator.py call prometheus_query \
  'container_memory_usage_bytes{name!=""}'

# Request rate no Traefik
python3 scripts/coding_vps_mcp_orchestrator.py call prometheus_query \
  'rate(traefik_entrypoint_requests_total[1m])'

# Listar todas as métricas disponíveis
python3 scripts/coding_vps_mcp_orchestrator.py call prometheus_metrics
```

## Issues Sentry

```bash
# Listar issues do projeto cartorio-api
python3 scripts/coding_vps_mcp_orchestrator.py call sentry_list_issues cartorio-api

# Disparar evento de teste
python3 scripts/coding_vps_mcp_orchestrator.py call sentry_capture_event \
  "smoke-test from squad3" info coding-vps
```

## Dashboards Grafana

```bash
# Listar dashboards disponíveis
python3 scripts/coding_vps_mcp_orchestrator.py call grafana_dashboards
```

## SSL / Certificados

```bash
# Ver certificados Let's Encrypt ativos
python3 scripts/coding_vps_mcp_orchestrator.py call letsencrypt_list
```

## Health check de Hostinger (VPS provider)

```bash
# Status da VPS via API Hostinger
python3 scripts/coding_vps_mcp_orchestrator.py call hostinger_api_status
```

## Workflow de investigação (receita)

Quando o bot está lento ou caindo:

1. **Tailscale OK?**
   ```bash
   python3 scripts/coding_vps_mcp_orchestrator.py call tailscale_ping 100.99.172.84
   ```

2. **VPS respondendo?**
   ```bash
   ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 "uptime"
   ```

3. **Qual serviço caiu?**
   ```bash
   python3 scripts/coding_vps_mcp_orchestrator.py call health_check_all | jq '.results[] | select(.healthy==false) | .service'
   ```

4. **Logs do serviço com problema**
   ```bash
   python3 scripts/coding_vps_mcp_orchestrator.py call service_logs <service-name> 300
   ```

5. **Recursos saturados?**
   ```bash
   python3 scripts/coding_vps_mcp_orchestrator.py call docker_stats
   ```

6. **Erro recente no Sentry?**
   ```bash
   python3 scripts/coding_vps_mcp_orchestrator.py call sentry_list_issues cartorio-api
   ```

7. **Restart se necessário**
   ```bash
   python3 scripts/coding_vps_mcp_orchestrator.py call restart_service <service-name>
   ```

## Alertas recomendados (Prometheus + Alertmanager)

| Métrica | Threshold | Ação |
|---|---|---|
| `up{job="coding-vps"} == 0` | 1m | Notificar + investigar |
| CPU > 80% por 5min | 5m | Escalar ou restart |
| Memória > 90% | 5m | Restart OOM-killer |
| Disk > 85% | 1h | Limpar volumes |
| SSL expira < 14 dias | 24h | Renovar Let's Encrypt |

## Comandos nativos (sem MCP)

```bash
# Via SSH direto
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 <<'EOF'
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker stats --no-stream
docker service ls
EOF
```
