# 🚨 RUNBOOK VPS — Cartório 2 Notas Uberlândia

> **REGRA DE OURO**: SEMPRE use `ssh cartorio`. **NUNCA** use `ssh vps` (IP stale 100.120.250.91 não existe).
> **Versão**: 1.0.0 (2026-06-23)
> **Owner**: ZCode + cartorio-devops

---

## 1. Acesso à VPS

### Tailscale (RECOMENDADO)
```bash
ssh cartorio
# ou
ssh cartorio-ts
# ou
ssh 100.99.172.84
# Key: ~/.ssh/id_ed25519_cartorio
```

### IP público (fallback)
```bash
ssh cartorio-public
# ou
ssh 187.77.236.77
# Key: mesma
```

### ⚠️ NÃO use
```bash
ssh vps           # IP stale 100.120.250.91 (NÃO EXISTE)
ssh vps-tailscale # mesmo IP stale
ssh vps-public    # 148.230.75.172 caiu em outro projeto (udiapods_*)
```

---

## 2. Comandos úteis

### Estado geral
```bash
# Containers UP
ssh cartorio 'docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" | grep cartorio'

# Health por container
ssh cartorio 'docker ps --filter "name=cartorio" --format "{{.Names}}: {{.Status}}"'

# Logs últimos 50
ssh cartorio 'docker service logs cartorio_api --tail 50'
```

### Restart seguro
```bash
# N8N (raro quebrar)
ssh cartorio 'docker service update --force cartorio_n8n'

# API (deploy)
ssh cartorio 'docker service update --force cartorio_api'

# Redis (cuidado, perde cache)
ssh cartorio 'docker service update --force cartorio_redis'
```

### Validar domínios públicos
```bash
for d in api flow whatsapp agent easypanel supbase chatwoot; do
  code=$(curl -s -m 5 -o /dev/null -w "%{http_code}" https://${d}.2notasudi.com.br/)
  echo "$d.2notasudi.com.br -> $code"
done
```

Status esperado:
- api/flow/whatsapp/agent/easypanel → 200
- supbase → 401 (Kong OK)
- chatwoot → 000 (DNS pendente, configurar na Hostinger)

---

## 3. Trilha de auditoria (3 ground truths)

**Antes de declarar "sistema down", validar:**

1. **SSH conecta** com alias correto? (`ssh cartorio`)
2. **Container UP**? (`docker service ls | grep cartorio`)
3. **Domínio responde** com status esperado? (curl acima)

Se os 3 passam → sistema está no ar. Problema é de acesso local ou interpretação de status code.

---

## 4. Pendências VPS (T0.7-T0.12 do SUPER_PLANO v0.6.0)

### cartorio-devops (T0.7-T0.8)
- [ ] T0.7: cert wildcard + Traefik router `*.tail2fe279.ts.net`
- [ ] T0.8: Tailscale ACL tag `tag:cartorio`

### Pietra UI (T0.9-T0.12)
- [ ] T0.9: DNS `chatwoot.2notasudi.com.br` (Hostinger/Cloudflare)
- [ ] T0.10: Chatwoot Agent Bot (webhook → `/api/v1/webhook/chatwoot`)
- [ ] T0.11: Easypanel API key regenerar (a antiga morreu 401)
- [ ] T0.12: Decidir typo `supbase` vs `supabase` (P2 opcional)

---

## 5. Contatos de emergência

- **CEO/Dono**: Pietra (Gustavo Almeida) — `gustavomar.fullstack@gmail.com`
- **DPO**: `dpo@2notasudi.com.br` (LGPD)
- **Easypanel UI**: `https://easypanel.2notasudi.com.br`
- **Hostinger painel**: `https://hpanel.hostinger.com`
- **Cloudflare**: `https://dash.cloudflare.com`
- **Tailscale admin**: `https://login.tailscale.com/admin`

---

## 6. Comandos PROIBIDOS (vai quebrar)

