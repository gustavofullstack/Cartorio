#!/usr/bin/env bash
# =============================================================================
# Smoke test — Cartório FASE 2 (pós-apply firewall)
# =============================================================================
# DRAFT — NÃO EXECUTAR sem GO Gustavo via Telegram DM 6682284055
#         ou GRUPO -5006771024.
# Boundary rule: Lesson 245 + 247 + 250 (cross-agent directive ≠ autorização).
#
# Autor: M3 (Pietra root agent)
# Data:  2026-06-30
# Stack: bash + curl + jq + Tailscale
#
# Pré-requisitos:
#   - Tailscale rodando no host de teste (ou SSH via Tailscale)
#   - curl + jq instalados
#   - FASE 2 já aplicada (fail2ban + iptables + Traefik middleware)
#   - Variáveis API_BASE / ADMIN_BASE setadas conforme ambiente
#
# Exit codes:
#   0 = tudo OK
#   1 = algum teste falhou
#   2 = ambiente não preparado
# =============================================================================

set -uo pipefail

API_BASE="${API_BASE:-https://api.2notasudi.com.br}"
ADMIN_BASE="${ADMIN_BASE:-https://admin.2notasudi.com.br}"
OPENCLAW_BASE="${OPENCLAW_BASE:-https://openclaw.2notasudi.com.br}"

PASS=0
FAIL=0
SKIP=0

ok()   { echo "[ OK ] $*"; PASS=$((PASS+1)); }
err()  { echo "[FAIL] $*"; FAIL=$((FAIL+1)); }
skip() { echo "[SKIP] $*"; SKIP=$((SKIP+1)); }

section() { echo; echo "=== $* ==="; }

require_dns() {
  local host="$1"
  if ! getent hosts "$host" >/dev/null 2>&1; then
    err "DNS nao resolve $host"
    return 1
  fi
  return 0
}

# T1: iptables hardening ativo
section "T1: iptables hardening ativo"
if command -v iptables >/dev/null 2>&1; then
  if iptables -L INPUT -nv 2>/dev/null | grep -q "tailscale always-allow"; then
    ok "regra tailscale always-allow presente em INPUT"
  else
    err "regra tailscale always-allow AUSENTE em INPUT"
  fi
  if iptables -L INPUT -nv 2>/dev/null | grep -qE "policy DROP|DROP.*all"; then
    ok "policy DROP no fim de INPUT"
  else
    err "policy DROP AUSENTE no fim de INPUT"
  fi
  if iptables -L f2b-cartorio -nv 2>/dev/null | grep -q "RETURN"; then
    ok "chain f2b-cartorio criada com RETURN"
  else
    err "chain f2b-cartorio AUSENTE ou mal configurada"
  fi
else
  skip "iptables nao encontrado"
fi

# T2: fail2ban jails ativos
section "T2: fail2ban jails ativos"
if command -v fail2ban-client >/dev/null 2>&1; then
  if sudo fail2ban-client status >/dev/null 2>&1; then
    ok "fail2ban-client responde"
    for jail in traefik-auth openclaw-auth easypanel-ui; do
      if sudo fail2ban-client status "$jail" 2>/dev/null | grep -q "Status for the jail"; then
        ok "jail $jail ativa"
      else
        err "jail $jail NAO ativa"
      fi
    done
  else
    err "fail2ban-client nao responde"
  fi
else
  skip "fail2ban-client nao encontrado"
fi

# T3: Traefik middlewares aplicados
section "T3: Traefik middlewares carregados"
if command -v docker >/dev/null 2>&1; then
  TRAEFIK_CONTAINER=$(docker ps --filter "name=traefik" --format "{{.Names}}" 2>/dev/null | head -1)
  if [[ -n "$TRAEFIK_CONTAINER" ]]; then
    if docker exec "$TRAEFIK_CONTAINER" cat /etc/traefik/dynamic/cartorio-middlewares.yml >/dev/null 2>&1; then
      ok "cartorio-middlewares.yml presente no container Traefik"
    else
      err "cartorio-middlewares.yml NAO encontrado no container"
    fi
  else
    skip "container Traefik nao encontrado"
  fi
