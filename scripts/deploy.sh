#!/usr/bin/env bash
# scripts/deploy.sh
# Deploy do backend para Easypanel via git push.
# NAO mexe com secrets - apenas builda e dispara deploy.
#
# Uso:
#   ./scripts/deploy.sh staging
#   ./scripts/deploy.sh prod

set -euo pipefail

ENV="${1:-staging}"

if [[ "$ENV" != "staging" && "$ENV" != "prod" ]]; then
  echo "ERRO: ambiente deve ser 'staging' ou 'prod' (recebido: $ENV)"
  exit 1
fi

# Cores
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Diretorio raiz
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo -e "${YELLOW}=== Deploy para $ENV ===${NC}"
echo ""

# 1. Pre-deploy checks
echo -e "${YELLOW}[1/5] Pre-deploy checks${NC}"
git status --short
git log --oneline -3
echo ""

# Confirmar com usuario
read -p "Continuar deploy para $ENV? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Deploy cancelado"
  exit 1
fi

# 2. Rodar quality gates
echo -e "${YELLOW}[2/5] Quality gates (make qa)${NC}"
./scripts/test-all.sh
echo ""

# 3. Backup pre-deploy (N8N workflow #09)
echo -e "${YELLOW}[3/5] Backup pre-deploy (workflow #09)${NC}"
if [ -n "${N8N_API_KEY:-}" ] && [ -n "${N8N_BASE_URL:-}" ]; then
  echo "Disparando workflow #09..."
  curl -s -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
    "$N8N_BASE_URL/api/v1/workflows/9/execute" || \
    echo -e "${YELLOW}WARN: backup workflow nao disparou${NC}"
else
  echo -e "${YELLOW}WARN: N8N_API_KEY ou N8N_BASE_URL nao definidos - pulando backup${NC}"
fi
echo ""

# 4. Tag + push
echo -e "${YELLOW}[4/5] Tag + push para origin/$ENV${NC}"
TAG="v$(date +%Y%m%d-%H%M%S)-$ENV"
git tag -a "$TAG" -m "Deploy $ENV em $(date '+%Y-%m-%d %H:%M:%S')"
git push origin "$ENV" --follow-tags
echo -e "${GREEN}Push OK: tag $TAG${NC}"
echo ""

# 5. Easypanel auto-deploy (se Easypanel estiver conectado)
echo -e "${YELLOW}[5/5] Easypanel auto-deploy${NC}"
if [ -n "${EASYPANEL_API_KEY:-}" ]; then
  echo "Disparando redeploy em Easypanel..."
  # Implementacao especifica depende da API do Easypanel
  # Documentado em docs/ENV_PRODUCTION.md
  echo -e "${YELLOW}TODO: implementar trigger Easypanel${NC}"
else
  echo -e "${YELLOW}EASYPANEL_API_KEY nao definido - deploy manual via UI${NC}"
fi
echo ""

echo -e "${GREEN}=== Deploy $ENV iniciado ===${NC}"
echo "Tag: $TAG"
echo "Acompanhe em: https://api.2notasudi.com.br/api/v1/health/radar"
