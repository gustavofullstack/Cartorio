#!/bin/bash
# =============================================================================
# DIAGNOSE Chatwoot Crashloop (INC-005b)
# Root cause: cartorio_chatwoot (web) NAO esta na rede cartorio_supabase_default
#            portanto nao consegue resolver "db" para conectar no postgres do Supabase
# =============================================================================

set -euo pipefail

echo "=========================================="
echo "DIAGNOSE Chatwoot Crashloop (INC-005b)"
echo "=========================================="
echo ""

# 1. Status do servico
echo "[1/6] Status do servico cartorio_chatwoot..."
ssh cartorio "docker service ps cartorio_chatwoot 2>&1 | head -5"

# 2. Redes disponiveis
echo ""
echo "[2/6] Redes Docker Swarm (qual deveria estar o Chatwoot):"
ssh cartorio "docker network ls --filter name=cartorio 2>&1 | head -10"

# 3. Chatwoot (web) esta na rede correta?
echo ""
echo "[3/6] Chatwoot (web) esta na rede cartorio_supabase_default?"
if ssh cartorio "docker network inspect cartorio_supabase_default 2>&1 | grep -q cartorio_chatwoot-web" 2>/dev/null; then
    echo "  ✅ SIM - esta na rede"
else
    echo "  ❌ NAO - root cause do crashloop"
fi
echo ""
echo "  (Chatwoot-sidekiq ESTA na rede: chatwoot-sidekiq aparece na listagem)"
ssh cartorio "docker network inspect cartorio_supabase_default 2>&1 | grep -c chatwoot"

# 4. Chatwoot-web em qual rede?
echo ""
echo "[4/6] Em qual rede o cartorio_chatwoot (web) esta?"
CHATWOOT_NET=$(ssh cartorio "docker inspect cartorio_chatwoot 2>&1 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(list(d[0][\"NetworkSettings\"][\"Networks\"].keys()))'" 2>&1)
echo "  Redes: $CHATWOOT_NET"

# 5. Solucao recomendada
echo ""
echo "[5/6] SOLUCAO:"
echo "  1. Conectar cartorio_chatwoot a rede cartorio_supabase_default"
echo "  2. OU mudar POSTGRES_HOST para FQDN do kong (http://cartorio_supabase-kong:8000)"
echo "  3. OU recriar servico via Easypanel UI com network correta"
echo ""
echo "  COMANDO MANUAL (via SSH):"
echo "  ssh cartorio 'docker service update --network-add cartorio_supabase_default cartorio_chatwoot'"
echo ""
echo "  OU via Easypanel UI:"
echo "  https://easypanel.2notasudi.com.br/projects/cartorio/services/cartorio_chatwoot/networks"
echo "  Adicionar rede: cartorio_supabase_default"

# 6. Validacao (se ja foi corrigido)
echo ""
echo "[6/6] Validacao final..."
sleep 2
HEALTH=$(curl -sk "https://api.2notasudi.com.br/api/v1/health/radar" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  {d[\"services\"][\"chatwoot\"]}')")
echo "  Chatwoot status: $HEALTH"
if [ "$HEALTH" = "online" ]; then
    echo "  ✅ Chatwoot voltou!"
else
    echo "  ⚠️ Chatwoot ainda offline - requer acao manual"
fi
