#!/bin/bash
# diagnose_vps_and_bot.sh — Diagnóstico automático pós-queda VPS + deteccao de Cloudflare tunnel
#
# USO: bash scripts/diagnose_vps_and_bot.sh
#
# O que ele faz:
#  1. Health-check dos 6 dominios production
#  2. Se VPS down: detecta Cloudflare tunnel ativo (setWebhook URL ≠ sherlock)
#  3. Se tunnel UP: valida /health + /metrics + envia msg de teste + score 1000 pts
#  4. Se API DOWN: aponta causa-raiz + checklist pra Gustavo
#
# NAO modica nada — apenas diagnostica.

set -uo pipefail

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
vps_up=0
for d in api flow whatsapp chat agent easypanel; do
  code=$(curl -sk -o /dev/null -m 6 -w "%{http_code}" "https://$d.2notasudi.com.br/" 2>/dev/null || echo "TIMEOUT")
  if [ "$code" = "200" ] || [ "$code" = "401" ]; then
    echo -e "  ${GREEN}OK${NC}  $d.2notasudi.com.br  HTTP=$code"
    vps_up=1
  else
    echo -e "  ${RED}DOWN${NC}  $d.2notasudi.com.br  HTTP=$code"
  fi
done

echo
echo "[2] VPS Hostinger IP direto (bypass DNS):"
code_direct=$(curl -sk -o /dev/null -m 6 -w "%{http_code}" "https://$VPS_IP:443/" 2>/dev/null || echo "TIMEOUT")
echo "  IP $VPS_IP:443  HTTP=$code_direct"
ssh_check=$(ssh -o ConnectTimeout=5 -o BatchMode=yes root@"$VPS_IP" "echo SSH_OK" 2>&1 || echo "SSH_DOWN")
echo "  SSH $VPS_IP:22  $ssh_check"

echo
echo "[3] Telegram bot webhook + deteccao tunnel:"
webhook_json=$(curl -sk -m 6 "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo" 2>/dev/null)
webhook_url=$(echo "$webhook_json" | python3 -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('result',{}).get('url',''))" 2>/dev/null || echo "")
echo "  URL: $webhook_url"

# Detecta tunnel Cloudflare = bot respondendo via tunnel
tunnel_base=""
if echo "$webhook_url" | grep -q "trycloudflare.com"; then
  tunnel_base=$(echo "$webhook_url" | sed 's|/api/v1/telegram/webhook||')
  echo -e "  ${GREEN}Cloudflare TUNEL detectado${NC} -> $tunnel_base"
elif echo "$webhook_url" | grep -q "api.2notasudi.com.br"; then
  tunnel_base="https://api.2notasudi.com.br"
  echo -e "  ${GREEN}Webhook via api.2notasudi.com.br${NC}"
elif echo "$webhook_url" | grep -q "sherlock.st"; then
  echo -e "  ${YELLOW}Webhook em sherlock proxy (decisao Gustavo B6)${NC}"
else
  echo -e "  ${YELLOW}Webhook em URL nao padrao${NC}"
fi

echo
echo "[4] Health + Metrics endpoint:"
if [ -n "$tunnel_base" ]; then
  h_code=$(curl -sk -o /dev/null -m 6 -w "%{http_code}" "$tunnel_base/api/v1/telegram/health" 2>/dev/null || echo "TIMEOUT")
  h_body=$(curl -sk -m 6 "$tunnel_base/api/v1/telegram/health" 2>/dev/null)
  echo "  GET /api/v1/telegram/health  HTTP=$h_code"
  echo "  body: $h_body"
  echo
  m_body=$(curl -sk -m 6 "$tunnel_base/api/v1/telegram/metrics" 2>/dev/null)
  echo "  GET /api/v1/telegram/metrics"
  echo "  body: $m_body"
fi

echo
echo "[5] Smoke test 7 comandos canonicos (se tunnel UP):"
if [ -n "$tunnel_base" ]; then
  score=0
  for cmd in /start /menu /agendar /protocolo /humano /cancelar /lgpd; do
    code=$(curl -sk -o /dev/null -m 8 -w "%{http_code}" -X POST "$tunnel_base/api/v1/telegram/webhook" \
      -H "Content-Type: application/json" \
      -d "{\"update_id\":$RANDOM,\"message\":{\"chat\":{\"id\":6682284055},\"text\":\"$cmd\",\"message_id\":$RANDOM}}" 2>/dev/null || echo "TIMEOUT")
    if [ "$code" = "200" ]; then
      echo -e "  ${GREEN}OK${NC}  $cmd  HTTP=$code"
      score=$((score + 1))
    else
      echo -e "  ${RED}FAIL${NC} $cmd  HTTP=$code"
    fi
  done
  echo
  echo "  SCORE: $score/7 comandos respondendo"
  if [ "$score" -eq 7 ]; then
    echo -e "  ${GREEN}STATUS: 7/7 = NOTA $((score * 143)) / 1000${NC}"
  fi
fi

echo
echo "=== DIAGNOSTICO ENCERRADO ==="
echo
echo "ACAO RECOMENDADA por Gustavo (executar manualmente):"
echo "  1. Se VPS up: confirmar 6 dominios OK acima"
echo "  2. Se VPS down + tunnel ativo: bot RESPONDE via tunnel (score=$((7)) se OK)"
echo "  3. Hostinger painel (https://hpanel.hostinger.com): Resume VM se pausada"
echo "  4. Cloudflare DNS: confirmar 6 A records -> $VPS_IP"
echo "  5. EasyPanel: docker service ls | grep cartorio_"
echo "  6. setWebhook alternativo: https://api.2notasudi.com.br/api/v1/telegram/webhook"
