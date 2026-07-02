#!/usr/bin/env bash
# Para Linux/VPS: adiciona cron ao crontab
set -euo pipefail
PROJECT="/Users/gustavoalmeida/projetos/Cartorio"
SCRIPT="$PROJECT/.harness/loop-engineer/goal-loop-cron.sh"

# Adds to crontab (auto-validation every 4h, GOAL loop engine)
( crontab -l 2>/dev/null | grep -v "cartorio-goal-loop" || true ; \
  echo "0 */4 * * * /bin/bash $SCRIPT" \
) | crontab -

echo "✅ crontab entry added: 0 */4 * * * /bin/bash $SCRIPT"
echo "   Comando pra verificar: crontab -l | grep cartorio"
