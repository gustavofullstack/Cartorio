#!/bin/bash
# Importa TODOS os workflows do repo infra/n8n-workflows/ para o N8N
# Uso: N8N_API_KEY=xxx ./import_all_to_n8n.sh
#
# Cria workflows como INATIVOS (active=false) para Gustavo ligar manualmente.
# Workflows que ja existem (mesmo nome) sao pulados.

set -e

N8N_URL="${N8N_URL:-https://cartorio-n8n.dfgdxq.easypanel.host}"
N8N_API_KEY="${N8N_API_KEY:?Defina N8N_API_KEY no env}"

WORKFLOWS_DIR="$(dirname "$0")"
IMPORTED=0
SKIPPED=0
FAILED=0

# Lista nomes ja existentes no N8N
EXISTING=$(curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_URL/api/v1/workflows?limit=200" | python3 -c "import json, sys; print(' '.join(w['name'] for w in json.load(sys.stdin).get('data', [])))")

for f in "$WORKFLOWS_DIR"/*.json; do
    name=$(python3 -c "import json; print(json.load(open('$f'))['name'])" 2>/dev/null)
    if [ -z "$name" ]; then
        echo "SKIP: $f (no name field)"
        continue
    fi

    # Pula se ja existe
    if echo "$EXISTING" | grep -qF "$name"; then
        echo "EXISTS: $name (skipping)"
        SKIPPED=$((SKIPPED+1))
        continue
    fi

    # Prepara body (so name/nodes/connections/settings - chaves read-only removidas)
    BODY=$(python3 -c "
import json
with open('$f') as f:
    d = json.load(f)
keep = ['name', 'nodes', 'connections', 'settings']
clean = {k: v for k, v in d.items() if k in keep}
# Adiciona Noop se referenciado em connection mas nao definido em nodes
node_ids = {n.get('id') for n in clean.get('nodes', [])}
node_names = {n.get('name') for n in clean.get('nodes', [])}
import re
def find_targets(connections):
    for src, info in connections.items():
        for output_list in info.get('main', []):
            for conn in output_list:
                if conn.get('node') not in node_names and conn.get('node') not in node_ids:
                    yield conn.get('node')

missing = set()
for conn in clean.get('connections', {}).values():
    missing.update(find_targets({'_': conn}))
for name in missing:
    if name and name not in node_names and name not in node_ids:
        clean['nodes'].append({
            'id': 'noop-' + name.lower().replace(' ', '-'),
            'name': name,
            'type': 'n8n-nodes-base.noOp',
            'typeVersion': 1,
            'position': [900, 420],
            'parameters': {}
        })
print(json.dumps(clean))
")
    RESP=$(curl -s -X POST "$N8N_URL/api/v1/workflows" \
        -H "X-N8N-API-KEY: $N8N_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$BODY")

    if echo "$RESP" | grep -q '"id"'; then
        WFID=$(echo "$RESP" | python3 -c "import json, sys; print(json.load(sys.stdin)['id'])")
        echo "IMPORTED: $name (id=$WFID)"
        IMPORTED=$((IMPORTED+1))
    else
        echo "FAILED: $name - $RESP"
        FAILED=$((FAILED+1))
    fi
done

echo
echo "=== Summary ==="
echo "Imported: $IMPORTED"
echo "Skipped (already exists): $SKIPPED"
echo "Failed: $FAILED"
