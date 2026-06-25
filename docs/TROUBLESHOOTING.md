# Troubleshooting — Cartório Chatbot

> Guia de troubleshooting para problemas comuns em produção.
> Última atualização: 2026-06-26.

## TL;DR

**Regra de ouro**: SEMPRE verificar `/api/v1/health/radar` PRIMEIRO. Se 1+ serviço está DOWN, é a causa raiz.

**Princípio P1**: Validar via `curl/ssh` (ground truth) antes de mudar código (briefing pode estar errado — Lesson 169).

**Princípio P2**: Em race conditions com cartorio-dev, SEMPRE `git fetch && git push` antes de commitar (Lesson 178).

---

## Índice

1. [API FastAPI](#1-api-fastapi)
2. [N8N Workflows](#2-n8n-workflows)
3. [Supabase / DB](#3-supabase--db)
4. [Redis](#4-redis)
5. [OpenClaw Gateway](#5-openclaw-gateway)
6. [Evolution API (WhatsApp)](#6-evolution-api-whatsapp)
7. [Chatwoot CRM](#7-chatwoot-crm)
8. [Traefik / SSL](#8-traefik--ssl)
9. [Tailscale VPN](#9-tailscale-vpn)
10. [DNS / Cloudflare](#10-dns--cloudflare)
11. [Backup](#11-backup)
12. [LGPD Compliance](#12-lgpd-compliance)

---

## 1. API FastAPI

### 1.1 Erro 500 genérico

```bash
# 1. Ver logs do container
ssh root@100.99.172.84 "docker service logs cartorio_api --tail 100"

# 2. Ver últimas requests lentas
curl -fsS "https://api.2notasudi.com.br/admin/slow-queries?limit=20" \
  -H "X-API-Key: $API_KEY"

# 3. Verificar conexão DB
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_api') python -c 'from app.db import engine; print(engine.pool.status())'"

# 4. Restart se necessário
ssh root@100.99.172.84 "docker service update --force cartorio_api"
```

### 1.2 Erro 502 Bad Gateway (Traefik)

```bash
# 1. Container API pode estar crashando em loop
ssh root@100.99.172.84 "docker ps -a | grep cartorio_api"

# 2. Ver última linha do log
ssh root@100.99.172.84 "docker service logs cartorio_api --tail 5"

# 3. Ver healthcheck do container
ssh root@100.99.172.84 "docker inspect $(docker ps -qf 'name=cartorio_api') --format '{{json .State.Health}}' | jq"
```

### 1.3 Timeout em chamada para OpenClaw

```bash
# 1. Verificar se OpenClaw está UP
curl -fsS https://agent.2notasudi.com.br/health

# 2. Se UP, verificar latência
time curl -fsS https://agent.2notasudi.com.br/health

# 3. Ver logs de timeout
ssh root@100.99.172.84 "docker service logs cartorio_api | grep -i timeout | tail -20"

# 4. Ajustar timeout no endpoint se necessário
# backend/app/api/v1/router.py: aumentar timeout OpenClaw WS para 30s
```

### 1.4 Erro 422 Validation Error

```python
# Pydantic schema validation falhou. Ver:
# 1. Logs do endpoint específico
# 2. OpenAPI spec: https://api.2notasudi.com.br/openapi.json
# 3. Regras de validação em backend/app/schemas/

# Teste local com schema:
from app.schemas.atendimento import AtendimentoCreate
try:
    data = AtendimentoCreate(**payload)
except ValidationError as e:
    print(e.errors())
```

### 1.5 mamba / circular import

```python
# Se Python reclamou de "partially initialized module"
# Causa: import circular
# Fix: refatorar imports (lazy import dentro da função)

# Sintoma:
ImportError: cannot import name 'X' from partially initialized module 'Y'
```

---

## 2. N8N Workflows

### 2.1 Workflow não executa

```bash
# 1. Ver status do WF
curl -fsS "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID" \
  -H "X-N8N-API-KEY: $N8N_KEY" | jq '.active,.nodes[].type'

# 2. Ver execuções recentes
curl -fsS "https://flow.2notasudi.com.br/api/v1/executions?workflowId=$WF_ID&limit=5" \
  -H "X-N8N-API-KEY: $N8N_KEY" | jq '.data[].status'

# 3. Ativar se inativo
curl -fsS -X PATCH "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID" \
  -H "X-N8N-API-KEY: $N8N_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

### 2.2 HTTP Request 4xx/5xx

```bash
# 1. Verificar credencial (API key pode ter expirado)
# UI: N8N → Credentials → Test

# 2. Verificar URL
# 3. Verificar timeout (5s padrão — aumentar se LLM call)
# 4. Verificar retry policy (3x exp backoff deve estar ativo)
```

### 2.3 Webhook não recebe

```bash
# 1. Verificar URL webhook
curl -fsS -X POST "https://flow.2notasudi.com.br/webhook/$WEBHOOK_PATH" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# 2. Se 404, WF está inativo ou path errado
# 3. Se 200 mas não processa, ver error log do WF
```

### 2.4 Cron não dispara

```bash
# 1. Ver WF #25 (metrics collector) está ativo
# 2. Ver N8N queue mode (pode estar processando atrasado)
# 3. Restart n8n-runner
ssh root@100.99.172.84 "docker service update --force cartorio_n8n-runner"
```

---

## 3. Supabase / DB

### 3.1 Erro de conexão

```bash
# 1. Verificar se Kong está UP
curl -fsS https://supbase.2notasudi.com.br/auth/v1/health

# 2. Verificar se DB aceita conexões
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_supabase-db') pg_isready -U postgres"

# 3. Verificar connection pool
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c 'SELECT count(*), state FROM pg_stat_activity GROUP BY state;'"
```

### 3.2 RLS bloqueia query legítima

```sql
-- Verificar policies ativas
SELECT schemaname, tablename, policyname, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public';

-- Exemplo: desabilitar RLS temporariamente para debug (CUIDADO!)
ALTER TABLE clientes DISABLE ROW LEVEL SECURITY;
-- ... fazer query ...
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;
```

### 3.3 Alembic drift

```bash
# DB tem tabelas mas alembic_version está atrás
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_api') alembic current"
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_api') alembic heads"

# Fix: stamp para alinhar (Lesson 179)
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_api') alembic stamp head"
```

### 3.4 Query lenta (>1s)

```sql
-- Ver top queries lentas
SELECT pid, now() - query_start as duration, query, state
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > INTERVAL '1 second'
ORDER BY duration DESC;

-- Matar query travada
SELECT pg_cancel_backend(pid);
-- Se não resolver:
SELECT pg_terminate_backend(pid);
```

### 3.5 Disk full

```bash
# 1. Verificar uso
ssh root@100.99.172.84 "df -h"

# 2. Limpar WAL antigos (Supabase)
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c 'SELECT pg_size_pretty(pg_database_size(current_database()));'"

# 3. Rodar VACUUM FULL (locka tabela - cuidado)
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -d postgres -c 'VACUUM FULL;'"
```

---

## 4. Redis

### 4.1 Connection refused

```bash
# 1. Verificar se container está UP
ssh root@100.99.172.84 "docker ps | grep cartorio_redis"

# 2. PING
ssh root@100.99.172.84 "redis-cli -h localhost -p 6379 -a \$REDIS_AUTH PING"

# 3. Restart se necessário
ssh root@100.99.172.84 "docker service update --force cartorio_redis"
```

### 4.2 Memória cheia (OOM)

```bash
# 1. Ver uso
ssh root@100.99.172.84 "redis-cli -p 6379 -a \$REDIS_AUTH INFO memory | grep used_memory_human"

# 2. Ver chaves por tipo
ssh root@100.99.172.84 "redis-cli -p 6379 -a \$REDIS_AUTH --scan --pattern 'sess:*' | wc -l"

# 3. Limpar sessões expiradas (não impacta produção - só remove expirados)
ssh root@100.99.172.84 "redis-cli -p 6379 -a \$REDIS_AUTH --scan --pattern 'sess:*' | xargs -L 100 redis-cli -p 6379 -a \$REDIS_AUTH DEL"
```

### 4.3 Pub/Sub não entrega

```bash
# 1. Verificar canais ativos
ssh root@100.99.172.84 "redis-cli -p 6379 -a \$REDIS_AUTH PUBSUB CHANNELS '*'"

# 2. Testar manualmente
ssh root@100.99.172.84 "redis-cli -p 6379 -a \$REDIS_AUTH SUBSCRIBE test_channel"
# Em outro terminal:
ssh root@100.99.172.84 "redis-cli -p 6379 -a \$REDIS_AUTH PUBLISH test_channel 'hello'"
```

---

## 5. OpenClaw Gateway

### 5.1 Contexto limitado (131k vs 1M) — RESOLVIDO v4.0.0

**Histórico**: Bloco 12.5 do SUPER PROMPT v4.0.0 documentou contexto 131.1k. Resolvido em 25/06/2026 via SSH VPS + Python script injection em `models.json`.

```bash
# Verificar configuração atual
ssh root@100.99.172.84 "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/models.json | jq '.providers.opencode_go.models[0].contextWindow'"

# Esperado: 1048576
# Se voltar para 131072, re-aplicar fix (ver E07_OPENCLAW_CONTEXT_FIX.md)
```

### 5.2 /v1/chat HTTP 404 (WS funciona)

**Causa**: gateway.http schema rejeitado pelo OpenClaw Gateway.

**Workaround**: Usar WebSocket (`/v1/chat` WS) ao invés de HTTP.

```python
# Errado (404)
import requests
requests.post("https://agent.2notasudi.com.br/v1/chat", json={...})

# Correto (WS)
import websockets
async with websockets.connect("wss://agent.2notasudi.com.br/v1/chat") as ws:
    await ws.send(json.dumps({...}))
    response = await ws.recv()
```

### 5.3 Agent não pensa (thinking OFF)

```bash
# Verificar se thinking está ON
ssh root@100.99.172.84 "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json | jq '.thinking'"

# Esperado:
# {
#   "enabled": true,
#   "mode": "adaptive",
#   "budget_tokens": 10000
# }

# Se disabled, editar e restart
```

### 5.4 Chave OpenCode-Go inválida

**Sintoma**: OpenClaw retorna 401 ou "Invalid API key"

```bash
# Verificar chave atual (NÃO expor em logs)
ssh root@100.99.172.84 "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json | jq -r '.api_key' | head -c 10"

# Deve começar com "sk-xcRwExjQ..."
# Se diferente, atualizar (chave válida: sk-xcRwExjQjqmlc5swP8umqK2YqWUfVt23H3Xl6dpd9TqEyi16ssJXzHeUFGNNIfsJ)
```

---

## 6. Evolution API (WhatsApp)

### 6.1 Instância desconectada (state=close)

```bash
# 1. Ver status
curl -fsS "https://whatsapp.2notasudi.com.br/instance/connectionState/cartorio-2notas" \
  -H "apikey: $EVO_API_KEY" | jq

# 2. SUI: Gustavo escanear QR no Manager UI
# https://whatsapp.2notasudi.com.br/manager

# 3. Se TriQ Hub (teste), reconectar via UI
```

### 6.2 Webhook não recebe eventos

```bash
# 1. Verificar webhook configurado
curl -fsS "https://whatsapp.2notasudi.com.br/webhook/find/cartorio-2notas" \
  -H "apikey: $EVO_API_KEY" | jq

# 2. Testar manualmente
curl -fsS -X POST "https://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas" \
  -H "apikey: $EVO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://flow.2notasudi.com.br/webhook/evo-in",
    "enabled": true,
    "events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]
  }'
```

### 6.3 Mensagem não envia

```bash
# Verificar limite diário (Meta: 1000 mensagens/dia para utility templates)
# Verificar se número destino é válido
# Ver logs
ssh root@100.99.172.84 "docker service logs cartorio_evolution-api --tail 50"
```

---

## 7. Chatwoot CRM

### 7.1 Inbox WhatsApp desconectado

```bash
# 1. Verificar inbox configurada
curl -fsS "https://chat.2notasudi.com.br/api/v1/accounts/1/inboxes" \
  -H "api_access_token: $CW_TOKEN" | jq

# 2. Reconectar WhatsApp via Evolution API:
# UI: Chatwoot → Settings → Inboxes → WhatsApp → Reconnect
```

### 7.2 Bot não aparece como agente

```bash
# 1. Criar bot agent
curl -fsS -X POST "https://chat.2notasudi.com.br/api/v1/accounts/1/agents" \
  -H "api_access_token: $CW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pietra Cartório",
    "email": "pietra@2notasudi.com.br",
    "role": "agent"
  }'

# 2. Atribuir conversas para o bot via API ou HITL button
```

### 7.3 HITL não funciona

```bash
# 1. Verificar custom attribute configurado
# Settings → Custom Attributes → bot_paused (boolean)

# 2. Testar toggle
curl -fsS -X POST "https://chat.2notasudi.com.br/api/v1/accounts/1/conversations/$ID/toggle_typing_status" \
  -H "api_access_token: $CW_TOKEN"

# 3. Verificar workflow N8N #03 (handoff) está ativo
```

---

## 8. Traefik / SSL

### 8.1 Certificado expirado

```bash
# 1. Ver certificados
ssh root@100.99.172.84 "docker exec $(docker ps -qf 'name=traefik') cat /acme.json | jq '.letsencrypt.Certificates[].domain'"

# 2. Forçar renovação
ssh root@100.99.172.84 "docker service update --force cartorio_traefik"

# 3. Verificar
curl -vI https://api.2notasudi.com.br/health 2>&1 | grep -i "expire"
```

### 8.2 502 Bad Gateway via Traefik

```bash
# 1. Verificar se container alvo está UP
ssh root@100.99.172.84 "docker ps | grep cartorio_api"

# 2. Ver logs Traefik
ssh root@100.99.172.84 "docker service logs cartorio_traefik --tail 50"

# 3. Verificar labels do serviço
ssh root@100.99.172.84 "docker inspect cartorio_api --format '{{json .Spec.Labels}}' | jq"
```

---

## 9. Tailscale VPN

### 9.1 Não conecta à VPS

```bash
# 1. Verificar status local
tailscale status

# 2. SSH direto (fallback)
ssh root@187.77.236.77 -i ~/.ssh/id_ed25519_cartorio

# 3. Reiniciar Tailscale na VPS
ssh root@100.99.172.84 "systemctl restart tailscaled"

# 4. Reautenticar
ssh root@100.99.172.84 "tailscale up"
```

### 9.2 MagicDNS não resolve

```bash
# 1. Verificar DNS
nslookup vps-cartorio.tail2fe279.ts.net

# 2. Se falhar, usar IP direto
ssh root@100.99.172.84
```

---

## 10. DNS / Cloudflare

### 10.1 Domínio não resolve

```bash
# 1. Verificar propagação
dig api.2notasudi.com.br +short

# 2. Esperado: 187.77.236.77

# 3. Se não resolver, criar A record (SUI - Gustavo)
# Cloudflare Dashboard → 2notasudi.com.br → DNS → Add Record
# Type: A, Name: api, IPv4: 187.77.236.77, Proxy: Proxied
```

### 10.2 SSL Cloudflare conflict

```bash
# Se Cloudflare proxy está ON, SSL é terminated no Cloudflare (Full Strict)
# Traefik precisa de certificado válido (Let's Encrypt) para origin

# Fix: Cloudflare → SSL/TLS → Full (Strict)
```

---

## 11. Backup

### 11.1 Backup não rodou

```bash
# 1. Verificar cron
ssh root@100.99.172.84 "cat /etc/cron.d/cartorio-backup"

# 2. Rodar manualmente
ssh root@100.99.172.84 "/usr/local/bin/cartorio-backup.sh"

# 3. Verificar arquivo
ssh root@100.99.172.84 "ls -lah /var/backups/cartorio/ | tail -5"

# 4. Ver logs
ssh root@100.99.172.84 "tail -50 /var/log/cartorio-backup.log"
```

### 11.2 Backup corrompido

```bash
# 1. Verificar integridade
ssh root@100.99.172.84 "tar -tzf /var/backups/cartorio/backup-2026-06-26.tar.gz | head -10"

# 2. Se OK, restaurar (em staging primeiro!)
ssh root@100.99.172.84 "cd /tmp && tar -xzf /var/backups/cartorio/backup-2026-06-26.tar.gz"
```

### 11.3 Backup S3 não enviado

```bash
# 1. Verificar credenciais AWS
ssh root@100.99.172.84 "cat /root/.aws/credentials"

# 2. Testar conexão
ssh root@100.99.172.84 "aws s3 ls s3://cartorio-backups/"

# 3. Se não tem AWS, é PENDENTE (SUI - Gustavo exportar credenciais)
```

---

## 12. LGPD Compliance

### 12.1 Audit log parou (dead man's switch)

```bash
# 1. Verificar última inserção
curl -fsS "https://api.2notasudi.com.br/api/v1/admin/audit/health" \
  -H "X-API-Key: $API_KEY"

# 2. Se > 1h, trigger manual
curl -fsS -X POST "https://api.2notasudi.com.br/api/v1/admin/audit/check-now" \
  -H "X-API-Key: $API_KEY"

# 3. Verificar se voltou
sleep 60 && curl -fsS "https://api.2notasudi.com.br/api/v1/admin/audit/health"
```

### 12.2 Solicitação de exclusão (D09)

```bash
# 1. Cliente pede exclusão via WhatsApp
# 2. API registra solicitação
# 3. Cron roda diariamente e anonimiza após 30 dias

# Acompanhar:
psql $SUPABASE_URL -c "SELECT * FROM lgpd_data_subject_requests WHERE type = 'EXCLUSION' AND status = 'PENDING'"

# Forçar execução manual:
curl -fsS -X POST "https://api.2notasudi.com.br/api/v1/lgpd/process-exclusions" \
  -H "X-API-Key: $API_KEY"
```

### 12.3 PII vazou em log

```bash
# 1. Identificar log contaminado
grep -r "CPF:" /var/log/cartorio/ | head -10

# 2. Remover entrada (cuidado: manter audit_trail do incidente)
# 3. Rotacionar o log
# 4. Reportar para DPO (dpo@2notasudi.com.br)
# 5. Atualizar PII scrub regex
```

---

## 13. Lições Aprendidas (Troubleshooting)

| # | Lição | Descrição |
|---|-------|-----------|
| 169 | Briefing vs Ground Truth | SEMPRE validar via curl/ssh antes de mudar código |
| 178 | Race condition | SEMPRE `git fetch && git push` antes de commitar |
| 179 | Alembic drift | Usar `alembic stamp head` para alinhar |
| 181 | Git cache stale | `git update-index --refresh` antes de planejar cleanup |
| 51 | N8N_BLOCK_ENV_ACCESS | Variáveis de env não acessíveis em Code nodes |
| 113 | Gap-fix-inline-ABSORB | Aplicar fix absorvendo gap inline, não criando task nova |
| 163 | Reset paralelo | Outro agent pode dropar endpoints, sempre verificar após |

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-03
**Versão**: 1.0.0
