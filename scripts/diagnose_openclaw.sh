#!/bin/bash
# =============================================================================
# DIAGNOSE + RECOVER OpenClaw Agent (502 Bad Gateway)
# USO: bash scripts/diagnose_openclaw.sh
#
# Passos:
# 1. Verifica conectividade SSH
# 2. Verifica status do container
# 3. Coleta logs recentes
# 4. Tenta restart automatico
# 5. Valida via API
# =============================================================================

set -euo pipefail

echo "=========================================="
echo "DIAGNOSE + RECOVER OpenClaw Agent"
echo "=========================================="
echo ""

# 1. SSH connectivity check
echo "[1/5] Verificando conectividade SSH via alias 'cartorio'..."
if ! ssh -o ConnectTimeout=5 cartorio "echo OK" >/dev/null 2>&1; then
    echo "❌ Falha ao conectar via alias 'cartorio' (Tailscale 100.99.172.84)"
    echo "   Gustavo precisa executar este script manualmente."
    exit 1
fi
echo "  ✅ SSH OK"

# 2. Container status
echo ""
echo "[2/5] Status do container cartorio_openclaw-gateway..."
ssh cartorio "docker service ps cartorio_openclaw-gateway | head -5"

# 3. Recent logs
echo ""
echo "[3/5] Logs recentes (ultimas 30 linhas)..."
ssh cartorio "docker service logs cartorio_openclaw-gateway --tail 30 2>&1 | head -50"

# 4. Tentar restart
echo ""
echo "[4/5] Tentando restart do container..."
ssh cartorio "docker service update --force cartorio_openclaw-gateway"
sleep 15
echo "  Aguardando 15s para container inicializar..."

# 5. Validação final via API
echo ""
echo "[5/5] Validação via API..."
HEALTH=$(curl -sk -o /dev/null -w "%{http_code}" "https://agent.2notasudi.com.br/health" 2>/dev/null)
RADAR_STATUS=$(curl -sk "https://api.2notasudi.com.br/api/v1/health/radar" 2>/dev/null | python3 -c "import json, sys; print(json.load(sys.stdin)['services']['openclaw'])" 2>/dev/null || echo "unknown")

if [ "$HEALTH" = "200" ]; then
    echo "  ✅ OpenClaw /health: 200 OK"
    echo "  Radar status: $RADAR_STATUS"
    echo ""
    echo "=========================================="
    echo "✅ RECOVERY BEM-SUCEDIDO!"
    echo "=========================================="
else
    echo "  ❌ OpenClaw /health: $HEALTH (esperado 200)"
    echo "  Radar status: $RADAR_STATUS"
    echo ""
    echo "=========================================="
    echo "⚠️ RECOVERY FALHOU — Investigar manualmente"
    echo "=========================================="
    echo ""
    echo "Próximos passos manuais:"
    echo "  1. ssh cartorio 'docker service logs cartorio_openclaw-gateway --tail 100'"
    echo "  2. Verificar agent.json em /home/node/.openclaw/agents/main/agent/"
    echo "  3. Verificar credenciais OpenCode-Go (NÃO rotacionar)"
    echo "  4. Verificar modelo (deve ser minimax-m3)"
    echo "  5. Verificar context_window (deve ser 1000000)"
fi
