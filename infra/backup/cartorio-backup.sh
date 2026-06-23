#!/bin/bash
# Backup diário do Supabase + n8n + cartorio-api
# Owner: cartorio-n8n
# Schedule: 0 3 * * * (3 AM diario)
# Retention: 7 dias local + push S3 (TODO)

set -e

BACKUP_DIR="/var/backups/cartorio"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)
RETAIN_DAYS=7

mkdir -p $BACKUP_DIR

echo "[$TIMESTAMP] Iniciando backup Supabase + n8n + cartorio-api"

# 1. Backup Supabase completo (cartorio + n8n + chatwoot + evolution)
for db in cartorio n8n chatwoot evolution; do
  echo "  - Backup database: $db"
  docker exec cartorio_supabase-db-1 pg_dump -U supabase_admin -h 127.0.0.1 \
    -Fc --no-owner --no-acl $db 2>/dev/null \
    > "$BACKUP_DIR/supabase_${db}_${TIMESTAMP}.dump"
done

# 2. Backup n8n workflows (via API)
echo "  - Backup n8n workflows + credentials"
N8N_KEY=$(grep N8N_API_KEY /etc/easypanel/projects/cartorio/n8n/.env 2>/dev/null | cut -d= -f2)
if [ -n "$N8N_KEY" ]; then
  mkdir -p "$BACKUP_DIR/n8n_${TIMESTAMP}"
  curl -sk "https://flow.2notasudi.com.br/api/v1/workflows?limit=200" \
    -H "X-N8N-API-KEY: $N8N_KEY" > "$BACKUP_DIR/n8n_${TIMESTAMP}/workflows.json"
  curl -sk "https://flow.2notasudi.com.br/api/v1/credentials" \
    -H "X-N8N-API-KEY: $N8N_KEY" > "$BACKUP_DIR/n8n_${TIMESTAMP}/credentials.json"
fi

# 3. Backup cartorio-api .env + alembic + migrations
echo "  - Backup cartorio-api .env + migrations"
cp /etc/easypanel/projects/cartorio/api/code/.env "$BACKUP_DIR/cartorio_api_${TIMESTAMP}.env"
cp -r /Users/gustavoalmeida/projetos/Cartorio/backend/app/models \
  "$BACKUP_DIR/cartorio_models_${TIMESTAMP}" 2>/dev/null || true

# 4. Backup Chatwoot config
echo "  - Backup chatwoot config"
docker exec cartorio_chatwoot cat /app/.env 2>/dev/null > "$BACKUP_DIR/chatwoot_${TIMESTAMP}.env" || true

# 5. Compress everything
echo "  - Compressing"
cd $BACKUP_DIR
tar -czf "cartorio_backup_${TIMESTAMP}.tar.gz" \
  supabase_*.dump n8n_${TIMESTAMP}/ cartorio_api_${TIMESTAMP}.env \
  chatwoot_${TIMESTAMP}.env 2>/dev/null
rm -rf n8n_${TIMESTAMP}/ chatwoot_${TIMESTAMP}.env

# 6. Cleanup old backups (manter 7 dias)
echo "  - Cleaning backups > $RETAIN_DAYS days"
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETAIN_DAYS -delete
find $BACKUP_DIR -name "*.dump" -mtime +$RETAIN_DAYS -delete

# 7. Status
echo "[$TIMESTAMP] Backup completo"
ls -lah $BACKUP_DIR/cartorio_backup_${TIMESTAMP}.tar.gz
du -sh $BACKUP_DIR/

# 8. Health check (envia alerta se algo falhou)
if [ ! -f "$BACKUP_DIR/cartorio_backup_${TIMESTAMP}.tar.gz" ]; then
  echo "BACKUP FAILED: tar.gz nao criado" >&2
  exit 1
fi