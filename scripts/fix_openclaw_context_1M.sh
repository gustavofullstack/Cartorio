#!/bin/bash
# =============================================================================
# FIX OpenClaw Agent Context: 131k → 1M tokens
# SQUAD E — URGENTE (Super Prompt v4.0.0 Bloco 12.5)
# =============================================================================
#
# PROBLEMA: OpenClaw context limitado a 131.1k tokens (deveria ser 1M)
# FONTE: L155 — OpenClaw MiniMax-M3 1M context + thinking adaptive
#
# SOLUÇÃO: Editar 2 arquivos em /home/node/.openclaw/agents/main/agent/
#
# EXECUÇÃO (como root via Tailscale SSH):
#   ssh root@100.99.172.84 "bash -s" < scripts/fix_openclaw_context_1M.sh
#
# APÓS EXECUTAR: Restart do container cartorio_openclaw-gateway
#
# =============================================================================

set -euo pipefail

AGENT_DIR="/home/node/.openclaw/agents/main/agent"
MODELS_JSON="${AGENT_DIR}/models.json"
AGENT_JSON="${AGENT_DIR}/agent.json"
BACKUP_DIR="/home/node/.openclaw/backups/fix_1M_$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "FIX OpenClaw Context 131k → 1M"
echo "=========================================="
echo ""

# 1. SSH connectivity check (via alias 'cartorio' - NUNCA IP direto)
echo "[1/6] Verificando conectividade SSH na VPS..."
if ! ssh -o ConnectTimeout=5 cartorio "echo OK" >/dev/null 2>&1; then
    echo "❌ Falha ao conectar via alias SSH 'cartorio' (Tailscale 100.99.172.84)"
    echo "   Gustavo precisa executar este script manualmente."
    exit 1
fi

# 2. Backup dos arquivos originais
echo "[2/6] Criando backup em ${BACKUP_DIR}..."
ssh cartorio "mkdir -p ${BACKUP_DIR} && cp ${MODELS_JSON} ${BACKUP_DIR}/models.json.bak && cp ${AGENT_JSON} ${BACKUP_DIR}/agent.json.bak"

# 3. Verificar estado atual
echo "[3/6] Estado ANTES do fix:"
ssh cartorio "cat ${MODELS_JSON} | python3 -c 'import json, sys; d=json.load(sys.stdin); print(\"  model:\", d.get(\"model\")); print(\"  max_tokens:\", d.get(\"max_tokens\", d.get(\"max_completion_tokens\", \"NOT SET\")))'"

# 4. Aplicar fix em models.json (max_tokens = 1000000)
echo "[4/6] Aplicando fix em models.json (max_tokens=1000000)..."
ssh cartorio "python3 << 'PYEOF'
import json
from pathlib import Path

models_path = Path('${MODELS_JSON}')
data = json.loads(models_path.read_text())

# Set max_tokens = 1M (context window completo)
if 'models' in data:
    # Formato: { 'models': { 'name': {config} } }
    for model_name, model_config in data['models'].items():
        if 'context_length' in model_config:
            model_config['context_length'] = 1000000
        if 'max_tokens' in model_config:
            model_config['max_tokens'] = 1000000
        if 'max_output_tokens' in model_config:
            model_config['max_output_tokens'] = 32000  # output separado
        print(f'  Updated model: {model_name}')
elif isinstance(data, dict):
    # Formato direto: { 'model': '...', 'max_tokens': ... }
    data['max_tokens'] = 1000000
    data['context_length'] = 1000000
    print('  Updated root config')

models_path.write_text(json.dumps(data, indent=2))
print('  models.json updated successfully')
PYEOF"

# 5. Atualizar agent.json (nova chave OpenCode-Go + modelo minimax-m3)
echo "[5/6] Aplicando nova chave OpenCode-Go + modelo minimax-m3 em agent.json..."
ssh cartorio "python3 << 'PYEOF'
import json
from pathlib import Path

agent_path = Path('${AGENT_JSON}')
data = json.loads(agent_path.read_text())

# Nova chave OpenCode-Go (NÃO rotacionar — Gustavo autorizou)
NEW_KEY = 'sk-xcRwExjQjqmlc5swP8umqK2YqWUfVt23H3Xl6dpd9TqEyi16ssJXzHeUFGNNIfsJ'

# Update API key em providers
if 'providers' in data:
    for provider_name, provider_config in data['providers'].items():
        if provider_name == 'openai' or 'opencode' in provider_name.lower():
            if 'api_key' in provider_config:
                old_key = provider_config['api_key']
                if 'xcRwExjQ' not in old_key:
                    provider_config['api_key'] = NEW_KEY
                    print(f'  Updated provider key: {provider_name}')
                else:
                    print(f'  Already updated: {provider_name}')

# Update thinking config (adaptive)
if 'thinking' in data:
    data['thinking']['enabled'] = True
    data['thinking']['mode'] = 'adaptive'
    print('  Thinking: adaptive mode enabled')

# Update model principal (MINIMAX-M3 conforme Gustavo 2026-06-24)
if 'model' in data:
    data['model'] = 'minimax-m3'
    print(f'  Model: {data[\"model\"]}')

# Update max_tokens se existir no root
if 'max_tokens' in data:
    data['max_tokens'] = 1000000
# Update context_window se existir (1M tokens)
if 'context_window' in data:
    data['context_window'] = 1000000

agent_path.write_text(json.dumps(data, indent=2))
print('  agent.json updated successfully')
PYEOF"

# 6. Restart do container
echo "[6/6] Restart do container cartorio_openclaw-gateway..."
ssh cartorio "docker service update --force cartorio_openclaw-gateway"

# Aguardar container estar UP
sleep 10
echo ""
echo "Verificando saúde pós-restart:"
ssh cartorio "docker service ps cartorio_openclaw-gateway | head -3"

# 7. Validação final via API
echo ""
echo "Validação via API:"
HEALTH=$(curl -sk -o /dev/null -w "%{http_code}" "https://agent.2notasudi.com.br/health")
if [ "$HEALTH" = "200" ]; then
    echo "  ✅ OpenClaw health: 200 OK"
    echo ""
    echo "=========================================="
    echo "✅ FIX APLICADO COM SUCESSO!"
    echo "=========================================="
    echo ""
    echo "Próximos passos:"
    echo "  1. Testar contexto real enviando mensagem longa"
    echo "  2. Verificar logs: ssh cartorio docker service logs cartorio_openclaw-gateway"
    echo "  3. Atualizar .harness/memory/MEMORY.md com L155 fix"
else
    echo "  ❌ OpenClaw health: $HEALTH (esperado 200)"
    echo "  Investigar: ssh cartorio docker service logs cartorio_openclaw-gateway"
    exit 1
fi
