#!/bin/bash
# ════════════════════════════════════════════════════════════════════════
# Wave Status — Mostra progresso agregado do super plano v25
# Modified by Gustavo Almeida — 2026-07-14
# ════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="$SCRIPT_DIR/state"
SUPER_PLANO="$SCRIPT_DIR/../../../SUPER_PLANO_100_TASKS_25_SQUADS_v25.md"

if [[ ! -d "$STATE_DIR" ]]; then
    echo "No state yet. Run: bash master-loop-v25.sh 0"
    exit 0
fi

echo "═══════════════════════════════════════════════════════"
echo "  SUPER PLANO v25 — STATUS"
echo "═══════════════════════════════════════════════════════"
echo ""

# Count wave files
TOTAL_WAVES=$(find "$STATE_DIR" -name "wave-*.json" -type f 2>/dev/null | wc -l | tr -d ' ')
DONE_WAVES=$(find "$STATE_DIR" -name "wave-*.json" -type f -exec grep -l '"status": "done"' {} \; 2>/dev/null | wc -l | tr -d ' ')
PARTIAL_WAVES=$(find "$STATE_DIR" -name "wave-*.json" -type f -exec grep -l '"status": "partial"' {} \; 2>/dev/null | wc -l | tr -d ' ')

echo "Waves done:     $DONE_WAVES / 25"
echo "Waves partial:  $PARTIAL_WAVES / 25"
echo "Waves total:    $TOTAL_WAVES / 25"
echo ""
echo "Tasks done:     ~$((DONE_WAVES * 4)) / 100"
echo ""

# Last 5 waves
echo "═══════════════════════════════════════════════════════"
echo "  Last 5 waves"
echo "═══════════════════════════════════════════════════════"
find "$STATE_DIR" -name "wave-*.json" -type f | sort | tail -5 | while read f; do
    WAVE=$(jq -r '.wave' "$f" 2>/dev/null || echo "?")
    STATUS=$(jq -r '.status' "$f" 2>/dev/null || echo "?")
    TIMESTAMP=$(jq -r '.timestamp_end // .timestamp' "$f" 2>/dev/null || echo "?")
    echo "  S$WAVE  $STATUS  $TIMESTAMP"
done

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Gates (última verificação)"
echo "═══════════════════════════════════════════════════════"

cd "$SCRIPT_DIR/../../../backend" 2>/dev/null && {
    echo ""
    echo "  pytest:"
    uv run pytest --no-cov -q 2>&1 | grep -E "(passed|failed|error)" | head -3 | sed 's/^/    /'
    echo ""
    echo "  mypy:"
    uv run mypy app/ 2>&1 | tail -1 | sed 's/^/    /'
    echo ""
    echo "  ruff:"
    uv run ruff check . 2>&1 | tail -1 | sed 's/^/    /'
} || echo "  (backend dir not accessible)"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Next steps"
echo "═══════════════════════════════════════════════════════"
NEXT_WAVE=$((DONE_WAVES + PARTIAL_WAVES))
if [[ $NEXT_WAVE -lt 25 ]]; then
    echo "  Next wave: S$NEXT_WAVE"
    echo "  Run: bash .harness/loop-engineer/super-loop/master-loop-v25.sh $NEXT_WAVE"
else
    echo "  ALL WAVES DONE! 🎉"
fi
echo ""