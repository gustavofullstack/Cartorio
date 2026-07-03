#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# LOOP CONTINUE — Retomada de sessão
# ═══════════════════════════════════════════════════════════════════════════════
# Quando nova sessão inicia (Gustavo volta após dormir), este script lê o
# state/last.json e imprime os próximos passos + carry_over_tasks + blockers.
#
# Mapeia a skill `loop` para este script (Lesson 139).
#
# Uso:
#   bash .harness/loop-engineer/loop-continue.sh
#
# Output:
#   - Próximo step recomendado
#   - Tasks em carry-over (de cycles anteriores)
#   - Blockers pendentes
#   - Status dos gates
#
# ═══════════════════════════════════════════════════════════════════════════════
set -uo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
STATE_DIR="$PROJECT/.harness/loop-engineer/state"
LAST="$STATE_DIR/last.json"
GOALS="$PROJECT/GOALS.md"

echo "═══════════════════════════════════════════════════════════════════"
echo "  CARTÓRIO LOOP CONTINUE — $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

if [ ! -f "$LAST" ]; then
  echo "⚠️  No state yet. Run goal-loop-cron.sh first."
  echo "   Comando: bash $PROJECT/.harness/loop-engineer/goal-loop-cron.sh"
  exit 1
fi

echo "📂 LAST CYCLE STATE"
echo "─────────────────────────────────────────────────────────────────"
echo ""

# Resumo do último cycle
NEXT_STEP=$(grep -o '"next_step": "[^"]*"' "$LAST" | head -1 | cut -d'"' -f4)
echo "▶ NEXT STEP: $NEXT_STEP"
echo ""

# Carry over tasks
if grep -q "carry_over_tasks" "$LAST" 2>/dev/null; then
  echo "📋 CARRY OVER TASKS:"
  grep -oE '"[A-Z][A-Z0-9-]+"' "$LAST" | grep -E 'T[0-9]|DEP|MEM|BRAIN' | head -10 | sed 's/^/   • /'
  echo ""
fi

# Blockers
if grep -q "blockers" "$LAST" 2>/dev/null; then
  echo "🚧 BLOCKERS:"
  grep -oE '"[A-Z][A-Z0-9-]+[A-Z]"' "$LAST" | grep -E 'SUI|BLOCKED' | head -5 | sed 's/^/   • /'
  echo ""
fi

# Gates
echo "🔒 GATES:"
grep -oE '"(mypy|ruff|pytest)": [^,}]*' "$LAST" | sed 's/^/   /'
echo ""

# Goals link
echo "📊 GOALS CANÔNICOS: $GOALS"
[ -f "$GOALS" ] && echo "   ✅ Arquivo existe" || echo "   ❌ Arquivo NÃO existe"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo "  AÇÃO RECOMENDADA: retomar carry_over_tasks via /goal ou /loop"
echo "═══════════════════════════════════════════════════════════════════"