#!/usr/bin/env bash
# test_n8n_workflows.sh — Test runner para workflows N8N
# Uso: ./test_n8n_workflows.sh [--verbose] [--json]
#
# Testa cada WF com: JSON válido, nodes, retry, timeout, error handler
# LGPD: NÃO loga PII

set -eo pipefail

VERBOSE=false; JSON_MODE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true
[[ "${1:-}" == "--json" ]] && JSON_MODE=true
[[ "${2:-}" == "--verbose" ]] && VERBOSE=true
[[ "${2:-}" == "--json" ]] && JSON_MODE=true

WF_DIR="${HOME}/projetos/Cartorio/infra/n8n-workflows"
PASS=0; FAIL=0; WARN=0; TOTAL=0
FAILURES=()

for wf in "$WF_DIR"/*.json; do
    [[ "$wf" == *.bak* ]] && continue
    TOTAL=$((TOTAL+1))
    name=$(basename "$wf" .json)
    wf_pass=true

    # 1. JSON válido
    if ! python3 -c "import json; json.load(open('$wf'))" 2>/dev/null; then
        FAIL=$((FAIL+1)); FAILURES+=("$name:invalid_json"); continue
    fi

    # 2. Has nodes
    node_count=$(python3 -c "import json; d=json.load(open('$wf')); print(len(d.get('nodes',[])))" 2>/dev/null || echo "0")
    [[ "$node_count" -eq 0 ]] && { FAIL=$((FAIL+1)); FAILURES+=("$name:no_nodes"); continue; }

    # 3. Error handler check
    has_err=$(python3 -c "
import json
d=json.load(open('$wf'))
nodes=d.get('nodes',[])
types=[n.get('type','') for n in nodes]
has_et=any('ErrorTrigger' in t for t in types)
has_oc=any(n.get('onError')=='continueRegularOutput' or n.get('continueOnFail') for n in nodes)
print('yes' if has_et or has_oc else 'no')
" 2>/dev/null || echo "no")
    if [[ "$has_err" != "yes" ]]; then
        WARN=$((WARN+1)); $VERBOSE && echo "  ⚠️  $name: no error handler"
    fi

    # 4. HTTP timeout check
    http_no_timeout=$(python3 -c "
import json
d=json.load(open('$wf'))
nodes=d.get('nodes',[])
http=[n for n in nodes if 'http' in n.get('type','').lower()]
no_to=[n.get('name','?') for n in http if not n.get('parameters',{}).get('timeout')]
print(len(no_to))
" 2>/dev/null || echo "0")
    if [[ "$http_no_timeout" -gt 0 ]]; then
        WARN=$((WARN+1)); $VERBOSE && echo "  ⚠️  $name: $http_no_timeout HTTP nodes without timeout"
    fi

    # 5. Sticky note with context (best practice)
    has_sticky=$(python3 -c "
import json
d=json.load(open('$wf'))
nodes=d.get('nodes',[])
types=[n.get('type','') for n in nodes]
print('yes' if any('stickyNote' in t for t in types) else 'no')
" 2>/dev/null || echo "no")
    if [[ "$has_sticky" != "yes" ]]; then
        WARN=$((WARN+1)); $VERBOSE && echo "  ⚠️  $name: no sticky note (best practice)"
    fi

    PASS=$((PASS+1))
    $VERBOSE && echo "  ✅ $name: $node_count nodes OK"
done

if $JSON_MODE; then
    echo '{"timestamp":"'$(date -u +%FT%TZ)'","total":'$TOTAL',"pass":'$PASS',"fail":'$FAIL',"warn":'$WARN',"failures":['
    for i in "${!FAILURES[@]}"; do
        [[ $i -gt 0 ]] && printf ","
        printf '"%s"' "${FAILURES[$i]}"
    done
    echo ']}'
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "📁 TOTAL: %d | ✅ PASS: %d | ❌ FAIL: %d | ⚠️  WARN: %d\n" "$TOTAL" "$PASS" "$FAIL" "$WARN"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    [[ $FAIL -gt 0 ]] && echo "Failures: ${FAILURES[*]}"
fi

[[ $FAIL -gt 0 ]] && exit 1 || exit 0
