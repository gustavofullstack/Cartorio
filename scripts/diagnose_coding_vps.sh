#!/usr/bin/env bash
# diagnose_coding_vps.sh - Script diagnóstico REUTILIZÁVEL da coding-vps
# Usage: bash scripts/diagnose_coding_vps.sh
# Requer: SSH key ~/.ssh/id_ed25519_cartorio + acesso Tailscale 100.99.172.84
# Source: Lesson 158 (2026-07-08)

set -uo pipefail
SSH_KEY="${SSH_PRIVATE_KEY:-~/.ssh/id_ed25519_cartorio}"
HOST="${SSH_TAILSCALE_HOST:-100.99.172.84}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Coding-vps Diagnostic (SSH ${HOST}) ==="
echo ""

# 1. Conectividade
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$SSH_KEY" "root@${HOST}" "echo connected" >/dev/null 2>&1; then
  echo -e "${RED}✗ SSH unreachable at ${HOST}${NC}"
  exit 1
fi
echo -e "${GREEN}✓ SSH connected${NC}"

# 2. Listar services do projeto
echo ""
echo "=== Services (replicas state) ==="
ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker service ls --format '{{.Name}}|{{.Replicas}}|{{.Image}}' \
   | grep coding-vps | sort" 2>/dev/null | head -50 | \
  awk -F'|' '{
    printf "%-60s %-8s %s\n", $1, $2, $3
  }'

# 3. Detectar OFF
echo ""
echo "=== Services OFF ==="
OFF=$(ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker service ls --format '{{.Name}}|{{.Replicas}}' | grep coding-vps | grep -v '1/1'" 2>/dev/null)
if [ -z "$OFF" ]; then
  echo -e "${GREEN}✓ Todos os services 1/1${NC}"
else
  echo "$OFF" | while read line; do
    name=$(echo "$line" | cut -d'|' -f1)
    state=$(echo "$line" | cut -d'|' -f2)
    echo -e "${YELLOW}${name}${NC} = ${state}"
    echo "  --- error ---"
    ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
      "docker service ps '${name}' --no-trunc 2>&1 | grep -E '(Error|Rejected|Shutdown)' | head -3" 2>/dev/null | sed 's/^/  /'
  done
fi

# 4. Containers running
echo ""
echo "=== Containers running ==="
ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker ps --filter 'name=coding-vps' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>/dev/null | head -20

# 5. Score
echo ""
TOTAL=$(ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker service ls --format '{{.Name}}' | grep -c coding-vps" 2>/dev/null)
UP=$(ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker service ls --format '{{.Replicas}}' | grep -c '^1/1$'" 2>/dev/null)
PCT=$(awk "BEGIN {printf \"%.0f\", (${UP}/${TOTAL})*100}")
echo -e "${GREEN}Score coding-vps: ${UP}/${TOTAL} (${PCT}%)${NC}"

# 6. litellm config
echo ""
echo "=== litellm-app env ==="
ssh -o BatchMode=yes -i "$SSH_KEY" "root@${HOST}" \
  "docker service inspect coding-vps_apenas_para_auxilio_litellm-app \
   --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}'" 2>/dev/null | head -15

echo ""
echo "Done."