```bash
# NÃO execute sem Gustavo autorizar
ssh cartorio 'docker service rm cartorio_*'        # remove serviço
ssh cartorio 'docker network rm easypanel-cartorio' # remove rede
ssh cartorio 'rm -rf /var/lib/docker/volumes/*'     # deleta volumes (DADOS)
ssh cartorio 'docker swarm leave --force'           # sai do swarm
```

Modified by ZCode (Pietra session 2026-06-23)

---

## 11. Cenarios de Incidente (10 cenarios praticos)

> Comandos exatos para resolver problemas comuns em PRODUCAO.
> Cada cenario: sintoma, diagnostico, solucao, prevencao.

### Cenario 1: "API retornando 500 em todas as rotas"

**Sintoma**: `/health` retorna 500, webhooks nao funcionam, dashboard caiu.

**Diagnostico**:
```bash
ssh cartorio
docker service logs cartorio_api --tail 100
# OU
easypanel services logs cartorio_api --tail 100
```

**Causas comuns**:
- DB offline (postmaster caiu)
- Variavel de env faltando
- Migration Alembic nao aplicada
- OOM (out of memory)

**Solucao**:
```bash
# 1. Checar DB
curl http://localhost:8000/api/v1/health/db

# 2. Se DB offline, ver logs
docker service logs cartorio_supabase-db-1 --tail 50

# 3. Restart do servico
docker service update --force cartorio_api

# 4. Se persistir, ver env
docker exec cartorio_api.1.<task_id> env | grep -E "DATABASE|REDIS|SUPABASE"
```

**Prevencao**: monitorar `/api/v1/health/db` em alerta Grafana.

---

### Cenario 2: "Audit log quebrado - /api/v1/audit/verify retorna invalid"

**Sintoma**: LGPD audit verify retorna `{valid: false, broken_at_id: N}`.

**Diagnostico**:
```bash
# Ver entrada exata quebrada
docker exec cartorio_supabase-db-1 psql -U supabase_admin -d cartorio \
  -c "SELECT id, hash_anterior, hash_atual, criado_em FROM audit_log WHERE id BETWEEN N-2 AND N+2;"
```

**Causa**: alguma entrada foi editada manualmente OU o hash chain tem inconsistencia.

**Solucao**:
- Se foi editada por admin (LGPD esqueci meu dado), AUDITAR quem editou
- Se foi bug, verificar se o servico estava rodando durante o periodo
- **NUNCA** edite o audit log manualmente (imutavel por design LGPD)

**Prevencao**: GRANT INSERT-only no role do backend (`REVOKE UPDATE, DELETE ON audit_log FROM cartorio_app`).

---

### Cenario 3: "Chatwoot restart loop (B1 SUI)"

**Sintoma**: Container Chatwoot reiniciando a cada 30s.

**Diagnostico**:
```bash
docker service ps cartorio_chatwoot
docker service logs cartorio_chatwoot --tail 50
```

**Solucao** (RCA em ADR-015):
1. Aplicar fix OOM: aumentar memoria para 2GB no Easypanel
2. Verificar healthcheck: `HEALTHCHECK --interval=30s --timeout=10s`
3. Se ainda loopar, ver ADR-015 4 hipoteses e排查

---

### Cenario 4: "OpenClaw context overflow (B2 SUI)"

**Sintoma**: OpenClaw reinicia a cada 50-100 mensagens, contexto perdido.

**Diagnostico**:
```bash
docker service logs cartorio_openclaw-gateway --tail 30
```

**Solucao** (5min):
1. OpenClaw UI: Settings > Context > Max messages = 50
2. TTL: 24h
3. Compaction manual: `curl -X POST http://localhost:18790/compact`

Ref: ADR-016.

---

### Cenario 5: "Redis offline - rate limit fail-open"

**Sintoma**: Logs mostram `rate_limit: Redis offline, fail-open`.

**Diagnostico**:
```bash
docker service ps cartorio_redis
docker service logs cartorio_redis --tail 50
curl http://localhost:8000/api/v1/health/redis
```

**Solucao**:
```bash
docker service update --force cartorio_redis
# Se persistir, ver firewall
iptables -L DOCKER-USER | grep 6379
```

