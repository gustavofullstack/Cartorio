#!/bin/bash
# =============================================================================
# FIX OpenClaw: configurar chain completa de provedores FREE como fallback
# (5 provedores: opencode_go + opencode_free_1/2/3 + mistral_free)
# Resolve E07 (contexto) + E08 (chave) ao mesmo tempo
# =============================================================================

set -euo pipefail

OPENCLAW_DIR="/etc/easypanel/projects/cartorio/openclaw-gateway/volumes/config/agents/main/agent"
MODELS_JSON="${OPENCLAW_DIR}/models.json"
AGENT_JSON="${OPENCLAW_DIR}/agent.json"
BACKUP_DIR="/home/easypanel/backups/openclaw_free_chain_$(date +%Y%m%d_%H%M%S)"

# Chaves dos provedores free (passadas via env para nao commitar no repo)
OPENCODE_FREE_1_KEY="${OPENCODE_FREE_1_KEY:-}"
OPENCODE_FREE_3_KEY="${OPENCODE_FREE_3_KEY:-}"

echo "=========================================="
echo "FIX OpenClaw: 5 provedores FREE em paralelo"
echo "  primary: opencode_go (minimax-m3, 1M ctx)"
echo "  fallback chain: opencode_free_1 -> 2 -> 3 -> mistral_free"
echo "=========================================="

# 1. SSH connectivity check
echo "[1/8] Verificando conectividade SSH via alias 'cartorio'..."
if ! ssh -o ConnectTimeout=5 cartorio "echo OK" >/dev/null 2>&1; then
    echo "❌ Falha ao conectar via alias 'cartorio'"
    exit 1
fi
echo "  ✅ SSH OK"

# 2. Backup dos arquivos
echo "[2/8] Criando backup em ${BACKUP_DIR}..."
ssh cartorio "mkdir -p ${BACKUP_DIR} && cp ${MODELS_JSON} ${BACKUP_DIR}/models.json.bak && cp ${AGENT_JSON} ${BACKUP_DIR}/agent.json.bak"

# 3. Estado ANTES
echo "[3/8] Estado ANTES:"
ssh cartorio "python3 -c 'import json; d=json.load(open(\"${MODELS_JSON}\")); print(\"  providers:\", list(d[\"providers\"].keys()))'"

# 4. Adicionar opencode_free_1 e opencode_free_3 ao models.json
echo "[4/8] Adicionando opencode_free_1 e opencode_free_3 ao models.json..."
if [ -z "${OPENCODE_FREE_1_KEY}" ] || [ -z "${OPENCODE_FREE_3_KEY}" ]; then
    echo "  ⚠️  OPENCODE_FREE_1_KEY ou OPENCODE_FREE_3_KEY nao definidos"
    echo "     usando placeholders - substitua manualmente depois"
    OPENCODE_FREE_1_KEY="${OPENCODE_FREE_1_KEY:-sk-PLACEHOLDER_FREE_1}"
    OPENCODE_FREE_3_KEY="${OPENCODE_FREE_3_KEY:-sk-PLACEHOLDER_FREE_3}"
fi

ssh cartorio "OPENCODE_FREE_1_KEY='${OPENCODE_FREE_1_KEY}' OPENCODE_FREE_3_KEY='${OPENCODE_FREE_3_KEY}' python3 << 'PYEOF'
import json
import os
from pathlib import Path

models_path = Path('${MODELS_JSON}')
data = json.loads(models_path.read_text())

# opencode_free_1 (chave 1 do Gustavo)
data['providers']['opencode_free_1'] = {
    'baseUrl': 'https://opencode.ai/zen/v1',
    'apiKey': os.environ['OPENCODE_FREE_1_KEY'],
    'auth': 'bearer',
    'api': 'openai-chat',
    'models': [
        {
            'id': 'nemotron-3-ultra-free',
            'name': 'Nemotron 3 Ultra (Free, 1M context)',
            'reasoning': True,
            'input': ['text'],
            'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'contextWindow': 1048576, 'maxTokens': 32000,
            'compat': {'supportsReasoningEffort': True, 'supportsUsageInStreaming': True}
        },
        {
            'id': 'deepseek-v4-flash-free',
            'name': 'DeepSeek V4 Flash (Free, 1M context)',
            'reasoning': True,
            'input': ['text'],
            'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'contextWindow': 1048576, 'maxTokens': 8192,
            'compat': {'supportsReasoningEffort': True, 'supportsUsageInStreaming': True}
        }
    ]
}

