#!/usr/bin/env bash
# ============================================================================
# cloudflare_tunnel_fallback.sh — Script de fallback do túnel Cloudflare (S3.T4)
# Executa um túnel ad-hoc, extrai a URL e notifica o Telegram de SRE.
#
# Modified by Gustavo Almeida.
# ============================================================================

set -euo pipefail

# Configs
PROJECT_ROOT="/Users/gustavoalmeida/Projetos/Cartorio"
LOG_FILE="/tmp/cloudflare_tunnel_fallback.log"
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN deve ser injetado pelo secret manager}"
TELEGRAM_CHAT_ID="6682284055"

echo "=============================================================="
# 1. Parar túneis anteriores rodando em background
if pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "[INFO] Parando instâncias antigas do cloudflared tunnel..."
    pkill -f "cloudflared tunnel" || true
    sleep 2
fi

# 2. Iniciar o túnel ad-hoc
echo "[RUN] Iniciando túnel Cloudflare ad-hoc na porta 8000..."
nohup cloudflared tunnel --url http://localhost:8000 > "$LOG_FILE" 2>&1 &

# 3. Aguardar o túnel inicializar e gerar a URL trycloudflare.com
echo "[WAIT] Aguardando a alocação da URL do túnel pelo Cloudflare..."
TUNNEL_URL=""
for i in {1..15}; do
    sleep 2
    TUNNEL_URL=$(grep -o -E 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_FILE" | head -n 1 || true)
    if [[ -n "$TUNNEL_URL" ]]; then
        break
    fi
    echo "  .. aguardando URL ($i/15) .."
done

if [[ -z "$TUNNEL_URL" ]]; then
    echo "[ERR] Falha ao extrair a URL do túnel de $LOG_FILE"
    echo "=== ÚLTIMAS LINHAS DO LOG ==="
    tail -n 15 "$LOG_FILE"
    exit 1
fi

echo "[SUCCESS] Túnel Cloudflare iniciado com sucesso!"
echo "URL do Túnel: $TUNNEL_URL"

# 5. Notificar administrador via Telegram
echo "[NOTIFY] Enviando notificação para o Telegram de SRE..."
MSG="⚠️ *CLOUDFLARE TUNNEL FALLBACK INICIADO*\nO túnel de emergência do Cartório está ativo!\n\n🔗 *URL temporária de Webhooks*:\n\`$TUNNEL_URL\`\n\n_Modified by Gustavo Almeida._"

curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d "chat_id=$TELEGRAM_CHAT_ID" \
    -d "text=$MSG" \
    -d "parse_mode=Markdown" > /dev/null

echo "[OK] Notificação enviada!"
echo "=============================================================="
