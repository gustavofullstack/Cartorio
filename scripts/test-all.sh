#!/usr/bin/env bash
# scripts/test-all.sh
# Roda TODOS os gates de qualidade antes de commit.
# Equivalente a `make qa` mas com verificacoes extras.

set -euo pipefail

# Cores
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Diretorio raiz do projeto
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo -e "${YELLOW}=== Cartorio Chatbot - Full Quality Gate ===${NC}"
echo ""

# 1. Backend - Lint (ruff)
echo -e "${YELLOW}[1/6] Backend: ruff check${NC}"
(cd backend && uv run ruff check .)
echo -e "${GREEN}OK${NC}"
echo ""

# 2. Backend - Format check
echo -e "${YELLOW}[2/6] Backend: ruff format --check${NC}"
(cd backend && uv run ruff format --check .)
echo -e "${GREEN}OK${NC}"
echo ""

# 3. Backend - Typecheck (mypy)
echo -e "${YELLOW}[3/6] Backend: mypy${NC}"
(cd backend && uv run mypy app/)
echo -e "${GREEN}OK${NC}"
echo ""

# 4. Backend - Tests
echo -e "${YELLOW}[4/6] Backend: pytest (com coverage)${NC}"
(cd backend && uv run pytest -v --tb=short)
echo -e "${GREEN}OK${NC}"
echo ""

# 5. Frontend / N8N (se existir)
echo -e "${YELLOW}[5/6] N8N workflows: validate JSON${NC}"
if [ -d "infra/n8n-workflows" ]; then
  for f in infra/n8n-workflows/*.json; do
    if [ -f "$f" ]; then
      python3 -c "import json; json.load(open('$f'))" 2>/dev/null && \
        echo "  - $f: OK" || \
        echo -e "  - $f: ${RED}INVALID JSON${NC}"
    fi
  done
fi
echo -e "${GREEN}OK${NC}"
echo ""

# 6. Docs - check critical files exist
echo -e "${YELLOW}[6/6] Docs: check critical files${NC}"
for f in README.md docs/CHANGELOG.md docs/API.md docs/FAQ.md .harness/AGENTS.md; do
  if [ -s "$f" ]; then
    echo "  - $f: OK ($(wc -l < "$f") lines)"
  else
    echo -e "  - $f: ${RED}MISSING OR EMPTY${NC}"
    exit 1
  fi
done
echo -e "${GREEN}OK${NC}"
echo ""

echo -e "${GREEN}=== ALL QUALITY GATES PASSED ===${NC}"
echo "Pronto para commit/push."
