#!/usr/bin/env bash
# scripts/loki_sample_query.sh
#
# G7.18.T4 — dry-run friendly helper for Loki sample LogQL queries.
# Default: print queries/curls only (--dry-run). Use --ready / --query to hit Loki.
#
# Usage:
#   bash scripts/loki_sample_query.sh --dry-run
#   LOKI_URL=http://127.0.0.1:3100 bash scripts/loki_sample_query.sh --ready
#   bash scripts/loki_sample_query.sh --query api-502
#   bash scripts/loki_sample_query.sh --list
#
# Env:
#   LOKI_URL   default http://127.0.0.1:3100
#   LOKI_LIMIT default 50
#   LOKI_RANGE_SECS default 900 (15m)
#
# No secrets. Safe offline with --dry-run.
#
# Modified by Gustavo Almeida — G7 Wave 27 cartorio-sre

set -euo pipefail

LOKI_URL="${LOKI_URL:-http://127.0.0.1:3100}"
LOKI_LIMIT="${LOKI_LIMIT:-50}"
LOKI_RANGE_SECS="${LOKI_RANGE_SECS:-900}"

DRY_RUN=1
DO_READY=0
DO_LABELS=0
QUERY_KEY=""
LIST_ONLY=0

readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

log_info() { printf "${YELLOW}[INFO]${NC} %s\n" "$*"; }
log_ok()   { printf "${GREEN}[OK]${NC} %s\n" "$*"; }
log_fail() { printf "${RED}[FAIL]${NC} %s\n" "$*"; }

usage() {
  cat <<'EOF'
loki_sample_query.sh — G7.18.T4 sample LogQL helper

  --dry-run          Print queries only (default if no action flag)
  --ready            GET /ready (live)
  --labels           GET /loki/api/v1/labels (live)
  --query KEY        Run named sample (live unless --dry-run forced first)
  --list             List sample keys + LogQL
  --live             Actually call Loki for --query (sets dry-run off)
  -h, --help         This help

Sample keys:
  api-502       cartorio_api lines with 502
  api-error     cartorio_api JSON level error
  n8n-error     n8n / cartorio_n8n errors
  n8n-db        n8n DB auth failures (Lesson 176 pattern)
  traefik-502   traefik container 502
  chatwoot-db   chatwoot PG connection errors
  evolution-db  evolution Prisma P1001
  pii-audit     CPF-shaped pattern (restricted; pipeline health)
EOF
}

# Returns LogQL for a key
logql_for() {
  case "$1" in
    api-502)
      echo '{container=~".*cartorio_api.*"} |= "502" or |= "Bad Gateway"'
      ;;
    api-error)
      echo '{swarm_service="cartorio_api"} | json | level=~"(?i)error|critical"'
      ;;
    n8n-error)
      echo '{container=~".*n8n.*"} |~ "(?i)error|failed|exception"'
      ;;
    n8n-db)
      echo '{container=~".*n8n.*"} |= "password authentication failed" or |= "error initializing DB"'
      ;;
    traefik-502)
      echo '{container=~".*traefik.*"} |= "502"'
      ;;
    chatwoot-db)
      echo '{container=~".*chatwoot.*"} |~ "(?i)PG::ConnectionBad|Host is unreachable|ActiveRecord"'
      ;;
    evolution-db)
      echo '{container=~".*evolution.*"} |= "P1001" or |= "Can'\''t reach database"'
      ;;
    pii-audit)
      # Pipeline health only — do not paste results into public tickets
      echo '{job=~".+"} |~ `\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}`'
      ;;
    *)
      return 1
      ;;
  esac
}

list_samples() {
  local keys=(api-502 api-error n8n-error n8n-db traefik-502 chatwoot-db evolution-db pii-audit)
  printf '%-14s  %s\n' "KEY" "LOGQL"
  printf '%-14s  %s\n' "----" "-----"
  local k q
  for k in "${keys[@]}"; do
    q="$(logql_for "$k")"
    printf '%-14s  %s\n' "$k" "$q"
  done
}

