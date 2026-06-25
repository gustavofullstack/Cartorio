# 🛠️ Runbook Operacional — C9

> **SQUAD C** | **Owner**: cartorio-zcode + cartorio-dev
> **Data**: 2026-06-26
> **Status**: ✅ DONE

Procedimentos operacionais do dia-a-dia para o sistema Cartório 2º Notas.

---

## 🎯 Comandos Rápidos (cheat sheet)

### SSH VPS
```bash
# SEMPRE usar alias (NUNCA IP direto)
ssh cartorio                    # alias do ~/.ssh/config (Tailscale 100.99.172.84)
```

### Docker Swarm
```bash
# Status de todos os services
ssh cartorio "docker service ls"

# Status detalhado de um service
ssh cartorio "docker service ps cartorio_api"

# Logs em tempo real
ssh cartorio "docker service logs cartorio_api --tail 100 -f"

# Restart de um service
ssh cartorio "docker service update --force cartorio_api"

# Stats de recursos
ssh cartorio "docker stats --no-stream"
```

### Health Checks
```bash
# Radar geral (7 servicos)
curl https://api.2notasudi.com.br/api/v1/health/radar | jq

# Individual
for s in api flow whatsapp chat agent supbase easypanel; do
  curl -sk -o /dev/null -w "$s.2notasudi.com.br: %{http_code}\n" https://$s.2notasudi.com.br/
done
```

### Métricas Prometheus
```bash
# Endpoint completo
curl -s https://api.2notasudi.com.br/api/v1/metrics/prometheus | head -50

# Filtro específico
curl -s https://api.2notasudi.com.br/api/v1/metrics/prometheus | grep cartorio_db_pool

# DB Pool stats
curl -sk -H "X-API-Key: $CARTORIO_API_KEY" https://api.2notasudi.com.br/admin/pool
```

### Supabase / DB
```bash
# Conectar ao Postgres cartorio
ssh cartorio "docker exec -it cartorio_db psql -U supabase_admin -d cartorio"

# Audit log recente
ssh cartorio "docker exec cartorio_db psql -U supabase_admin -d cartorio -c 'SELECT id, actor_id, action, created_at FROM audit_log ORDER BY created_at DESC LIMIT 20'"

# Slow queries
ssh cartorio "docker exec cartorio_db psql -U supabase_admin -d cartorio -c 'SELECT pid, now()-query_start as duration, query FROM pg_stat_activity WHERE state = \"active\" AND now()-query_start > interval \"200ms\"'"

# Tabelas + count
ssh cartorio "docker exec cartorio_db psql -U supabase_admin -d cartorio -c 'SELECT schemaname, COUNT(*) FROM pg_tables GROUP BY schemaname'"
```

### Redis
```bash
# PING
ssh cartorio "redis-cli -h cartorio_redis -a @Techno832466 PING"

# Estatísticas
ssh cartorio "redis-cli -h cartorio_redis -a @Techno832466 INFO stats | head -20"

# Memória
ssh cartorio "redis-cli -h cartorio_redis -a @Techno832466 INFO memory | grep used_memory_human"

# Chaves por padrão
ssh cartorio "redis-cli -h cartorio_redis -a @Techno832466 KEYS 'session:*' | wc -l"

# Limpar cache (CUIDADO em produção)
ssh cartorio "redis-cli -h cartorio_redis -a @Techno832466 FLUSHDB"
```

### N8N Workflows
```bash
# API N8N (via Bash)
N8N_API_KEY="eyJ..."  # do .env
curl -X GET "https://flow.2notasudi.com.br/api/v1/workflows" -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.[] | {id, name, active}'

# Re-executar workflow
curl -X POST "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID/execute" -H "X-N8N-API-KEY: $N8N_API_KEY" -d '{}'

# Listar executions
curl -X GET "https://flow.2notasudi.com.br/api/v1/executions?limit=10" -H "X-N8N-API-KEY: $N8N_API_KEY" | jq
```

### Evolution API
```bash
# Status instâncias
curl -X GET "https://whatsapp.2notasudi.com.br/instance/fetchInstances" \
  -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" | jq

# QR Code (regenerar)
curl -X GET "https://whatsapp.2notasudi.com.br/instance/connect/cartorio-2notas" \
  -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" | jq

# Restart instance
curl -X POST "https://whatsapp.2notasudi.com.br/instance/restart/cartorio-2notas" \
  -H "apikey: 429683C4C977415CAAFCCE10F7D57E11"
```

