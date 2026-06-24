#!/usr/bin/env bash
# migra-workflows-v1-to-v2.sh
# Template de script de migracao de WF v1 -> v2 com breaking change.
# Editar WF_V1_ID, WF_V2_FILE, WF_V2_NAME antes de executar.
#
# Uso: ./migra-workflows-v1-to-v2.sh
#
# Pre-requisito: rodar checklist pre-migration (ver MIGRATION.md)

set -euo pipefail

# === CONFIGURAR AQUI ===
WF_V1_ID="OQRIOVHcOjpkQ0Of"               # ID do workflow v1 ativo
WF_V2_FILE="/Users/gustavoalmeida/projetos/Cartorio/infra/n8n-workflows/03-handoff-human-chatwoot.json"
WF_V2_NAME="03 - Handoff Humano (Chatwoot v2)"
N8N_BASE_URL="${N8N_BASE_URL:-https://flow.2notasudi.com.br}"

# === NAO EDITAR ABAIXO ===
WF_NEW_ID=""
LOG="/var/log/cartorio-migration-$(date +%Y%m%d-%H%M%S).log"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# Pre-checks
[[ -z "${N8N_API_KEY:-}" ]] && { log "ERROR: N8N_API_KEY nao definido"; exit 1; }
[[ ! -f "$WF_V2_FILE" ]] && { log "ERROR: arquivo v2 nao encontrado: $WF_V2_FILE"; exit 1; }
command -v jq >/dev/null || { log "ERROR: jq nao instalado"; exit 1; }

log "=== Migracao iniciada ==="
log "v1 ID: $WF_V1_ID"
log "v2 file: $WF_V2_FILE"

# 1. Backup pre-migration
log "Passo 1/6: Backup pre-migration ..."
bash /Users/gustavoalmeida/projetos/Cartorio/scripts/backup_n8n_workflows.sh 2>>"$LOG" || true

# 2. Desativa v1
log "Passo 2/6: Desativando v1 ($WF_V1_ID) ..."
curl -fsS -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/workflows/$WF_V1_ID/deactivate" >>"$LOG" 2>&1 || \
  log "WARN: nao foi possivel desativar v1 (pode ja estar inativo)"

# 3. Cria v2
log "Passo 3/6: Criando v2 ..."
WF_NEW_ID=$(curl -fsS -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @"$WF_V2_FILE" \
  "$N8N_BASE_URL/api/v1/workflows" | jq -r '.id')

if [[ -z "$WF_NEW_ID" || "$WF_NEW_ID" == "null" ]]; then
  log "ERROR: falha ao criar v2"
  exit 1
fi
log "v2 criado com ID: $WF_NEW_ID"

# 4. Ativa v2
log "Passo 4/6: Ativando v2 ($WF_NEW_ID) ..."
curl -fsS -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/workflows/$WF_NEW_ID/activate" >>"$LOG" 2>&1

# 5. Arquiva v1 (soft delete)
log "Passo 5/6: Arquivando v1 ($WF_V1_ID) ..."
curl -fsS -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/workflows/$WF_V1_ID/archive" >>"$LOG" 2>&1 || true

# 6. Re-export v2 para repo (capturar IDs reais)
log "Passo 6/6: Re-export v2 para repo ..."
sleep 3   # N8N pode levar alguns segundos para enriquecer o JSON
curl -fsS -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_BASE_URL/api/v1/workflows/$WF_NEW_ID" \
  -o "$WF_V2_FILE" 2>>"$LOG"

log "=== Migracao concluida ==="
log "v1: $WF_V1_ID (arquivado)"
log "v2: $WF_NEW_ID (ativo)"
log "Log: $LOG"
log ""
log "PROXIMOS PASSOS:"
log "  1. Rodar pos-migration checklist (MIGRATION.md)"
log "  2. python3 scripts/n8n_workflow_test.py"
log "  3. git add + commit 'chore(n8n): migrate <WF> v1->v2'"
log "  4. Atualizar CHANGELOG.md + tag n8n-v2.0.0"

exit 0
