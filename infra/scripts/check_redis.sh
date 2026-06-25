#!/usr/bin/env bash
# check_redis.sh — Verifica status do Redis na VPS
# Uso: ./check_redis.sh
#
# Verifica: PONG, auth, memória, keys, conexões

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"
VPS="root@100.99.172.84"

echo "🔴 Redis Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. PING
echo "1️⃣ PING..."
PONG=$(ssh "$VPS" "redis-cli -p 1001 -a @Techno832466 PING 2>/dev/null" || echo "FAIL")
if [[ "$PONG" == "PONG" ]]; then
    printf "${GREEN}✅${NC} Redis: PONG\n"
else
    printf "${RED}❌${NC} Redis: %s\n" "$PONG"
fi

# 2. Memory
echo ""
echo "2️⃣ Memory..."
ssh "$VPS" "redis-cli -p 1001 -a @Techno832466 INFO memory 2>/dev/null | grep -E 'used_memory_human|used_memory_peak_human|maxmemory_human'" 2>/dev/null

# 3. Keys
echo ""
echo "3️⃣ Keys..."
KEYS=$(ssh "$VPS" "redis-cli -p 1001 -a @Techno832466 DBSIZE 2>/dev/null" || echo "unknown")
printf "   %s\n" "$KEYS"

# 4. Connections
echo ""
echo "4️⃣ Connections..."
ssh "$VPS" "redis-cli -p 1001 -a @Techno832466 INFO clients 2>/dev/null | grep -E 'connected_clients|blocked_clients'" 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Redis check complete"
