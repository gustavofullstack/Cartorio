#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# INTENSIVE MODE — While Gustavo is away (runs every 30min)
# ═══════════════════════════════════════════════════════════════════════════════
set -uo pipefail
PROJECT="/Users/gustavoalmeida/projetos/Cartorio"
LOG_DIR="/tmp/cartorio-while-away"
mkdir -p "$LOG_DIR"
INTENSIVE_LOG="$LOG_DIR/intensive-$(date +%Y%m%d-%H%M).log"

cd "$PROJECT/backend"

echo "═══ INTENSIVE TICK $(date) ═══" > "$INTENSIVE_LOG"

# 1. ruff
RUFF=$(source .venv/bin/activate 2>/dev/null && ruff check app/ 2>&1 | tail -1 || echo "RUFF_FAIL")
echo "ruff: $RUFF" >> "$INTENSIVE_LOG"

# 2. pytest (quick mode, no coverage for speed)
PYTEST=$(source .venv/bin/activate 2>/dev/null && python -m pytest --no-cov -q --tb=no 2>&1 | tail -1 || echo "PYTEST_FAIL")
echo "pytest: $PYTEST" >> "$INTENSIVE_LOG"

# 3. API health
API_HEALTH=$(curl -sf --max-time 5 https://api.2notasudi.com.br/health 2>/dev/null || echo "API_DOWN")
echo "api: $API_HEALTH" >> "$INTENSIVE_LOG"

# 4. Telegram bot warmup (1 ping)
TGBOT=$(curl -sf --max-time 5 https://api.2notasudi.com.br/api/v1/health/integracoes 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_services', 'unknown'))" 2>/dev/null || echo "0")
echo "services: $TGBOT total" >> "$INTENSIVE_LOG"

cd "$PROJECT"

# 5. Auto-fix trivial issues (only if safe)
if grep -q "All checks passed" <<< "$RUFF" && grep -q "passed" <<< "$PYTEST"; then
    echo "VERDICT: PASS" >> "$INTENSIVE_LOG"
else
    echo "VERDICT: FAIL - triggering fix" >> "$INTENSIVE_LOG"
    bash .harness/agents/03-fix-agent.sh >> "$INTENSIVE_LOG" 2>&1
fi

tail -8 "$INTENSIVE_LOG"
