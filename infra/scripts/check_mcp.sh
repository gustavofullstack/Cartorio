#!/usr/bin/env bash
# check_mcp.sh — Verifica status dos MCP servers
# Uso: ./check_mcp.sh
#
# Verifica: API MCP, N8N MCP

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"

echo "🔌 MCP Servers Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. API MCP
echo "1️⃣ API MCP (164 tools)..."
HTTP=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "https://api.2notasudi.com.br/mcp" 2>/dev/null || echo "000")
if [[ "$HTTP" == "200" || "$HTTP" == "405" ]]; then
    printf "${GREEN}✅${NC} API MCP: HTTP %s\n" "$HTTP"
else
    printf "${RED}❌${NC} API MCP: HTTP %s\n" "$HTTP"
fi

# 2. N8N MCP
echo ""
echo "2️⃣ N8N MCP (30 tools)..."
HTTP2=$(curl -sk -o /dev/null -w "%{http_code}" -m 8 "https://flow.2notasudi.com.br/mcp-server/http" 2>/dev/null || echo "000")
if [[ "$HTTP2" == "200" || "$HTTP2" == "405" ]]; then
    printf "${GREEN}✅${NC} N8N MCP: HTTP %s\n" "$HTTP2"
else
    printf "${RED}❌${NC} N8N MCP: HTTP %s\n" "$HTTP2"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ MCP check complete"
