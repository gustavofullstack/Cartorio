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

service_ready() {
  local service="$1"
  local replicas
  replicas=$(docker service ls --format '{{.Name}} {{.Replicas}}' 2>/dev/null \
    | awk -v expected="$service" '$1 == expected {print $2; exit}')
  [[ "$replicas" == "1/1" ]]
}

for service in \
  cartorio_api cartorio_redis cartorio_supabase cartorio_n8n \
  cartorio_evolution-api cartorio_chatwoot cartorio_chatwoot-sidekiq \
  cartorio_openclaw-gateway; do
  if service_ready "$service"; then report OK "service:${service}"; else report BLOCKED "service:${service}"; fi
done

if tailscale status --json >/dev/null 2>&1; then report OK tailscale; else report BLOCKED tailscale; fi
if /usr/local/bin/cartorio-backup-monitor.sh >/dev/null 2>&1; then report OK backup-local; else report BLOCKED backup-local; fi

api_env=$(docker service inspect cartorio_api --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}')
api_container=$(docker ps -q --filter 'label=com.docker.swarm.service.name=cartorio_api' | head -n 1)
chatwoot_base=$(printf '%s\n' "$api_env" | sed -n 's/^CHATWOOT_BASE_URL=//p' | head -n 1)
chatwoot_key=$(printf '%s\n' "$api_env" | sed -n 's/^CHATWOOT_API_KEY=//p' | head -n 1)
chatwoot_account=$(printf '%s\n' "$api_env" | sed -n 's/^CHATWOOT_ACCOUNT_ID=//p' | head -n 1)
if [[ -n "$chatwoot_base" && -n "$chatwoot_key" && -n "$chatwoot_account" ]] \
  && [[ "$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' -H "api_access_token: $chatwoot_key" "$chatwoot_base/api/v1/accounts/$chatwoot_account")" == "200" ]]; then
  report OK chatwoot-api
else
  report BLOCKED chatwoot-api
fi

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

whatsapp_connected=$(curl -sS --max-time 10 'https://api.2notasudi.com.br/api/v1/whatsapp/health' \
  | jq -r '.session_connected // false' 2>/dev/null || echo false)
if [[ "$whatsapp_connected" == "true" ]]; then report OK whatsapp-session; else report BLOCKED whatsapp-session; fi

if [[ -n "$api_container" ]] && docker exec "$api_container" python -c '
import os
import sys
import httpx

response = httpx.get(
    os.environ["OPENCLAW_BASE_URL"].rstrip("/") + "/v1/models",
    headers={"Authorization": "Bearer " + os.environ["OPENCLAW_API_KEY"]},
    timeout=10,
)
sys.exit(0 if response.status_code == 200 else 1)
' >/dev/null 2>&1; then
  report OK openclaw-api
else
  report BLOCKED openclaw-api
fi

for secret_name in hermes_api_server_key hermes_llm_api_key hermes_mcp_cartorio_api_key hermes_photon_project_secret; do
  if docker secret inspect "$secret_name" >/dev/null 2>&1; then report OK "hermes-secret:${secret_name}"; else report BLOCKED "hermes-secret:${secret_name}"; fi
done

printf 'CARTORIO_VPS_READINESS=%s\n' "$([[ "$failed" -eq 0 ]] && echo PASS || echo BLOCKED)"
exit "$([[ "$failed" -eq 0 ]] && echo 0 || echo 2)"
