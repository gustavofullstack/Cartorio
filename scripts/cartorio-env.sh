#!/bin/bash
# Cartorio env loader - exporta variáveis mínimas para dev local
set -e
PROJECT_ROOT="/Users/gustavoalmeida/projetos/Cartorio"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        # Skip APP_ENV=test (force development)
        if [ "$key" = "APP_ENV" ]; then
            export APP_ENV=development
            continue
        fi
        # Export value (trim quotes)
        value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
        export "$key=$value"
    done < <(grep -v '^[[:space:]]*$' "$ENV_FILE" | grep -v '^[[:space:]]*#')
fi

# Force required
export APP_ENV=development
export AUDIT_HMAC_KEY="${AUDIT_HMAC_KEY:-470e2d9738e946fd41f556101c6796c700956c7291836c8fc493a94cd3e404f3}"
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN deve ser injetado pelo secret manager}"
export TELEGRAM_BOT_TOKEN

cd "$PROJECT_ROOT/backend"
source "$PROJECT_ROOT/backend/.venv/bin/activate"
echo "[cartorio-env] APP_ENV=$APP_ENV AUDIT_HMAC_KEY_len=${#AUDIT_HMAC_KEY} TELEGRAM_TOKEN_len=${#TELEGRAM_BOT_TOKEN}"
