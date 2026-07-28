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
export FEISHU_APP_ID="$(read_required_secret hermes_lark_app_id)"
export FEISHU_APP_SECRET="$(read_required_secret hermes_lark_app_secret)"
export FEISHU_ALLOWED_USERS="$(read_required_secret hermes_lark_allowed_users)"
export FEISHU_DOMAIN="lark"
export FEISHU_CONNECTION_MODE="websocket"
export FEISHU_ALLOW_ALL_USERS="false"
export FEISHU_GROUP_POLICY="allowlist"
export FEISHU_REQUIRE_MENTION="true"
export FEISHU_ALLOW_BOTS="none"

exec hermes gateway run --no-supervise --external-supervisor
