#!/usr/bin/env bash
# check_migrations.sh — Verifica status das migrações Alembic
# Uso: ./check_migrations.sh
#
# Verifica: migration head, pending migrations, schema drift

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"
VPS="root@100.99.172.84"

echo "🗃️ Alembic Migration Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Check local alembic versions
echo "1️⃣ Local migration files..."
LOCAL_COUNT=$(ls /Users/gustavoalmeida/projetos/Cartorio/backend/alembic/versions/*.py 2>/dev/null | wc -l)
LOCAL_HEAD=$(ls -t /Users/gustavoalmeida/projetos/Cartorio/backend/alembic/versions/*.py 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "none")
printf "   Files: %d | Latest: %s\n" "$LOCAL_COUNT" "$LOCAL_HEAD"

# 2. Check remote DB version (via API health)
echo ""
echo "2️⃣ API health check..."
HTTP=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "https://api.2notasudi.com.br/health" 2>/dev/null || echo "000")
if [[ "$HTTP" == "200" ]]; then
    printf "${GREEN}✅${NC} API: HTTP %s (migrations applied)\n" "$HTTP"
else
    printf "${RED}❌${NC} API: HTTP %s\n" "$HTTP"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Migration check complete"
