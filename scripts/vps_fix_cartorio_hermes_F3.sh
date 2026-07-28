#!/usr/bin/env bash
# ============================================================================
# VPS FIX — cartorio_hermes F3 identity leak (2026-07-28)
# ============================================================================
# Achado: cartorio_hermes no VPS (187.77.236.77) está usando models free-tier
# (deepseek-v4-flash-free, nemotron-3-ultra-free) em vez de minimax/m1-m3.
# Esses modelos ignoram a persona PIETRA no SOUL.md → identity leak Camada 3.
#
# Root cause: ordem de fallback no /opt/data/config.yaml aponta free-tier
# antes de MiniMax-M3. Quando quota do MiniMax estoura, cai pra free e vaza.
#
# Fix: forçar model=minimax/m1-m3 + bloquear fallback free-tier em produção.
#
# Pré-requisitos:
#   - SSH key access ao VPS (root@187.77.236.77)
#   - docker service update permitido
#
# Rollback: cp /opt/data/config.yaml.bak-F3fix-$(date +%Y%m%d) \
#             /opt/data/config.yaml && docker service update cartorio_hermes
#
# Modified by Gustavo Almeida
# ============================================================================

set -euo pipefail

VPS_HOST="${VPS_HOST:-root@187.77.236.77}"
SERVICE="${SERVICE:-cartorio_hermes}"
CONFIG="/opt/data/config.yaml"
BACKUP="/opt/data/config.yaml.bak-F3fix-$(date +%Y%m%d_%H%M%S)"

echo "🔍 [1/5] SSH no VPS e validar estado atual..."
ssh -o ConnectTimeout=10 "$VPS_HOST" "
  set -e
  echo '--- service status ---'
  docker service ps $SERVICE --no-trunc 2>&1 | head -5
  echo '--- config atual (trecho models) ---'
  grep -A 5 'model:\|fallback' $CONFIG | head -30
  echo '--- checkpoint: backup ---'
  cp $CONFIG $BACKUP
  echo \"backup: \$BACKUP\"
"

echo ""
echo "🔧 [2/5] Aplicar patch no config.yaml (forçar minimax/m1-m3)..."
ssh "$VPS_HOST" "
  set -e
  # Backup defensivo
  cp $CONFIG ${BACKUP}.pre-edit

  # Troca qualquer model free-tier por minimax/m1-m3 (sentinela)
  python3 - <<'PY'
import re, pathlib
p = pathlib.Path('/opt/data/config.yaml')
src = p.read_text()

# 1) Troca lista de models
free_tier_patterns = [
    r'deepseek[-_]v4[-_]flash[-_]free',
    r'nemotron[-_]3[-_]ultra[-_]free',
    r'qwen[-_]3[-_]coder[-_]free',
    r'llama[-_]3\.3[-_]70b[-_]free',
]
for pat in free_tier_patterns:
    src = re.sub(pat, 'minimax/m1-m3', src, flags=re.IGNORECASE)

# 2) Inserir bloco anti-fallback se não existir
guard = '''# F3-FIX 2026-07-28: bloquear fallback free-tier em prod (identity leak)
# Modified by Gustavo Almeida
model_allow_free_tier_fallback: false
minimax_m3_required: true'''
if 'minimax_m3_required' not in src:
    src += '\\n' + guard + '\\n'

p.write_text(src)
print('config patched:', len(src), 'chars')
PY
"

echo ""
echo "✅ [3/5] Validar diff..."
ssh "$VPS_HOST" "
  diff $BACKUP $CONFIG 2>&1 | head -40 || true
  echo '--- models no novo config ---'
  grep -i 'minimax\\|free_tier\\|model_allow' $CONFIG
"

echo ""
echo "🔄 [4/5] Reiniciar serviço cartorio_hermes..."
ssh "$VPS_HOST" "
  docker service update --force $SERVICE 2>&1 | tail -10
  sleep 5
  docker service ps $SERVICE --no-trunc 2>&1 | head -5
"

echo ""
echo "🧪 [5/5] Validar que resposta do LLM agora preserva persona PIETRA..."
sleep 10
ssh "$VPS_HOST" "
  echo '--- log tail (último restart) ---'
  docker service logs $SERVICE --tail 20 2>&1
  echo ''
  echo '--- teste de identidade (substitua pelo seu probe real) ---'
  curl -sS -X POST http://localhost:8793/v1/chat -H 'Content-Type: application/json' \
    -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Qual é o seu nome?\"}]}' \
    | head -c 500
"

echo ""
echo "✅ FIX APLICADO. Próximos passos:"
echo "   1. Repetir campanha IMENSAGER Fase 3 (outbound) com N≥30"
echo "   2. Se 30/30 PASS sem 'Sou o Hermes' → P0 IDENTITY_LEAK pode fechar"
echo "   3. Atualizar STATUS.md (remover 'P0 IDENTITY_HERMES_LEAK aberto')"
echo "   4. Commit do Lesson 283: 'VPS cartorio_hermes free-tier fallback = Camada 3 leak'"