ns_now() {
  date -u +%s
}

range_bounds() {
  local end start
  end="$(ns_now)"
  start=$((end - LOKI_RANGE_SECS))
  # Loki expects nanoseconds
  echo "${start}000000000" "${end}000000000"
}

print_curl_query_range() {
  local query="$1"
  local start_ns end_ns
  read -r start_ns end_ns < <(range_bounds)
  cat <<EOF
curl -fsS -G '${LOKI_URL}/loki/api/v1/query_range' \\
  --data-urlencode 'query=${query}' \\
  --data-urlencode 'start=${start_ns}' \\
  --data-urlencode 'end=${end_ns}' \\
  --data-urlencode 'limit=${LOKI_LIMIT}'
EOF
}

run_ready() {
  local url="${LOKI_URL}/ready"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log_info "dry-run: curl -fsS ${url}"
    return 0
  fi
  if curl -fsS --max-time 5 "$url"; then
    echo
    log_ok "Loki ready at ${LOKI_URL}"
  else
    log_fail "Loki not ready at ${LOKI_URL}"
    return 1
  fi
}

run_labels() {
  local url="${LOKI_URL}/loki/api/v1/labels"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log_info "dry-run: curl -fsS ${url}"
    return 0
  fi
  curl -fsS --max-time 10 "$url" | (command -v jq >/dev/null && jq . || cat)
}

run_query() {
  local key="$1"
  local query
  if ! query="$(logql_for "$key")"; then
    log_fail "Unknown query key: ${key} (use --list)"
    return 1
  fi
  log_info "key=${key}"
  log_info "LogQL: ${query}"
  print_curl_query_range "$query"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log_info "dry-run only — pass --live to execute"
    return 0
  fi
  local start_ns end_ns
  read -r start_ns end_ns < <(range_bounds)
  local resp
  resp="$(curl -fsS -G "${LOKI_URL}/loki/api/v1/query_range" \
    --data-urlencode "query=${query}" \
    --data-urlencode "start=${start_ns}" \
    --data-urlencode "end=${end_ns}" \
    --data-urlencode "limit=${LOKI_LIMIT}")" || {
      log_fail "query_range failed"
      return 1
    }
  if command -v jq >/dev/null 2>&1; then
    local n
    n="$(echo "$resp" | jq '.data.result | length')"
    log_ok "streams=${n}"
    echo "$resp" | jq '{status, resultType: .data.resultType, streams: (.data.result|length), sample: [.data.result[0].stream // {}]}'
  else
    echo "$resp"
  fi
}

# --- args ---
if [[ $# -eq 0 ]]; then
  DRY_RUN=1
  log_info "No args — dry-run listing samples. Use -h for help."
  list_samples
  echo
  log_info "Example live: LOKI_URL=http://127.0.0.1:3100 $0 --live --query api-502"
  exit 0
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --live) DRY_RUN=0; shift ;;
    --ready) DO_READY=1; shift ;;
    --labels) DO_LABELS=1; shift ;;
    --list) LIST_ONLY=1; shift ;;
    --query)
      QUERY_KEY="${2:-}"
      if [[ -z "$QUERY_KEY" ]]; then log_fail "--query needs KEY"; exit 2; fi
      shift 2
      ;;
    *)
      log_fail "Unknown arg: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ "$LIST_ONLY" -eq 1 ]]; then
  list_samples
  exit 0
fi

# If user only asked --query without --live, keep dry-run (safe default)
if [[ "$DO_READY" -eq 1 ]]; then
  run_ready
fi
if [[ "$DO_LABELS" -eq 1 ]]; then
  run_labels
fi
if [[ -n "$QUERY_KEY" ]]; then
  run_query "$QUERY_KEY"
fi

if [[ "$DO_READY" -eq 0 && "$DO_LABELS" -eq 0 && -z "$QUERY_KEY" ]]; then
  usage
  exit 0
fi
