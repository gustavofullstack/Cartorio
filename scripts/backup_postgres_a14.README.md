# Backup PostgreSQL - Squad A Task A14

Backup incremental 4x/dia via `pg_basebackup` + retencao local 7d + upload S3 mensal.

## Especificacoes

| Item | Valor |
|------|-------|
| Frequencia | 4x/dia (02:00, 08:00, 14:00, 20:00 BRT) |
| Ferramenta | `pg_basebackup` (formato tar + gzip + WAL streaming) |
| Retencao local | 7 dias |
| Retencao S3 | Mensal (upload dia 1, classe STANDARD_IA) |
| Duracao tipica | 30-90s (depende do tamanho do DB) |
| Tamanho tipico | ~150MB compactado (cartorio Supabase) |
| Storage class | STANDARD_IA (S3) = -40% custo vs STANDARD |

## Cron (adicionar via `crontab -e` na VPS)

```cron
# Backup cartorio 4x/dia (BRT = UTC-3)
0 2,8,14,20 * * * /Users/gustavoalmeida/projetos/Cartorio/scripts/backup_postgres_a14.sh >> /var/log/cartorio-backup-cron.log 2>&1
```

## Variaveis de ambiente

| Variavel | Obrigatorio | Default | Descricao |
|----------|-------------|---------|-----------|
| `PG_HOST` | sim | 10.0.1.171 | IP/container do Postgres |
| `PG_PORT` | nao | 5432 | Porta |
| `PG_USER` | sim | supabase_admin | Usuario com direito a basebackup |
| `PGPASSWORD` | sim | - | Vem do `.env` da VPS |
| `BACKUP_DIR` | nao | /var/backups/postgres | Diretorio de destino |
| `LOG_FILE` | nao | /var/log/cartorio-backup-postgres.log | Log estruturado |
| `RETENTION_DAYS` | nao | 7 | Dias de retencao local |
| `S3_BUCKET` | nao | - | Se setado, upload mensal (dia 1) |

## Pre-requisitos VPS

```bash
# 1. Instalar pg_basebackup (cliente PostgreSQL)
apt install -y postgresql-client-15

# 2. Criar diretorio de backup
mkdir -p /var/backups/postgres
chown -R root:root /var/backups/postgres
chmod 700 /var/backups/postgres  # PII no DB = chmod restritivo

# 3. AWS CLI (opcional, para S3)
apt install -y awscli
aws configure  # set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY

# 4. Permissao no Postgres (ALTER ROLE pra backup)
docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1 -c \
  "ALTER ROLE supabase_admin REPLICATION;"
```

## Restore (DR)

```bash
# 1. Escolher backup
ls -la /var/backups/postgres/

# 2. Parar aplicacao
docker service scale cartorio_api=0

# 3. Limpar volume
docker exec cartorio_supabase-db-1 rm -rf /var/lib/postgresql/data/*

# 4. Restaurar
docker exec -i cartorio_supabase-db-1 tar -xzf <(cat /var/backups/postgres/2026-06-25-020000/base.tar.gz)

# 5. Subir aplicacao
docker service scale cartorio_api=1
```

## Monitoramento

- `/var/log/cartorio-backup-postgres.log` - log estruturado de cada execucao
- Alvo: 4 entradas por dia no log, sem `ERROR` ou `WARN`
- Validar: `grep -c "Backup concluido" /var/log/cartorio-backup-postgres.log` (deve crescer +1/dia)

## LGPD

- Backup contem PII (CPF, RG, etc) - **mesma protecao do DB principal**:
  - Permissao 700 no diretorio
  - Criptografia at-rest no volume (ZFS/LUKS)
  - S3 com SSE-KMS (configurar bucket)
  - Retencao 7d local eh o SUFICIENTE - 30d S3 cobre DR mensal
- Audit log: `audit_log` table registra `backup.completed` em cada execucao
- DPA com provedor S3 (AWS) coberto por D04 DPA Cloudflare (nao AWS direto) - **pendente revisao cartorio-lgpd**

## Cross-project lesson

> **Backup com `pg_basebackup -Xs -c fast`** = backup consistente com WAL streaming + checkpoint forced. Recovery Point Objective (RPO) ~= 0 se WAL archive estiver ativo. Trade-off: precisa de storage 2x do tamanho do DB durante o backup (cleanup auto).
