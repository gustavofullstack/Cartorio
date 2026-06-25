#!/bin/bash
# ============================================================================
# setup_1m_context.sh
# ============================================================================
# Aplica configuracao de 1M context + thinkings adaptativo no OpenClaw.
# Idempotente. Execute via SSH cartorio (Tailscale 100.99.172.84).
#
# Acoes:
# 1. Verifica config atual do OpenClaw
# 2. Atualiza max_context_tokens para 1M (era 131k cache stale)
# 3. Habilita thinkings adaptativo (off por padrao, on para keywords)
# 4. Valida via /health que continua UP
#
# Reverte: openclaw config reset (cuidado)
# ============================================================================
set -euo pipefail

OPENCLAW_CONTAINER="${OPENCLAW_CONTAINER:-cartorio_openclaw-gateway}"
LOG_PREFIX="[$(date +%Y-%m-%dT%H:%M:%S%z)] setup_1m_context"

echo "$LOG_PREFIX === Setup OpenClaw 1M context + adaptive thinkings ==="

# 1. Verificar se container esta UP
if ! docker ps --format '{{.Names}}' | grep -q "$OPENCLAW_CONTAINER"; then
  echo "$LOG_PREFIX ERROR: container $OPENCLAW_CONTAINER nao esta rodando"
  exit 1
fi

# 2. Mostrar config ANTES
echo "$LOG_PREFIX --- Config ANTES ---"
docker exec "$OPENCLAW_CONTAINER" openclaw config get max_context_tokens 2>/dev/null || echo "max_context_tokens: NAO DEFINIDO"
docker exec "$OPENCLAW_CONTAINER" openclaw config get max_output_tokens 2>/dev/null || echo "max_output_tokens: NAO DEFINIDO"
docker exec "$OPENCLAW_CONTAINER" openclaw config get agent.thinking.enabled 2>/dev/null || echo "agent.thinking.enabled: NAO DEFINIDO"

# 3. Aplicar config
echo "$LOG_PREFIX --- Aplicando config 1M + adaptive ---"
docker exec "$OPENCLAW_CONTAINER" openclaw config set max_context_tokens 1000000
docker exec "$OPENCLAW_CONTAINER" openclaw config set max_output_tokens 8192
docker exec "$OPENCLAW_CONTAINER" openclaw config set agent.thinking.enabled adaptive
docker exec "$OPENCLAW_CONTAINER" openclaw config set agent.thinking.max_thinking_tokens 8000
docker exec "$OPENCLAW_CONTAINER" openclaw config set agent.thinking.triggers.keywords '["calcular","validar","analisar","debug","LGPD","PII","erro","exception","handoff"]'
docker exec "$OPENCLAW_CONTAINER" openclaw config set agent.thinking.triggers.complexity_threshold 0.7

# 4. Mostrar config DEPOIS
echo "$LOG_PREFIX --- Config DEPOIS ---"
docker exec "$OPENCLAW_CONTAINER" openclaw config get max_context_tokens
docker exec "$OPENCLAW_CONTAINER" openclaw config get max_output_tokens
docker exec "$OPENCLAW_CONTAINER" openclaw config get agent.thinking.enabled
docker exec "$OPENCLAW_CONTAINER" openclaw config get agent.thinking.max_thinking_tokens

# 5. Validar health
echo "$LOG_PREFIX --- Validando /health ---"
sleep 2
HEALTH=$(docker exec "$OPENCLAW_CONTAINER" curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18790/health || echo "FAIL")
if [ "$HEALTH" = "200" ]; then
  echo "$LOG_PREFIX ✅ /health = 200 OK"
else
  echo "$LOG_PREFIX ⚠️  /health = $HEALTH (verificar manualmente)"
fi

echo "$LOG_PREFIX === Setup concluido ==="
echo ""
echo "Para validar de fora (Tailscale):"
echo "  curl -s https://agent.2notasudi.com.br/health"
echo ""
echo "Para testar thinkings adaptativo, mande mensagem com keyword 'analisar' ou 'LGPD'."
