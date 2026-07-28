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
PG_SERVICE_NAME="${PG_SERVICE_NAME:-cartorio_banco_de_dados}"
LOG_PREFIX="[cartorio-backup ${TIMESTAMP}]"

mkdir -p "${BACKUP_DIR}"

log() { echo "${LOG_PREFIX} $*"; }

resolve_pg_container() {
  docker ps -q --filter "label=com.docker.swarm.service.name=${PG_SERVICE_NAME}" \
    | head -n 1
}

# --- Pre-checks ---------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "ERRO: docker nao encontrado"; exit 1
fi

PG_CONTAINER=$(resolve_pg_container)
if [[ -z "${PG_CONTAINER}" ]]; then
  log "ERRO: nenhum task UP para o serviço ${PG_SERVICE_NAME}"; exit 1
fi

log "Iniciando backup"

# --- 1. Dump Postgres (bancos presentes no serviço Supabase) ------------
for db in supabase chatwoot evolution; do
  log "  - pg_dump ${db}"
  docker exec "${PG_CONTAINER}" sh -lc \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -h 127.0.0.1 \
      -Fc --no-owner --no-acl "$1"' -- "${db}" \
    > "${BACKUP_DIR}/supabase_${db}_${TIMESTAMP}.dump"
done

# --- 2. n8n workflows via API ------------------------------------------
# N8N API key pode vir de 5 fontes (ordem de prioridade):
#   1. env N8N_API_KEY exportada
#   2. /etc/cartorio-backup/n8n-api-key.env (modo recomendado, chmod 600)
#   3. /etc/easypanel/projects/cartorio/n8n/.env (caso Easypanel salve)
#   4. extraida direto do service Swarm cartorio_n8n (var Spec.TaskTemplate)
#   5. fallback interno da API do Cartório, caso a chave exclusiva de backup
#      tenha sido revogada. O valor nunca é impresso nem arquivado.
N8N_EXPORT_DIR="${BACKUP_DIR}/n8n_${TIMESTAMP}"
N8N_EXPORT_FILE="${N8N_EXPORT_DIR}/workflows.json"

export_n8n_via_cli() {
  local container remote_file
  container=$(docker ps -q --filter \
    "label=com.docker.swarm.service.name=cartorio_n8n" | head -n 1)
  remote_file="/tmp/cartorio-workflows-${TIMESTAMP}.json"
  [[ -n "${container}" ]] || return 1

  if docker exec "${container}" n8n export:workflow --all \
      --output="${remote_file}" >/dev/null 2>&1 \
    && docker cp "${container}:${remote_file}" "${N8N_EXPORT_FILE}" >/dev/null 2>&1; then
    docker exec "${container}" rm -f "${remote_file}" >/dev/null 2>&1 || true
    log "  - n8n workflows exportados pelo CLI interno"
    return 0
  fi

  docker exec "${container}" rm -f "${remote_file}" >/dev/null 2>&1 || true
  return 1
}

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
  log "  - n8n workflows"
  mkdir -p "${N8N_EXPORT_DIR}"
  if ! curl -fsSk "https://flow.2notasudi.com.br/api/v1/workflows?limit=200" \
    -H "X-N8N-API-KEY: ${N8N_KEY}" \
    -o "${N8N_EXPORT_FILE}" 2>/dev/null; then
    fallback_key=$(docker service inspect cartorio_system-api \
      --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}' 2>/dev/null \
      | sed -n 's/^N8N_API_KEY=//p' | head -n 1 || true)
    if [[ -n "${fallback_key}" && "${fallback_key}" != "${N8N_KEY}" ]] \
      && curl -fsSk "https://flow.2notasudi.com.br/api/v1/workflows?limit=200" \
        -H "X-N8N-API-KEY: ${fallback_key}" \
        -o "${N8N_EXPORT_FILE}" 2>/dev/null; then
      log "  - n8n workflows exportados pelo fallback interno"
    elif export_n8n_via_cli; then
      :
    else
      # O dump PostgreSQL não pode ser descartado porque uma exportação auxiliar
      # de workflow falhou. O alerta deixa a lacuna explícita para operação.
      log "AVISO: exportação n8n falhou; bancos foram preservados no backup"
      rm -rf "${N8N_EXPORT_DIR}"
    fi
  fi
else
  log "  - n8n: N8N_API_KEY nao encontrada; tentando CLI interno"
  mkdir -p "${N8N_EXPORT_DIR}"
  if ! export_n8n_via_cli; then
    log "AVISO: exportação n8n falhou; bancos foram preservados no backup"
    rm -rf "${N8N_EXPORT_DIR}"
  fi
fi

# Segredos são recuperados exclusivamente pelo gerenciador de segredos; nunca
# são copiados para um tar local sem criptografia e política de chaves.

# --- 3. Compacta tudo --------------------------------------------------
log "  - compactando"
cd "${BACKUP_DIR}"
archive_items=("supabase_"*"_${TIMESTAMP}.dump")
if [[ -d "n8n_${TIMESTAMP}" ]]; then
  archive_items+=("n8n_${TIMESTAMP}")
fi
tar -czf "cartorio_backup_${TIMESTAMP}.tar.gz" "${archive_items[@]}"
rm -rf "n8n_${TIMESTAMP}/"

# --- 6. Limpeza de backups antigos ------------------------------------
log "  - removendo backups > ${RETAIN_DAYS} dias"
find "${BACKUP_DIR}" -name "*.tar.gz" -mtime "+${RETAIN_DAYS}" -delete
find "${BACKUP_DIR}" -name "*.dump"   -mtime "+${RETAIN_DAYS}" -delete

# --- 7. Status final ---------------------------------------------------
SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1 || echo "?")
COUNT=$(ls -1 "${BACKUP_DIR}"/cartorio_backup_*.tar.gz 2>/dev/null | wc -l)
log "OK - diretorio ${BACKUP_DIR} (${SIZE}), ${COUNT} arquivo(s) .tar.gz retidos"

# Publica somente metadados no Redis da API. O arquivo de backup permanece na
# VPS; nenhum conteúdo, segredo ou credencial segue para este endpoint.
LAST_FILE=$(ls -1t "${BACKUP_DIR}"/cartorio_backup_*.tar.gz 2>/dev/null | head -1 || true)
if [[ -n "${LAST_FILE}" ]]; then
  LAST_ISO=$(date -u -d "@$(stat -c %Y "${LAST_FILE}")" +%FT%TZ)
  LAST_SIZE=$(stat -c %s "${LAST_FILE}")
  PAYLOAD=$(printf '{"ok":true,"last_backup_iso":"%s","last_backup_filename":"%s","last_backup_size_bytes":%s,"last_backup_age_hours":0,"backup_count_7d":%s,"updated_at":"%s"}' \
    "${LAST_ISO}" "$(basename "${LAST_FILE}")" "${LAST_SIZE}" "${COUNT}" "$(date -u +%FT%TZ)")
  if ! curl -fsSk --max-time 10 -X POST \
    "https://api.2notasudi.com.br/api/v1/health/backup/status" \
    -H "Content-Type: application/json" -d "${PAYLOAD}" >/dev/null; then
    log "AVISO: não foi possível publicar metadados do backup na API"
  fi
fi
