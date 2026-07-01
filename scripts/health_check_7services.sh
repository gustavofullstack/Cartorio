#!/usr/bin/env bash
# health_check_7services.sh — Health check dos 7 serviços críticos do Cartório
# Emit 1 linha por serviço: STATUS name url latency_ms
# Stdout line-buffered pra Monitor tool pegar como evento.
# Sai se algum serviço crítico cair (≠ 200 ou timeout).

set -u

# TGB token — fallback hardcoded pro health (bot já validado via E2E 20/20)
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN:-$(grep '^TELEGRAM_BOT_TOKEN=' /Users/gustavoalmeida/projetos/Cartorio/.env 2>/dev/null | cut -d= -f2)}"

# Formato: NOME|URL|EXPECTED_RANGE (pipe pra não conflitar com : da URL)
SERVICES=(
  "API|https://api.2notasudi.com.br/api/v1/health/live|200-299"
  "N8N|https://flow.2notasudi.com.br/|200-299"
  "EVO|https://whatsapp.2notasudi.com.br/|200-299"
  "CW|https://chat.2notasudi.com.br/api|200-299"
  "SUP|https://supbase.2notasudi.com.br/auth/v1/health|200-401"
  "OC|https://agent.2notasudi.com.br/health|200-299"
  "TGB|https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe|200-299"
)

DOWN=0
for entry in "${SERVICES[@]}"; do
  IFS='|' read -r name url expect <<< "$entry"
  start=$(date +%s%N)
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 -L "$url" 2>/dev/null || echo "000")
  end=$(date +%s%N)
  ms=$(( (end - start) / 1000000 ))

  lo="${expect%%-*}"
  hi="${expect##*-}"
  code_num="$code"
  [[ "${code_num:0:1}" == "0" ]] && code_num=0
  if (( code_num >= lo && code_num <= hi )); then ok=OK; else ok=DOWN; fi

  printf '%s %s %s %dms code=%s expect=%s\n' "$ok" "$name" "$url" "$ms" "$code" "$expect"
  [[ "$ok" == "DOWN" ]] && DOWN=$((DOWN+1))
done

if [[ $DOWN -gt 0 ]]; then
  echo "ALERT: $DOWN serviço(s) DOWN em $(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi
exit $DOWN