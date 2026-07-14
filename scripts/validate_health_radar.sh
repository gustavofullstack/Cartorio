#!/usr/bin/env bash
# Validador oficial: lê o radar e exige 6/6 serviços online (exceto 1 com justificativa)
set -euo pipefail
URL=${CARTORIO_RADAR_URL:-https://api.2notasudi.com.br/api/v1/health/radar}
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
status=$(curl -ksS --max-time 15 -o "$tmp" -w '%{http_code}' "$URL")
if [ "$status" != "200" ]; then
  echo "FAIL: radar HTTP $status"
  exit 1
fi
python3 - "$tmp" <<'PY'
import json, sys
with open(sys.argv[1]) as fp:
    data = json.load(fp)
print('overall', data.get('status'))
for name, s in data.get('services', {}).items():
    print(f'{name:<12} {s}')
online = sum(1 for s in data.get('services', {}).values() if s == 'online')
if online < 4:
    print(f'FAIL: only {online} services online (need >=4)')
    sys.exit(2)
print(f'PASS: {online} services online')
PY
