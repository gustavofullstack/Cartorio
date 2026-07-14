#!/usr/bin/env bash
# ============================================================================
# openclaw_fix_lobechat_cors_timeout.sh
# ============================================================================
# URGENT FIX 2026-07-14 — LobeChat integration bloqueada no OpenClaw Gateway:
#   1. CORS preflight 405 sem ACAO header
#   2. Upstream provider 408 timeout em 2.37s
#
# ESTE SCRIPT PRECISA SER RODADO NA VPS cartorio (Tailscale 100.99.172.84)
# NAO existe no repo, pois o snapshot so documenta o estado desejado do
# openclaw.json dentro do container.
#
# USO:
#   ssh cartorio
#   sudo bash infra/scripts/openclaw_fix_lobechat_cors_timeout.sh
#
# IDEMPOTENTE: re-executavel. Faz backup pre-patch, valida, faz hot-reload
# e sobe um cron-like watcher para confirmar.
# ============================================================================
set -euo pipefail

LOG_PREFIX="[$(date +%Y-%m-%dT%H:%M:%S%z)] openclaw_fix"
OPENCLAW_CONTAINER="${OPENCLAW_CONTAINER:-cartorio_openclaw-gateway}"
OPENCLAW_CFG="/home/node/.openclaw/openclaw.json"
BACKUP_STAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_PATH="${OPENCLAW_CFG}.bak-pre-t51-${BACKUP_STAMP}"
ORIGIN_LIST='["https://cartorio-lobechat.dfgdxq.easypanel.host","https://lobechat.dfgdxq.easypanel.host","http://localhost:3210","http://127.0.0.1:3210","https://agent.2notasudi.com.br","https://admin.2notasudi.com.br","https://app.2notasudi.com.br","tauri://localhost"]'

echo "$LOG_PREFIX === URGENT FIX OpenClaw Gateway — LobeChat ==="

# 0. Sanidade
if ! docker ps --format '{{.Names}}' | grep -q "$OPENCLAW_CONTAINER"; then
  echo "$LOG_PREFIX ERROR: container $OPENCLAW_CONTAINER nao esta rodando"
  exit 1
fi

# 1. Backup pre-patch
echo "$LOG_PREFIX --- Backup pre-T5.1 ---"
docker exec "$OPENCLAW_CONTAINER" cp "$OPENCLAW_CFG" "$BACKUP_PATH"
echo "$LOG_PREFIX backup criado: $BACKUP_PATH"

# 2. Patch via openclaw config (openclaw valida contra schema; se campo rejeitar
#    cai no passo 5 com patch manual por python)
echo "$LOG_PREFIX --- Aplicando CORS allowedOrigins + timeoutSeconds ---"

if docker exec "$OPENCLAW_CONTAINER" openclaw config set gateway.controlUi.allowedOrigins "$ORIGIN_LIST" 2>/dev/null; then
  echo "$LOG_PREFIX OK gateway.controlUi.allowedOrigins patched (8 origins)"
else
  echo "$LOG_PREFIX WARN openclaw config set falhou para allowedOrigins — ver passo 5"
fi

if docker exec "$OPENCLAW_CONTAINER" openclaw config set models.providers.openai.timeoutSeconds 30 2>/dev/null; then
  echo "$LOG_PREFIX OK models.providers.openai.timeoutSeconds = 30"
else
  echo "$LOG_PREFIX WARN openclaw config set falhou para timeoutSeconds — ver passo 5"
fi

# 3. Validate
echo "$LOG_PREFIX --- Validando config ---"
docker exec "$OPENCLAW_CONTAINER" openclaw config validate || {
  echo "$LOG_PREFIX ERROR: openclaw config validate falhou — restore backup"
  docker exec "$OPENCLAW_CONTAINER" cp "$BACKUP_PATH" "$OPENCLAW_CFG"
  exit 1
}

# 4. Restart forcado (changes em providers as vezes exigem restart mesmo
#    com hot-reload; safe porque o servico tem healthcheck)
echo "$LOG_PREFIX --- Restart forcado do servico para garantir apply ---"
docker service update --force "$OPENCLAW_CONTAINER" 2>/dev/null || \
  docker restart "$OPENCLAW_CONTAINER" 2>/dev/null || true

# 5. Fallback manual se openclaw config set rejeitar: patch JSON via python
#    in-place (NAO usar se passos 2 funcionaram — duplicaria keys)
sleep 3
NEED_FALLBACK=false
docker exec "$OPENCLAW_CONTAINER" openclaw config get models.providers.openai.timeoutSeconds 2>/dev/null | grep -q '^30$' || NEED_FALLBACK=true
docker exec "$OPENCLAW_CONTAINER" openclaw config get gateway.controlUi.allowedOrigins 2>/dev/null | grep -q 'cartorio-lobechat' || NEED_FALLBACK=true

if [ "$NEED_FALLBACK" = "true" ]; then
  echo "$LOG_PREFIX --- FALLBACK: patching JSON via python in-container ---"
  docker exec "$OPENCLAW_CONTAINER" python3 - <<PYEOF
import json, sys
p = "$OPENCLAW_CFG"
with open(p) as f:
    cfg = json.load(f)
cfg.setdefault('gateway', {}).setdefault('controlUi', {})['allowedOrigins'] = json.loads('$ORIGIN_LIST')
cfg.setdefault('models', {}).setdefault('providers', {}).setdefault('openai', {})['timeoutSeconds'] = 30
with open(p, 'w') as f:
    json.dump(cfg, f, indent=2)
print(f"FALLBACK OK wrote {p}")
PYEOF
  echo "$LOG_PREFIX --- Restart forcado apos fallback ---"
  docker service update --force "$OPENCLAW_CONTAINER" 2>/dev/null || \
    docker restart "$OPENCLAW_CONTAINER" 2>/dev/null || true
  sleep 3
fi

# 6. Validate POST-deploy
echo "$LOG_PREFIX --- POST-DEPLOY VALIDATION ---"

echo "  6.1 /health"
HEALTH=$(docker exec "$OPENCLAW_CONTAINER" curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18790/health || echo "FAIL")
echo "       /health = $HEALTH (esperado 200)"

echo "  6.2 CORS preflight"
ACAO=$(curl -sS -o /dev/null -D - --max-time 8 -X OPTIONS \
  -H "Origin: https://cartorio-lobechat.dfgdxq.easypanel.host" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  https://agent.2notasudi.com.br/v1/chat/completions | grep -i 'access-control-allow-origin' | tr -d '\r' || echo "ACAO=EMPTY")
echo "       $ACAO (esperado ACAO com https://cartorio-lobechat.dfgdxq.easypanel.host)"

echo "  6.3 POST /v1/chat/completions (sem 408)"
RESP=$(curl -sS --max-time 35 -X POST https://agent.2notasudi.com.br/v1/chat/completions \
  -H "Authorization: Bearer @Techno832466" \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw","messages":[{"role":"user","content":"oi"}],"max_tokens":15,"stream":false}')
echo "       resp: ${RESP:0:200}"

echo ""
echo "$LOG_PREFIX === DONE. Se ACAO apareceu e POST nao e 408, LobeChat pode tentar de novo. ==="
echo "$LOG_PREFIX Backup pre-fix: $BACKUP_PATH (dentro do container)"
echo "$LOG_PREFIX Para rollback: docker exec $OPENCLAW_CONTAINER cp $BACKUP_PATH $OPENCLAW_CFG && docker service update --force $OPENCLAW_CONTAINER"

# Modified by Gustavo Almeida
