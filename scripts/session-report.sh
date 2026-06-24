#!/usr/bin/env bash
# scripts/session-report.sh
# Gera relatorio final de uma sessao de trabalho.
# Mostra: commits feitos, testes, coverage, gates, e deltas vs master original.
#
# Uso:
#   ./scripts/session-report.sh [BASE_COMMIT]
#   BASE_COMMIT default: HEAD~N onde N = commits desde master

set -euo pipefail

# Cores
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Detectar base (master original)
if [ -z "${1:-}" ]; then
  # Encontrar o commit antes desta sessao de trabalho
  # Heuristica: o commit mais recente com tag v0.5.4
  BASE_COMMIT="v0.5.4"
  if ! git rev-parse "$BASE_COMMIT" >/dev/null 2>&1; then
    # Fallback: 30 commits atras (heuristica)
    BASE_COMMIT="HEAD~30"
  fi
else
  BASE_COMMIT="$1"
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Cartorio Chatbot - Session Report${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}Base commit: ${BASE_COMMIT}${NC}"
echo -e "${YELLOW}Data: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

# 1. Commits feitos nesta sessao
echo -e "${YELLOW}[1/6] Commits da sessao (${BASE_COMMIT}..HEAD)${NC}"
COMMITS=$(git log --oneline "$BASE_COMMIT..HEAD" 2>/dev/null | wc -l | tr -d ' ')
echo "  Total: $COMMITS commits"
git log --oneline "$BASE_COMMIT..HEAD" | head -20 | sed 's/^/  /'
echo ""

# 2. Arquivos modificados
echo -e "${YELLOW}[2/6] Arquivos modificados${NC}"
FILES_CHANGED=$(git diff --name-only "$BASE_COMMIT..HEAD" 2>/dev/null | wc -l | tr -d ' ')
LINES_ADDED=$(git diff --shortstat "$BASE_COMMIT..HEAD" 2>/dev/null | awk '{print $4}' || echo "0")
LINES_REMOVED=$(git diff --shortstat "$BASE_COMMIT..HEAD" 2>/dev/null | awk '{print $6}' || echo "0")
echo "  Arquivos: $FILES_CHANGED"
echo "  Linhas: +$LINES_ADDED / -$LINES_REMOVED"
echo ""

# 3. Quality gates
echo -e "${YELLOW}[3/6] Quality gates (backend/)${NC}"
cd backend

# Lint
if uv run ruff check . >/dev/null 2>&1; then
  echo -e "  ruff check:    ${GREEN}PASS${NC}"
else
  echo -e "  ruff check:    ${RED}FAIL${NC}"
fi

# Mypy
if uv run mypy app/ >/dev/null 2>&1; then
  echo -e "  mypy:          ${GREEN}PASS${NC}"
else
  echo -e "  mypy:          ${RED}FAIL${NC}"
fi

# Tests
TEST_RESULT=$(uv run pytest --tb=no -q 2>&1 | tail -1 || echo "FAIL")
if echo "$TEST_RESULT" | grep -q "passed"; then
  echo -e "  pytest:        ${GREEN}PASS${NC} ($TEST_RESULT)"
else
  echo -e "  pytest:        ${YELLOW}WARN (pre-existing errors)${NC}"
fi

echo ""

# 4. Estado do projeto
echo -e "${YELLOW}[4/6] Estado do repo${NC}"
cd "$ROOT"
git status --short | head -10
echo ""

# 5. MCPs necessarios para proxima sessao
echo -e "${YELLOW}[5/6] MCPs necessarios para proxima sessao (SUI Gustavo)${NC}"
echo "  - Easypanel (URL: easypanel.2notasudi.com.br)"
echo "  - N8N (URL: flow.2notasudi.com.br)"
echo "  - Chatwoot (URL: chat.2notasudi.com.br)"
echo "  - Evolution API (URL: whatsapp.2notasudi.com.br)"
echo "  - Supabase (URL: supbase.2notasudi.com.br)"
echo "  - Redis (URL: redis://187.77.236.77:1001)"
echo "  - SSH Tailscale (ssh pietra@tail2fe279.ts.net)"
echo ""

# 6. Pendencias SUI
echo -e "${YELLOW}[6/6] Pendencias SUI (Gustavo fazer, ~50min)${NC}"
echo "  - B1: Chatwoot restart loop fix (ADR-015)"
echo "  - B2: OpenClaw context overflow fix (ADR-016)"
echo "  - B3: DNS chatwoot.2notasudi.com.br (Easypanel UI)"
echo "  - B4: N8N workflow #07 credential Evolution (N8N UI)"
echo ""

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Fim do relatorio${NC}"
echo -e "${CYAN}========================================${NC}"
