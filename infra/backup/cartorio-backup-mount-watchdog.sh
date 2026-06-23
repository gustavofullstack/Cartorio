#!/bin/bash
# Watchdog: garante que /var/backups/cartorio esta montado no cartorio_api
# Roda a cada 15min via cron. Se mount sumiu, reaplica automaticamente.
#
# Contexto: BUG REAL achado em 2026-06-23 18:36 BRT
# O mount bind /var/backups/cartorio -> /var/backups/cartorio (readonly) no
# cartorio_api service some apos qualquer `docker service update --image`
# ou restart. Endpoint /api/v1/health/backup quebra com:
#   [Errno 2] No such file or directory: 'docker'
# Este watchdog detecta e reaplica em <30s.
#
# Instalacao:
#   1. Copiar para /usr/local/bin/cartorio-backup-watchdog.sh
#   2. chmod +x
#   3. Adicionar ao /etc/cron.d/cartorio-watchdog:
#      */15 * * * * root /usr/local/bin/cartorio-backup-watchdog.sh >> /var/log/cartorio-watchdog.log 2>&1

set -euo pipefail

SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_cartorio}"
VPS_HOST="${VPS_HOST:-100.99.172.84}"
SERVICE="${SERVICE:-cartorio_api}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/cartorio}"
LOG_TS="$(date -Iseconds)"

log() { echo "[${LOG_TS}] $*"; }

# 1. Verifica se o mount existe na spec do service
MOUNT_JSON=$(ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
  -i "${SSH_KEY}" "root@${VPS_HOST}" \
  "docker service inspect ${SERVICE} --format '{{ json .Spec.TaskTemplate.ContainerSpec.Mounts }}'" \
  2>/dev/null || echo "[]")

if echo "${MOUNT_JSON}" | grep -q "${BACKUP_DIR}"; then
  log "OK: mount ${BACKUP_DIR} presente em ${SERVICE}"
  exit 0
fi

# 2. Mount sumiu - reaplica
log "ALERTA: mount ${BACKUP_DIR} sumiu de ${SERVICE}, reaplicando..."
ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
  -i "${SSH_KEY}" "root@${VPS_HOST}" \
  "docker service update --mount-add type=bind,source=${BACKUP_DIR},target=${BACKUP_DIR},readonly ${SERVICE}" \
  >/dev/null 2>&1

# 3. Valida
sleep 4
if ssh -o ConnectTimeout=8 -i "${SSH_KEY}" "root@${VPS_HOST}" \
  "docker exec \$(docker ps -q -f name=${SERVICE}.1 | head -1) ls ${BACKUP_DIR}/*.tar.gz" \
  >/dev/null 2>&1; then
  log "FIX APLICADO: mount restaurado e tarballs visiveis no container"
  exit 0
else
  log "FALHA: mount reaplicado mas tarballs nao visiveis - investigar manualmente"
  exit 1
fi
