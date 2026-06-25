#!/bin/bash
# cartorio-backup-status.sh - E6.S7.T10 (2026-06-25)
#
# Cron hourly que consulta /api/v1/health/backup e envia alerta Telegram
# quando ok=false. Complementa o cron cartorio-backup.sh (daily 03:00) com
# monitoramente frequente.
#
# Setup:
#   sudo cp infra/backup/cartorio-backup-status.sh /usr/local/bin/
#   sudo chmod +x /usr/local/bin/cartorio-backup-status.sh
#   sudo cp infra/cron/cartorio-backup-status /etc/cron.d/
#   sudo systemctl restart cron
#
# Dependencies:
#   - curl
#   - jq (apt install jq)
#   - .env file com CARTORIO_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

set -euo pipefail

# ===== Config =====
SCRIPT_NAME="cartorio-backup-status"
API_URL="${CARTORIO_API_URL:-https://api.2notasudi.com.br}"
API_KEY="${CARTORIO_API_KEY:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
LOG_FILE="/var/log/${SCRIPT_NAME}.log"
STATE_FILE="/var/lib/${SCRIPT_NAME}/last_status.json"

# mkdir para state file
mkdir -p "$(dirname "$STATE_FILE")" 2>/dev/null || true

# ===== Parse args =====
DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown arg: $1" >&2
            exit 1
            ;;
    esac
done

# ===== Log helper =====
log() {
    local level="$1"
    shift
    local msg="$*"
    local ts
    ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "${ts} [${level}] ${msg}" | tee -a "$LOG_FILE" >&2
}

# ===== Send Telegram =====
send_telegram() {
    local msg="$1"
    if [[ "$DRY_RUN" == "true" ]]; then
        log "INFO" "[DRY-RUN] Telegram NAO enviado: ${msg}"
        return 0
    fi
    if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]]; then
        log "WARN" "TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID nao setados. Alerta nao enviado."
        return 1
    fi
    local payload
    payload=$(jq -n --arg chat_id "$TELEGRAM_CHAT_ID" --arg text "$msg" \
        '{chat_id: $chat_id, text: $text, parse_mode: "HTML"}')
    local response
    response=$(curl -s -m 10 -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" 2>&1)
    if echo "$response" | jq -e '.ok == true' >/dev/null 2>&1; then
        log "INFO" "Telegram alert enviado: ${msg}"
        return 0
    else
        log "ERROR" "Falha ao enviar Telegram: ${response}"
        return 1
    fi
}

# ===== Check backup status =====
check_backup() {
    if [[ -z "$API_KEY" ]]; then
        log "ERROR" "CARTORIO_API_KEY nao setado. Saindo."
        exit 1
    fi
    log "INFO" "Consultando ${API_URL}/api/v1/health/backup"

    local http_code
    local body
    body=$(curl -sk -m 30 -w "\n%{http_code}" \
        -H "X-API-Key: ${API_KEY}" \
        "${API_URL}/api/v1/health/backup" 2>&1)
    http_code=$(echo "$body" | tail -n 1)
    body=$(echo "$body" | head -n -1)

    log "INFO" "HTTP ${http_code}"

    if [[ "$http_code" != "200" ]]; then
        log "ERROR" "HTTP NAO 200 (${http_code}). Enviando alerta."
        send_telegram "🚨 <b>Cartorio Backup Status</b>%0AHTTP ${http_code} em ${API_URL}/api/v1/health/backup"
        return 1
    fi

    # Parse JSON
    local ok
    ok=$(echo "$body" | jq -r '.ok' 2>/dev/null)
    local age_hours
    age_hours=$(echo "$body" | jq -r '.last_backup_age_hours' 2>/dev/null)
    local source
    source=$(echo "$body" | jq -r '.source' 2>/dev/null)
    local err
    err=$(echo "$body" | jq -r '.error // ""' 2>/dev/null)

    log "INFO" "ok=${ok} age_hours=${age_hours} source=${source}"

    # Save state
    echo "$body" > "$STATE_FILE"

    # Decide alerta
    if [[ "$ok" != "true" ]]; then
        local msg
        msg="🚨 <b>Backup FAIL</b>%0A%0AStatus: ok=${ok}%0AAge: ${age_hours}h%0ASource: ${source}"
        if [[ -n "$err" ]]; then
            msg="${msg}%0AError: ${err}"
        fi
        send_telegram "$msg"
        return 1
    fi

    # Check se age > 26h (mesmo threshold do N8N workflow #09)
    if [[ -n "$age_hours" && "$age_hours" != "null" ]] && \
       awk "BEGIN {exit !($age_hours > 26)}"; then
        send_telegram "⚠️ <b>Backup STALE</b>%0AAge: ${age_hours}h (>26h threshold)"
        return 1
    fi

    log "INFO" "Backup OK (age=${age_hours}h)"
    return 0
}

# ===== Main =====
main() {
    log "INFO" "Iniciando check (DRY_RUN=${DRY_RUN})"
    if check_backup; then
        exit 0
    else
        exit 1
    fi
}

main