#!/usr/bin/env bash
# check_docker.sh — Verifica status dos containers Docker na VPS
# Uso: ./check_docker.sh
#
# Verifica: containers UP, memória, restarts, health

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"; NC="\033[0m"
VPS="root@100.99.172.84"

echo "🐳 Docker Status Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Docker services
echo "1️⃣ Docker Swarm Services..."
ssh "$VPS" "docker service ls --format '{{.Name}}\t{{.Replicas}}\t{{.Image}}' 2>/dev/null" | while IFS=$'\t' read -r name replicas image; do
    if [[ "$replicas" == *"0/"* ]]; then
        printf "${RED}❌${NC} %-30s %s\n" "$name" "$replicas"
    else
        printf "${GREEN}✅${NC} %-30s %s\n" "$name" "$replicas"
    fi
done

# 2. Container health
echo ""
echo "2️⃣ Container Health..."
ssh "$VPS" "docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null" | head -15 | while IFS=$'\t' read -r name status ports; do
    if [[ "$status" == *"unhealthy"* ]]; then
        printf "${RED}❌${NC} %-30s %s\n" "$name" "$status"
    elif [[ "$status" == *"restarting"* ]]; then
        printf "${YELLOW}⚠️${NC} %-30s %s\n" "$name" "$status"
    else
        printf "${GREEN}✅${NC} %-30s %s\n" "$name" "$status"
    fi
done

# 3. Memory usage
echo ""
echo "3️⃣ Memory Usage..."
ssh "$VPS" "docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' 2>/dev/null" | head -10

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Docker check complete"
