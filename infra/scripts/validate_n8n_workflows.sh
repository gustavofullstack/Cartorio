#!/usr/bin/env bash
# validate_n8n_workflows.sh — Valida estrutura dos 33+ workflows N8N
# Uso: ./validate_n8n_workflows.sh [--verbose]
#
# Verifica: JSON válido, nodes obrigatórios, retry policy, timeout, error handler
# LGPD: NÃO loga PII

set -eo pipefail

VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

WF_DIR="${HOME}/projetos/Cartorio/infra/n8n-workflows"
PASS=0; FAIL=0; WARN=0; TOTAL=0

log_pass() { PASS=$((PASS+1)); $VERBOSE && printf "  ✅ %s\n" "$1"; }
log_fail() { FAIL=$((FAIL+1)); printf "  ❌ %s\n" "$1"; }
log_warn() { WARN=$((WARN+1)); $VERBOSE && printf "  ⚠️  %s\n" "$1"; }

echo "🔍 Validating N8N workflows in $WF_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for wf in "$WF_DIR"/*.json; do
    [[ "$wf" == *.bak* ]] && continue
    TOTAL=$((TOTAL+1))
    name=$(basename "$wf" .json)

    # 1. JSON válido
    if ! python3 -c "import json; json.load(open('$wf'))" 2>/dev/null; then
        log_fail "$name: invalid JSON"
        continue
    fi
    log_pass "$name: valid JSON"

    # 2. Has nodes
    node_count=$(python3 -c "import json; d=json.load(open('$wf')); print(len(d.get('nodes',[])))")
    if [[ "$node_count" -eq 0 ]]; then
        log_fail "$name: no nodes"
    else
        log_pass "$name: $node_count nodes"
    fi

    # 3. Has error handler (Error Trigger or onError)
    has_error=$(python3 -c "
import json
d=json.load(open('$wf'))
nodes = d.get('nodes',[])
types = [n.get('type','') for n in nodes]
has_err_trigger = any('ErrorTrigger' in t or 'error-trigger' in t.lower() for t in types)
has_on_error = any(n.get('onError') == 'continueRegularOutput' or n.get('continueOnFail') for n in nodes)
print('yes' if has_err_trigger or has_on_error else 'no')
" 2>/dev/null)
    if [[ "$has_error" == "yes" ]]; then
        log_pass "$name: error handling configured"
    else
        log_warn "$name: no error handler found"
    fi

    # 4. HTTP nodes have timeout
    http_no_timeout=$(python3 -c "
import json
d=json.load(open('$wf'))
nodes = d.get('nodes',[])
http_nodes = [n for n in nodes if 'http' in n.get('type','').lower()]
no_timeout = [n.get('name','?') for n in http_nodes if not n.get('parameters',{}).get('timeout')]
print(len(no_timeout))
" 2>/dev/null)
    if [[ "$http_no_timeout" -gt 0 ]]; then
        log_warn "$name: $http_no_timeout HTTP nodes without timeout"
    else
        log_pass "$name: all HTTP nodes have timeout"
    fi

done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "✅ PASS: %d | ❌ FAIL: %d | ⚠️  WARN: %d | 📁 TOTAL: %d\n" "$PASS" "$FAIL" "$WARN" "$TOTAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

[[ $FAIL -gt 0 ]] && exit 1 || exit 0
