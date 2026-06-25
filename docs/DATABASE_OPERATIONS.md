# Database Operations — Cartório Chatbot

> Guia completo de operações de banco de dados (PostgreSQL/Supabase).
> Última atualização: 2026-06-26.

## TL;DR

**Banco central**: PostgreSQL 15+ (Supabase self-hosted).
**Total tabelas**: 134 (sendo 13 core do Cartório).
**Migrations**: 14 ativas (Alembic head 2026_06_25_0014).
**Backup**: 2x/dia (03:00 BRT lógico + 4x/dia físico pg_basebackup).

**Regra de ouro**: SEMPRE testar migration em staging antes de prod.

---

## Índice

1. [Conexão e Acesso](#1-conexão-e-acesso)
2. [Schema Core](#2-schema-core)
3. [Migrations Alembic](#3-migrations-alembic)
4. [Backups](#4-backups)
5. [Performance e Otimização](#5-performance-e-otimização)
6. [Manutenção](#6-manutenção)
7. [Segurança e RLS](#7-segurança-e-rls)
8. [Troubleshooting DB](#8-troubleshooting-db)
9. [Disaster Recovery](#9-disaster-recovery)
10. [Recursos](#10-recursos)

---

## 1. Conexão e Acesso

### 1.1 Strings de Conexão

```bash
# Via Tailscale (PREFERIDO)
postgresql://postgres:postgres@100.99.172.84:5432/postgres

# Via Supabase REST (PostgREST)
https://supbase.2notasudi.com.br/rest/v1/

# Via Supabase API GoTrue (Auth)
https://supbase.2notasudi.com.br/auth/v1/

# Service Role Key (admin - bypassa RLS)
$SUPABASE_SERVICE_ROLE_KEY

# Anon Key (cliente - respeita RLS)
$SUPABASE_ANON_KEY
```

### 1.2 psql Remoto

```bash
# Via container
ssh vps-cartorio "docker exec -it \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres"

# Via porta direta (não exposta externamente por segurança)
# Usar apenas Tailscale
psql "postgresql://postgres:postgres@100.99.172.84:5432/postgres"
```

### 1.3 Clientes Recomendados

| Cliente | Plataforma | Uso |
|---------|-----------|-----|
| **psql** | CLI | Tudo (preferencial) |
| **DBeaver** | Desktop | Visual query + ER diagram |
| **DBGate** (porta 3001) | Web (interno) | Visual query |
| **Redis Commander** (porta 8081) | Web | Cache/sessões |
| **Supabase Studio** (porta 3000) | Web | Schema + Auth + RLS |
| **pgAdmin** | Web/Desktop | Alternativa completa |

---

## 2. Schema Core

### 2.1 13 Tabelas Core do Cartório

```sql
-- 1. clientes - cadastro de clientes
clientes (
  id UUID PRIMARY KEY,
  cpf_hash TEXT UNIQUE,  -- hash para evitar PII plaintext
  nome TEXT,
  telefone TEXT,
  email TEXT,
  lgpd_consent_id UUID,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ  -- soft delete
);

-- 2. protocolos - solicitações
protocolos (
  id UUID PRIMARY KEY,
  numero TEXT UNIQUE,  -- "PROT-2026-000123"
  cliente_id UUID REFERENCES clientes(id),
  tipo TEXT,  -- 'emolumento', 'agendamento', 'segunda_via'
  status TEXT,  -- 'aberto', 'em_andamento', 'concluido', 'cancelado'
  dados JSONB,  -- dados específicos
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);

-- 3. atendimentos - registro de interações
atendimentos (
  id UUID PRIMARY KEY,
  cliente_id UUID REFERENCES clientes(id),
  protocolo_id UUID REFERENCES protocolos(id),
  canal TEXT,  -- 'whatsapp', 'telegram', 'presencial'
  agente TEXT,  -- 'pietra' ou nome humano
  mensagem_in TEXT,
  mensagem_out TEXT,
  duracao_seg INT,
  created_at TIMESTAMPTZ
);

-- 4. documentos - segunda via
documentos (
  id UUID PRIMARY KEY,
  cliente_id UUID REFERENCES clientes(id),
  tipo TEXT,
  arquivo_path TEXT,  -- Supabase Storage
  hash TEXT,  -- SHA256
  created_at TIMESTAMPTZ
);

-- 5. emolumentos - tabela MG 2026
emolumentos (
  id UUID PRIMARY KEY,
  tipo TEXT,
  valor DECIMAL(10,2),
  prazo_dias INT,
  observacoes TEXT,
  ativo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ
);

-- 6. conversas - histórico de mensagens
conversas (
  id UUID PRIMARY KEY,
  cliente_id UUID REFERENCES clientes(id),
  phone TEXT,
  message_id TEXT,  -- WhatsApp message ID
  direction TEXT,  -- 'in' ou 'out'
  content TEXT,
  correlation_id UUID,
  created_at TIMESTAMPTZ
);

-- 7. agendamentos - slots reservados
agendamentos (
  id UUID PRIMARY KEY,
  cliente_id UUID REFERENCES clientes(id),
  data DATE,
  hora_inicio TIME,
  hora_fim TIME,
  servico TEXT,
  status TEXT,
  created_at TIMESTAMPTZ
);

-- 8. audit_log - LGPD (5 anos retenção)
audit_log (
  id BIGSERIAL PRIMARY KEY,
  correlation_id UUID,
  user_id UUID,
  action TEXT,
  entity_type TEXT,
  entity_id TEXT,
  dados_before JSONB,
  dados_after JSONB,
  ip INET,
  user_agent TEXT,
  chain_hash TEXT,  -- SHA256 do registro anterior
  created_at TIMESTAMPTZ
);

-- 9. outbox_messages - padrão outbox
outbox_messages (
  id BIGSERIAL PRIMARY KEY,
  aggregate_type TEXT,
  aggregate_id TEXT,
  event_type TEXT,
  payload JSONB,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ
);

-- 10. webhook_events - recebidos
webhook_events (
  id BIGSERIAL PRIMARY KEY,
  source TEXT,  -- 'evolution', 'chatwoot', 'n8n'
  event_type TEXT,
  payload JSONB,
  processed BOOLEAN DEFAULT false,
  correlation_id UUID,
  created_at TIMESTAMPTZ
);

-- 11. lgpd_consents - consentimentos
lgpd_consents (
  id UUID PRIMARY KEY,
  cliente_id UUID REFERENCES clientes(id),
  aceito_em TIMESTAMPTZ,
  revogado_em TIMESTAMPTZ,
  ip INET,
  user_agent TEXT,
  texto_versao TEXT
);

-- 12. lgpd_audit_anpd - audit para ANPD
lgpd_audit_anpd (
  id BIGSERIAL PRIMARY KEY,
  tipo TEXT,  -- 'CONSENT', 'EXCLUSION', 'EXPORT', 'BREACH'
  cliente_id UUID,
  descricao TEXT,
  executado_por TEXT,  -- 'sistema' ou user_id
  created_at TIMESTAMPTZ
);

-- 13. workflow_publication_outbox - publish de WFs N8N
workflow_publication_outbox (
  id BIGSERIAL PRIMARY KEY,
  workflow_id TEXT,
  action TEXT,  -- 'publish', 'unpublish', 'update'
  payload JSONB,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ
);
```

### 2.2 Visualizar Schema

```bash
# Listar todas as tabelas
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c '\dt'"

# Descrever tabela
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c '\d clientes'"

# Ver índices
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c '\di+'"

# Ver triggers
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c \"SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE NOT tgisinternal;\""
```

---

## 3. Migrations Alembic

### 3.1 Estado Atual

```bash
# Ver head atual
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_api') alembic current"

# Ver chain de migrations
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_api') alembic history"

# Output esperado:
# 2026_06_25_0014 (head) - client notification fields (A26)
# 2026_06_25_0013 - agendamento cache fields
# ... (14 migrations ativas)
```

### 3.2 Criar Nova Migration

```bash
# 1. Local
cd backend

# 2. Editar model SQLAlchemy
nano app/models/nova_feature.py

# 3. Gerar migration automática
alembic revision --autogenerate -m "add nova feature"

# 4. REVISAR arquivo gerado!
# backend/alembic/versions/2026_06_26_xxxx_add_nova_feature.py
# - Verificar SQL (autogenerate nem sempre é 100%)
# - Adicionar indexes
# - Adicionar RLS se aplicável
# - Adicionar backfill se necessário

# 5. Testar local
alembic upgrade head
alembic downgrade -1  # testar reversão
alembic upgrade head  # aplicar novamente

# 6. Rodar testes
pytest backend/tests/

# 7. Commit
git add -A
git commit -m "feat(db): add nova feature migration"
git push origin master

# 8. Em prod, migration roda automaticamente no startup da API
```

### 3.3 Boas Práticas

```python
# ✅ Migration sempre reversível
def upgrade():
    op.add_column('clientes', sa.Column('novo_campo', sa.String(50)))
    op.create_index('ix_clientes_novo_campo', 'clientes', ['novo_campo'])

def downgrade():
    op.drop_index('ix_clientes_novo_campo', 'clientes')
    op.drop_column('clientes', 'novo_campo')

# ✅ Sempre em transação
# (Alembic já faz por padrão)

# ✅ Backfill se necessário
def upgrade():
    op.add_column('clientes', sa.Column('ativo', sa.Boolean(), server_default='true'))
    op.execute("UPDATE clientes SET ativo = true WHERE ativo IS NULL")
    op.alter_column('clientes', 'ativo', nullable=False)

# ❌ EVITAR
# - DROP TABLE em prod (usar soft delete)
# - ALTER TABLE com lock longo em tabelas grandes (usar CONCURRENTLY)
# - Mudanças sem migration versionada
```

### 3.4 Drift (DB vs Alembic)

**Sintoma**: DB tem tabelas que Alembic não conhece (ou vice-versa).

```bash
# Diagnosticar
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_api') alembic current"
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_api') alembic heads"

# Se DB está atrasado (não rodou última migration)
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_api') alembic upgrade head"

# Se DB está À FRENTE (tem migrations não versionadas)
# CUIDADO: investigar antes!
# Se foi intencional, marcar como stamp:
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_api') alembic stamp head"
```

---

## 4. Backups

### 4.1 Estratégia de Backup (3-2-1)

| Tipo | Frequência | Retenção | Storage |
|------|-----------|----------|---------|
| **Lógico (pg_dump)** | Diário 03:00 BRT | 7 dias local | `/var/backups/cartorio/` |
| **Físico (pg_basebackup)** | 4x/dia (00/06/12/18 UTC) | 7 dias local + S3 mensal | `/var/backups/pg_base/` + S3 |
| **WAL archiving** | Continuous | 7 dias | `/var/backups/wal/` |

### 4.2 Backup Lógico (Diário)

```bash
# Manual
ssh vps-cartorio "/usr/local/bin/cartorio-backup.sh"

# Conteúdo do script
#!/bin/bash
set -e
BACKUP_DIR=/var/backups/cartorio
DATE=$(date +%Y-%m-%d)
mkdir -p $BACKUP_DIR

# Dump de todos os DBs
for db in cartorio n8n chatwoot evolution; do
  docker exec cartorio_supabase-db pg_dump -U postgres -d $db | gzip > $BACKUP_DIR/${db}-${DATE}.sql.gz
done

# Backup N8N workflows
curl -fsS -H "X-N8N-API-KEY: $N8N_KEY" "https://flow.2notasudi.com.br/api/v1/workflows" > $BACKUP_DIR/n8n-workflows-${DATE}.json

# Compactar tudo
tar -czf $BACKUP_DIR/full-backup-${DATE}.tar.gz $BACKUP_DIR/*-${DATE}.*

# Limpar > 7 dias
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup OK: $(ls -lah $BACKUP_DIR/full-backup-${DATE}.tar.gz | awk '{print $5}')"
```

### 4.3 Backup Físico (4x/dia)

```bash
# Conteúdo de /usr/local/bin/pg_basebackup_4x.sh
#!/bin/bash
set -e
BACKUP_DIR=/var/backups/pg_base
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

docker exec cartorio_supabase-db pg_basebackup \
  -U postgres \
  -D /tmp/basebackup_$DATE \
  -Ft -z -Xs -P

docker cp cartorio_supabase-db:/tmp/basebackup_$DATE $BACKUP_DIR/
docker exec cartorio_supabase-db rm -rf /tmp/basebackup_$DATE

# Upload para S3 (mensal)
if [ "$(date +%d)" = "01" ]; then
  aws s3 cp $BACKUP_DIR/ s3://cartorio-backups/pg_base/ --recursive
fi
```

### 4.4 Restaurar Backup

```bash
# Lógico (1 DB)
LATEST=$(ssh vps-cartorio "ls -t /var/backups/cartorio/cartorio-*.sql.gz | head -1")
ssh vps-cartorio "gunzip -c $LATEST | docker exec -i cartorio_supabase-db psql -U postgres -d cartorio"

# Físico (cluster completo)
# CUIDADO: substitui TUDO
LATEST=$(ssh vps-cartorio "ls -t /var/backups/pg_base/base.tar.gz | head -1")
ssh vps-cartorio "
  docker exec cartorio_supabase-db bash -c 'rm -rf /var/lib/postgresql/data/*'
  docker cp $LATEST cartorio_supabase-db:/tmp/
  docker exec cartorio_supabase-db bash -c 'tar -xzf /tmp/$LATEST -C /var/lib/postgresql/data/'
  docker service update --force cartorio_supabase-db
"
```

### 4.5 Validar Backup

```bash
# Endpoint da API
curl -fsS https://api.2notasudi.com.br/api/v1/health/backup \
  -H "X-API-Key: $API_KEY" | jq

# Esperado:
# {
#   "last_backup": "2026-06-26T03:00:00Z",
#   "age_hours": 14,
#   "size_mb": 38,
#   "tarballs": 7,
#   "status": "OK"
# }
```

---

## 5. Performance e Otimização

### 5.1 Slow Queries (E8.A16)

```bash
# Ver top 20 queries lentas (>200ms)
curl -fsS "https://api.2notasudi.com.br/admin/slow-queries?limit=20" \
  -H "X-API-Key: $API_KEY" | jq

# Cada item:
# {
#   "query": "SELECT * FROM clientes WHERE...",
#   "duration_ms": 450,
#   "endpoint": "/api/v1/clientes",
#   "correlation_id": "abc-123",
#   "timestamp": "2026-06-26T17:30:00Z"
# }
```

### 5.2 EXPLAIN ANALYZE

```sql
-- Para query lenta, ver plano de execução
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) 
SELECT * FROM clientes WHERE cpf_hash = 'abc123';
```

**Sinais de problema**:
- `Seq Scan` em tabelas grandes (deveria ser `Index Scan`)
- `rows=N` muito diferente do real (estatísticas desatualizadas)
- `Sort` em memória (deveria usar índice)

### 5.3 Índices

```sql
-- Criar índice em coluna consultada
CREATE INDEX CONCURRENTLY ix_clientes_cpf_hash ON clientes (cpf_hash);

-- Índice composto
CREATE INDEX CONCURRENTLY ix_protocolos_cliente_status 
  ON protocolos (cliente_id, status);

-- Índice parcial (só linhas específicas)
CREATE INDEX CONCURRENTLY ix_protocolos_abertos 
  ON protocolos (cliente_id) 
  WHERE status = 'aberto';

-- Índice GIN (para JSONB)
CREATE INDEX CONCURRENTLY ix_protocolos_dados_gin 
  ON protocolos USING GIN (dados);

-- Índice para full-text search
CREATE INDEX CONCURRENTLY ix_clientes_nome_trgm 
  ON clientes USING GIN (nome gin_trgm_ops);

-- SEMPRE usar CONCURRENTLY em prod (não bloqueia tabela)
```

### 5.4 VACUUM e ANALYZE

```sql
-- Atualizar estatísticas (recomendado rodar diariamente)
ANALYZE;

-- Vacuum (libera espaço de tuplas mortas)
VACUUM (VERBOSE, ANALYZE) clientes;

-- Vacuum full (libera espaço em disco - LOCKA TABELA)
-- NÃO rodar em prod em horário de pico!
VACUUM FULL clientes;

-- Ver tuplas mortas
SELECT schemaname, relname, n_dead_tup, n_live_tup, 
       ROUND(n_dead_tup::numeric / NULLIF(n_live_tup, 0) * 100, 2) as dead_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;
```

### 5.5 Connection Pool

```sql
-- Ver conexões por DB
SELECT datname, count(*), state 
FROM pg_stat_activity 
GROUP BY datname, state;

-- Ver quem está conectando
SELECT usename, application_name, client_addr, count(*)
FROM pg_stat_activity
GROUP BY usename, application_name, client_addr;

-- Matar conexão específica
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE application_name = 'app_ofensor';
```

---

## 6. Manutenção

### 6.1 Tarefas Diárias (automatizadas via pg_cron)

```sql
-- Listar jobs
SELECT * FROM cron.job;

-- Job: VACUUM ANALYZE diário
SELECT cron.schedule('vacuum-analyze-daily', '0 3 * * *', 'VACUUM ANALYZE;');

-- Job: Limpar audit_log > 5 anos (LGPD)
SELECT cron.schedule('cleanup-audit-old', '0 4 1 * *', 
  $$DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '5 years'$$);

-- Job: Refresh materialized view
SELECT cron.schedule('refresh-mv-emolumento', '0 2 * * *', 
  'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_emolumento_ativo;');

-- Job: Limpar webhook_events processados > 30 dias
SELECT cron.schedule('cleanup-webhook-old', '0 5 * * *', 
  $$DELETE FROM webhook_events WHERE processed = true AND created_at < NOW() - INTERVAL '30 days'$$);
```

### 6.2 Tarefas Semanais (manual ou script)

```bash
# 1. Vacuum verbose (identificar tabelas com muita tupla morta)
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c 'VACUUM VERBOSE;'"

# 2. Reindex tabelas pequenas (CONCURRENTLY não funciona em todas)
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c 'REINDEX TABLE CONCURRENTLY audit_log;'"

# 3. Verificar tamanho do DB
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c \"SELECT pg_size_pretty(pg_database_size(current_database()));\""

# 4. Verificar tablespaces
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c \"SELECT spcname, pg_size_pretty(pg_tablespace_size(oid)) FROM pg_tablespace;\""
```

### 6.3 Tarefas Mensais

```bash
# 1. Análise de crescimento
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c \"
  SELECT 
    schemaname || '.' || relname as tabela,
    pg_size_pretty(pg_total_relation_size(relid)) as tamanho,
    pg_total_relation_size(relid) as bytes
  FROM pg_stat_user_tables
  ORDER BY pg_total_relation_size(relid) DESC
  LIMIT 20;
\""

# 2. Verificar queries mais executadas
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c \"
  SELECT query, calls, total_exec_time, mean_exec_time
  FROM pg_stat_statements
  ORDER BY total_exec_time DESC
  LIMIT 20;
\""

# 3. Validar backup restore (em staging!)
```

---

## 7. Segurança e RLS

### 7.1 Row Level Security (RLS)

**Tabelas com RLS ativo**:
- clientes
- protocolos
- documentos
- audit_log

```sql
-- Ver policies
SELECT schemaname, tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public';

-- Exemplo de policy (clientes só vêem seus próprios dados)
CREATE POLICY cliente_self_select ON clientes
  FOR SELECT
  USING (cpf_hash = current_setting('app.current_user_cpf')::text);

-- Service role bypassa RLS
-- (usar service_role_key para admin)
```

### 7.2 Princípios

```
✅ RLS em TODAS tabelas com dados pessoais
✅ Service role key APENAS em backend (nunca frontend)
✅ Anon key com RLS restritivo
✅ Policies testadas (TDD)
✅ Audit log de TODA ação (LGPD art. 37)
```

### 7.3 Permissões

```sql
-- Criar role para aplicação
CREATE ROLE cartorio_app LOGIN PASSWORD 'xxx';

-- Privilégios mínimos
GRANT CONNECT ON DATABASE cartorio TO cartorio_app;
GRANT USAGE ON SCHEMA public TO cartorio_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cartorio_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO cartorio_app;

-- Default para tabelas futuras
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
  GRANT SELECT, INSERT, UPDATE ON TABLES TO cartorio_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
  GRANT USAGE ON SEQUENCES TO cartorio_app;
```

### 7.4 Auditoria

```sql
-- pgaudit (log de TODAS queries)
-- Ativado em postgresql.conf:
-- shared_preload_libraries = 'pgaudit'
-- pgaudit.log = 'all'

-- Ver logs
ssh vps-cartorio "docker logs \$(docker ps -qf 'name=cartorio_supabase-db') 2>&1 | grep AUDIT"
```

---

## 8. Troubleshooting DB

### 8.1 Conexão Recusada

```bash
# 1. Verificar se container está UP
ssh vps-cartorio "docker ps | grep cartorio_supabase-db"

# 2. Ping
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') pg_isready -U postgres"

# 3. Restart se necessário
ssh vps-cartorio "docker service update --force cartorio_supabase-db"
```

### 8.2 Query Travada (Lock)

```sql
-- Ver locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Ver quem está bloqueando
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid,
       blocked_activity.query AS blocked_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
WHERE NOT blocked_locks.granted;

-- Matar processo bloqueador
SELECT pg_terminate_backend(<pid>);
```

### 8.3 Disco Cheio

```bash
# 1. Verificar uso
ssh vps-cartorio "df -h"

# 2. Ver maiores tabelas/índices
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c \"
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) 
  FROM pg_stat_user_tables 
  ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;\""

# 3. Limpar WAL
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c 'CHECKPOINT;'"

# 4. Vacuum full (locka tabela - cuidado!)
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c 'VACUUM FULL;'"
```

### 8.4 Replication Lag

```sql
-- Em replica (se houver)
SELECT EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_timestamp())) AS lag_seconds;
```

### 8.5 RLS Bloqueia Query Legítima

```sql
-- Verificar policies
SELECT * FROM pg_policies WHERE tablename = 'clientes';

-- Testar sem RLS (SERVICE ROLE)
SET ROLE postgres;
SELECT * FROM clientes LIMIT 5;
RESET ROLE;

-- Se realmente necessário, ajustar policy
DROP POLICY cliente_self_select ON clientes;
CREATE POLICY cliente_self_select ON clientes
  FOR SELECT
  USING (true);  -- CUIDADO!
```

---

## 9. Disaster Recovery

### 9.1 RPO (Recovery Point Objective)

**24 horas** (backup lógico diário) ou **6 horas** (pg_basebackup 4x/dia).

### 9.2 RTO (Recovery Time Objective)

**1-2 horas** (assumindo que VPS está acessível).

### 9.3 Cenários

| Cenário | RPO | RTO | Ação |
|---------|-----|-----|------|
| DB corrompido (dados perdidos) | 24h | 1h | Restaurar último backup lógico |
| VPS inacessível (disco morto) | 24h | 4h | Provisionar nova VPS + restaurar |
| Bug em migration | 0 | 5min | Reverter migration (`alembic downgrade`) |
| Audit log corrompido | 5 anos | 30min | Reconstruir de logs de aplicação |
| Data center disaster | 24h | 8h | Restaurar de S3 (backups externos) |

### 9.4 Testes de Recovery

**Frequência**: Mensal (primeiro sábado do mês)

```bash
# 1. Criar ambiente de staging
ssh vps-cartorio "
  docker run -d --name cartorio-staging-db \
    -e POSTGRES_PASSWORD=postgres \
    -v /var/backups/cartorio:/backups \
    postgres:15
"

# 2. Aguardar DB iniciar
sleep 30

# 3. Restaurar último backup
LATEST=$(ssh vps-cartorio "ls -t /backups/cartorio-*.sql.gz | head -1")
ssh vps-cartorio "gunzip -c $LATEST | docker exec -i cartorio-staging-db psql -U postgres -d postgres"

# 4. Validar
ssh vps-cartorio "docker exec cartorio-staging-db psql -U postgres -c 'SELECT count(*) FROM clientes;'"

# 5. Cleanup
ssh vps-cartorio "docker rm -f cartorio-staging-db"
```

---

## 10. Recursos

- **Schema completo**: `/docs/SUPABASE_SCHEMA.md`
- **Plataforma docs**: `/docs/platforms/SUPABASE.md`
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md`
- **API endpoints**: `/docs/API_ENDPOINTS_CATALOG.md`
- **LGPD**: `/docs/LGPD.md` + `/docs/ripd.md`

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
