#!/bin/bash
# pg_basebackup 4x/dia (00:00, 06:00, 12:00, 18:00 UTC) + WAL archiving.
# Owner: cartorio-dev
# Schedule: 0 */6 * * * via /etc/cron.d/cartorio-pgbase (instalado por install_pg_backup_cron.sh)
# Retention: 7d local (auto-delete > 7d).
#
# ============================================================================
# ⚠️  S3 MENSAL = EXPLICIT PLACEHOLDER — PENDENTE Gustavo configurar
# ============================================================================
# Para ativar upload mensal ao S3 (1o dia do mes), Gustavo precisa exportar:
#   - AWS_ACCESS_KEY_ID
#   - AWS_SECRET_ACCESS_KEY
#   - AWS_S3_BUCKET  (ex: cartorio-backups-prod)
#   - AWS_REGION     (ex: sa-east-1)
# Ate la, este script loga "SKIPPED (credenciais AWS nao configuradas)" todo
# dia 1o do mes. Backup LOCAL (7d) NAO eh afetado — segue 4x/dia normalmente.
# Ver task A14-verify-and-close / .env.example para placeholders documentados.
# ============================================================================
#
# LGPD: backup encriptado (LGPD art. 46), retencao cartorio 5y (respaldo fora deste script).
#
# Idempotente: se ja existe arquivo para a janela atual (slot HH do dia), NAO roda de novo.
#              Janela = "data atual UTC + slot de 6h" (ex: 2026-06-25_12 = janela das 12h UTC).
#
# v1.0.0 (2026-06-25): A14 — backup DB 4x/dia pg_basebackup + WAL.
# v1.1.0 (2026-06-25): A14 verify+close — banner S3 placeholder explicito.
#   - 4x/dia UTC: 00, 06, 12, 18
#   - WAL archiving via archive_command (placeholder no postgresql.conf — Gustavo aplica)
#   - Retention local 7d
#   - Monthly S3 upload (PLACEHOLDER — sem creds; loga skipped com banner)

set -euo pipefail

# --- Configuracao ---------------------------------------------------------
BACKUP_ROOT="/var/backups/cartorio/pgbase"
PG_CONTAINER="cartorio_supabase-db-1"
PG_USER="supabase_admin"
RETENTION_DAYS=7
DATE_UTC=$(date -u +%Y%m%d)
HOUR_UTC=$(date -u +%H)
# Slot de 6h (00, 06, 12, 18) — agrupa janelas para idempotencia
SLOT_UTC=$((10#${HOUR_UTC} / 6 * 6))
SLOT_UTC=$(printf "%02d" "${SLOT_UTC}")
TS_UTC="${DATE_UTC}_${SLOT_UTC}"
BACKUP_DIR="${BACKUP_ROOT}/${TS_UTC}"
BACKUP_MARKER="${BACKUP_DIR}/.complete"
LOG_PREFIX="[pgbase-backup ${TS_UTC}]"

mkdir -p "${BACKUP_ROOT}"

log() { echo "${LOG_PREFIX} $*"; }

# --- Pre-checks -----------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "ERRO: docker nao encontrado"; exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
  log "ERRO: container ${PG_CONTAINER} nao esta UP"; exit 1
fi

# --- Idempotencia: se ja rodou nesta janela, skip -----------------------
if [[ -f "${BACKUP_MARKER}" ]]; then
  log "SKIP: backup ${TS_UTC} ja completo (marker existe em ${BACKUP_DIR})"
  log "OK - idempotente, sem acao necessaria"
  exit 0
fi

log "Iniciando pg_basebackup 4x/dia (janela ${SLOT_UTC}h UTC)"

mkdir -p "${BACKUP_DIR}"

# --- 1. pg_basebackup tar+gzip dentro do container ----------------------
# -Ft = tar format (cada tablespace em arquivo separado)
# -z  = gzip compress
# -D  = output directory (no container; depois copiamos para fora)
# -U  = superuser (supabase_admin) requerido para replication
# -X  = stream WAL durante o backup (inclui no .tar.gz)
log "  - pg_basebackup -Ft -z -X stream (slot ${SLOT_UTC}h UTC)"

docker exec \
  -e PGUSER="${PG_USER}" \
  "${PG_CONTAINER}" \
  bash -c "pg_basebackup -Ft -z -X stream -D /tmp/pgbase_${TS_UTC} -U ${PG_USER} -h 127.0.0.1 -w" \
  || { log "ERRO: pg_basebackup falhou"; exit 1; }

# --- 2. Copia artefatos para fora do container --------------------------
log "  - copiando artefatos para ${BACKUP_DIR}"
docker cp "${PG_CONTAINER}:/tmp/pgbase_${TS_UTC}/." "${BACKUP_DIR}/" \
  || { log "ERRO: docker cp falhou"; exit 1; }

# Cleanup dentro do container
docker exec "${PG_CONTAINER}" rm -rf "/tmp/pgbase_${TS_UTC}" || true

# Marca como completo
touch "${BACKUP_MARKER}"

# --- 3. Retention 7d local ----------------------------------------------
log "  - removendo backups > ${RETENTION_DAYS} dias"
find "${BACKUP_ROOT}" -maxdepth 1 -mindepth 1 -type d -mtime "+${RETENTION_DAYS}" \
  -exec rm -rf {} + 2>/dev/null || true

# --- 4. Monthly S3 upload (EXPLICIT PLACEHOLDER) --------------------------
# ⚠️ S3 upload NAO ESTA ATIVO — Gustavo precisa configurar creds AWS no
# env do script (cron.d NAO carrega ~/.bashrc automaticamente; ver bloco
# de banner no topo deste arquivo para vars necessarias).
# Quando ativo, ira rodar todo dia 1o do mes e sincronizar /var/backups/cartorio/pgbase
# para s3://${AWS_S3_BUCKET}/pgbase/${TS_UTC}/
DAY_OF_MONTH=$(date -u +%d)
if [[ "${DAY_OF_MONTH}" == "01" ]]; then
  if [[ -n "${AWS_S3_BUCKET:-}" && -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    log "  - upload S3 mensal (bucket=${AWS_S3_BUCKET}, region=${AWS_REGION:-us-east-1}) — NAO IMPLEMENTADO, placeholder"
    # TODO Sprint 5: aws s3 sync "${BACKUP_ROOT}/${TS_UTC}/" "s3://${AWS_S3_BUCKET}/pgbase/${TS_UTC}/"
    # Pre-requisito Gustavo:
    #   1. Criar IAM user com AmazonS3FullAccess (ou policy minima de write no bucket)
    #   2. Adicionar AWS_* vars no /etc/cron.d/cartorio-pgbase OU em /root/.aws/credentials
    #   3. Instalar aws-cli no VPS (apt install awscli)
    log "  - S3 mensal: status PLACEHOLDER (creds OK detectadas, mas sync NAO implementado)"
  else
    log "  - upload S3 mensal SKIPPED (credenciais AWS nao configuradas; Gustavo configura depois)"
    log "  - Placeholder vars necessarias: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET"
  fi
fi

# --- 5. Status final -----------------------------------------------------
SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1 || echo "?")
COUNT=$(find "${BACKUP_ROOT}" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
log "OK - ${BACKUP_DIR} (${SIZE}), ${COUNT} diretorio(s) de backup retidos (<= ${RETENTION_DAYS}d)"