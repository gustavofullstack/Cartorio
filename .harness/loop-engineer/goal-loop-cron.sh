#!/usr/bin/env bash
# LOOP ENGINEER · /goal auto-reactivação
set -uo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
AGENT_DIR="$PROJECT/.harness/agents"
OUT="/tmp/cartorio-loop-$(date +%Y%m%d-%H%M%S).json"

cd "$PROJECT"

RES_ANALYZE_FILE="/tmp/loop-analyze-$$.json"
RES_TEST_FILE="/tmp/loop-test-$$.json"
"$AGENT_DIR/01-analyze-agent.sh" >/dev/null 2>&1 && cp "$(ls -t /tmp/cartorio-analyze-*.json 2>/dev/null | head -1)" "$RES_ANALYZE_FILE" 2>/dev/null || echo '{"verdict":"FAIL"}' > "$RES_ANALYZE_FILE"
"$AGENT_DIR/02-test-agent.sh" >/dev/null 2>&1 && cp "$(ls -t /tmp/cartorio-test-*.json 2>/dev/null | head -1)" "$RES_TEST_FILE" 2>/dev/null || echo '{"verdict":"FAIL"}' > "$RES_TEST_FILE"

RES_ANALYZE=$(cat "$RES_ANALYZE_FILE" 2>/dev/null || echo '{"verdict":"FAIL"}')
RES_TEST=$(cat "$RES_TEST_FILE" 2>/dev/null || echo '{"verdict":"FAIL"}')

NEXT_STEP="wait"
if echo "$RES_TEST" | grep -q '"verdict": "PASS"'; then
  NEXT_STEP="paperclip_task_board"
elif echo "$RES_TEST" | grep -q '"verdict": "FAIL"'; then
  NEXT_STEP="fix_agent_then_retest"
fi

CYCLE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

cat > "$OUT" <<JSON_EOF
{
  "loop_engineer": "goal-loop-cron",
  "cycle": "$CYCLE",
  "next_step": "$NEXT_STEP",
  "results": {
    "analyze": $(cat $RES_ANALYZE_FILE),
    "test": $(cat $RES_TEST_FILE)
  },
  "auto_chain": [
    "01-analyze-agent",
    "02-test-agent",
    "03-fix-agent (if FAIL)",
    "04-document-agent (always)",
    "05-memory-agent (always)",
    "PROGRESS.md auto-update"
  ],
  "cron_install_hint": "instalar via launchd ou cron do SO quando puder"
}
JSON_EOF

cat "$OUT"
rm -f "$RES_ANALYZE_FILE" "$RES_TEST_FILE"
