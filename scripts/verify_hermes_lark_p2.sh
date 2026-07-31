#!/usr/bin/env bash
set -euo pipefail

# Read-only production gate for the canonical cartorio_hermes service.
# It never changes services, reads secret values, or prints event payloads.

SSH_TARGET="${SSH_TARGET:-cartorio}"
WINDOW="${WINDOW:-15m}"

run_remote() {
  ssh -o BatchMode=yes -o ConnectTimeout=8 "$SSH_TARGET" "$1"
}

echo "[1/5] service replica"
run_remote 'test "$(docker service ls --filter name=cartorio_hermes --format "{{.Replicas}}")" = "1/1"'

echo "[2/5] single running task"
run_remote 'test "$(docker service ps cartorio_hermes --filter desired-state=running --format "{{.CurrentState}}" | wc -l | tr -d " ")" = "1"'

echo "[3/5] no legacy P1 or missing processors"
legacy_count="$(run_remote "docker service logs cartorio_hermes --since '$WINDOW' 2>&1 | grep -Eic 'processor not found|type: message([[:space:]]|$)|type: message_read' || true")"
test "$legacy_count" = "0"

echo "[4/5] modern P2 inbound observed"
p2_count="$(run_remote "docker service logs cartorio_hermes --since '$WINDOW' 2>&1 | grep -Fic 'im.message.receive_v1' || true")"
test "$p2_count" -gt 0

echo "[5/5] MCP secret-context connectivity"
run_remote 'CID=$(docker ps -q --filter name=cartorio_hermes | head -1); test -n "$CID"; docker exec --user hermes "$CID" sh -lc '\''export MCP_CARTORIO_API_KEY=$(cat /run/secrets/hermes_mcp_cartorio_api_key); /opt/hermes/bin/hermes mcp test cartorio 2>&1 | grep -q "Connected"'\'''

echo "P2_RUNTIME_GATE=PASS"
