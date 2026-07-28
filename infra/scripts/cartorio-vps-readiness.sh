#!/usr/bin/env bash
# Gate de prontidão somente leitura da VPS do Cartório.
# Não imprime credenciais, payloads de clientes ou conteúdo de backups.

set -euo pipefail

failed=0

report() {
  local state="$1"
  local name="$2"
  printf '%s %s\n' "$state" "$name"
  [[ "$state" == "OK" ]] || failed=1
}

note() {
  printf 'SKIP %s\n' "$1"
}

service_ready() {
  local service="$1"
  local replicas
  replicas=$(docker service ls --format '{{.Name}} {{.Replicas}}' 2>/dev/null \
    | awk -v expected="$service" '$1 == expected {print $2; exit}')
  [[ "$replicas" == "1/1" ]]
}

for service in \
  cartorio_system-api cartorio_memory-cache cartorio_banco_de_dados \
  cartorio_n8n cartorio_n8n-runner cartorio_whatsapp-api cartorio_hermes \
  cartorio_supabase_auth cartorio_supabase_realtime cartorio_supabase_storage; do
  if service_ready "$service"; then report OK "service:${service}"; else report BLOCKED "service:${service}"; fi
done

if tailscale status --json >/dev/null 2>&1; then report OK tailscale; else report BLOCKED tailscale; fi
if /usr/local/bin/cartorio-backup-monitor.sh >/dev/null 2>&1; then report OK backup-local; else report BLOCKED backup-local; fi

api_env=$(docker service inspect cartorio_system-api --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}')
note chatwoot-retired
note openclaw-retired

n8n_key=$(printf '%s\n' "$api_env" | sed -n 's/^N8N_API_KEY=//p' | head -n 1)
if [[ -n "$n8n_key" ]] \
  && [[ "$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' -H "X-N8N-API-KEY: $n8n_key" 'https://flow.2notasudi.com.br/api/v1/workflows?limit=1')" == "200" ]]; then
  report OK n8n-workflows
else
  report BLOCKED n8n-workflows
fi
if [[ -n "$n8n_key" ]] \
  && [[ "$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' -H "X-N8N-API-KEY: $n8n_key" 'https://flow.2notasudi.com.br/api/v1/executions?limit=1')" == "200" ]]; then
  report OK n8n-executions
else
  report BLOCKED n8n-executions
fi

n8n_db_container=$(docker ps -q \
  --filter 'label=com.docker.swarm.service.name=cartorio_n8n-db' | head -n 1)
if [[ -n "$n8n_db_container" ]] \
  && docker exec "$n8n_db_container" sh -lc '
count=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
  "select count(*) from workflow_entity")
test "${count:-0}" -gt 0
' >/dev/null 2>&1; then
  report OK n8n-workflow-database
else
  report BLOCKED n8n-workflow-database
fi

whatsapp_connected=$(curl -sS --max-time 10 'https://api.2notasudi.com.br/api/v1/whatsapp/health' \
  | jq -r '.session_connected // false' 2>/dev/null || echo false)
if [[ "$whatsapp_connected" == "true" ]]; then report OK whatsapp-session; else report BLOCKED whatsapp-session; fi

hermes_container=$(docker ps -q --filter 'label=com.docker.swarm.service.name=cartorio_hermes' | head -n 1)
if [[ -n "$hermes_container" ]] \
  && docker exec -u 10000 "$hermes_container" hermes gateway status \
    >/dev/null 2>&1; then
  report OK hermes-gateway
else
  report BLOCKED hermes-gateway
fi

if [[ -n "$hermes_container" ]] \
  && docker exec -u 10000 "$hermes_container" hermes mcp list 2>/dev/null \
    | grep -Eq '1 selected.*enabled'; then
  report OK hermes-mcp-allowlist
else
  report BLOCKED hermes-mcp-allowlist
fi

if [[ -n "$hermes_container" ]] \
  && docker exec -u 10000 "$hermes_container" python -c '
import json
from pathlib import Path

root = Path("/opt/data")
global_store = json.loads(
    (root / "platforms/pairing/feishu-approved.json").read_text(encoding="utf-8")
)
profile_store = json.loads(
    (root / "profiles/default/pairing/feishu-approved.json").read_text(encoding="utf-8")
)
raise SystemExit(0 if global_store and global_store == profile_store else 1)
' >/dev/null 2>&1; then
  report OK hermes-feishu-pairing
else
  report BLOCKED hermes-feishu-pairing
fi

for secret_name in hermes_minimax_api_key hermes_mcp_cartorio_api_key; do
  if docker secret inspect "$secret_name" >/dev/null 2>&1; then report OK "hermes-secret:${secret_name}"; else report BLOCKED "hermes-secret:${secret_name}"; fi
done

printf 'CARTORIO_VPS_READINESS=%s\n' "$([[ "$failed" -eq 0 ]] && echo PASS || echo BLOCKED)"
exit "$([[ "$failed" -eq 0 ]] && echo 0 || echo 2)"
