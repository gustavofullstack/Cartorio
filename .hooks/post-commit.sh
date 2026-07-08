#!/usr/bin/env bash
# .hooks/post-commit.sh
# Squad 3 — 2026-07-08
# Detecta mudanças em arquivos sensíveis e roda validações automáticas.
#
# Triggers:
#   1. Mudança em scripts/coding_vps_mcp_orchestrator.py  → syntax check via ast
#   2. Mudança em .agents/skills/                          → regenera INDEX.md
#
# Instalação (one-time):
#   git config core.hooksPath .hooks
#   chmod +x .hooks/post-commit.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

CHANGED_FILES="$(git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --name-only --cached)"

log() { printf "\033[1;36m[post-commit]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[post-commit][WARN]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[post-commit][ERR]\033[0m %s\n" "$*"; }
ok() { printf "\033[1;32m[post-commit][OK]\033[0m %s\n" "$*"; }

if [ -z "$CHANGED_FILES" ]; then
  log "Nenhum arquivo alterado no último commit. Saindo."
  exit 0
fi

# ------------------------------------------------------------
# 1. Syntax check em scripts/coding_vps_mcp_orchestrator.py
# ------------------------------------------------------------
if echo "$CHANGED_FILES" | grep -q "^scripts/coding_vps_mcp_orchestrator.py$"; then
  log "Detectada mudança em coding_vps_mcp_orchestrator.py → rodando AST syntax check"
  if python3 -c "import ast; ast.parse(open('scripts/coding_vps_mcp_orchestrator.py').read()); print('AST_OK')" 2>&1; then
    ok "AST syntax check passed"
  else
    err "AST syntax check FAILED — revertendo commit recomendado"
    exit 1
  fi

  log "Contando tools registradas"
  TOOL_COUNT=$(python3 scripts/coding_vps_mcp_orchestrator.py list 2>/dev/null | head -1 | grep -oE '[0-9]+ tools' | head -1 | awk '{print $1}')
  if [ -n "$TOOL_COUNT" ]; then
    ok "Orchestrator agora expõe $TOOL_COUNT tools"
    if [ "$TOOL_COUNT" -lt 100 ]; then
      warn "Total de tools ($TOOL_COUNT) abaixo da meta Squad 3 (100+)"
    fi
  fi
fi

# ------------------------------------------------------------
# 2. Mudança em .agents/skills/ → regenerar INDEX.md
# ------------------------------------------------------------
if echo "$CHANGED_FILES" | grep -q "^\.agents/skills/"; then
  log "Detectada mudança em .agents/skills/ → atualizando INDEX.md"
  if [ -f ".agents/skills/INDEX.md" ]; then
    # Verificar que INDEX.md já está no commit (autorregenerado é responsabilidade de outro hook)
    if echo "$CHANGED_FILES" | grep -q "^\.agents/skills/INDEX.md$"; then
      ok "INDEX.md já está atualizado no commit"
    else
      warn "INDEX.md não foi atualizado junto — rode: ./.hooks/regenerate_skill_index.sh"
    fi
  else
    warn "INDEX.md não existe — squad3 não rodou ainda"
  fi
fi

ok "post-commit hook completed"
exit 0
