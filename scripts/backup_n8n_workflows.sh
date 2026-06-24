#!/usr/bin/env bash
# backup_n8n_workflows.sh
# Exporta todos workflows N8N via API para /var/backups/n8n-workflows/YYYY-MM-DD/
# Compressao gzip. Retencao local 7 dias. S3 upload opcional (comentado).
#
# Cron sugerido: 0 4 * * * /Users/gustavoalmeida/projetos/Cartorio/scripts/backup_n8n_workflows.sh
#
# Variaveis de ambiente:
#   N8N_API_KEY    - obrigatorio (X-N8N-API-KEY header)
#   N8N_BASE_URL   - opcional (default https://flow.2notasudi.com.br)
#   BACKUP_DIR     - opcional (default /var/backups/n8n-workflows)
#   S3_BUCKET      - opcional (se setado, upload para s3://$S3_BUCKET/...)
#
# Reusa padroes de n8n_workflow_test.py (X-N8N-API-KEY, /api/v1/workflows)

set -euo pipefail

# Configuracao
N8N_BASE_URL="${N8N_BASE_URL:-https://flow.2notasudi.com.br}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/n8n-workflows}"
LOG_FILE="${LOG_FILE:-/var/log/cartorio-backup.log}"
RETENTION_DAYS=7
DATE=$(date +%Y-%m-%d)
TARGET_DIR="$BACKUP_DIR/$DATE"

# Logging
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
log "=== Backup N8N workflows iniciado ==="

# Pre-checks
if [[ -z "${N8N_API_KEY:-}" ]]; then
  log "ERROR: N8N_API_KEY nao definido"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  log "ERROR: curl nao instalado"
  exit 1
fi

if ! command -v gzip >/dev/null 2>&1; then
  log "ERROR: gzip nao instalado"
  exit 1
fi

# Cria diretorio
mkdir -p "$TARGET_DIR"
log "Diretorio alvo: $TARGET_DIR"

# Lista workflows
log "Listando workflows em $N8N_BASE_URL ..."
WORKFLOWS_JSON=$(curl -fsS -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/workflows?limit=200" 2>>"$LOG_FILE")

if [[ -z "$WORKFLOWS_JSON" ]]; then
  log "ERROR: resposta vazia ao listar workflows"
  exit 1
fi

# Extrai IDs e nomes (requer python3)
WF_LIST=$(echo "$WORKFLOWS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for w in data.get('data', []):
    print(f\"{w.get('id')}|{w.get('name', 'unnamed')}\")
")

COUNT=$(echo "$WF_LIST" | wc -l | tr -d ' ')
log "Encontrados $COUNT workflows"

# Exporta cada um
EXPORTED=0
FAILED=0
while IFS='|' read -r WF_ID WF_NAME; do
  [[ -z "$WF_ID" ]] && continue
  SAFE_NAME=$(echo "$WF_NAME" | tr ' /' '__' | tr -cd '[:alnum:]._-')
  OUT_FILE="$TARGET_DIR/${WF_ID}_${SAFE_NAME}.json"
  if curl -fsS -H "X-N8N-API-KEY: $N8N_API_KEY" \
       "$N8N_BASE_URL/api/v1/workflows/$WF_ID" \
       -o "$OUT_FILE" 2>>"$LOG_FILE"; then
    EXPORTED=$((EXPORTED + 1))
  else
    FAILED=$((FAILED + 1))
    log "  FAIL export $WF_ID ($WF_NAME)"
  fi
done <<< "$WF_LIST"

log "Exportados: $EXPORTED / $COUNT (falhas: $FAILED)"

# Metadata
cat > "$TARGET_DIR/_metadata.json" <<EOF
{
  "date": "$DATE",
  "n8n_base_url": "$N8N_BASE_URL",
  "total_workflows": $COUNT,
  "exported": $EXPORTED,
  "failed": $FAILED,
  "retention_days": $RETENTION_DAYS,
  "version": "1.0.0"
}
EOF

# Compressao gzip
log "Comprimindo $TARGET_DIR ..."
tar -czf "$TARGET_DIR.tar.gz" -C "$BACKUP_DIR" "$DATE"
rm -rf "$TARGET_DIR"
log "Arquivo final: $TARGET_DIR.tar.gz"

# Limpeza retencao 7 dias
log "Removendo backups com mais de $RETENTION_DAYS dias ..."
find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" | wc -l | tr -d ' ')
log "Backups restantes: $REMAINING"

# S3 upload opcional (descomentar e configurar AWS credentials)
# if [[ -n "${S3_BUCKET:-}" ]] && command -v aws >/dev/null 2>&1; then
#   log "Upload S3 para s3://$S3_BUCKET/n8n-workflows/$DATE.tar.gz ..."
#   aws s3 cp "$TARGET_DIR.tar.gz" "s3://$S3_BUCKET/n8n-workflows/$DATE.tar.gz" \
#     --storage-class STANDARD_IA 2>>"$LOG_FILE"
# else
#   log "S3 upload desabilitado (S3_BUCKET ou AWS CLI nao configurado)"
# fi

log "=== Backup concluido: $TARGET_DIR.tar.gz ==="
exit 0