### Chatwoot
```bash
# Status (precisa de credencial)
curl -sk -H "api_access_token: $CHATWOOT_API_KEY" \
  "https://chat.2notasudi.com.br/api/v1/accounts" | jq

# Listar conversas recentes
curl -sk -H "api_access_token: $CHATWOOT_API_KEY" \
  "https://chat.2notasudi.com.br/api/v1/accounts/1/conversations?status=open&per_page=10" | jq
```

### OpenClaw Agent
```bash
# Health
curl https://agent.2notasudi.com.br/health

# Models disponíveis
curl https://agent.2notasudi.com.br/v1/models

# Agents configurados
curl https://agent.2notasudi.com.br/v1/agents | jq

# Testar contexto (sending test message)
curl -X POST "https://agent.2notasudi.com.br/v1/messages" \
  -H "Authorization: Bearer $OPENCLAW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent": "main", "message": "ping", "user_id": "test"}'
```

---

## 📦 Deploy Routine

### Backend API (cartorio-api)

```bash
# 1. Build local
cd /Users/gustavoalmeida/projetos/Cartorio/backend
uv run pytest --no-cov -q  # 1219 passed
uv run ruff check app/
uv run mypy app/

# 2. Commit + push
cd ..
git add .
git commit -m "feat(api): <descrição>"
git push origin master

# 3. Auto-deploy via GitHub Actions (CI/CD)
# OU manual via Easypanel:
ssh cartorio
cd /home/easypanel/projects/cartorio
git pull origin master
docker service update --force cartorio_api
curl https://api.2notasudi.com.br/health
```

### N8N Workflows

```bash
# Backup
bash scripts/backup_n8n.sh  # /home/easypanel/backups/n8n-*.json

# Workflow individual (exportar via UI)
# 1. Acessar https://flow.2notasudi.com.br
# 2. Workflow > Download

# Importar workflow
# UI N8N > Workflows > Import from File
```

### OpenClaw Agent config

```bash
# Backup agent.json + models.json
ssh cartorio "cp /home/node/.openclaw/agents/main/agent/agent.json /home/easypanel/backups/agent.json.bak"
ssh cartorio "cp /home/node/.openclaw/agents/main/agent/models.json /home/easypanel/backups/models.json.bak"

# Editar
ssh cartorio "nano /home/node/.openclaw/agents/main/agent/agent.json"
ssh cartorio "nano /home/node/.openclaw/agents/main/agent/models.json"

# Restart
ssh cartorio "docker service update --force cartorio_openclaw-gateway"
```

---

## 🗄️ Backup Routine

### Cron jobs configurados
- **03:00 BRT**: pg_basebackup cartório DB (`/usr/local/bin/pg_basebackup_4x.sh`)
- **03:30 BRT**: Audit verify (`/usr/local/bin/audit_chain_daily.sh`)
- **04:00 BRT**: N8N workflows export (`scripts/backup_n8n.sh`)
- **A cada 5min**: Cartorio health check (`/etc/cron.d/cartorio-health-check`)

### Verificar último backup
```bash
ssh cartorio "ls -la /home/easypanel/backups/cartorio/ | tail -10"
ssh cartorio "ls -la /home/easypanel/backups/supabase/ | tail -10"
```

### Backup manual
```bash
# DB cartório
ssh cartorio "/usr/local/bin/pg_basebackup_4x.sh"

# N8N workflows
ssh cartorio "bash /home/easypanel/projects/cartorio/scripts/backup_n8n.sh"

# OpenClaw agent config
ssh cartorio "cp /home/node/.openclaw/agents/main/agent/{agent,models}.json /home/easypanel/backups/"
```

### Restore de backup
```bash
# DB (NÃO rodar em produção sem autorização!)
ssh cartorio "gunzip -c /home/easypanel/backups/cartorio/pg_basebackup/base_20260625_030000.tar.gz | pg_restore -U supabase_admin -d cartorio_restore"
```

---

## 🔍 Diagnóstico

