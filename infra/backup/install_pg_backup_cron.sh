#!/bin/bash
# Instala (idempotente) cron entry do pg_basebackup 4x/dia.
# Owner: cartorio-dev
# Roda no VPS via: sudo bash install_pg_backup_cron.sh
#
# Cron target: /etc/cron.d/cartorio-pgbase (system-wide, NAO edita /etc/crontab do root)
# Frequencia: 0 */6 * * *  (00:00, 06:00, 12:00, 18:00 UTC)
# Script alvo: /usr/local/bin/pg_basebackup_4x.sh (instalado separadamente pelo Gustavo via scp)
#
# Idempotencia: se arquivo /etc/cron.d/cartorio-pgbase ja existe com mesmo conteudo, NAO reescreve.
#               Se existe mas conteudo mudou, atualiza (com diff log).
#               Para instalar script: scp pg_basebackup_4x.sh root@100.99.172.84:/usr/local/bin/
#
# v1.0.0 (2026-06-25): A14

set -euo pipefail

CRON_FILE="/etc/cron.d/cartorio-pgbase"
SCRIPT_PATH="/usr/local/bin/pg_basebackup_4x.sh"
CRON_USER="root"

# Conteudo canonico do cron file
read -r -d '' CRON_CONTENT <<'EOF' || true
# A14 — pg_basebackup 4x/dia (00:00, 06:00, 12:00, 18:00 UTC).
# Owner: cartorio-dev. Installed by install_pg_backup_cron.sh (idempotente).
# Logs: /var/log/cartorio-pgbase.log (vazio = OK).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

0 */6 * * * root /usr/local/bin/pg_basebackup_4x.sh >> /var/log/cartorio-pgbase.log 2>&1
EOF

log() { echo "[install_pg_backup_cron] $*"; }

# --- Pre-check: precisa de root para escrever em /etc/cron.d/ -----------
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  log "ERRO: precisa rodar como root (tente: sudo $0)"
  exit 1
fi

# --- Pre-check: script alvo existe? --------------------------------------
if [[ ! -x "${SCRIPT_PATH}" ]]; then
  log "AVISO: ${SCRIPT_PATH} nao encontrado ou nao executavel"
  log "  Instale com: scp pg_basebackup_4x.sh root@100.99.172.84:${SCRIPT_PATH}"
  log "  Depois: chmod +x ${SCRIPT_PATH}"
  log "  Continuando mesmo assim — cron vai falhar ate instalar"
fi

# --- Idempotencia: compara conteudo atual vs canonico ---------------------
if [[ -f "${CRON_FILE}" ]]; then
  CURRENT=$(cat "${CRON_FILE}")
  if [[ "${CURRENT}" == "${CRON_CONTENT}" ]]; then
    log "OK - ${CRON_FILE} ja existe com conteudo canonico (idempotente, sem mudancas)"
    exit 0
  fi
  log "ATUALIZANDO ${CRON_FILE} (conteudo mudou desde ultima instalacao)"
  log "BACKUP: ${CRON_FILE}.bak-$(date -u +%Y%m%d_%H%M%S)"
  cp -a "${CRON_FILE}" "${CRON_FILE}.bak-$(date -u +%Y%m%d_%H%M%S)"
else
  log "CRIANDO ${CRON_FILE} (primeira instalacao)"
fi

# --- Escrita canonica ----------------------------------------------------
printf '%s\n' "${CRON_CONTENT}" > "${CRON_FILE}"
chmod 0644 "${CRON_FILE}"
chown root:root "${CRON_FILE}"

# --- Validacao -----------------------------------------------------------
log "Validando com crontab -T (se disponivel)"
if command -v crontab >/dev/null 2>&1; then
  if crontab -T -u "${CRON_USER}" "${CRON_FILE}" 2>/dev/null; then
    log "OK - crontab -T validou sintaxe"
  else
    log "AVISO: crontab -T nao disponivel nesta distro, validacao pulada"
  fi
fi

# --- Status final --------------------------------------------------------
log "OK - cron instalado em ${CRON_FILE}"
log "Agendamento: 0 */6 * * * (00:00, 06:00, 12:00, 18:00 UTC)"
log "Script alvo: ${SCRIPT_PATH}"
log "Log destino: /var/log/cartorio-pgbase.log"
log ""
log "Para testar manualmente (sem esperar cron):"
log "  bash ${SCRIPT_PATH}"
log ""
log "Para verificar proximas execucoes:"
log "  cat ${CRON_FILE}"