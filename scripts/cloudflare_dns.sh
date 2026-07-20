#!/usr/bin/env bash
# cloudflare_dns.sh — Gerencia DNS records do domínio 2notasudi.com.br via Cloudflare API
# Token esperado em /Users/gustavoalmeida/projetos/Cartorio/.secrets/cloudflare.env
# Formato: CLOUDFLARE_API_TOKEN=...; CLOUDFLARE_ZONE_ID=...; CLOUDFLARE_ACCOUNT_ID=... (opcional)
#
# Uso:
#   ./scripts/cloudflare_dns.sh add       # cria A records para langfuse/chatwoot/argilla
#   ./scripts/cloudflare_dns.sh remove-flow # remove A record zombie flow.2notasudi.com.br
#   ./scripts/cloudflare_dns.sh list      # lista todos os records
#   ./scripts/cloudflare_dns.sh verify    # curl 200 OK em cada subdomínio
#
# Modified by Gustavo Almeida — 2026-07-02 (Wave 10 — DNS Cloudflare automation)

set -uo pipefail

# Paths
SECRETS_DIR="/Users/gustavoalmeida/projetos/Cartorio/.secrets"
SECRET_FILE="/Users/gustavoalmeida/projetos/Cartorio/.secrets/cloudflare.env"
TARGET_IP="187.77.236.77"   # IP público do VPS Hostinger (A record target)
DOMAIN="2notasudi.com.br"

# Records que queremos GARANTIR (criar/atualizar)
REQUIRED_RECORDS=(
  "langfuse.2notasudi.com.br"
  "chatwoot.2notasudi.com.br"
  "argilla.2notasudi.com.br"
  "n8n.2notasudi.com.br"
  "supabase.2notasudi.com.br"
)
# Records que queremos REMOVER (zombie/legacy)
ZOMBIE_RECORDS=(
  "flow.2notasudi.com.br"
)

# Colors
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

