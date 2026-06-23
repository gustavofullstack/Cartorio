#!/bin/bash
# Backup diario do projeto cartorio (VPS-side).
# Owner: cartorio-dev / cartorio-n8n
# Schedule: 0 3 * * * (3 AM diario) via /etc/cron.d/cartorio-backup
# Retention: 7 dias local + push S3 (TODO)
#
# v0.4.0 (2026-06-23): paths ajustados para VPS (/etc/easypanel/...),
# pre-checks de docker/container, exit codes propagados via set -euo pipefail,
# logs prefixados por timestamp.
#
# ANTES desse fix o cron apontava para /Users/gustavoalmeida/projetos/Cartorio/...
# (path do MAC) -> nunca rodou. Esse script precisa estar em /usr/local/bin/
# e o cron precisa apontar pra ele.

set -euo pipefail

BACKUP_DIR="/var/backups/cartorio"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETAIN_DAYS=7
LOG_PREFIX="[cartorio-backup ${TIMESTAMP}]"

mkdir -p "${BACKUP_DIR}"

log() { echo "${LOG_PREFIX} $*"; }

# --- Pre-checks ---------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "ERRO: docker nao encontrado"; exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q '^cartorio_supabase-db-1$'; then
  log "ERRO: container cartorio_supabase-db-1 nao esta UP"; exit 1
fi

log "Iniciando backup"

# --- 1. Dump Postgres (cartorio + n8n + chatwoot + evolution) ----------
for db in cartorio n8n chatwoot evolution; do
  log "  - pg_dump ${db}"
  docker exec cartorio_supabase-db-1 pg_dump -U supabase_admin -h 127.0.0.1 \
    -Fc --no-owner --no-acl "${db}" > "${BACKUP_DIR}/supabase_${db}_${TIMESTAMP}.dump"
done

# --- 2. n8n workflows + credentials via API ---------------------------
# N8N API key pode vir de 4 fontes (ordem de prioridade):
#   1. env N8N_API_KEY exportada
#   2. /etc/cartorio-backup/n8n-api-key.env (modo recomendado, chmod 600)
#   3. /etc/easypanel/projects/cartorio/n8n/.env (caso Easypanel salve)
#   4. extraida direto do service Swarm cartorio_n8n (var Spec.TaskTemplate)
N8N_KEY="${N8N_API_KEY:-}"
if [[ -z "${N8N_KEY}" && -f /etc/cartorio-backup/n8n-api-key.env ]]; then
  # shellcheck disable=SC1091
  set -a; source /etc/cartorio-backup/n8n-api-key.env; set +a
  N8N_KEY="${N8N_API_KEY:-}"
fi
if [[ -z "${N8N_KEY}" ]]; then
  N8N_ENV="/etc/easypanel/projects/cartorio/n8n/.env"
  if [[ -f "${N8N_ENV}" ]]; then
    N8N_KEY=$(grep -E '^N8N_API_KEY=' "${N8N_ENV}" | cut -d= -f2- || true)
  fi
fi
if [[ -z "${N8N_KEY}" ]]; then
  N8N_KEY=$(docker service inspect cartorio_n8n \
    --format '{{ json .Spec.TaskTemplate.ContainerSpec.Env }}' 2>/dev/null \
    | tr ',' '\n' | grep -oE 'N8N_API_KEY=[^"]+' | cut -d= -f2- || true)
fi
if [[ -n "${N8N_KEY}" ]]; then
  log "  - n8n workflows + credentials (key len=${#N8N_KEY})"
  mkdir -p "${BACKUP_DIR}/n8n_${TIMESTAMP}"
  curl -sk "https://flow.2notasudi.com.br/api/v1/workflows?limit=200" \
    -H "X-N8N-API-KEY: ${N8N_KEY}" \
    -o "${BACKUP_DIR}/n8n_${TIMESTAMP}/workflows.json"
  curl -sk "https://flow.2notasudi.com.br/api/v1/credentials" \
    -H "X-N8N-API-KEY: ${N8N_KEY}" \
    -o "${BACKUP_DIR}/n8n_${TIMESTAMP}/credentials.json"
else
  log "  - n8n: N8N_API_KEY nao encontrada em nenhum path, pulando workflows"
fi

# --- 3. cartorio-api .env ----------------------------------------------
log "  - cartorio-api .env"
cp /etc/easypanel/projects/cartorio/api/code/.env \
   "${BACKUP_DIR}/cartorio_api_${TIMESTAMP}.env" 2>/dev/null || \
  log "    (aviso: nao foi possivel copiar .env do cartorio_api)"

# --- 4. Chatwoot .env --------------------------------------------------
log "  - chatwoot .env"
docker exec cartorio_chatwoot cat /app/.env 2>/dev/null \
  > "${BACKUP_DIR}/chatwoot_${TIMESTAMP}.env" || true

# --- 5. Compacta tudo --------------------------------------------------
log "  - compactando"
cd "${BACKUP_DIR}"
tar -czf "cartorio_backup_${TIMESTAMP}.tar.gz" \
  supabase_*.dump n8n_${TIMESTAMP}/ cartorio_api_${TIMESTAMP}.env \
  chatwoot_${TIMESTAMP}.env 2>/dev/null || true
rm -rf "n8n_${TIMESTAMP}/" "chatwoot_${TIMESTAMP}.env"

# --- 6. Limpeza de backups antigos ------------------------------------
log "  - removendo backups > ${RETAIN_DAYS} dias"
find "${BACKUP_DIR}" -name "*.tar.gz" -mtime "+${RETAIN_DAYS}" -delete
find "${BACKUP_DIR}" -name "*.dump"   -mtime "+${RETAIN_DAYS}" -delete

# --- 7. Status final ---------------------------------------------------
SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1 || echo "?")
COUNT=$(ls -1 "${BACKUP_DIR}"/cartorio_backup_*.tar.gz 2>/dev/null | wc -l)
log "OK - diretorio ${BACKUP_DIR} (${SIZE}), ${COUNT} arquivo(s) .tar.gz retidos"