### API lenta
```bash
# 1. Verificar DB pool
curl -sk -H "X-API-Key: $CARTORIO_API_KEY" https://api.2notasudi.com.br/admin/pool

# 2. Verificar slow queries
curl -sk -H "X-API-Key: $CARTORIO_API_KEY" https://api.2notasudi.com.br/admin/slow-queries

# 3. Verificar Redis
ssh cartorio "redis-cli -h cartorio_redis -a @Techno832466 INFO stats | grep instantaneous"

# 4. Verificar logs API
ssh cartorio "docker service logs cartorio_api --tail 100 | grep -E 'slow|error|timeout'"
```

### N8N workflow falhou
```bash
# 1. Identificar workflow
curl -X GET "https://flow.2notasudi.com.br/api/v1/executions?limit=5&status=error" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | {workflowId, startedAt, "data.resultData.error.message"}'

# 2. Ver logs
ssh cartorio "docker service logs cartorio_n8n --tail 200 | grep -A 3 ERROR"

# 3. Re-executar (se seguro)
WF_ID=<id>
curl -X POST "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID/execute" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" -d '{}'
```

### WhatsApp flow não responde
```bash
# 1. Verificar webhook
curl -X POST "https://flow.2notasudi.com.br/webhook/evo-in" \
  -H "Content-Type: application/json" \
  -d '{"event":"messages.upsert","data":{...}}'

# 2. Verificar Evolution
curl -X GET "https://whatsapp.2notasudi.com.br/instance/connectionState/cartorio-2notas" \
  -H "apikey: 429683C4C977415CAAFCCE10F7D57E11"

# 3. Verificar OpenClaw
curl https://agent.2notasudi.com.br/health
```

### OpenClaw context overflow
```bash
# 1. Verificar config
ssh cartorio "cat /home/node/.openclaw/agents/main/agent/models.json"

# 2. Verificar max_tokens
# Esperado: 1000000 (1M)

# 3. Aplicar fix se necessário
bash scripts/fix_openclaw_context_1M.sh
```

---

## 🔄 Manutenção

### Limpeza de logs antigos (> 90 dias)
```bash
ssh cartorio "find /var/lib/docker/containers -name '*.log' -mtime +90 -delete"
```

### Limpeza de backups > 7 dias
```bash
ssh cartorio "find /home/easypanel/backups -mtime +7 -delete"
```

### Restart de todos os services (sempre que houver update de imagem)
```bash
ssh cartorio "docker service update --force cartorio_api cartorio_n8n cartorio_evolution-api cartorio_chatwoot cartorio_chatwoot-sidekiq cartorio_openclaw-gateway"
```

### Atualização de imagens Docker
```bash
# 1. Pull novas imagens
ssh cartorio "docker pull easypanel/cartorio/api:v0.7.0"
ssh cartorio "docker pull n8nio/n8n:1.95.0"

# 2. Update services
ssh cartorio "docker service update --image easypanel/cartorio/api:v0.7.0 cartorio_api"

# 3. Validar
curl https://api.2notasudi.com.br/health
```

### Pruning de Docker (cleanup geral)
```bash
ssh cartorio "docker system prune -a --volumes"  # ⚠️ CUIDADO com volumes
```

---

## 🚨 Procedimentos Críticos

### Reiniciar VPS inteira (emergência)
```bash
# 1. Avisar Gustavo (DM)
# 2. Avisar Squad Grupo
# 3. Aguardar 10min (lifetime connection drain)
# 4. Restart controlado
ssh cartorio "shutdown -r +5 'Manutencao programada'"
# 5. Após reboot, verificar Swarm
ssh cartorio "docker node ls"
ssh cartorio "docker service ls"
```

### Escalar para VPS maior (quando RAM < 10% livre)
1. Gustavo contrata upgrade Hostinger
2. Snapshot disco (Easypanel)
3. Migrar dados
4. Atualizar DNS (se IP mudar)
5. Validar todos os 8 serviços

---

## 🔗 Links

- **Health radar**: https://api.2notasudi.com.br/api/v1/health/radar
- **Grafana**: https://[VPS-IP]:3000 (interno)
- **SLA**: `docs/SLA.md`
- **Incident Response**: `docs/INCIDENT_RESPONSE.md`
- **Secrets**: `docs/SECRETS_MANAGEMENT.md`
- **Capacity**: `docs/CAPACITY_PLANNING.md`
- **Super Prompt v4.0.0**: PROMPT.MD (Bloco 7.4 SSH)

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26
**Próxima revisão**: 2026-07-26 (mensal)
**Status**: ✅ C9 SQUAD C DONE