**Prevencao**: Redis monitorado em `/api/v1/health/redis` no Grafana.

---

### Cenario 6: "Webhook Evolution nao chega no backend"

**Sintoma**: Cliente manda msg WhatsApp, bot nao responde.

**Diagnostico**:
```bash
# 1. Ver webhook configurado
curl -s -H "apikey: $EVOLUTION_API_KEY" \
  http://whatsapp.2notasudi.com.br/webhook/find/cartorio-2notas

# 2. Testar webhook
curl -X POST https://api.2notasudi.com.br/api/v1/webhook/evolution \
  -H "Content-Type: application/json" \
  -d '{"event": "test"}'
```

**Solucao**:
```bash
# Reconfigurar webhook
curl -X POST -H "apikey: $EVOLUTION_API_KEY" -H "Content-Type: application/json" \
  -d '{"url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
       "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]}' \
  http://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas
```

---

### Cenario 7: "Backup diario falhou (3 dias consecutivos)"

**Sintoma**: Alerta Telegram do N8N workflow #09 (Monitor Backup Diario).

**Diagnostico**:
```bash
# 1. Ver logs do N8N workflow
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "http://flow.2notasudi.com.br/api/v1/executions?workflowId=9&limit=5" | jq .

# 2. Verificar cron em si
ssh cartorio crontab -l | grep backup

# 3. Verificar backup manual
ls -lh /var/backups/cartorio/ | tail
```

**Solucao**:
```bash
# Rodar backup manual
ssh cartorio /usr/local/bin/cartorio-backup.sh

# Se falhar, ver espaco em disco
ssh cartorio df -h
```

---

### Cenario 8: "DNS nao resolve (cartorio-api.2notasudi.com.br NXDOMAIN)"

**Sintoma**: `curl https://cartorio-api.2notasudi.com.br` retorna DNS error.

**Diagnostico**:
```bash
nslookup cartorio-api.2notasudi.com.br
# Se NXDOMAIN: DNS nao configurado OU nao propagado
```

**Solucao**:
1. Easypanel UI > Services > cartorio_api > Domains
2. Verificar se dominio esta listado
3. Se nao, adicionar e salvar
4. Aguardar 5min para propagacao

---

### Cenario 9: "Cliente pede direito ao esquecimento (LGPD art. 18 VI)"

**Sintoma**: Cliente envia "esqueci meu dado" via WhatsApp/web.

**Diagnostico**:
- Confirmar identidade do cliente (canal autenticado)
- Verificar se pedido foi feito pelo proprio cliente

**Solucao**:
```bash
# Confirmar com DPO
# Executar via API
curl -X POST -H "X-API-Key: $DPO_KEY" -H "Content-Type: application/json" \
  -d '{"cliente_id": 42, "confirmacao_dupla": true, "motivo": "cliente_solicitou"}' \
  https://api.2notasudi.com.br/api/v1/lgpd/direito-esquecimento

# Confirmar ao cliente em <15 dias (prazo LGPD)
```

**Prevencao**: politica publicada em `politica-privacidade.2notasudi.com.br`.

---

### Cenario 10: "Servicos fora do ar (todos 503)"

**Sintoma**: TODOS os 7 servicos do `/health/radar` retornam offline.

**Diagnostico**:
```bash
ssh cartorio
docker node ls
docker network ls | head
# Checar se Swarm ainda funciona
docker service ls | wc -l
```

**Causa provavel**: VPS reiniciou OU Docker daemon crash OU disk full.

**Solucao**:
```bash
# 1. Reiniciar Docker
sudo systemctl restart docker

# 2. Reiniciar Swarm (cuidado - pode perder state)
sudo systemctl restart docker
sleep 30
docker node ls

# 3. Forcar restart de todos os servicos
for s in $(docker service ls -q); do
  docker service update --force $s
done
```

**Prevencao**: UptimeRobot em `https://api.2notasudi.com.br/health` + alerta Telegram.

---

Modified by ZCode/Mavis - 2026-06-24
