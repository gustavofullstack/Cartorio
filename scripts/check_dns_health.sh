#!/usr/bin/env bash
# scripts/check_dns_health.sh
#
# Verifica saude DNS dos 10 subdominios prod de 2notasudi.com.br
# Reporta OK / NXDOMAIN para cada e retorna exit code conforme MODE.
#
# Uso:
#   bash scripts/check_dns_health.sh              # soft (default) — 7 core OK => exit 0
#   MODE=strict bash scripts/check_dns_health.sh  # todos os 10 devem resolver
#   DNS_CHECK_STRICT=1 bash scripts/check_dns_health.sh  # alias de MODE=strict
#   make dns-check                                # soft via Makefile
#   make dns-check-strict                         # strict
#
# Requisito: dig (dnsutils) instalado. No macOS: brew install bind; no Ubuntu: apt install dnsutils.
#
# Exit codes:
#   0 = soft: core 7 OK (HOLD NXDOMAIN nos 3 opcionais e OK em soft)
#       strict: todos os 10 hosts resolvem
#   1 = soft: ao menos 1 host CORE falhou
#       strict: ao menos 1 host (core ou optional) falhou
#   2 = erro de pre-requisito (dig ausente, etc)
#
# Modified by Gustavo Almeida — 2026-07-17 (cartorio-sre G7 Wave28 / G7.12.T2 soft mode)

set -euo pipefail

readonly EXPECTED_IP="187.77.236.77"
readonly DOMAIN="2notasudi.com.br"

# Core (7) — devem sempre resolver em prod
readonly CORE_HOSTS=(
    "api"
    "flow"
    "whatsapp"
    "chat"
    "agent"
    "supbase"
    "easypanel"
)

# Optional / HOLD-GUSTAVO UI (3) — A records chatwoot/n8n/supabase ainda nao provisionados
readonly OPTIONAL_HOSTS=(
    "chatwoot"
    "n8n"
    "supabase"
)

# Lista completa (core + optional) para iteracao
readonly HOSTS=("${CORE_HOSTS[@]}" "${OPTIONAL_HOSTS[@]}")

# MODE: soft (default) | strict
# Prefer DNS_CHECK_STRICT=1 for CI gate full; soft allows make dns-check green on 7/10 HOLD.
_mode_raw="${MODE:-}"
if [ -z "${_mode_raw}" ]; then
    if [ "${DNS_CHECK_STRICT:-0}" = "1" ] || [ "${DNS_CHECK_STRICT:-}" = "true" ]; then
        _mode_raw="strict"
    else
        _mode_raw="soft"
    fi
fi
MODE="$(printf '%s' "${_mode_raw}" | tr '[:upper:]' '[:lower:]')"
case "${MODE}" in
    soft|strict) ;;
    *)
        printf '[FAIL] MODE invalido: %s (use soft|strict)\n' "${MODE}" >&2
        exit 2
        ;;
esac

# Cores
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log_info()  { printf "${YELLOW}[INFO]${NC} %s\n" "$*"; }
log_ok()    { printf "${GREEN}[OK]${NC} %s\n" "$*"; }
log_fail()  { printf "${RED}[FAIL]${NC} %s\n" "$*"; }
log_hold()  { printf "${YELLOW}[HOLD]${NC} %s\n" "$*"; }

is_core_host() {
    local h="$1"
    local c
    for c in "${CORE_HOSTS[@]}"; do
        if [ "${c}" = "${h}" ]; then
            return 0
        fi
    done
    return 1
}

# Pre-check: dig existe?
if ! command -v dig >/dev/null 2>&1; then
    log_fail "dig nao encontrado. Instale: brew install bind (macOS) ou apt install dnsutils (Ubuntu)"
    exit 2
fi

log_info "Validando DNS de ${DOMAIN} (esperado: ${EXPECTED_IP} ou IP Cloudflare proxy)"
log_info "MODE=${MODE} (soft=core7; strict=all10; force strict: DNS_CHECK_STRICT=1)"
echo ""

ok_count=0
fail_count=0
core_fail_count=0
optional_fail_count=0
failed_hosts=()
core_failed_hosts=()
optional_failed_hosts=()

for host in "${HOSTS[@]}"; do
    fqdn="${host}.${DOMAIN}"
    # Tenta 1.1.1.1 (Cloudflare resolver) — se proxy ON, retorna IP Cloudflare (104.x ou 172.x).
    # Se proxy OFF (DNS-only cinza), retorna 187.77.236.77.
    # Nao validamos o IP exato porque proxy pode estar ON/OFF dependendo do record.
    # Validacao: resposta nao vazia.
    result=$(dig +short "${fqdn}" A @1.1.1.1 2>/dev/null | head -1)

    if [ -z "${result}" ]; then
        if is_core_host "${host}"; then
            log_fail "${fqdn} -> NXDOMAIN (CORE)"
            core_fail_count=$((core_fail_count + 1))
            core_failed_hosts+=("${fqdn}")
        else
            if [ "${MODE}" = "strict" ]; then
                log_fail "${fqdn} -> NXDOMAIN (OPTIONAL/strict)"
            else
                log_hold "${fqdn} -> NXDOMAIN (OPTIONAL HOLD — esperado ate UI Cloudflare/DNS)"
            fi
            optional_fail_count=$((optional_fail_count + 1))
            optional_failed_hosts+=("${fqdn}")
        fi
        fail_count=$((fail_count + 1))
        failed_hosts+=("${fqdn}")
    elif [ "${result}" = "${EXPECTED_IP}" ]; then
        log_ok "${fqdn} -> ${result} (IP real)"
        ok_count=$((ok_count + 1))
    else
        # IP Cloudflare proxy (104.x ou 172.x) — valido
        log_ok "${fqdn} -> ${result} (Cloudflare proxy / other)"
        ok_count=$((ok_count + 1))
    fi
done

echo ""
log_info "Total: ${ok_count} OK / ${fail_count} FAIL (core_fail=${core_fail_count} optional_fail=${optional_fail_count}) MODE=${MODE}"

if [ "${MODE}" = "soft" ]; then
    if [ "${core_fail_count}" -eq 0 ]; then
        log_ok "DNS health: PASS (soft) — core ${#CORE_HOSTS[@]}/${#CORE_HOSTS[@]} OK"
        if [ "${optional_fail_count}" -gt 0 ]; then
            log_hold "Optional HOLD NXDOMAIN (${optional_fail_count}): ${optional_failed_hosts[*]}"
            log_hold "Provisione via infra/dns/CLOUDFLARE_RUNBOOK.md + docs/DNS_A_RECORDS_WAVE28_G7.md"
            log_info "Para exigir 10/10: MODE=strict make dns-check  (ou make dns-check-strict)"
        fi
        exit 0
    else
        log_fail "DNS health: FAIL (soft) — core NXDOMAIN: ${core_failed_hosts[*]}"
        log_fail "Core hosts devem resolver. Ver infra/dns/CLOUDFLARE_DNS_RECORDS.md"
        exit 1
    fi
else
    # strict
    if [ "${fail_count}" -eq 0 ]; then
        log_ok "DNS health: PASS (strict) — ${#HOSTS[@]}/${#HOSTS[@]} OK"
        exit 0
    else
        log_fail "DNS health: FAIL (strict) (${fail_count} NXDOMAIN: ${failed_hosts[*]})"
        log_fail "Provisione os A records faltantes via infra/dns/CLOUDFLARE_RUNBOOK.md"
        exit 1
    fi
fi
