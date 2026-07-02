#!/usr/bin/env bash
# health_check_27services.sh — Health check completo do Docker Swarm (27 serviços)
# Emite 1 linha por serviço: STATUS name state replicas latency_ms health
# Detecta CrashLoop antes do 502 público.
#
# Uso:  ./scripts/health_check_27services.sh
#       ./scripts/health_check_27services.sh --json
#       ./scripts/health_check_27services.sh --only-down
#
# Compatível com bash 3.2 (macOS default — sem declare -A).
#
# Modified by Gustavo Almeida — 2026-07-02 (Wave 7 — TODO-004 Swarm healthchecks)

set -uo pipefail

SSH_ALIAS="${SSH_ALIAS:-cartorio}"
ONLY_DOWN=0
JSON_MODE=0

for arg in "$@"; do
  case "$arg" in
    --json) JSON_MODE=1 ;;
    --only-down) ONLY_DOWN=1 ;;
    -h|--help) echo "Uso: $0 [--json] [--only-down]"; exit 0 ;;
  esac
done

if ! command -v ssh >/dev/null 2>&1; then
  echo "ERRO: ssh nao encontrado" >&2
  exit 2
fi

if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_ALIAS" "echo OK" >/dev/null 2>&1; then
  echo "ERRO: ssh $SSH_ALIAS indisponivel" >&2
  exit 3
fi

# Coletar estado completo via ssh em uma unica chamada
REMOTE_REPORT=$(ssh "$SSH_ALIAS" "docker service ls --format '{{.Name}}|{{.Replicas}}|{{.Image}}' | sort" 2>/dev/null)
if [[ -z "$REMOTE_REPORT" ]]; then
  echo "ERRO: docker service ls vazio" >&2
  exit 4
fi

# Coletar health + restart de cada container em uma unica ssh (reduz round-trips)
HEALTH_TMP=$(mktemp)
trap 'rm -f "$HEALTH_TMP"' EXIT
ssh "$SSH_ALIAS" bash <<'SSH_EOF' > "$HEALTH_TMP" 2>/dev/null
for s in $(docker service ls --format '{{.Name}}'); do
  cid=$(docker ps -q --filter "label=com.docker.swarm.service.name=$s" | head -1)
  if [[ -n "$cid" ]]; then
    hstate=$(docker inspect --format='{{.State.Health.Status}}' "$cid" 2>/dev/null || echo none)
    rstate=$(docker inspect --format='{{.State.Status}}' "$cid" 2>/dev/null || echo unknown)
    restarts=$(docker inspect --format='{{.RestartCount}}' "$cid" 2>/dev/null || echo 0)
    echo "$s|$rstate|$hstate|$restarts"
  else
    echo "$s|missing|none|0"
  fi
done
SSH_EOF

TOTAL=0
UP=0
DOWN=0
WARN=0

declare -a RESULTS=()

while IFS='|' read -r name replicas image; do
  TOTAL=$((TOTAL + 1))
  want="${replicas%%/*}"
  cur="${replicas##*/}"

  # Buscar health no tmp file (grep, ja que bash 3.2 nao tem assoc arrays)
  health_line=$(grep -F "${name}|" "$HEALTH_TMP" 2>/dev/null | head -1 || true)
  if [[ -n "$health_line" ]]; then
    IFS='|' read -r _ rstate hstate restarts <<< "$health_line"
  else
    rstate="unknown"; hstate="none"; restarts="0"
  fi

  # Veredito
  status="UP"
  if [[ "$cur" != "$want" ]]; then
    status="DOWN"
  elif [[ "$rstate" == "restarting" || "$rstate" == "missing" ]]; then
    status="WARN"
  fi

  case "$status" in
    UP)   UP=$((UP + 1)) ;;
    DOWN) DOWN=$((DOWN + 1)) ;;
    WARN) WARN=$((WARN + 1)) ;;
  esac

  RESULTS+=("$status|$name|$replicas|$rstate|$hstate|$restarts|$image")
done <<< "$REMOTE_REPORT"

# Saida
if [[ $JSON_MODE -eq 1 ]]; then
  echo "{"
  echo "  \"total\": $TOTAL, \"up\": $UP, \"down\": $DOWN, \"warn\": $WARN,"
  echo "  \"services\": ["
  first=1
  for r in "${RESULTS[@]}"; do
    IFS='|' read -r st n rep rs hs ri img <<< "$r"
    [[ $first -eq 1 ]] && first=0 || echo ","
    short_img=$(echo "$img" | awk -F: '{print $1":"$2}' | awk -F/ '{print $NF}')
    printf '    {"status":"%s","name":"%s","replicas":"%s","state":"%s","health":"%s","restarts":%d,"image":"%s"}' \
      "$st" "$n" "$rep" "$rs" "$hs" "${ri:-0}" "$short_img"
  done
  echo ""
  echo "  ]"
  echo "}"
else
  printf "%-6s %-35s %-10s %-12s %-10s %-8s %s\n" "STATUS" "SERVICE" "REPLICAS" "STATE" "HEALTH" "RESTART" "IMAGE"
  printf -- "-%.0s" {1..120}; echo ""
  for r in "${RESULTS[@]}"; do
    IFS='|' read -r st n rep rs hs ri img <<< "$r"
    [[ $ONLY_DOWN -eq 1 && "$st" == "UP" ]] && continue
    short_img=$(echo "$img" | awk -F/ '{print $NF}' | cut -c1-50)
    printf "%-6s %-35s %-10s %-12s %-10s %-8s %s\n" "$st" "$n" "$rep" "$rs" "$hs" "$ri" "$short_img"
  done
  echo ""
  printf "TOTAL=%d UP=%d WARN=%d DOWN=%d\n" "$TOTAL" "$UP" "$WARN" "$DOWN"
fi

# Exit code: 0 tudo UP, 1 algum DOWN, 2 so WARN
if [[ $DOWN -gt 0 ]]; then
  exit 1
elif [[ $WARN -gt 0 ]]; then
  exit 2
fi
exit 0