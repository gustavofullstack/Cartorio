#!/bin/bash
# ════════════════════════════════════════════════════════════════════════
# Agent Runner — Executa 1 task via claude CLI (or echo if claude missing)
# Cartório 2º Notas Super Plano v25
# Modified by Gustavo Almeida — 2026-07-14
# ════════════════════════════════════════════════════════════════════════

set -euo pipefail

WAVE="$1"
TASK_NUM="$2"   # 1-4
REIN="$3"       # cartorio-dev / cartorio-n8n / cartorio-lgpd / cartorio-sre
TASK_ID="$4"    # E25.S{n}.T{m}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPER_PLANO="$SCRIPT_DIR/../../../SUPER_PLANO_100_TASKS_25_SQUADS_v25.md"

# Color codes
if [[ -t 1 ]]; then
    BLUE='\033[0;34m'; GREEN='\033[0;32m'; NC='\033[0m'
else
    BLUE=''; GREEN=''; NC=''
fi

echo -e "${BLUE}[agent-runner]${NC} wave=$WAVE task=$TASK_NUM rein=$REIN task_id=$TASK_ID"

# Build task prompt from SUPER_PLANO
PROMPT=$(cat <<EOF
TASK: $TASK_ID
REIN: $REIN
WAVE: $WAVE

Read the SUPER_PLANO file at: $SUPER_PLANO

Find your task E25.S$WAVE.T$TASK_NUM and execute it following the AGENTS.md
workflow: analyze → test → fix → improve → optimize → document → comment → save memory.

CRITICAL RULES:
1. Branch from master: git checkout -b feat/$TASK_ID
2. Tests must pass (pytest 2800+)
3. Coverage must stay >=95%
4. Mypy must be 0 errors
5. Ruff must be 0 errors
6. Conventional Commits, end with "Modified by Gustavo Almeida"
7. Save lesson in .harness/memory/lesson-NNN-$TASK_ID-*.md
8. Append to PROGRESS.md
9. PR description should reference $TASK_ID

Return JSON: {"status": "done|failed", "commits": N, "lesson": "path", "files_modified": [...]}
EOF
)

# Try to dispatch via Task tool (claude CLI)
if command -v claude &>/dev/null; then
    echo "[agent-runner] claude CLI available, dispatching..."
    cd "$SCRIPT_DIR/../../.."
    claude --print "$PROMPT" 2>&1 || {
        echo "[agent-runner] claude failed, falling back to echo"
        echo "$PROMPT"
        exit 1
    }
else
    echo "[agent-runner] claude CLI not found, simulating task execution"
    echo "═══════════════════════════════════════════════════════"
    echo "TASK PROMPT:"
    echo "═══════════════════════════════════════════════════════"
    echo "$PROMPT"
    echo "═══════════════════════════════════════════════════════"
    echo "[agent-runner] SIMULATED — no actual execution"
    # In real production, would call claude CLI or other agent runner
    # For now, just simulate success
    echo '{"status": "simulated", "task_id": "'$TASK_ID'", "rein": "'$REIN'"}'
fi

echo -e "${GREEN}[agent-runner]${NC} task $TASK_ID dispatched"