#!/usr/bin/env bash
# check_openclaw.sh — Verifica status do OpenClaw Gateway
# Uso: ./check_openclaw.sh
#
# Verifica: health, agents, context size

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"
OCL_URL="https://agent.2notasudi.com.br"

echo "🤖 OpenClaw Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Health
echo "1️⃣ Health check..."
HEALTH=$(curl -sk -m 8 "${OCL_URL}/health" 2>/dev/null || echo "{}")
if echo "$HEALTH" | grep -q '"ok":true'; then
    printf "${GREEN}✅${NC} OpenClaw: HEALTH OK\n"
else
    printf "${RED}❌${NC} OpenClaw: HEALTH FAIL — %s\n" "$HEALTH"
fi

# 2. Agents
echo ""
echo "2️⃣ Agents..."
AGENTS=$(curl -sk -m 8 "${OCL_URL}/v1/agents" 2>/dev/null || echo "[]")
if echo "$AGENTS" | grep -q "Pietra"; then
    printf "${GREEN}✅${NC} Pietra agent found\n"
else
    printf "${YELLOW}⚠️${NC} Pietra agent not found in response\n"
fi

# 3. Context size check
echo ""
echo "3️⃣ Context size..."
echo "   Check via agent config: /home/node/.openclaw/agents/main/agent/models.json"
echo "   Expected: max_tokens = 1000000 (1M)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ OpenClaw check complete"
