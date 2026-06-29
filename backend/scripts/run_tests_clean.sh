#!/usr/bin/env bash
# run_tests_clean.sh — executa pytest com env vars sensiveis "limpas"
# para nao vazar settings de producao (.env carregado em shell)
# para o conftest (que usa setdefault, nao sobrescreve valores ja setados).
#
# Variaveis que precisam ser unsetadas antes do pytest:
# - AUDIT_HMAC_KEY (conftest seta a*64)
# - DATABASE_URL (conftest seta sqlite)
# - CHATWOOT_ACCOUNT_ID / CHATWOOT_INBOX_ID (conftest seta 0)
# - CARTORIO_API_KEY_HEADER (nao interfere, mas zera por higiene)
# - TELEGRAM_WEBHOOK_SECRET (conftest NAO seta; precisa ser None para webhook tests)
# - TELEGRAM_BOT_TOKEN_CARTORIO / TELEGRAM_BOT_TOKEN_TEST_CARTORIO / TELEGRAM_BOT_TOKEN_MAVIS
# - TELEGRAM_BOT_USERNAME_TEST / TELEGRAM_BOT_USERNAME_PIETRA / TELEGRAM_GROUP_PIETRA_SQUAD
#
# Uso:
#   ./scripts/run_tests_clean.sh                    # roda pytest completo
#   ./scripts/run_tests_clean.sh tests/test_foo.py  # roda arquivo especifico
#   ./scripts/run_tests_clean.sh -k "audit"        # roda por keyword
#
# Modified by Gustavo Almeida

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Variaveis que interferem no conftest (setdefault nao sobrescreve valor existente)
ENV_UNSET=(
  AUDIT_HMAC_KEY
  DATABASE_URL
  CARTORIO_API_KEY_HEADER
  CHATWOOT_ACCOUNT_ID
  CHATWOOT_INBOX_ID
  TELEGRAM_WEBHOOK_SECRET
  TELEGRAM_BOT_TOKEN_CARTORIO
  TELEGRAM_BOT_TOKEN_TEST_CARTORIO
  TELEGRAM_BOT_TOKEN_MAVIS
  TELEGRAM_BOT_USERNAME_TEST
  TELEGRAM_BOT_USERNAME_PIETRA
  TELEGRAM_GROUP_PIETRA_SQUAD
)

# Monta comando env -u para cada var
ENV_CMD=()
for v in "${ENV_UNSET[@]}"; do
  ENV_CMD+=(-u "$v")
done

# Garante venv existe
if [[ ! -d .venv ]]; then
  echo "[run_tests_clean] .venv nao encontrado em backend/." >&2
  exit 1
fi

# Se nao passou args, roda tudo (default do pyproject)
if [[ $# -eq 0 ]]; then
  echo "[run_tests_clean] Rodando pytest completo (gates: coverage >=90%)..."
  exec env "${ENV_CMD[@]}" .venv/bin/pytest "$@"
fi

echo "[run_tests_clean] Rodando pytest com args: $*"
exec env "${ENV_CMD[@]}" .venv/bin/pytest "$@"