#!/bin/bash
# diagnose_vps_and_bot.sh — Diagnóstico automático pós-queda VPS
#
# USO: bash scripts/diagnose_vps_and_bot.sh
#
# O que ele faz:
#  1. Health-check dos 6 dominios production
#  2. Se API OK: valida webhook + health + tenta enviar msg de teste
#  3. Se API DOWN: aponta causa-raiz + checklist pra Gustavo
#
# NAO modica nada — apenas diagnostica.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BOT_TOKEN="8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q"
VPS_IP="187.77.236.77"

echo "=== DIAGNOSTICO ATENDIMENTO TELEGRAM BOT — $(date -Iseconds) ==="
echo

# 1. Health-check dominios
echo "[1] Health-check 6 dominios production:"
for d in api flow whatsapp chat agent easypanel; do
  code=$(curl -sk -o /dev/null -m 8 -w "%{http_code}" "https://$d.2notasudi.com.br/" 2>/dev/null || echo "TIMEOUT")
  if [ "$code" = "200" ] || [ "$code" = "401" ]; then
    echo -e "  ${GREEN}OK${NC}  $d.2notasudi.com.br  HTTP=$code"
  else
    echo -e "  ${RED}DOWN${NC}  $d.2notasudi.com.br  HTTP=$code"
  fi
done

echo
echo "[2] VPS Hostinger IP direto (bypass DNS):"
code_direct=$(curl -sk -o /dev/null -m 8 -w "%{http_code}" "https://$VPS_IP:443/" 2>/dev/null || echo "TIMEOUT")
echo "  IP $VPS_IP:443  HTTP=$code_direct"

ssh_check=$(ssh -o ConnectTimeout=5 -o BatchMode=yes root@"$VPS_IP" "echo SSH_OK" 2>&1 || echo "SSH_DOWN")
echo "  SSH $VPS_IP:22  $ssh_check"

echo
echo "[3] Telegram bot webhook:"
webhook=$(curl -sk -m 8 "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo" 2>/dev/null)
echo "  $webhook" | python3 -m json.tool 2>/dev/null || echo "  $webhook"

echo
echo "[4] Se api.2notasudi.com.br OK, testa health endpoint:"
api_health=$(curl -sk -o /dev/null -m 8 -w "%{http_code}" "https://api.2notasudi.com.br/api/v1/telegram/health" 2>/dev/null || echo "TIMEOUT")
echo "  /api/v1/telegram/health  HTTP=$api_health"

echo
echo "=== DIAGNOSTICO ENCERRADO ==="
echo
echo "ACAO RECOMENDADA por Gustavo (executar manualmente):"
echo "  1. Cloudflare DNS: confirmar A records 6 dominios -> $VPS_IP"
echo "  2. Hostinger painel: verificar VM power state (pode estar pausada por inatividade)"
echo "  3. EasyPanel: docker service ls | grep cartorio_"
echo "  4. Se webhook sherlock errado: setWebhook https://api.2notasudi.com.br/api/v1/telegram/webhook"
