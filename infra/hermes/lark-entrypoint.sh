#!/bin/sh
set -eu

read_required_secret() {
  secret_path="/run/secrets/$1"
  if [ ! -s "${secret_path}" ]; then
    printf 'required Docker Secret is missing: %s\n' "$1" >&2
    exit 78
  fi
  cat "${secret_path}"
}

umask 077
export HERMES_HOME="${HERMES_HOME:-/opt/data}"
export MINIMAX_API_KEY="$(read_required_secret hermes_minimax_api_key)"
export MCP_CARTORIO_API_KEY="$(read_required_secret hermes_mcp_cartorio_api_key)"
export MCP_CARTORIO_URL="${MCP_CARTORIO_URL:-http://cartorio_system-api:8000/mcp/}"
export HERMES_LLM_MODEL="${HERMES_LLM_MODEL:-MiniMax-M3}"
export HERMES_LLM_BASE_URL="${HERMES_LLM_BASE_URL:-https://api.minimax.io/anthropic}"
export MINIMAX_BASE_URL="${MINIMAX_BASE_URL:-${HERMES_LLM_BASE_URL}}"

# FEISHU_APP_ID / FEISHU_APP_SECRET are persisted by Hermes' native Lark
# onboarding in HERMES_HOME/.env. Keep credentials out of the Swarm spec and
# preserve the OAuth state across task replacement through the data volume.
export FEISHU_DOMAIN="lark"
export FEISHU_CONNECTION_MODE="websocket"
export FEISHU_ALLOW_ALL_USERS="false"
export FEISHU_GROUP_POLICY="allowlist"
export FEISHU_REQUIRE_MENTION="true"
export FEISHU_ALLOWED_USERS="d3983edd,2bbfa27a"
export FEISHU_ALLOW_BOTS="none"
export HERMES_GATEWAY_BUSY_ACK_ENABLED="false"

if [ -r /run/configs/SOUL.md ]; then
  install -m 0600 /run/configs/SOUL.md "${HERMES_HOME}/SOUL.md"
fi

plugin_dir="${HERMES_HOME}/plugins/pietra-public-output"
install -d -m 0700 "${plugin_dir}"
install -m 0600 /run/configs/pietra-public-output.plugin.yaml "${plugin_dir}/plugin.yaml"
install -m 0600 /run/configs/pietra-public-output.__init__.py "${plugin_dir}/__init__.py"
install -m 0600 /run/configs/pietra-public-output.guard.py "${plugin_dir}/public_output_guard.py"
python /run/configs/reconcile_public_profile.py \
  "${HERMES_HOME}/config.yaml" \
  /run/configs/config.cartorio.yaml \
  "${HERMES_HOME}/skills"

# The image reconciles profiles before this entrypoint runs. A persisted
# "running" state would start an s6-managed gateway and race this foreground
# process, causing both instances to exit. Keep Swarm as the sole supervisor.
hermes gateway stop >/dev/null 2>&1 || true

exec hermes gateway run --no-supervise --external-supervisor
