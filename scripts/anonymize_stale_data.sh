#!/bin/bash
# ============================================================================
# Wrapper em shell para purga e anonimização manual de dados (LGPD S2.T4)
# Executa anonymize_stale_data.py sob o ambiente virtual do Cartório.
#
# Modified by Gustavo Almeida.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Salva a DATABASE_URL informada pelo usuário antes de carregar o env
USER_DB_URL="$DATABASE_URL"

# Carrega ambiente do Cartório e ativa virtualenv
if [ -f "$PROJECT_ROOT/scripts/cartorio-env.sh" ]; then
    # Captura a saída silenciosamente e importa as envs
    source "$PROJECT_ROOT/scripts/cartorio-env.sh" > /dev/null
else
    # Fallback caso rode sem cartorio-env
    if [ -f "$PROJECT_ROOT/backend/.venv/bin/activate" ]; then
        source "$PROJECT_ROOT/backend/.venv/bin/activate"
    fi
fi

# Restaura a DATABASE_URL se informada pelo usuário
if [ ! -z "$USER_DB_URL" ]; then
    export DATABASE_URL="$USER_DB_URL"
fi

# Roda o script de purga manual de emergência
python3 "$SCRIPT_DIR/anonymize_stale_data.py"
