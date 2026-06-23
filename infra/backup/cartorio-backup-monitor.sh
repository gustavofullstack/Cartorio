#!/bin/bash
# Monitor do backup diario cartorio.
# Roda a cada 6h via systemd timer.
# Se ultimo backup > 26h atras, alerta via webhook Chatwoot ou log critico.
#
# v0.4.4 (2026-06-23): cria monitor pro bug onde cron /etc/cron.d/cartorio-backup
# rodava silenciosamente sem validar saida, deixando backup "parado" sem deteccao.

set -euo pipefail

BACKUP_DIR="/var/backups/cartorio"
MAX_AGE_HOURS=26

# 1. Verifica se diretorio existe
if [[ ! -d "${BACKUP_DIR}" ]]; then
  echo "[CRITICAL] Diretorio ${BACKUP_DIR} nao existe" >&2
  exit 1
fi

# 2. Acha o tar.gz mais recente
LATEST=$(find "${BACKUP_DIR}" -name "cartorio_backup_*.tar.gz" -printf "%T@\n" 2>/dev/null | sort -rn | head -1)
if [[ -z "${LATEST}" ]]; then
  echo "[CRITICAL] Nenhum backup encontrado em ${BACKUP_DIR}" >&2
  exit 1
fi

# 3. Calcula idade
NOW_EPOCH=$(date +%s)
BACKUP_EPOCH=$(echo "${LATEST}" | cut -d. -f1)
AGE_HOURS=$(echo "scale=2; (${NOW_EPOCH} - ${BACKUP_EPOCH}) / 3600" | bc)

# 4. Avalia
if (( $(echo "${AGE_HOURS} > ${MAX_AGE_HOURS}" | bc -l) )); then
  echo "[ALERT] Backup mais recente tem ${AGE_HOURS}h (limite ${MAX_AGE_HOURS}h)"
  exit 2
else
  echo "[OK] Backup mais recente tem ${AGE_HOURS}h (limite ${MAX_AGE_HOURS}h)"
  exit 0
fi
