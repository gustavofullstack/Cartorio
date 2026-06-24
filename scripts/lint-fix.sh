#!/usr/bin/env bash
# scripts/lint-fix.sh
# Auto-fix de lint + format. Roda ANTES de commit para evitar
# erros em CI.
#
# Uso:
#   ./scripts/lint-fix.sh

set -euo pipefail

YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

echo -e "${YELLOW}=== Auto-fix lint + format ===${NC}"
echo ""

echo -e "${YELLOW}[1/3] ruff check --fix${NC}"
uv run ruff check . --fix
echo ""

echo -e "${YELLOW}[2/3] ruff format${NC}"
uv run ruff format .
echo ""

echo -e "${YELLOW}[3/3] verificacao final (deve passar)${NC}"
uv run ruff check .
uv run ruff format --check .
echo ""

echo -e "${GREEN}=== Auto-fix completo ===${NC}"
echo "Rode 'git diff' para revisar as mudancas antes de commit."
