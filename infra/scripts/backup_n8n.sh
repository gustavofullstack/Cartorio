#!/usr/bin/env bash
# backup_n8n.sh — Backup dos workflows N8N
# Uso: ./backup_n8n.sh [--restore]
#
# Exporta todos os WFs via N8N API e salva localmente
# LGPD: NÃO loga PII

set -eo pipefail

RESTORE=false
[[ "${1:-}" == "--restore" ]] && RESTORE=true

N8N_URL="https://flow.2notasudi.com.br"
BACKUP_DIR="${HOME}/projetos/Cartorio/infra/n8n-workflows/backup-$(date +%Y%m%d-%H%M)"
API_KEY="${N8N_API_KEY:-}"

if [[ -z "$API_KEY" ]]; then
    echo "❌ N8N_API_KEY não configurada. Exporte: export N8N_API_KEY=<key>"
    exit 1
fi

echo "📦 Backup N8N Workflows..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if $RESTORE; then
    echo "⚠️  Modo RESTORE — copiando WFs de volta..."
    # TODO: implementar restore via N8N API
    echo "❌ Restore ainda não implementado"
    exit 1
fi

# 1. Listar workflows
echo "1️⃣ Listando workflows..."
WFS=$(curl -sk -H "X-N8N-API-KEY: $API_KEY" "${N8N_URL}/api/v1/workflows" 2>/dev/null)
WF_COUNT=$(echo "$WFS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null || echo "0")
echo "   Encontrados: $WF_COUNT workflows"

# 2. Criar diretório de backup
mkdir -p "$BACKUP_DIR"
echo "2️⃣ Diretório: $BACKUP_DIR"

# 3. Exportar cada workflow
echo "3️⃣ Exportando workflows..."
SAVED=0
echo "$WFS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for wf in d.get('data', []):
    print(wf.get('id', 'unknown'))
" 2>/dev/null | while read -r wf_id; do
    [[ -z "$wf_id" ]] && continue
    WF_DATA=$(curl -sk -H "X-N8N-API-KEY: $API_KEY" "${N8N_URL}/api/v1/workflows/${wf_id}" 2>/dev/null)
    WF_NAME=$(echo "$WF_DATA" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('name','unknown'))" 2>/dev/null || echo "unknown")
    echo "$WF_DATA" > "$BACKUP_DIR/${wf_id}-${WF_NAME}.json" 2>/dev/null
    SAVED=$((SAVED+1))
    echo "   ✅ ${wf_id}: ${WF_NAME}"
done

# 4. Criar manifesto
cat > "$BACKUP_DIR/MANIFEST.json" << EOF
{
  "timestamp": "$(date -u +%FT%TZ)",
  "workflow_count": $WF_COUNT,
  "source": "$N8N_URL",
  "backup_dir": "$BACKUP_DIR"
}
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Backup completo! $WF_COUNT workflows em $BACKUP_DIR"
