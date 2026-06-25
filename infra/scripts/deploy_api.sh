#!/usr/bin/env bash
# deploy_api.sh — Deploy da API Cartório na VPS
# Uso: ./deploy_api.sh [version]
#
# Steps: build → push → update service → health check
# LGPD: NÃO loga PII

set -eo pipefail

VERSION="${1:-latest}"
VPS="root@100.99.172.84"
SERVICE="cartorio_api"
REGISTRY="easypanel/cartorio"

echo "🚀 Deploying API v${VERSION}..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Health check antes do deploy
echo "1️⃣ Health check PRE-deploy..."
HTTP_PRE=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "https://api.2notasudi.com.br/health" 2>/dev/null || echo "000")
if [[ "$HTTP_PRE" != "200" ]]; then
    echo "⚠️  API PRE-deploy: HTTP $HTTP_PRE (pode já estar DOWN)"
fi

# 2. Build na VPS
echo "2️⃣ Build na VPS..."
ssh "$VPS" "cd /tmp && ls cartorio/backend/ >/dev/null 2>&1 && echo 'Build dir OK' || echo 'Build dir missing — SCP first'"

# 3. Docker build
echo "3️⃣ Docker build..."
ssh "$VPS" "cd /tmp/cartorio/backend && docker build -t ${REGISTRY}/api:v${VERSION} -t ${REGISTRY}/api:latest . 2>&1 | tail -5"

# 4. Update service
echo "4️⃣ Docker service update..."
ssh "$VPS" "docker service update --image ${REGISTRY}/api:latest ${SERVICE} 2>&1 | tail -3"

# 5. Wait for startup
echo "5️⃣ Aguardando startup (10s)..."
sleep 10

# 6. Health check POST-deploy
echo "6️⃣ Health check POST-deploy..."
HTTP_POST=$(curl -sk -o /dev/null -w "%{http_code}" -m 15 "https://api.2notasudi.com.br/health" 2>/dev/null || echo "000")
if [[ "$HTTP_POST" == "200" ]]; then
    echo "✅ API v${VERSION} deployada com sucesso! HTTP 200"
else
    echo "❌ API deploy FALHOU! HTTP $HTTP_POST"
    echo "Rollback: ssh $VPS 'docker service update --image ${REGISTRY}/api:previous ${SERVICE}'"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deploy completo!"
