#!/usr/bin/env bash
# check_backup.sh — Verifica status do backup na VPS
# Uso: ./check_backup.sh
#
# Verifica: /var/log/cartorio-backup-status.json + /var/backups/cartorio/

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"
VPS="root@100.99.172.84"

echo "💾 Backup Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Check backup status JSON
echo "1️⃣ Backup status JSON..."
STATUS=$(ssh "$VPS" "cat /var/log/cartorio-backup-status.json 2>/dev/null" || echo "{}")
if echo "$STATUS" | grep -q '"ok":true'; then
    LAST=$(echo "$STATUS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('last_backup_iso','unknown'))" 2>/dev/null || echo "unknown")
    printf "${GREEN}✅${NC} Last backup: %s\n" "$LAST"
else
    printf "${RED}❌${NC} Backup status: %s\n" "$STATUS"
fi

# 2. Check backup files
echo ""
echo "2️⃣ Backup files..."
BACKUP_COUNT=$(ssh "$VPS" "ls /var/backups/cartorio/*.tar.gz 2>/dev/null | wc -l" || echo "0")
BACKUP_SIZE=$(ssh "$VPS" "du -sh /var/backups/cartorio/ 2>/dev/null | cut -f1" || echo "unknown")
printf "   Files: %s | Size: %s\n" "$BACKUP_COUNT" "$BACKUP_SIZE"

if [[ "$BACKUP_COUNT" -gt 0 ]]; then
    LATEST=$(ssh "$VPS" "ls -t /var/backups/cartorio/*.tar.gz 2>/dev/null | head -1" || echo "none")
    printf "   Latest: %s\n" "$(basename "$LATEST" 2>/dev/null || echo 'none')"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Backup check complete"
