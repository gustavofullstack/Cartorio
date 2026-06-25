#!/usr/bin/env bash
# check_deps.sh — Verifica dependências do sistema
# Uso: ./check_deps.sh
#
# Verifica: docker, docker compose, python3, uv, node, npm, curl, jq, redis-cli

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"

check() {
    local name="$1" cmd="$2"
    if command -v "$cmd" &>/dev/null; then
        printf "${GREEN}✅${NC} %-20s %s\n" "$name" "$($cmd --version 2>/dev/null | head -1)"
    else
        printf "${RED}❌${NC} %-20s NOT FOUND\n" "$name"
    fi
}

echo "🔍 Checking system dependencies..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check "Docker" "docker"
check "Docker Compose" "docker-compose"
check "Python 3" "python3"
check "UV (package manager)" "uv"
check "Node.js" "node"
check "npm" "npm"
check "curl" "curl"
check "jq" "jq"
check "redis-cli" "redis-cli"
check "git" "git"
check "ssh" "ssh"
check "rsync" "rsync"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Dependency check complete"
