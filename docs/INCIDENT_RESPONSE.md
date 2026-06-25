# 🚨 Incident Response — C14

> **SQUAD C** | **Owner**: cartorio-zcode + cartorio-dev
> **Data**: 2026-06-26
> **Status**: ✅ DONE

Playbooks detalhados de resposta a incidentes para o sistema Cartório 2º Notas.

---

## 🎯 Severidade e Resposta

| Sev | Impacto | Resposta | Resolução | Comunicação |
|-----|---------|----------|-----------|-------------|
| **P0** | Sistema DOWN | < 15min | < 1h | Telegram DM+grupo |
| **P1** | Funcionalidade degradada | < 1h | < 4h | Telegram grupo |
| **P2** | Feature impactada | < 4h | < 1 dia | Telegram grupo |
| **P3** | Cosmético | < 1 semana | próximo sprint | assíncrono |

---

## 🚨 Playbook 1: API DOWN (P0)

### Sinais
- `curl /api/v1/health/radar` retorna 5xx ou timeout
- Alerta Prometheus: `up{job="api"} == 0`
- Alerta Telegram GRUPO PIETRA SQUAD

### Resposta (15min)
```bash
# 1. Verificar container
ssh root@100.99.172.84 "docker service ps cartorio_api"

# 2. Ver logs
ssh root@100.99.172.84 "docker service logs cartorio_api --tail 100"

# 3. Restart
ssh root@100.99.172.84 "docker service update --force cartorio_api"

# 4. Validar
sleep 5
curl https://api.2notasudi.com.br/health

# 5. Se ainda DOWN, rollback
ssh root@100.99.172.84 "docker service update --image easypanel/cartorio/api:v0.6.0 cartorio_api"
```

### Pós-incidente
1. Criar `docs/POSTMORTEMS.md#INC-XXX` (template abaixo)
2. Atualizar `.harness/memory/MEMORY.md` com lesson
3. Commit: `docs(incident): postmortem INC-XXX`
4. Notificar Gustavo via Telegram DM

---

## 🚨 Playbook 2: WhatsApp Flow Interrompido (P0)

### Sinais
- Cliente envia msg mas não recebe resposta em 30s
- `audit_log` não registra nova entrada em 5min
- OpenClaw WS disconnect (log)

### Resposta
```bash
# 1. Verificar Evolution API
curl https://whatsapp.2notasudi.com.br/manager

# 2. Verificar instance
ssh root@100.99.172.84 "docker service logs cartorio_evolution-api --tail 50"

# 3. Verificar webhook N8N
curl -X GET "https://flow.2notasudi.com.br/api/v1/workflows" -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.[] | select(.name | contains("evo"))'

# 4. Testar webhook manualmente
curl -X POST "https://flow.2notasudi.com.br/webhook/evo-in" -H "Content-Type: application/json" -d @test-payload.json

# 5. Restart chain
ssh root@100.99.172.84 "docker service update --force cartorio_evolution-api cartorio_n8n"
```

---

## 🚨 Playbook 3: Database Connection Pool Saturado (P1)

### Sinais
- API retorna 500 com "FATAL: too many connections"
- `/admin/pool` mostra checked_out == total_capacity
- Latência sobe > 2s

### Resposta
```bash
# 1. Verificar pool stats
curl -sk -H "X-API-Key: $API_KEY" https://api.2notasudi.com.br/admin/pool

# 2. Identificar connections abertas
ssh root@100.99.172.84 "docker exec cartorio_api python -c \"
import psycopg2
conn = psycopg2.connect(DSN)
cur = conn.cursor()
cur.execute('SELECT pid, application_name, state, query_start FROM pg_stat_activity WHERE datname = current_database() AND state != \"idle\"')
for r in cur.fetchall():
    print(r)
\""

# 3. Matar connections idle
ssh root@100.99.172.84 "docker exec cartorio_db pg_terminate_backend(...)"
```

### Mitigação
- A15: `db_pool_size=20`, `db_max_overflow=10` (total 30)
- Se recorrente: adicionar PgBouncer ou upgrade Supabase RAM

---

## 🚨 Playbook 4: OpenClaw 401 Unauthorized (P0 — PII)

### Sinais
- API retorna 401 "agent unauthorized" (logs)
- OpenClaw Agent WS disconnect
- Telegram bot para de responder

### Resposta
```bash
# 1. Verificar chave OpenCode-Go
ssh root@100.99.172.84 "docker exec cartorio_openclaw-gateway env | grep OPENCODE"

# 2. Verificar config agent.json
ssh root@100.99.172.84 "cat /home/node/.openclaw/agents/main/agent/agent.json | grep -A 2 api_key"

# 3. Atualizar chave (SEM rotacionar — Gustavo autoriza)
# scripts/fix_openclaw_context_1M.sh já faz isso

# 4. Restart
ssh root@100.99.172.84 "docker service update --force cartorio_openclaw-gateway"
```

---

## 🚨 Playbook 5: LGPD - Cliente Solicita Exclusão (P1)

### Sinais
- Cliente envia mensagem com "EXCLUIR DADOS" / "SAIR" / "DELETAR"
- Workflow #D25 recebe solicitação
- API registra em `lgpd_requests` table

### Resposta (SLA: 15 dias)
```bash
# 1. Confirmar identidade (documento com foto)
# 2. Verificar retenção legal (5 anos para protocolos concluídos)
# 3. Agendar anonimização 30 dias
ssh root@100.99.172.84 "docker exec cartorio_api python -c \"
from app.jobs.retencao import anonimizar_cliente
anonimizar_cliente(cliente_id, motivo='LGPD_ESQUECIMENTO')
\""
# 4. Notificar DPO
echo "Solicitacao LGPD processada - cliente: $NOME" | mail -s "LGPD Esquecimento" dpo@2notasudi.com.br
```

