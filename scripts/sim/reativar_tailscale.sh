#!/usr/bin/env bash
# reativar_tailscale.sh — Reativa Tailscale no VPS de forma PERMANENTE.
# Uso:
#   1. Gerar auth key em https://login.tailscale.com/admin/settings/keys
#      → "Generate auth key" → Reusable: true, Expiry: 90 days (max),
#        Pre-approved: true, Tags: tag:vps (se aplicável)
#   2. Colar aqui:
#        bash reativar_tailscale.sh tskey-auth-XXXXXXXX
#
# Resultado:
#   - tailscaled continua rodando (não precisa reiniciar)
#   - tailscale up --authkey=... autentica sem browser
#   - Salva em /etc/tailscale/login-history (não desloga mais)
#   - Confirma com tailscale status e ping
set -euo pipefail

AUTHKEY="${1:-}"
if [[ -z "$AUTHKEY" ]]; then
  echo "ERRO: passe a auth key como argumento"
  echo "Uso: $0 tskey-auth-XXXXXXXX"
  exit 1
fi

VPS_IP="${VPS_IP:-187.77.236.77}"
KEY_FILE="${HOME}/.ssh/id_ed25519_cartorio"

echo "=== 1. SSH no VPS ==="
ssh -i "$KEY_FILE" -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
  "root@${VPS_IP}" bash -s -- "$AUTHKEY" <<'REMOTE'
set -euo pipefail
AUTHKEY="$1"

echo "=== 2. Estado atual Tailscale ==="
tailscale status 2>&1 | head -5

echo ""
echo "=== 3. Ativando Tailscale com auth key ==="
# --accept-routes: aceita rotas subnet do admin
# --ssh: habilita Tailscale SSH (opcional)
# --operator=gustavo: usuário operator
# --advertise-tags=tag:vps: tag para ACLs
# A key já vem com --pre-approved=true se gerada assim
tailscale up \
  --authkey="$AUTHKEY" \
  --accept-routes \
  --hostname="vps-cartorio" \
  --operator="${SUDO_USER:-root}"

echo ""
echo "=== 4. Validando ==="
sleep 3
tailscale status 2>&1 | head -10
echo ""
echo "=== 5. Testando ping para o nó vps-cartorio ==="
tailscale ping --peer-ip=100.99.172.84 2>&1 | head -5 || true
echo ""
echo "=== 6. IP Tailscale na interface ==="
ip -4 addr show tailscale0 2>&1 | grep inet || echo "sem inet"
REMOTE

echo ""
echo "=== 7. Teste do Mac local ==="
echo "Seu Mac está em:"
tailscale status --json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('  IP:', d.get('TailscaleIPs',['?'])[0])" || echo "?"
echo ""
echo "Ping para vps-cartorio:"
ping -c 2 -W 3 100.99.172.84 2>&1 | tail -5 || true
echo ""
echo "SSH via Tailscale:"
ssh -i "$KEY_FILE" -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
  root@100.99.172.84 "echo OK_TAILSCALE_SSH; hostname; tailscale status | head -3" 2>&1 | tail -10