log()  { printf "${BLUE}[%s]${NC} %s\n" "$(date +%H:%M:%S)" "$*" >&2; }
ok()   { printf "${GREEN}[OK]${NC} %s\n" "$*" >&2; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$*" >&2; }
err()  { printf "${RED}[ERR]${NC} %s\n" "$*" >&2; }

# Carregar token
load_token() {
  if [[ ! -f "$SECRET_FILE" ]]; then
    err "Arquivo de secret nao encontrado: $SECRET_FILE"
    err "Crie com: (touch $SECRET_FILE && chmod 600 $SECRET_FILE && echo 'CLOUDFLARE_API_TOKEN=...' >> $SECRET_FILE)"
    err "Token: dashboard.cloudflare.com/profile/api-tokens (perm Zone:DNS:Edit no zone 2notasudi.com.br)"
    return 1
  fi
  # shellcheck disable=SC1090
  source "$SECRET_FILE"
  if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    err "CLOUDFLARE_API_TOKEN nao definido em $SECRET_FILE"
    return 1
  fi
  return 0
}

# Cloudflare API call genérico
cf_api() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local url="https://api.cloudflare.com/client/v4${path}"
  local args=(-sS -X "$method" -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" -H "Content-Type: application/json")
  [[ -n "$body" ]] && args+=(-d "$body")
  curl "${args[@]}" "$url"
}

# Acha zone_id do domínio
get_zone_id() {
  cf_api GET "/zones?name=${DOMAIN}" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    if d.get('success') and d.get('result'):
        print(d['result'][0]['id'])
    else:
        print('NOT_FOUND', file=sys.stderr)
        sys.exit(2)
except Exception as e:
    print(f'PARSE_ERR: {e}', file=sys.stderr)
    sys.exit(3)
"
}

# Lista records existentes (filtra por nome)
list_records() {
  local zone_id="$1"
  cf_api GET "/zones/${zone_id}/dns_records?per_page=100" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if not d.get('success'):
    print('FAIL', file=sys.stderr)
    sys.exit(1)
for r in d.get('result', []):
    print(f\"{r['type']:6} {r['name']:50} -> {r.get('content','?'):20} (id={r['id']}, proxied={r.get('proxied',False)})\")
"
}

# Cria/atualiza A record
upsert_a_record() {
  local zone_id="$1"
  local name="$2"
  local content="$3"
  local proxied="${4:-false}"

  # Verifica se já existe
  local existing
  existing=$(cf_api GET "/zones/${zone_id}/dns_records?type=A&name=${name}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
recs = d.get('result', [])
if recs:
    print(recs[0]['id'], recs[0].get('content', ''))
else:
    print('')
" 2>/dev/null)

  local existing_id existing_ip
  existing_id=$(echo "$existing" | awk '{print $1}')
  existing_ip=$(echo "$existing" | awk '{print $2}')

  if [[ -n "$existing_id" && "$existing_ip" == "$content" ]]; then
    ok "A record $name → $content ja existe (id=$existing_id)"
    return 0
  fi

  if [[ -n "$existing_id" ]]; then
    log "Atualizando A record existente $name (id=$existing_id, old=$existing_ip, new=$content)"
    local body="{\"type\":\"A\",\"name\":\"$name\",\"content\":\"$content\",\"proxied\":$proxied,\"ttl\":1}"
    local resp
    resp=$(cf_api PUT "/zones/${zone_id}/dns_records/${existing_id}" "$body")
    if echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('success') else 1)" 2>/dev/null; then
      ok "Atualizado: $name → $content"
    else
      err "Falha ao atualizar: $resp"
      return 1
    fi
  else
    log "Criando novo A record $name → $content"
    local body="{\"type\":\"A\",\"name\":\"$name\",\"content\":\"$content\",\"proxied\":$proxied,\"ttl\":1}"
    local resp
    resp=$(cf_api POST "/zones/${zone_id}/dns_records" "$body")
    if echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('success') else 1)" 2>/dev/null; then
      ok "Criado: $name → $content"
    else
      err "Falha ao criar: $resp"
      return 1
    fi
  fi
}

# Remove A record
delete_a_record() {
  local zone_id="$1"
  local name="$2"

  local existing_id
  existing_id=$(cf_api GET "/zones/${zone_id}/dns_records?type=A&name=${name}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
recs = d.get('result', [])
if recs:
    print(recs[0]['id'])
" 2>/dev/null)

  if [[ -z "$existing_id" ]]; then
    ok "A record $name nao existe (ja removido)"
    return 0
  fi

  log "Removendo A record $name (id=$existing_id)"
  local resp
  resp=$(cf_api DELETE "/zones/${zone_id}/dns_records/${existing_id}")
  if echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('success') else 1)" 2>/dev/null; then
    ok "Removido: $name"
  else
    err "Falha ao remover: $resp"
    return 1
  fi
}

# Valida que cada subdomínio retorna 200 OK via Traefik (router tem que existir)
verify_endpoints() {
  log "Verificando HTTP 200/3xx em cada subdomínio criado..."
  local fail=0
  for name in "${REQUIRED_RECORDS[@]}"; do
    local code
    code=$(curl -sk -o /dev/null -m 10 -w "%{http_code}" "https://${name}/" 2>/dev/null || echo "000")
    if [[ "$code" =~ ^[2-3][0-9][0-9]$ ]]; then
      ok "$name: HTTP $code"
    else
      warn "$name: HTTP $code (DNS pode ter propagado mas router Traefik nao encontrado)"
      fail=$((fail + 1))
    fi
  done
  return $fail
}

# Main
main() {
  local cmd="${1:-help}"
  load_token || return 2
  local zone_id
  zone_id=$(get_zone_id) || return 3
  ok "Zone ID encontrado: $zone_id"

  case "$cmd" in
    add)
      log "Adicionando A records para ${REQUIRED_RECORDS[*]}"
      local rc=0
      for name in "${REQUIRED_RECORDS[@]}"; do
        upsert_a_record "$zone_id" "$name" "$TARGET_IP" "false" || rc=$?
      done
      log "Validacao HTTP (aguarda 30s para DNS propagar):"
      sleep 30
      verify_endpoints || rc=$?
      return $rc
      ;;
    remove-flow)
      log "Removendo A records zombie: ${ZOMBIE_RECORDS[*]}"
      local rc=0
      for name in "${ZOMBIE_RECORDS[@]}"; do
        delete_a_record "$zone_id" "$name" || rc=$?
      done
      return $rc
      ;;
    list)
      log "Listando todos os records do zone $DOMAIN:"
      list_records "$zone_id"
      ;;
    verify)
      verify_endpoints
      ;;
    help|--help|-h|"")
      cat <<EOF
Uso: $0 <comando>

Comandos:
  add            Cria/atualiza A records para langfuse/chatwoot/argilla + verifica 200 OK
  remove-flow    Remove A record zombie flow.2notasudi.com.br (turn 45)
  list           Lista todos os DNS records do zone 2notasudi.com.br
  verify         Verifica HTTP 200/3xx em cada subdomínio criado
  help           Mostra esta ajuda

Setup:
  1. Criar token Cloudflare: https://dash.cloudflare.com/profile/api-tokens
     - Template: "Edit zone DNS" (perm Zone:DNS:Edit)
     - Zone Resources: Include > Specific zone > 2notasudi.com.br
  2. Salvar em: $SECRET_FILE (chmod 600)
     Conteudo:
       CLOUDFLARE_API_TOKEN=seu-token-aqui
EOF
      ;;
    *)
      err "Comando desconhecido: $cmd"
      main help
      return 1
      ;;
  esac
}

main "$@"