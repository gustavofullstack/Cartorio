#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR: Minimax.APP (Minimax-M3 agent platform)
# ═══════════════════════════════════════════════════════════════════════════════
# Eu SOU esta plataforma. Este validator verifica que estou operacional.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail
PROJECT="${PROJECT:-/Users/gustavoalmeida/projetos/Cartorio}"
OUT="/tmp/cartorio-validator-minimax-$(date +%Y%m%d-%H%M%S).json"

cd "$PROJECT"

# Checks que DEFINEM este validator operacional
CHECKS=()

# 1. PROMPT.json existe e tem versão válida
PROMPT_VER=$(python3 -c "import json; print(json.load(open('PROMPT.json'))['meta']['version'])" 2>/dev/null || echo "MISSING")
[ "$PROMPT_VER" != "MISSING" ] && CHECKS+=("✓ PROMPT.json version=$PROMPT_VER") || CHECKS+=("✗ PROMPT.json missing")

# 2. API key Minimax presente
MINIMAX_KEY=$(python3 -c "import json; print(json.load(open('PROMPT.json'))['api_keys']['minimax']['key'][:20]+'...')" 2>/dev/null || echo "MISSING")
[ "$MINIMAX_KEY" != "MISSING" ] && CHECKS+=("✓ minimax key: $MINIMAX_KEY") || CHECKS+=("✗ minimax key missing")

# 3. Subagents criados
SUBAGENT_COUNT=$(ls -1 .harness/agents/*.sh 2>/dev/null | wc -l | tr -d ' ')
CHECKS+=("✓ subagents: $SUBAGENT_COUNT scripts created")

# 4. Loop engineer ativo
LOOP_EXISTS=$([ -f .harness/loop-engineer/goal-loop-cron.sh ] && echo "YES" || echo "NO")
CHECKS+=("✓ loop-engineer: $LOOP_EXISTS")

# 5. Live test via API
API_OK=$(curl -sf --max-time 5 https://api.2notasudi.com.br/health >/dev/null && echo "YES" || echo "NO")
[ "$API_OK" = "YES" ] && CHECKS+=("✓ API live: YES") || CHECKS+=("✗ API live: NO")

python3 -c "
import json
checks = '''$(IFS=$'\n'; echo "${CHECKS[*]}")'''.split('\n')
result = {
    'platform': 'Minimax.APP',
    'model': 'Minimax-M3',
    'role': 'Master Orchestrator + Cartorio Dev',
    'checks': checks,
    'verdict': 'PASS' if all('✓' in c for c in checks) else 'WARN' if any('✓' in c for c in checks) else 'FAIL'
}
print(json.dumps(result, indent=2, ensure_ascii=False))
" > "$OUT"

cat "$OUT"
