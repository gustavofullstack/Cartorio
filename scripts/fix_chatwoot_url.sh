#!/bin/bash
# =============================================================================
# FIX Chatwoot URL (INC-005)
# Resolve: Chatwoot 502 Bad Gateway
# Root cause: CHATWOOT_BASE_URL=http://cartorio_chatwoot:3000 so funciona
# dentro do Docker Swarm, NAO em DNS local do Mac
# =============================================================================

set -euo pipefail

ENV_FILE="${1:-/Users/gustavoalmeida/projetos/Cartorio/backend/cartorio-api.env}"
BACKUP="${ENV_FILE}.bak.inc005-$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "FIX Chatwoot URL (INC-005)"
echo "=========================================="

# 1. Estado ANTES
echo "[1/5] Estado ANTES:"
if grep -q '^CHATWOOT_BASE_URL=' "$ENV_FILE" 2>/dev/null; then
    grep '^CHATWOOT_BASE_URL=' "$ENV_FILE"
else
    echo "  CHATWOOT_BASE_URL not found in $ENV_FILE"
    exit 1
fi

# 2. Backup
echo ""
echo "[2/5] Criando backup em $BACKUP..."
cp "$ENV_FILE" "$BACKUP"
echo "  Backup: $BACKUP"

# 3. Aplicar fix
echo ""
echo "[3/5] Aplicando fix (cartorio_chatwoot:3000 -> chat.2notasudi.com.br)..."
sed -i.tmp 's|^CHATWOOT_BASE_URL=.*|CHATWOOT_BASE_URL=https://chat.2notasudi.com.br|' "$ENV_FILE"
rm -f "$ENV_FILE.tmp"
grep '^CHATWOOT_BASE_URL=' "$ENV_FILE"

# 4. Validar
echo ""
echo "[4/5] Validacao..."
NEW_URL=$(grep '^CHATWOOT_BASE_URL=' "$ENV_FILE" | cut -d= -f2-)
if [ "$NEW_URL" = "https://chat.2notasudi.com.br" ]; then
    echo "  CHATWOOT_BASE_URL atualizado com sucesso"
else
    echo "  AVISO: URL nao corresponde ao esperado"
    echo "  Esperado: https://chat.2notasudi.com.br"
    echo "  Atual: $NEW_URL"
fi

# 5. DNS check (chat.2notasudi.com.br precisa resolver)
echo ""
echo "[5/5] DNS check..."
if dig +short chat.2notasudi.com.br >/dev/null 2>&1; then
    echo "  chat.2notasudi.com.br resolves OK"
else
    echo "  chat.2notasudi.com.br NAO resolve (Cloudflare A record pendente)"
    echo "  Gustavo precisa criar A record: chat -> 187.77.236.77"
fi

echo ""
echo "=========================================="
echo "FIX APLICADO"
echo "=========================================="
echo ""
echo "NOTAS:"
echo "1. Este fix muda o .env mas NAO roda o container (sem restart automatico)"
echo "2. Gustavo precisa rodar 'ssh cartorio docker service update --force cartorio_api' para aplicar"
echo "3. OU cartorio-dev pode incluir este fix no proximo deploy"
echo "4. Se chat.2notasudi.com.br NAO resolver, restaurar backup: mv $BACKUP $ENV_FILE"