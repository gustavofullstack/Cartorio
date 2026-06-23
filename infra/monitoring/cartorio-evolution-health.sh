#!/bin/bash
# Health check Evolution API instance cartorio-2notas.
# v0.5.0 (2026-06-23): Roda a cada 5min via systemd timer.
# IP do container resolvido dinamicamente via docker inspect.

set -euo pipefail

INSTANCE="${1:-cartorio-2notas}"
EVO_KEY="429683C4C977415CAAFCCE10F7D57E11"

# Resolve IP dinamicamente (Easypanel pode re-escalar container)
CID=$(docker ps -qf "name=cartorio_evolution-api" | head -1)
if [[ -z "$CID" ]]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [CRITICAL] Container cartorio_evolution-api nao encontrado"
  exit 1
fi

EVO_IP=$(docker inspect "$CID" --format "{{(index .NetworkSettings.Networks \"cartorio_supabase_default\").IPAddress}}" 2>/dev/null)
if [[ -z "$EVO_IP" ]]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [CRITICAL] IP do cartorio_evolution-api nao resolvido"
  exit 1
fi

STATE=$(curl -sf --max-time 5 -H "apikey: ${EVO_KEY}" \
  "http://${EVO_IP}:8080/instance/connectionState/${INSTANCE}" \
  | jq -r ".instance.state // \"error\"" 2>/dev/null)

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

case "${STATE}" in
  open)        echo "[$TS] [OK] Evolution instance ${INSTANCE} state=${STATE}"; exit 0 ;;
  connecting)  echo "[$TS] [WARN] Evolution instance ${INSTANCE} state=${STATE} (QR scan pendente)"; exit 0 ;;
  close|closed) echo "[$TS] [CRITICAL] Evolution instance ${INSTANCE} state=${STATE}"; exit 1 ;;
  error|"")    echo "[$TS] [CRITICAL] Evolution instance ${INSTANCE} state=${STATE}"; exit 1 ;;
  *)           echo "[$TS] [CRITICAL] Evolution instance ${INSTANCE} state=${STATE} (unknown)"; exit 1 ;;
esac
