#!/usr/bin/env bash
# 03-fix-agent — FASE FIX
set -uo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
OUT="/tmp/cartorio-fix-$(date +%Y%m%d-%H%M%S).json"

FIXES_APPLIED=""
FIXES_REJECTED=""

# FIX 1: Install missing deps (check + install)
cd "$PROJECT/backend"
if ! source .venv/bin/activate 2>/dev/null && python -c "import fakeredis" 2>/dev/null; then
  cd "$PROJECT" && uv pip install fakeredis pytest-asyncio 2>&1 | tail -1 >/dev/null
  FIXES_APPLIED="${FIXES_APPLIED}deps_install,"
fi
cd "$PROJECT"

# FIX 2: ruff auto-fix safe rules (E,W,F)
cd "$PROJECT/backend"
RUFF_FIX=$(source .venv/bin/activate && ruff check app/ --select E,W,F --fix 2>&1 | tail -1 || true)
if echo "$RUFF_FIX" | grep -qE "fixed|reformatted"; then
  FIXES_APPLIED="${FIXES_APPLIED}ruff_autofix_safe,"
fi
cd "$PROJECT"

# FIX 3: format code
cd "$PROJECT/backend"
RUFF_FMT=$(source .venv/bin/activate && ruff format app/ 2>&1 | tail -1 || true)
if echo "$RUFF_FMT" | grep -qE "[0-9]+ files"; then
  FIXES_APPLIED="${FIXES_APPLIED}ruff_format,"
fi
cd "$PROJECT"

# FIXES_REJECTED: anything user-gated or destructive (commit/push/rotate-key)
FIXES_REJECTED="rotate_keys,git_push,auto_commit,delete_db,force_redeploy"

# Strip trailing comma
FIXES_APPLIED=$(echo "$FIXES_APPLIED" | sed 's/,$//')

cat > "$OUT" <<JSON_EOF
{
  "agent": "03-fix-agent",
  "phase": "fix",
  "fixes_applied": "$FIXES_APPLIED",
  "fixes_rejected": "$FIXES_REJECTED",
  "policy": "min_viable_safe_only",
  "ready_for_commit": true,
  "ready_for_push": false
}
JSON_EOF

cat "$OUT"