### Compliance
- LGPD art. 18 VI (esquecimento)
- Mas: retenção 5 anos para protocolos (Provimento CNJ 74/2018)
- Audit log LGPD art. 37 (5 anos retenção do registro)

---

## 🚨 Playbook 6: N8N Workflow Failure (P1)

### Sinais
- Workflow status: `error` (visible em N8N UI)
- Alerta Telegram B11 (error handler global)
- Métrica `n8n_wf_executions_total{status="error"}` sobe

### Resposta
```bash
# 1. Verificar qual workflow falhou
# (alert Telegram indica)

# 2. Ver executions
curl -X GET "https://flow.2notasudi.com.br/api/v1/executions" -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | select(.status=="error") | {id, workflowId, startedAt, data: .data.resultData.error.message}'

# 3. Re-executar manualmente se necessário
curl -X POST "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID/execute" -H "X-N8N-API-KEY: $N8N_API_KEY" -d '{}'

# 4. Investigar log
ssh root@100.99.172.84 "docker service logs cartorio_n8n --tail 100 | grep ERROR"
```

---

## 🚨 Playbook 7: Backup Failure (P0 LGPD)

### Sinais
- `/api/v1/health/backup` retorna 500 ou stale
- Cron `cartorio-backup-monitor` alerta Telegram
- Backup file missing em `/home/easypanel/backups/`

### Resposta
```bash
# 1. Verificar cron
ssh root@100.99.172.84 "systemctl status cartorio-backup.timer"

# 2. Rodar backup manual
ssh root@100.99.172.84 "/usr/local/bin/pg_basebackup_4x.sh"

# 3. Verificar arquivo gerado
ssh root@100.99.172.84 "ls -la /home/easypanel/backups/cartorio/"

# 4. Se falhar, verificar espaço em disco
ssh root@100.99.172.84 "df -h /home/easypanel/backups"
```

### Compliance
- LGPD art. 37 (5 anos retenção) — backup é parte do compliance
- Provimento CNJ 74/2018

---

## 📊 Tabela de Escalação

| Severidade | Quem Notificar | Quando |
|------------|----------------|--------|
| P0 | Gustavo (DM) + Squad grupo | IMEDIATO |
| P1 | Squad grupo + Gustavo se 30min sem solução | < 30min |
| P2 | Squad grupo | < 1h |
| P3 | Linear ticket | < 1 dia |

---

## 🔧 Ferramentas de Diagnóstico

### Health Checks
```bash
# Todos servicos
curl https://api.2notasudi.com.br/api/v1/health/radar

# Individual
for s in api flow whatsapp chat agent supbase easypanel; do
  curl -sk -o /dev/null -w "$s: %{http_code}\n" https://$s.2notasudi.com.br/
done
```

### Logs Centralizados
```bash
# API
ssh root@100.99.172.84 "docker service logs cartorio_api --tail 100"

# N8N
ssh root@100.99.172.84 "docker service logs cartorio_n8n --tail 100"

# Supabase
ssh root@100.99.172.84 "docker exec cartorio_db psql -U postgres -c 'SELECT * FROM pg_stat_activity LIMIT 20'"
```

### Métricas Prometheus
```bash
curl https://api.2notasudi.com.br/api/v1/metrics/prometheus
```

---

## 🔄 Pós-Incidente

### Checklist obrigatório
- [ ] Criar postmortem em `docs/POSTMORTEMS.md`
- [ ] Atualizar `.harness/memory/MEMORY.md` com lesson
- [ ] Commit: `docs(incident): postmortem INC-XXX`
- [ ] Push para origin/master
- [ ] Notificar Gustavo via Telegram DM (se P0/P1)
- [ ] Se LGPD: notificar DPO
- [ ] Se credencial comprometida: rotacionar AGORA (com Gustavo)
- [ ] Atualizar este playbook com lições aprendidas

### Postmortem template
```markdown
## INC-XXX: <Título>

**Data**: YYYY-MM-DD HH:MM BRT
**Severidade**: P0/P1/P2/P3
**Duração**: XXmin (HH:MM até HH:MM)
**Detectado por**: <quem>
**Resolvido por**: <quem>

### Timeline
- HH:MM — evento 1
- HH:MM — evento 2
- HH:MM — resolução

### Root Cause
<descrição>

### Impact
- Usuários afetados: XXX
- Mensagens perdidas: XX
- Receita perdida: R$ XX

### Resolution
<como foi resolvido>

### Lessons Learned
- L<num>: <descrição>
- L<num>: <descrição>

### Action Items
- [ ] AI-1: <descrição>
- [ ] AI-2: <descrição>
```

---

## 🔗 Links

- **Health radar**: https://api.2notasudi.com.br/api/v1/health/radar
- **Postmortems**: `docs/POSTMORTEMS.md`
- **SLA**: `docs/SLA.md`
- **Runbook**: `docs/RUNBOOK_VPS.md`
- **Memory**: `.harness/memory/MEMORY.md`
- **Super Prompt v4.0.0**: PROMPT.MD (Bloco 15.3)

---

**Mantido por**: ZCode/Mavis (orquestrador)
**Última atualização**: 2026-06-26
**Próxima revisão**: 2026-09-26 (trimestral)
**Status**: ✅ C14 SQUAD C DONE
