#!/usr/bin/env bash
# Gate somente leitura para o deploy do Hermes Cartório na VPS.
# Nunca imprime valores de Docker Secrets ou de variáveis de ambiente.

set -euo pipefail

required_secrets=(
  hermes_api_server_key
  hermes_llm_api_key
  hermes_mcp_cartorio_api_key
  hermes_photon_project_secret
  hermes_lark_app_id
  hermes_lark_app_secret
  hermes_lark_allowed_users
)
network_name="${HERMES_NETWORK_NAME:-easypanel-cartorio}"
failed=0

check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf 'OK %s\n' "$label"
  else
    printf 'MISSING %s\n' "$label" >&2
    failed=1
  fi
}

check 'docker CLI' command -v docker
check 'Swarm ativo' bash -c '[[ "$(docker info --format {{.Swarm.LocalNodeState}})" == active ]]'
check "rede ${network_name}" docker network inspect "${network_name}"

for secret_name in "${required_secrets[@]}"; do
  check "Docker Secret ${secret_name}" docker secret inspect "${secret_name}"
done

if [[ "${failed}" -ne 0 ]]; then
  printf 'HERMES_PREFLIGHT=BLOCKED\n' >&2
  exit 2
fi

printf 'HERMES_PREFLIGHT=PASS\n'