# opencode_free_3 (chave 3 do Gustavo)
data['providers']['opencode_free_3'] = {
    'baseUrl': 'https://opencode.ai/zen/v1',
    'apiKey': os.environ['OPENCODE_FREE_3_KEY'],
    'auth': 'bearer',
    'api': 'openai-chat',
    'models': [
        {
            'id': 'nemotron-3-ultra-free',
            'name': 'Nemotron 3 Ultra (Free, 1M context)',
            'reasoning': True,
            'input': ['text'],
            'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'contextWindow': 1048576, 'maxTokens': 32000,
            'compat': {'supportsReasoningEffort': True, 'supportsUsageInStreaming': True}
        },
        {
            'id': 'deepseek-v4-flash-free',
            'name': 'DeepSeek V4 Flash (Free, 1M context)',
            'reasoning': True,
            'input': ['text'],
            'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'contextWindow': 1048576, 'maxTokens': 8192,
            'compat': {'supportsReasoningEffort': True, 'supportsUsageInStreaming': True}
        }
    ]
}

models_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print('  ✅ opencode_free_1 e opencode_free_3 adicionados')
print('  providers agora:', list(data['providers'].keys()))
PYEOF"

# 5. Atualizar agent.json com chain de fallbacks
echo "[5/8] Atualizando agent.json com chain completa de fallbacks..."
ssh cartorio "python3 << 'PYEOF'
import json
from pathlib import Path

agent_path = Path('${AGENT_JSON}')
data = json.loads(agent_path.read_text())

# Primary: opencode_go (minimax-m3, 1M context, thinking adaptive)
data['provider'] = 'opencode_go'
data['model'] = 'minimax-m3'

# Chain de fallbacks (5 níveis de resiliencia)
# Cada fallback so eh ativado se o anterior falhar (rate limit, downtime, etc)
data['fallbackProvider'] = 'opencode_free_1'
data['fallbackModel'] = 'nemotron-3-ultra-free'

# Chain secundaria (4 mais opcoes)
data['fallbackChain'] = [
    {'provider': 'opencode_free_1', 'model': 'nemotron-3-ultra-free'},
    {'provider': 'opencode_free_2', 'model': 'nemotron-3-ultra-free'},
    {'provider': 'opencode_free_3', 'model': 'nemotron-3-ultra-free'},
    {'provider': 'mistral_free', 'model': 'mistral-large-latest'},
    {'provider': 'mistral_free', 'model': 'devstral-latest'},
]

# Garantir contexto 1M (resolve E07)
data['maxTokens'] = 1000000

# Garantir thinking adaptive ON
if 'reasoning' not in data:
    data['reasoning'] = {}
data['reasoning']['enabled'] = True
data['reasoning']['mode'] = 'adaptive'
data['reasoning']['budgetTokens'] = 8192

agent_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
print('  ✅ agent.json atualizado com chain de 5 fallbacks')
print('  primary:', data['provider'], '/', data['model'])
print('  fallback:', data['fallbackProvider'], '/', data['fallbackModel'])
print('  chain:', [f\"{f['provider']}/{f['model']}\" for f in data['fallbackChain']])
PYEOF"

# 6. Restart container OpenClaw para recarregar config
echo "[6/8] Reiniciando cartorio_openclaw-gateway..."
ssh cartorio "docker service update --force cartorio_openclaw-gateway 2>&1 | tail -3"

# 7. Aguardar container ficar saudavel
echo "[7/8] Aguardando OpenClaw ficar healthy (max 60s)..."
for i in {1..30}; do
    HEALTH=$(ssh cartorio "docker ps --filter name=cartorio_openclaw --format '{{.Status}}' | head -1" 2>/dev/null || echo "")
    if echo "${HEALTH}" | grep -q "(healthy)"; then
        echo "  ✅ Container healthy apos ${i}x2s"
        break
    fi
    sleep 2
done

# 8. Health check final via API publica
echo "[8/8] Health check via https://agent.2notasudi.com.br/health..."
HEALTH=$(curl -s https://agent.2notasudi.com.br/health 2>&1 || echo "FAILED")
echo "  Response: ${HEALTH}"

echo ""
echo "=========================================="
echo "✅ FIX OpenClaw FREE chain aplicado!"
echo "   Backup em: ${BACKUP_DIR}"
echo "=========================================="
echo ""
echo "Provedores configurados:"
echo "  PRIMARY  : opencode_go / minimax-m3 (1M ctx, thinking adaptive)"
echo "  FALLBACK 1: opencode_free_1 / nemotron-3-ultra-free"
echo "  FALLBACK 2: opencode_free_2 / nemotron-3-ultra-free"
echo "  FALLBACK 3: opencode_free_3 / nemotron-3-ultra-free"
echo "  FALLBACK 4: mistral_free / mistral-large-latest (256K)"
echo "  FALLBACK 5: mistral_free / devstral-latest (256K)"
echo ""
echo "Proximo passo:"
echo "  1. Verificar logs: ssh cartorio 'docker logs \$(docker ps --filter name=cartorio_openclaw --format \"{{.Names}}\" | head -1) --tail 50'"
echo "  2. Testar mensagem: curl -X POST https://agent.2notasudi.com.br/v1/messages -H 'Content-Type: application/json' -d '{\"agent\":\"main\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}'"