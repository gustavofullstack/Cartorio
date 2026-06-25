#!/bin/bash
# =============================================================================
# FIX OpenClaw: adicionar modelo minimax-m3 ao models.json
# (exit 78 = modelo nao encontrado no provider)
# =============================================================================

set -euo pipefail

OPENCLAW_DIR="/etc/easypanel/projects/cartorio/openclaw-gateway/volumes/config/agents/main/agent"
MODELS_JSON="${OPENCLAW_DIR}/models.json"
AGENT_JSON="${OPENCLAW_DIR}/agent.json"
BACKUP_DIR="/home/easypanel/backups/openclaw_minimax3_fix_$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "FIX OpenClaw: minimax-m3 + agent.json"
echo "=========================================="

# 1. SSH connectivity check
echo "[1/6] Verificando conectividade SSH via alias 'cartorio'..."
if ! ssh -o ConnectTimeout=5 cartorio "echo OK" >/dev/null 2>&1; then
    echo "❌ Falha ao conectar via alias 'cartorio'"
    exit 1
fi
echo "  ✅ SSH OK"

# 2. Backup dos arquivos
echo "[2/6] Criando backup em ${BACKUP_DIR}..."
ssh cartorio "mkdir -p ${BACKUP_DIR} && cp ${MODELS_JSON} ${BACKUP_DIR}/models.json.bak && cp ${AGENT_JSON} ${BACKUP_DIR}/agent.json.bak"

# 3. Verificar estado ANTES
echo "[3/6] Estado ANTES:"
ssh cartorio "python3 -c 'import json; d=json.load(open(\"${MODELS_JSON}\")); oc=d[\"providers\"].get(\"opencode_go\",{}); print(\"  opencode_go models:\", [m[\"id\"] for m in oc.get(\"models\", [])])'"

# 4. Adicionar minimax-m3 ao models.json
echo "[4/6] Adicionando minimax-m3 ao models.json..."
ssh cartorio "python3 << 'PYEOF'
import json
from pathlib import Path

models_path = Path('${MODELS_JSON}')
data = json.loads(models_path.read_text())

oc = data.get('providers', {}).get('opencode_go', {})
existing_ids = [m['id'] for m in oc.get('models', [])]

if 'minimax-m3' not in existing_ids:
    # Encontrar o config do deepseek-v4-flash para clonar
    deepseek_cfg = None
    for m in oc.get('models', []):
        if m['id'] == 'deepseek-v4-flash':
            deepseek_cfg = m.copy()
            break

    if deepseek_cfg:
        new_model = {
            'id': 'minimax-m3',
            'name': 'Minimax M3 (OpenCode-Go, 1M context)',
            'reasoning': True,
            'input': ['text'],
            'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'contextWindow': 1048576,  # 1M
            'maxTokens': 32000,
            'compat': {
                'supportsReasoningEffort': True,
                'supportsUsageInStreaming': True,
                'supportsAdaptiveThinking': True,
            },
        }
        oc.setdefault('models', []).append(new_model)
        models_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f'  + minimax-m3 added (contextWindow=1048576)')
    else:
        print('  ! deepseek-v4-flash not found — skipping')
else:
    print('  = minimax-m3 already present')
PYEOF"

# 5. Atualizar agent.json para usar minimax-m3
echo "[5/6] Atualizando agent.json para usar minimax-m3..."
ssh cartorio "python3 << 'PYEOF'
import json
from pathlib import Path

agent_path = Path('${AGENT_JSON}')
data = json.loads(agent_path.read_text())

current_model = data.get('model', '')
if current_model != 'minimax-m3':
    data['model'] = 'minimax-m3'
    agent_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f'  ~ model: {current_model} -> minimax-m3')
else:
    print('  = model already minimax-m3')
PYEOF"

# 6. Restart e validar
echo "[6/6] Restart do container + validacao..."
ssh cartorio "docker service update --force cartorio_openclaw-gateway 2>&1 || echo 'Service nao existe — precisa recriar via Easypanel UI'"
sleep 20

echo ""
echo "Verificacao via API:"
for i in 1 2 3; do
    HEALTH=$(curl -sk -o /dev/null -w '%{http_code}' https://agent.2notasudi.com.br/health 2>/dev/null)
    echo "  Tentativa $i: OpenClaw /health: $HEALTH"
    if [ "$HEALTH" = "200" ]; then
        echo "  ✅ RECOVERY BEM-SUCEDIDO!"
        break
    fi
    sleep 15
done

echo ""
echo "Radar status:"
curl -sk "https://api.2notasudi.com.br/api/v1/health/radar" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  Status: {d[\"status\"]}')
for k, v in d['services'].items():
    print(f'    {k:12s}: {v}')"