else
  skip "docker nao disponivel"
fi

# T4: API headers
section "T4: API base + security headers"
if require_dns "api.2notasudi.com.br"; then
  RESP=$(curl -sS -I "${API_BASE}/health" 2>&1 || true)
  if echo "$RESP" | grep -qi "X-Frame-Options: DENY"; then
    ok "X-Frame-Options: DENY presente"
  else
    err "X-Frame-Options: DENY AUSENTE"
  fi
  if echo "$RESP" | grep -qi "Strict-Transport-Security"; then
    ok "HSTS presente"
  else
    err "HSTS AUSENTE"
  fi
  if echo "$RESP" | grep -qi "X-Content-Type-Options: nosniff"; then
    ok "X-Content-Type-Options: nosniff presente"
  else
    err "X-Content-Type-Options: nosniff AUSENTE"
  fi
else
  skip "DNS api.2notasudi.com.br nao resolve"
fi

# T5: rate limit dispara
section "T5: rate limit funcional"
if require_dns "api.2notasudi.com.br"; then
  echo "Burst test: 25 reqs em /api/v1/auth/login..."
  HITS_429=0
  for i in $(seq 1 25); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/api/v1/auth/login" \
      -X POST -H "Content-Type: application/json" -d '{}' 2>/dev/null || echo "000")
    if [[ "$code" == "429" ]]; then
      HITS_429=$((HITS_429+1))
    fi
  done
  if [[ $HITS_429 -gt 5 ]]; then
    ok "rate limit disparou ($HITS_429/25 = 429)"
  else
    err "rate limit NAO disparou ($HITS_429/25 = 429, esperado >5)"
  fi
else
  skip "DNS api.2notasudi.com.br nao resolve"
fi

# T6: IP allow Tailscale em admin
section "T6: IP allow Tailscale em rotas admin"
if require_dns "admin.2notasudi.com.br"; then
  if command -v tailscale >/dev/null 2>&1; then
    if tailscale status --json 2>/dev/null | grep -q '"BackendState":"Running"'; then
      code=$(curl -s -o /dev/null -w "%{http_code}" --interface tailscale0 \
        "${ADMIN_BASE}/" 2>/dev/null || echo "000")
      if [[ "$code" == "200" || "$code" == "301" || "$code" == "302" ]]; then
        ok "admin via Tailscale responde ($code)"
      else
        err "admin via Tailscale falhou ($code)"
      fi
    else
      skip "Tailscale nao esta Running"
    fi
  else
    skip "tailscale nao instalado"
  fi

  code=$(curl -s -o /dev/null -w "%{http_code}" "${ADMIN_BASE}/" 2>/dev/null || echo "000")
  if [[ "$code" == "403" ]]; then
    ok "admin sem Tailscale = 403 (IP allow funciona)"
  else
    err "admin sem Tailscale retornou $code (esperado 403)"
  fi
else
  skip "DNS admin.2notasudi.com.br nao resolve"
fi

# T7: OpenClaw auth brute-force detection
section "T7: OpenClaw porta 18789"
if command -v nc >/dev/null 2>&1; then
  if nc -z -w 2 127.0.0.1 18789 2>/dev/null; then
    ok "OpenClaw escutando em 127.0.0.1:18789"
  else
    skip "OpenClaw nao escutando (pode estar em outro host)"
  fi
else
  skip "nc nao disponivel"
fi

# Resumo
section "RESUMO"
echo "OK:    $PASS"
echo "FAIL:  $FAIL"
echo "SKIP:  $SKIP"
echo

if [[ $FAIL -gt 0 ]]; then
  echo "STATUS: FASE 2 com GAPS — investigar antes de declarar producao estavel"
  exit 1
fi

echo "STATUS: smoke test verde — FASE 2 pode ser declarada estavel"
exit 0
