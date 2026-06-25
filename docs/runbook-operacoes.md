# Runbook Operacoes - Cartorio 2o Notas

**SQUAD C C6** - procedures de operacao dia-a-dia
**Owner**: Gustavo Almeida + DPO Maria Silva
**Atualizado**: 2026-06-25

## 1. Daily Operations (09:00 BRT)

### 1.1 Check Health (5 min)
```bash
curl -s https://api.2notasudi.com.br/api/v1/health/radar | python3 -m json.tool
# Esperado: 8/8 integracoes online, status=green, offline=0
```

### 1.2 Check Audit Log Freshness (1 min)
```bash
curl -s https://api.2notasudi.com.br/api/v1/admin/audit/dead-mans-switch/check \
  -H "X-API-Key: $CARTORIO_API_KEY" | python3 -m json.tool
# Esperado: status_code=200, level=healthy
```

### 1.3 Check Telegram bot (1 min)
```bash
curl -s "https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/getWebhookInfo"
# Esperado: url=https://api.2notasudi.com.br/api/v1/telegram/webhook, pending_update_count=0
```

### 1.4 Check Supabase schema (1 min)
```bash
curl -s "https://supbase.2notasudi.com.br/rest/v1/" -H "apikey: $SUPABASE_ANON_KEY" | head -c 200
# Esperado: {"swagger":"2.0",...}
```

### 1.5 Check N8N workflows (2 min)
```bash
cd backend && uv run python scripts/test_n8n_workflows.py
# Esperado: 42 passed, 3 failed (pre-existentes)
```

## 2. Weekly Operations (segunda 09:00 BRT)

### 2.1 Backup verify (10 min)
```bash
# A14 ja faz 4x/dia
curl -s https://api.2notasudi.com.br/api/v1/health/backup-v2 \
  -H "X-API-Key: $CARTORIO_API_KEY" | python3 -m json.tool
# Esperado: last_backup_age_hours < 8
```

### 2.2 Audit chain verify (5 min)
```bash
curl -s https://api.2notasudi.com.br/api/v1/audit/verify \
  -H "X-API-Key: $CARTORIO_API_KEY" | python3 -m json.tool
# Esperado: chain_ok=true
```

### 2.3 LGPD dashboard review (10 min)
```bash
curl -s https://api.2notasudi.com.br/api/v1/admin/lgpd/relatorio-anual \
  -H "X-API-Key: $CARTORIO_API_KEY" | python3 -m json.tool
```

### 2.4 N8N metrics review
```bash
curl -s https://api.2notasudi.com.br/api/v1/metrics/prometheus | grep "n8n_wf"
```

## 3. Monthly Operations (1o dia util 09:00 BRT)

### 3.1 ANPD relatorio anual (D9)
- Ja auto-gerado em `audit_log` snapshot_diario_2355 (S0 S03)
- Manual: curl /api/v1/admin/lgpd/relatorio-anual

### 3.2 Backup restore test (30 min)
- Baixar ultimo backup pg_basebackup
- Subir em container descartavel
- Validar dados consistentes

### 3.3 LGPD retentions review
```bash
curl -s https://api.2notasudi.com.br/api/v1/admin/lgpd/retention/check \
  -H "X-API-Key: $CARTORIO_API_KEY"
```

### 3.4 Mavis status review
- /api/v1/brain/loop-state
- /api/v1/health/integracoes
- /api/v1/metrics/prometheus (parsear)

## 4. Incident Response (Playbooks)

### 4.1 API down (5xx > 1min)
1. Check /api/v1/health/integracoes
2. Check API logs: `docker service logs cartorio_api --tail 100`
3. Restart: `docker service update --force cartorio_api`
4. Notify Gustavo + DPO via Telegram GRUPO Pietra (B11)
5. Update incident: Linear CAR-XXX

### 4.2 N8N WF falha
1. Check WF execution: /flow.2notasudi.com.br/executions
2. Ver error stack
3. Re-try: B06 error handler global ja faz
4. If persistent: rollback WF via git checkout <commit>

### 4.3 Evolution API down
1. Check /instance/connectionState/cartorio-2notas
2. Se state=close: pedir Gustavo escanear QR
3. Se 5xx: restart Evolution: `docker service update --force cartorio_evolution-api`
4. Verify webhook config: `webhook/set/cartorio-2notas`

### 4.4 Supabase down
1. Check container: `docker ps | grep supabase`
2. Check logs: `docker logs cartorio_supabase-db-1 --tail 50`
3. Restart: `docker service update --force cartorio_supabase-db-1`
4. Verify RLS: `psql -c "\dp"`

### 4.5 OpenClaw down
1. Check /healthz
2. Check config: `docker exec cartorio_openclaw-gateway-1 openclaw config get agents.defaults.model`
3. Restart: `docker service update --force cartorio_openclaw-gateway`

### 4.6 LGPD data breach (art. 48 - 72h)
1. Contain: revoke keys, isolate container
2. Investigate: audit_log desde timestamp
3. ANPD notification: ate 72h
4. Customer notification: se afetar > 100 ou dado sensivel
5. Document: criar incident report
6. Linear CAR-XXX "BREACH-YYYY-MM-DD"

## 5. Deploy

### 5.1 CI/CD pipeline
- Push to master -> Render auto-deploy (J3)
- GitHub Actions ci.yml roda gates (J7)
- Apos merge: `cd /Users/gustavoalmeida/projetos/Cartorio && git push origin master`

### 5.2 Alembic migrations
```bash
cd backend
uv run alembic upgrade head  # local
# Em prod:
docker exec cartorio_api.1.<id> alembic upgrade head
```

### 5.3 N8N WFs
- Editar em /Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/*.json
- Push master -> render auto-deploy
- Manual sync: Settings -> Workflows -> Import

## 6. Security

### 6.1 Secret rotation (NUNCA - regra Gustavo)
- NAO rotacionar chaves (so Gustavo + Pietra temos acesso)
- Salvar sempre em .env.local + .secrets/{name}.env + ~/.mavis/secrets/

### 6.2 PII Protection
- PII nunca em logs (D8 sanitizer)
- IP truncado /24 em logs (D13)
- Audit log imutavel com HMAC chain

### 6.3 LGPD rights (art. 18)
- Confirmacao: GET /api/v1/lgpd/clientes/{id}/historico
- Acesso: GET /api/v1/lgpd/export {cliente_id}
- Correcao: PATCH /api/v1/clientes/{id}
- Eliminacao: DELETE /api/v1/lgpd/clientes/{id} (D14)
- Portabilidade: GET /api/v1/lgpd/export
- Revogacao: DELETE /api/v1/lgpd/consent

Modified by Pietra + Gustavo Almeida 2026-06-25
