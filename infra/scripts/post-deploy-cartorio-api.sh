#!/bin/bash
# ============================================================================
# post-deploy-cartorio-api.sh
# ============================================================================
# Workaround para Lesson 103: Easypanel rebuild SOBRESCREVE spec do cartorio_api
# service no Swarm, fazendo CARTORIO_API_KEY sumir do env, e o container
# falha restart com "Field required".
#
# Este script reaplica o env CARTORIO_API_KEY no service apos cada git push +
# Easypanel rebuild. Validar SEMPRE apos push:
#   1. git push origin master
#   2. sleep 90 (Easypanel rolling restart)
#   3. ./infra/scripts/post-deploy-cartorio-api.sh
#   4. Smoke test: curl https://api.2notasudi.com.br/health
#
# Idempotente. Executa via SSH cartorio (Tailscale 100.99.172.84).
#
# Reverte: este script NAO remove a chave (apenas garante que existe).
# Para remover (NAO recomendado): ssh cartorio 'docker service update
#   --env-rm CARTORIO_API_KEY cartorio_api'
# ============================================================================
set -euo pipefail

VPS_HOST="${VPS_HOST:-root@100.99.172.84}"
EXPECTED_KEY="${CARTORIO_API_KEY:-$(grep '^CARTORIO_API_KEY=' backend/.env 2>/dev/null | cut -d'=' -f2)}"
LOG_PREFIX="[$(date +%Y-%m-%dT%H:%M:%S%z)] post-deploy"

if [ -z "$EXPECTED_KEY" ]; then
  echo "$LOG_PREFIX ERROR: CARTORIO_API_KEY nao encontrada em backend/.env"
  exit 1
fi

# 1. Validar key tem 64 chars hex
KEY_LEN=${#EXPECTED_KEY}
if [ "$KEY_LEN" -ne 64 ]; then
  echo "$LOG_PREFIX ERROR: CARTORIO_API_KEY tem $KEY_LEN chars (esperado 64)"
  exit 1
fi

echo "$LOG_PREFIX === Post-deploy cartorio_api env reaplication ==="
echo "$LOG_PREFIX VPS: $VPS_HOST"
echo "$LOG_PREFIX Key fingerprint: ${EXPECTED_KEY:0:8}"

# 2. Verificar estado atual do env no service
echo "$LOG_PREFIX --- Service env (current) ---"
ssh "$VPS_HOST" 'docker service inspect cartorio_api --format "{{json .Spec.TaskTemplate.ContainerSpec.Env}}" 2>/dev/null' \
  | python3 -c "
import json, sys
envs = json.loads(sys.stdin.read().strip())
has_key = any(e.startswith('CARTORIO_API_KEY=') for e in envs)
print(f'CARTORIO_API_KEY presente no spec: {has_key}')
"

# 3. Reaplicar env (idempotente)
echo "$LOG_PREFIX --- Reaplicando env ---"
ssh "$VPS_HOST" "docker service update --env-add CARTORIO_API_KEY=$EXPECTED_KEY cartorio_api" 2>&1 | tail -3

# 4. Esperar restart
echo "$LOG_PREFIX --- Aguardando restart (60s) ---"
sleep 60

# 5. Validar
echo "$LOG_PREFIX --- Validacao pos-restart ---"
CONTAINER_ID=$(ssh "$VPS_HOST" 'docker ps -qf name=cartorio_api | head -1')
CONTAINER_KEY=$(ssh "$VPS_HOST" "docker exec $CONTAINER_ID env | grep ^CARTORIO_API_KEY=" 2>&1)
if echo "$CONTAINER_KEY" | grep -q "$EXPECTED_KEY"; then
  echo "$LOG_PREFIX ✅ CARTORIO_API_KEY presente no container"
  echo "$LOG_PREFIX === SUCCESS ==="
else
  echo "$LOG_PREFIX ❌ CARTORIO_API_KEY NAO presente"
  echo "$LOG_PREFIX Container env: $CONTAINER_KEY"
  exit 1
fi

# 6. Smoke test (opcional, requer internet)
if [ -n "${SMOKE_TEST:-}" ]; then
  echo "$LOG_PREFIX --- Smoke test ---"
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-API-Key: $EXPECTED_KEY" \
    https://api.2notasudi.com.br/api/v1/cliente/1)
  if [ "$HTTP" = "200" ] || [ "$HTTP" = "404" ]; then
    echo "$LOG_PREFIX ✅ Smoke test $HTTP"
  else
    echo "$LOG_PREFIX ❌ Smoke test $HTTP"
    exit 1
  fi
fi

echo "$LOG_PREFIX === Done ==="
