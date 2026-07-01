#!/usr/bin/env bash
# health_check_7services.sh — Health check dos 7 serviços críticos do Cartório
# Emit 1 linha por serviço: STATUS name url latency_ms
# Stdout line-buffered pra Monitor tool pegar como evento.
# Sai se algum serviço crítico cair (≠ OK).

set -u

# TGB token — resolve a partir do backend/.env caso não esteja setado no env
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN:-$(grep '^TELEGRAM_BOT_TOKEN=' /Users/gustavoalmeida/projetos/Cartorio/backend/.env 2>/dev/null | cut -d= -f2 | tr -d '\"')}"

# Formato: NOME|TIPO|ENDERECO|EXPECTED
SERVICES=(
  "API|HTTP|https://api.2notasudi.com.br/api/v1/health/live|200-299"
  "EVO|HTTP|https://whatsapp.2notasudi.com.br/|200-299"
  "CW|HTTP|https://chat.2notasudi.com.br/api|200-299"
  "OC|HTTP|https://agent.2notasudi.com.br/health|200-299"
  "TGB|HTTP|https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe|200-299"
  "SUP|TCP|100.99.172.84:5094|open"
  "REDIS|TCP|100.99.172.84:1001|open"
)

DOWN=0
for entry in "${SERVICES[@]}"; do
  IFS='|' read -r name type addr expect <<< "$entry"
  start=$(date +%s%N)

  if [[ "$type" == "HTTP" ]]; then
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 -L "$addr" 2>/dev/null || echo "000")
    lo="${expect%%-*}"
    hi="${expect##*-}"
    code_num="$code"
    [[ "${code_num:0:1}" == "0" ]] && code_num=0
    if (( code_num >= lo && code_num <= hi )); then ok=OK; else ok=DOWN; fi
  else
    # TCP check
    ip="${addr%%:*}"
    port="${addr##*:}"
    if nc -z -w3 "$ip" "$port" 2>/dev/null; then
      ok=OK
      code="open"
    else
      ok=DOWN
      code="closed"
    fi
  fi

  end=$(date +%s%N)
  ms=$(( (end - start) / 1000000 ))

  printf '%s %s %s %dms code=%s expect=%s\n' "$ok" "$name" "$addr" "$ms" "$code" "$expect"
  [[ "$ok" == "DOWN" ]] && DOWN=$((DOWN+1))
done

if [[ $DOWN -gt 0 ]]; then
  echo "ALERT: $DOWN serviço(s) DOWN em $(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi
exit $DOWN