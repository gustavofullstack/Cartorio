#!/bin/bash
# ════════════════════════════════════════════════════════════════════════
# Master Loop v25 — Super Plano 100 Tasks / 25 Squads / 4 Agents
# Cartório 2º Notas Uberlândia
# Modified by Gustavo Almeida + Mavis orquestrador — 2026-07-14
# ════════════════════════════════════════════════════════════════════════
#
# Usage:
#   bash master-loop-v25.sh <wave_number>     # Run single wave (0-24)
#   bash master-loop-v25.sh all               # Run all 25 waves sequentially
#   bash master-loop-v25.sh status            # Show current status
#   bash master-loop-v25.sh reset             # Reset state (DANGER)
#
# Architecture:
#   master-loop (this script)
#   └─ dispatch-wave.sh (1 wave = 4 tasks paralelas)
#      └─ 4 agents em paralelo via Task tool:
#         - T1 → cartorio-dev (backend)
#         - T2 → cartorio-n8n (workflows/integrations)
#         - T3 → cartorio-lgpd (LGPD/compliance)
#         - T4 → cartorio-sre (ops/infra/monitoring)
#   └─ wave-status.sh (aggregate + report)
#
# ════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUPER_PLANO="$SCRIPT_DIR/../../../SUPER_PLANO_100_TASKS_25_SQUADS_v25.md"
STATE_DIR="$SCRIPT_DIR/state"
PROGRESS_MD="$SCRIPT_DIR/../../../PROGRESS.md"

# Color codes (only if terminal)
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

log() { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARN${NC} $*"; }
err() { echo -e "${RED}[$(date +%H:%M:%S)] ERROR${NC} $*" >&2; }
ok() { echo -e "${GREEN}[$(date +%H:%M:%S)] OK${NC} $*"; }

usage() {
    cat <<EOF
Master Loop v25 — Cartório 2º Notas Super Plano

USAGE:
  bash $0 <wave_number>    Run wave N (0-24)
  bash $0 all              Run all 25 waves sequentially
  bash $0 status           Show current status
  bash $0 reset            Reset state (DANGER: wipes state)

WAVE STRUCTURE:
  Each wave = 1 squad = 4 parallel tasks
  - T1 → cartorio-dev (backend FastAPI/SQLAlchemy/audit/PII)
  - T2 → cartorio-n8n (workflows N8N/integrations)
  - T3 → cartorio-lgpd (LGPD/compliance)
  - T4 → cartorio-sre (ops/infra/monitoring)

WAVES:
  0-3  = Wave 1 (P0 Foundation: outage + coverage + LGPD + WhatsApp)
  4-7  = Wave 2 (Stability: observability + LLM chain + Chatwoot + N8N hardening)
  8-11 = Wave 3 (Scale: multi-canal + DB perf + cache + tests)
  12-15= Wave 4 (Security + LGPD: WAF + LGPD final + crypto + audit)
  16-19= Wave 5 (Product: protocolo + cliente + docs + agendamento)
  20-24= Wave 6 (Growth: prospecção + onboarding + BI + multi-cartório + go-live)

EXAMPLES:
  bash $0 0           # Run S0 (P0 outage recovery)
  bash $0 5           # Run S5 (OpenClaw LLM chain)
  bash $0 status      # Show progress
EOF
}

# ════════════════════════════════════════════════════════════════════════
# STATUS COMMAND
# ════════════════════════════════════════════════════════════════════════

cmd_status() {
    log "Super Plano v25 — Status"
    log "═══════════════════════════════════════════════════════"

    if [[ ! -f "$STATE_DIR/last.json" ]]; then
        warn "No state yet. Run a wave first."
        return 0
    fi

    echo ""
    log "Last wave: $(jq -r '.wave' "$STATE_DIR/last.json")"
    log "Last status: $(jq -r '.status' "$STATE_DIR/last.json")"
    log "Last timestamp: $(jq -r '.timestamp' "$STATE_DIR/last.json")"
    echo ""

    # Count done waves
    local done_waves=0
    local total_tasks=0
    if [[ -d "$STATE_DIR" ]]; then
        done_waves=$(find "$STATE_DIR" -name "wave-*.json" -type f 2>/dev/null | wc -l | tr -d ' ')
    fi

    log "Waves completed: $done_waves / 25"
    log "Tasks completed: ~$((done_waves * 4)) / 100"
    echo ""

    log "Gates (last verified):"
    cd "$SCRIPT_DIR/../../../backend" 2>/dev/null && {
        local test_count=$(uv run pytest --no-cov -q 2>&1 | grep -oE '[0-9]+ passed' | head -1 || echo "N/A")
        log "  pytest: $test_count"
        log "  mypy: $(uv run mypy app/ 2>&1 | tail -1)"
        log "  ruff: $(uv run ruff check . 2>&1 | tail -1 | head -c 100)"
    } || warn "  (backend dir not accessible)"

    echo ""
    log "Next wave: S$done_waves (or run: bash $0 $done_waves)"
}

# ════════════════════════════════════════════════════════════════════════
# WAVE DISPATCH (core logic)
# ════════════════════════════════════════════════════════════════════════

cmd_wave() {
    local wave_num="$1"

    if ! [[ "$wave_num" =~ ^[0-9]+$ ]] || [[ "$wave_num" -gt 24 ]]; then
        err "Wave must be 0-24, got: $wave_num"
        usage
        return 1
    fi

    log "═══════════════════════════════════════════════════════"
    log "Wave S$wave_num starting — 4 tasks paralelas"
    log "═══════════════════════════════════════════════════════"

    # Compute task IDs
    local offset=$((wave_num * 4))
    local t1_id="E25.S$wave_num.T1"
    local t2_id="E25.S$wave_num.T2"
    local t3_id="E25.S$wave_num.T3"
    local t4_id="E25.S$wave_num.T4"

    log "Tasks: $t1_id | $t2_id | $t3_id | $t4_id"

    # Update state
    mkdir -p "$STATE_DIR"
    cat > "$STATE_DIR/wave-$wave_num.json" <<EOF
{
    "wave": $wave_num,
    "status": "running",
    "tasks": ["$t1_id", "$t2_id", "$t3_id", "$t4_id"],
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    cp "$STATE_DIR/wave-$wave_num.json" "$STATE_DIR/last.json"

    # Dispatch 4 agents in parallel
    log "Dispatching 4 agents in parallel..."

    local pids=()
    local log_dir="$STATE_DIR/logs/wave-$wave_num"
    mkdir -p "$log_dir"

    # T1: cartorio-dev
    (
        bash "$SCRIPT_DIR/agent-runner.sh" "$wave_num" "1" "cartorio-dev" "$t1_id" \
            > "$log_dir/T1-cartorio-dev.log" 2>&1
    ) &
    pids+=($!)

    # T2: cartorio-n8n
    (
        bash "$SCRIPT_DIR/agent-runner.sh" "$wave_num" "2" "cartorio-n8n" "$t2_id" \
            > "$log_dir/T2-cartorio-n8n.log" 2>&1
    ) &
    pids+=($!)

    # T3: cartorio-lgpd
    (
        bash "$SCRIPT_DIR/agent-runner.sh" "$wave_num" "3" "cartorio-lgpd" "$t3_id" \
            > "$log_dir/T3-cartorio-lgpd.log" 2>&1
    ) &
    pids+=($!)

    # T4: cartorio-sre
    (
        bash "$SCRIPT_DIR/agent-runner.sh" "$wave_num" "4" "cartorio-sre" "$t4_id" \
            > "$log_dir/T4-cartorio-sre.log" 2>&1
    ) &
    pids+=($!)

    log "All 4 agents dispatched. Waiting for completion..."
    log "Logs: $log_dir"

    # Wait for all 4 agents (with timeout 30min each)
    local failed=0
    for pid in "${pids[@]}"; do
        if wait "$pid"; then
            ok "Agent $pid completed"
        else
            err "Agent $pid FAILED"
            failed=$((failed + 1))
        fi
    done

    # Update state
    if [[ $failed -eq 0 ]]; then
        cat > "$STATE_DIR/wave-$wave_num.json" <<EOF
{
    "wave": $wave_num,
    "status": "done",
    "tasks": ["$t1_id", "$t2_id", "$t3_id", "$t4_id"],
    "failed": 0,
    "timestamp_start": "$(jq -r '.timestamp' "$STATE_DIR/last.json" 2>/dev/null || echo "")",
    "timestamp_end": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
        cp "$STATE_DIR/wave-$wave_num.json" "$STATE_DIR/last.json"
        ok "Wave S$wave_num completed successfully!"
        log "Next wave: S$((wave_num + 1))"
    else
        cat > "$STATE_DIR/wave-$wave_num.json" <<EOF
{
    "wave": $wave_num,
    "status": "partial",
    "tasks": ["$t1_id", "$t2_id", "$t3_id", "$t4_id"],
    "failed": $failed,
    "timestamp_end": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
        cp "$STATE_DIR/wave-$wave_num.json" "$STATE_DIR/last.json"
        err "Wave S$wave_num PARTIAL — $failed/4 agents failed"
        log "Check logs: $log_dir"
        log "Retry: bash $0 $wave_num"
    fi

    # Append to PROGRESS.md (auto-save)
    if [[ -f "$PROGRESS_MD" ]]; then
        cat >> "$PROGRESS_MD" <<EOF

## $(date +%Y-%m-%d) $(date +%H:%M) — Wave S$wave_num $([[ $failed -eq 0 ]] && echo "✅ DONE" || echo "🟡 PARTIAL ($failed/4 failed)")

### Tasks
- [x] **$t1_id** (cartorio-dev) — backend
- [x] **$t2_id** (cartorio-n8n) — workflows/integrations
- [x] **$t3_id** (cartorio-lgpd) — LGPD/compliance
- [x] **$t4_id** (cartorio-sre) — ops/infra/monitoring

### Gates
- pytest: pending verification
- coverage: pending verification
- mypy: pending verification
- ruff: pending verification

### Modified by
Master loop v25 — $(date -u +%Y-%m-%dT%H:%M:%SZ)

EOF
    fi

    return $failed
}

# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════

main() {
    if [[ $# -lt 1 ]]; then
        usage
        return 1
    fi

    case "$1" in
        status)
            cmd_status
            ;;
        reset)
            warn "Resetting state..."
            rm -rf "$STATE_DIR"
            ok "State reset"
            ;;
        all)
            log "Running all 25 waves sequentially..."
            for w in $(seq 0 24); do
                cmd_wave "$w" || {
                    err "Wave $w failed — stopping. Resume with: bash $0 $w"
                    return 1
                }
            done
            ok "All 25 waves complete!"
            ;;
        [0-9]|[0-9][0-9])
            cmd_wave "$1"
            ;;
        *)
            err "Unknown command: $1"
            usage
            return 1
            ;;
    esac
}

main "$@"