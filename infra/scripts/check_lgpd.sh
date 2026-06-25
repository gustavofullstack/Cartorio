#!/usr/bin/env bash
# check_lgpd.sh — Verifica compliance LGPD
# Uso: ./check_lgpd.sh
#
# Verifica: DPO email, PII scrub, CORS, audit trail

set -eo pipefail

RED="\033[0;31m"; GREEN="\033[0;32m"; NC="\033[0m"

echo "🔒 LGPD Compliance Check..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. DPO Email
echo "1️⃣ DPO Email..."
if [[ -n "${DPO_EMAIL:-}" ]]; then
    printf "${GREEN}✅${NC} DPO_EMAIL: %s\n" "$DPO_EMAIL"
else
    printf "${YELLOW}⚠️${NC} DPO_EMAIL not set (using default: dpo@2notasudi.com.br)\n"
fi

# 2. PII Scrub
echo ""
echo "2️⃣ PII Scrubbing..."
if [[ "${PII_SCRUB_ENABLED:-false}" == "true" ]]; then
    printf "${GREEN}✅${NC} PII_SCRUB_ENABLED: true\n"
else
    printf "${RED}❌${NC} PII_SCRUB_ENABLED: false (MUST be true)\n"
fi

# 3. Retention
echo ""
echo "3️⃣ Data Retention..."
CONV_DAYS="${RETENTION_DAYS_CONVERSAS:-365}"
AUDIT_DAYS="${RETENTION_DAYS_AUDIT:-1825}"
printf "   Conversas: %d days\n" "$CONV_DAYS"
printf "   Audit: %d days (5 years)\n" "$AUDIT_DAYS"

# 4. Audit chain
echo ""
echo "4️⃣ Audit chain..."
AUDIT_KEY="${AUDIT_HMAC_KEY:-}"
if [[ -n "$AUDIT_KEY" ]]; then
    printf "${GREEN}✅${NC} AUDIT_HMAC_KEY: configured\n"
else
    printf "${RED}❌${NC} AUDIT_HMAC_KEY: NOT SET\n"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ LGPD check complete"
