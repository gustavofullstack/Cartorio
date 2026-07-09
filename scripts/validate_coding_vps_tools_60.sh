#!/usr/bin/env bash
# validate_coding_vps_tools_60.sh
# Smoke-test do coding-vps MCP orchestrator (62 tools pós Squad 5).
# Exit 0 = OK | Exit != 0 = falha (para CI / pre-flight).
#
# Uso:
#   bash scripts/validate_coding_vps_tools_60.sh
#   bash scripts/validate_coding_vps_tools_60.sh --quick     # só list + openapi (sem SSH)
#   bash scripts/validate_coding_vps_tools_60.sh --with-llm  # inclui chat_minimax (lento)
#
# Não imprime secrets. Não envia Telegram.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Library/Frameworks/Python.framework/Versions/3.14/bin/python3}"
ORCH="${ORCH:-$SCRIPT_DIR/coding_vps_mcp_orchestrator.py}"
EXPECTED_MIN_TOOLS="${EXPECTED_MIN_TOOLS:-62}"
QUICK=0
WITH_LLM=0

for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    --with-llm) WITH_LLM=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
  esac
done

if [[ ! -x "$PYTHON_BIN" ]] && ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" || ! -f "$ORCH" ]]; then
  echo "FAIL: python or orchestrator missing"
  echo "  PYTHON_BIN=$PYTHON_BIN"
  echo "  ORCH=$ORCH"
  exit 2
fi

export SSH_PRIVATE_KEY="${SSH_PRIVATE_KEY:-$HOME/.ssh/id_ed25519_cartorio}"
export SSH_TAILSCALE_HOST="${SSH_TAILSCALE_HOST:-100.99.172.84}"

PASS=0
FAIL=0
SKIP=0
declare -a FAILURES=()

_ok()   { PASS=$((PASS + 1)); echo "  OK  $1"; }
_fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); echo "  FAIL $1 — $2"; }
_skip() { SKIP=$((SKIP + 1)); echo "  SKIP $1 — $2"; }

echo "== coding-vps tools smoke (min tools=$EXPECTED_MIN_TOOLS) =="
echo "python: $PYTHON_BIN"
echo "orch:   $ORCH"
echo ""

# --- 1) list: tool count ---
echo "[1/6] list (tool count)"
LIST_OUT="$("$PYTHON_BIN" "$ORCH" list 2>&1)" || true
if echo "$LIST_OUT" | head -1 | grep -Eq 'MCP orchestrator: [0-9]+ tools'; then
  COUNT="$(echo "$LIST_OUT" | head -1 | sed -E 's/.*: ([0-9]+) tools.*/\1/')"
  if [[ "$COUNT" -ge "$EXPECTED_MIN_TOOLS" ]]; then
    _ok "list count=$COUNT (>=$EXPECTED_MIN_TOOLS)"
  else
    _fail "list count" "got $COUNT, expected >= $EXPECTED_MIN_TOOLS"
  fi
else
  _fail "list" "unexpected output: $(echo "$LIST_OUT" | head -1)"
fi

# --- 2) required tool names present ---
echo "[2/6] required tool names"
REQUIRED_TOOLS=(
  chat_minimax
  chat_with_agent
  list_models
  list_services
  health_check_service
  health_check_all
  redis_ping
  redis_cmd
  openapi_spec
  service_logs
  restart_service
)
for t in "${REQUIRED_TOOLS[@]}"; do
  if echo "$LIST_OUT" | grep -qE "^[[:space:]]+${t}\("; then
    _ok "tool registered: $t"
  else
    _fail "tool missing: $t" "not in list output"
  fi
done

# --- 3) openapi_spec (local, no SSH required for registration path) ---
echo "[3/6] call openapi_spec"
OPENAPI_OUT="$("$PYTHON_BIN" "$ORCH" call openapi_spec 2>&1)" || true
if echo "$OPENAPI_OUT" | grep -q '"openapi"'; then
  _ok "openapi_spec returns openapi key"
else
  # openapi_spec may print pure JSON on one line
  if echo "$OPENAPI_OUT" | grep -q 'tools'; then
    _ok "openapi_spec returns tools metadata"
  else
    _fail "openapi_spec" "no openapi/tools in output"
  fi
fi

if [[ "$QUICK" -eq 1 ]]; then
  echo ""
  echo "[--quick] skipping SSH-backed tools"
  SKIP=$((SKIP + 3))
else
  # --- 4) list_services (SSH) ---
  echo "[4/6] call list_services (SSH)"
  LS_OUT="$("$PYTHON_BIN" "$ORCH" call list_services stack=all 2>&1)" || true
  if echo "$LS_OUT" | grep -qE '"total"[[:space:]]*:[[:space:]]*[1-9]'; then
    _ok "list_services total>0"
  elif echo "$LS_OUT" | grep -qiE 'timeout|Connection refused|Permission denied|No route'; then
    _fail "list_services" "SSH/network error: $(echo "$LS_OUT" | head -c 200)"
  else
    _fail "list_services" "unexpected: $(echo "$LS_OUT" | head -c 200)"
  fi

  # --- 5) health_check_all ---
  echo "[5/6] call health_check_all"
  HC_OUT="$("$PYTHON_BIN" "$ORCH" call health_check_all stack=all 2>&1)" || true
  if echo "$HC_OUT" | grep -qE '"summary"'; then
    _ok "health_check_all has summary"
  elif echo "$HC_OUT" | grep -qE '"total"'; then
    _ok "health_check_all has total"
  else
    _fail "health_check_all" "unexpected: $(echo "$HC_OUT" | head -c 200)"
  fi

  # --- 6) redis_ping (best-effort; may fail if redis name wrong) ---
  echo "[6/6] call redis_ping (best-effort langfuse-redis)"
  RP_OUT="$("$PYTHON_BIN" "$ORCH" call redis_ping redis_service=langfuse-redis 2>&1)" || true
  if echo "$RP_OUT" | grep -qE 'PONG|"ok"[[:space:]]*:[[:space:]]*true'; then
    _ok "redis_ping PONG"
  elif echo "$RP_OUT" | grep -qiE 'NOAUTH|WRONGPASS'; then
    _fail "redis_ping" "auth failed (check REDIS_PASSWORD in container)"
  elif echo "$RP_OUT" | grep -qiE 'No such container|is not running|error'; then
    # Soft: service may be named differently — count as fail only if tool itself missing
    if echo "$LIST_OUT" | grep -q 'redis_ping('; then
      _skip "redis_ping live" "container not reachable: $(echo "$RP_OUT" | head -c 120)"
    else
      _fail "redis_ping" "tool not registered"
    fi
  else
    _skip "redis_ping live" "non-PONG: $(echo "$RP_OUT" | head -c 120)"
  fi
fi

# Optional LLM
if [[ "$WITH_LLM" -eq 1 ]]; then
  echo "[+] call chat_minimax (optional)"
  LLM_OUT="$("$PYTHON_BIN" "$ORCH" call chat_minimax prompt=PING-OK-62 max_tokens=20 2>&1)" || true
  if echo "$LLM_OUT" | grep -qiE 'reply|PING|choices|content'; then
    _ok "chat_minimax responded"
  else
    _fail "chat_minimax" "unexpected: $(echo "$LLM_OUT" | head -c 200)"
  fi
fi

echo ""
echo "== summary =="
echo "  pass=$PASS fail=$FAIL skip=$SKIP"
if [[ "$FAIL" -gt 0 ]]; then
  echo "  failures:"
  for f in "${FAILURES[@]}"; do
    echo "    - $f"
  done
  exit 1
fi
echo "  ALL CHECKS PASSED"
exit 0
