#!/usr/bin/env bash
# Deprecated deployment entrypoint.
# Production API moved from cartorio_api to cartorio_system-api. This guard
# prevents an accidental rollout to the legacy service/image pair.
set -euo pipefail

echo "REFUSING: cartorio_api is a legacy Swarm service and is not the public API."
echo "Use infra/scripts/deploy_system_api.sh --check for a read-only preflight."
printf '%s\n' \
  "A production rollout requires: CARTORIO_DEPLOY_APPROVED=YES" \
  "infra/scripts/deploy_system_api.sh --apply"
exit 64
