#!/usr/bin/env bash
# tests/manual/verify_dns_records.sh
#
# Integration test manual (NAO roda no pytest — shell-only).
# Assume que Gustavo ja criou os 3 A records no Cloudflare UI:
#   - chatwoot.2notasudi.com.br -> 187.77.236.77
#   - n8n.2notasudi.com.br      -> 187.77.236.77
#   - supabase.2notasudi.com.br -> 187.77.236.77
#
# Executa:
#   bash tests/manual/verify_dns_records.sh
#   make dns-verify-records
#
# Resultado:
#   [WORK] = DNS resolveu (IP real ou Cloudflare proxy)
#   [HOLD] = ainda NXDOMAIN — Gustavo precisa provisionar
#
# Exit 0 se todos [WORK], 1 se algum [HOLD].
#
# Modified by Gustavo Almeida — 2026-07-15 (cartorio-sre F4 / T059)

set -euo pipefail

readonly EXPECTED_IP="187.77.236.77"
readonly DOMAIN="2notasudi.com.br"

readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# Os 3 hosts que dependem de Gustavo provisionar
readonly PENDING_HOSTS=(
    "chatwoot"
    "n8n"
    "supabase"
)

work_count=0
hold_count=0
hold_list=()

echo "============================================================"
echo "  DNS Records Integration Test — cartorio-sre F4 / T059"
echo "  Data: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================"
echo ""

if ! command -v dig >/dev/null 2>&1; then
    echo -e "${RED}[ERROR]${NC} dig nao encontrado. Instale bind/dnsutils."
    exit 2
fi

for host in "${PENDING_HOSTS[@]}"; do
    fqdn="${host}.${DOMAIN}"
    echo -n "Testing ${fqdn} ... "
    result=$(dig +short "${fqdn}" A @1.1.1.1 2>/dev/null | head -1)

    if [ -z "${result}" ]; then
        echo -e "${YELLOW}[HOLD]${NC} ainda NXDOMAIN — Gustavo precisa criar o A record no Cloudflare"
        hold_count=$((hold_count + 1))
        hold_list+=("${fqdn}")
    elif [ "${result}" = "${EXPECTED_IP}" ]; then
        echo -e "${GREEN}[WORK]${NC} -> ${result} (IP real)"
        work_count=$((work_count + 1))
    else
        # IP Cloudflare proxy (104.x / 172.x) — valido
        echo -e "${GREEN}[WORK]${NC} -> ${result} (Cloudflare proxy)"
        work_count=$((work_count + 1))
    fi
done

echo ""
echo "============================================================"
echo -e "Resultado: ${GREEN}${work_count} WORK${NC} / ${YELLOW}${hold_count} HOLD${NC} de ${#PENDING_HOSTS[@]} pendentes"
echo "============================================================"

if [ "${hold_count}" -eq 0 ]; then
    echo -e "${GREEN}[PASS]${NC} Todos os 3 A records foram provisionados. F4 esta completo."
    echo ""
    echo "Proximo passo (cartorio-sre F5): merge infra/traefik/ROUTERS_PENDENTES.yaml"
    echo "no /etc/traefik/dynamic/main.yaml do VPS."
    exit 0
else
    echo -e "${YELLOW}[HOLD]${NC} Gustavo precisa provisionar ${hold_count} A records no Cloudflare:"
    for h in "${hold_list[@]}"; do
        echo "  - $h -> 187.77.236.77"
    done
    echo ""
    echo "Ver infra/dns/CLOUDFLARE_RUNBOOK.md para passo-a-passo UI."
    exit 1
fi
