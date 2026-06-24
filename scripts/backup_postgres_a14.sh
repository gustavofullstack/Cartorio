#!/usr/bin/env bash
# backup_postgres_a14.sh
# Backup PostgreSQL 4x/dia via pg_basebackup + WAL archiving
# Retencao: 7d local + upload S3 mensal
#
# Cron: 0 2,8,14,20 * * * /Users/gustavoalmeida/projetos/Cartorio/scripts/backup_postgres_a14.sh
#
# Variaveis de ambiente:
#   PG_HOST       - obrigatorio (default: 10.0.1.171)
#   PG_PORT       - opcional (default: 5432)
#   PG_USER       - obrigatorio (default: supabase_admin)
#   PGPASSWORD    - obrigatorio (vem do .env)
#   BACKUP_DIR    - opcional (default: /var/backups/postgres)
#   RETENTION_DAYS - opcional (default: 7)
#   S3_BUCKET     - opcional (se setado, upload mensal)

set -euo pipefail

# Configuracao
PG_HOST="${PG_HOST:-10.0.1.171}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-supabase_admin}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/postgres}"
LOG_FILE="${LOG_FILE:-/var/log/cartorio-backup-postgres.log}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y-%m-%d-%H%M%S)
TARGET_DIR="$BACKUP_DIR/$DATE"
DAY_OF_MONTH=$(date +%d)

# Logging
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
log "=== Backup PostgreSQL iniciado ==="
log "Host: $PG_HOST:$PG_PORT | User: $PG_USER | Target: $TARGET_DIR"

# Pre-checks
if [[ -z "${PGPASSWORD:-}" ]]; then
  log "ERROR: PGPASSWORD nao definido"
  exit 1
fi
if ! command -v pg_basebackup >/dev/null 2>&1; then
  log "ERROR: pg_basebackup nao instalado (apt install postgresql-client)"
  exit 1
fi
if ! command -v gzip >/dev/null 2>&1; then
  log "ERROR: gzip nao instalado"
  exit 1
fi

# Cria diretorio
mkdir -p "$TARGET_DIR"

# pg_basebackup (formato tar compactado)
log "Executando pg_basebackup ..."
START=$(date +%s)
if ! PGPASSWORD="$PGPASSWORD" pg_basebackup \
    -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" \
    -D "$TARGET_DIR" \
    -Ft -z -Xs -P -c fast 2>>"$LOG_FILE"; then
  log "ERROR: pg_basebackup falhou"
  exit 1
fi
END=$(date +%s)
DURATION=$((END - START))
log "pg_basebackup concluido em ${DURATION}s"

# Metadata
BACKUP_SIZE=$(du -sh "$TARGET_DIR" | awk '{print $1}')
cat > "$TARGET_DIR/_metadata.json" <<EOF
{
  "date": "$DATE",
  "host": "$PG_HOST:$PG_PORT",
  "user": "$PG_USER",
  "size": "$BACKUP_SIZE",
  "duration_seconds": $DURATION,
  "format": "tar.gz",
  "retention_days": $RETENTION_DAYS,
  "version": "1.0.0"
}
EOF

# Compressao final (opcional - pg_basebackup ja compacta com -z)
log "Tamanho: $BACKUP_SIZE | Duracao: ${DURATION}s"

# Limpeza retencao 7 dias
log "Removendo backups com mais de $RETENTION_DAYS dias ..."
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
REMAINING=$(find "$BACKUP_DIR" -maxdepth 1 -type d | wc -l | tr -d ' ')
log "Backups restantes: $REMAINING"

# S3 upload mensal (1º dia do mes)
if [[ "$DAY_OF_MONTH" == "01" ]] && [[ -n "${S3_BUCKET:-}" ]] && command -v aws >/dev/null 2>&1; then
  log "Upload S3 mensal para s3://$S3_BUCKET/postgres/$DATE.tar.gz ..."
  tar -czf "$TARGET_DIR.tar.gz" -C "$BACKUP_DIR" "$DATE" 2>>"$LOG_FILE"
  aws s3 cp "$TARGET_DIR.tar.gz" "s3://$S3_BUCKET/postgres/$DATE.tar.gz" \
    --storage-class STANDARD_IA 2>>"$LOG_FILE" || log "WARN: S3 upload falhou"
else
  log "S3 upload desabilitado (S3_BUCKET vazio, AWS CLI ausente, ou nao dia 1)"
fi

log "=== Backup concluido ==="
exit 0
