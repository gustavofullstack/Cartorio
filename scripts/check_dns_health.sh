#!/usr/bin/env bash
# scripts/check_dns_health.sh
#
# Verifica saude DNS dos 10 subdominios prod de 2notasudi.com.br
# Reporta OK / NXDOMAIN para cada e retorna exit 0 se todos OK, 1 caso contrario.
#
# Uso:
#   bash scripts/check_dns_health.sh
#   make dns-check
#
# Requisito: dig (dnsutils) instalado. No macOS: brew install bind; no Ubuntu: apt install dnsutils.
#
# Exit codes:
#   0 = todos os 10 hosts resolvem (saida: 187.77.236.77 ou IP Cloudflare proxy)
#   1 = ao menos 1 host retornou NXDOMAIN
#   2 = erro de pre-requisito (dig ausente, etc)
#
# Modified by Gustavo Almeida — 2026-07-15 (cartorio-sre F4 / T057)

set -euo pipefail

readonly EXPECTED_IP="187.77.236.77"
readonly DOMAIN="2notasudi.com.br"

# Lista canonica de hosts (7 ativos + 3 pendentes ate merge Cloudflare UI Gustavo)
readonly HOSTS=(
    "api"
    "flow"
    "whatsapp"
    "chat"
    "agent"
    "supbase"
    "easypanel"
    "chatwoot"
    "n8n"
    "supabase"
)

# Cores
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log_info()  { printf "${YELLOW}[INFO]${NC} %s\n" "$*"; }
log_ok()    { printf "${GREEN}[OK]${NC} %s\n" "$*"; }
log_fail()  { printf "${RED}[FAIL]${NC} %s\n" "$*"; }

# Pre-check: dig existe?
if ! command -v dig >/dev/null 2>&1; then
    log_fail "dig nao encontrado. Instale: brew install bind (macOS) ou apt install dnsutils (Ubuntu)"
    exit 2
fi

log_info "Validando DNS de ${DOMAIN} (esperado: ${EXPECTED_IP} ou IP Cloudflare proxy)"
echo ""

ok_count=0
fail_count=0
failed_hosts=()

for host in "${HOSTS[@]}"; do
    fqdn="${host}.${DOMAIN}"
    # Tenta 1.1.1.1 (Cloudflare) — se proxy ON, retorna IP Cloudflare (104.x ou 172.x).
    # Se proxy OFF (DNS-only cinza), retorna 187.77.236.77.
    # Nao validamos o IP exato porque proxy pode estar ON/OFF dependendo do record.
    # Validacao: resposta nao vazia.
    result=$(dig +short "${fqdn}" A @1.1.1.1 2>/dev/null | head -1)

    if [ -z "${result}" ]; then
        log_fail "${fqdn} -> NXDOMAIN"
        fail_count=$((fail_count + 1))
        failed_hosts+=("${fqdn}")
    elif [ "${result}" = "${EXPECTED_IP}" ]; then
        log_ok "${fqdn} -> ${result} (IP real)"
        ok_count=$((ok_count + 1))
    else
        # IP Cloudflare proxy (104.x ou 172.x) — valido
        log_ok "${fqdn} -> ${result} (Cloudflare proxy)"
        ok_count=$((ok_count + 1))
    fi
done

echo ""
log_info "Total: ${ok_count} OK / ${fail_count} FAIL"

if [ "${fail_count}" -eq 0 ]; then
    log_ok "DNS health: PASS"
    exit 0
else
    log_fail "DNS health: FAIL (${fail_count} NXDOMAIN: ${failed_hosts[*]})"
    log_fail "Provisione os A records faltantes via infra/dns/CLOUDFLARE_RUNBOOK.md"
    exit 1
fi
