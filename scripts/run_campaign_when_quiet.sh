#!/bin/bash
# Aguarda janela quieta (15 min sem mensagens novas no chat 364) e dispara
# a campanha de 100 casos. Uso: bash scripts/run_campaign_when_quiet.sh
set -u
CHAT_ID=364
QUIET_MIN=15
LOG_DIR="/Users/gustavoalmeida/Projetos/Cartorio/artifacts/imessage"
mkdir -p "$LOG_DIR"
cd /Users/gustavoalmeida/Projetos/Cartorio

last_id=""
quiet_since=$(date +%s)

while true; do
  cur_id=$(imsg history --chat-id "$CHAT_ID" --limit 1 --json 2>/dev/null | python3 -c "import sys,json;print(json.loads(sys.stdin.readline()).get('id',''))" 2>/dev/null)
  now=$(date +%s)
  if [ -n "$cur_id" ] && [ "$cur_id" != "$last_id" ]; then
    last_id="$cur_id"
    quiet_since=$now
    echo "[$(date '+%H:%M:%S')] atividade na linha (id=$cur_id) — resetando janela"
  fi
  elapsed=$(( (now - quiet_since) / 60 ))
  if [ "$elapsed" -ge "$QUIET_MIN" ]; then
    echo "[$(date '+%H:%M:%S')] linha quieta por ${elapsed}min — disparando campanha"
    break
  fi
  sleep 120
done

TS=$(date +%Y%m%d_%H%M)
uv run python scripts/imessage_e2e_runner.py > "$LOG_DIR/campaign_100_${TS}.log" 2>&1
echo "[$(date '+%H:%M:%S')] campanha finalizada (exit=$?) — log: $LOG_DIR/campaign_100_${TS}.log"
