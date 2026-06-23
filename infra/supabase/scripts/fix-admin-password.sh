#!/usr/bin/env bash
# ==============================================================================
# fix-admin-password.sh — Idempotent fix for Supabase db-1 SCRAM hash mismatch
# ==============================================================================
#
# ----------------------------------------------------------------------------
#  ⛔ POR QUE EXISTE (LEIA ANTES DE EXECUTAR!)
# ----------------------------------------------------------------------------
#
# Em 2026-06-23 14:23 BRT, o cartorio teve P0 quando db-1 + supavisor-1
# entraram em restart loop porque o SCRAM hash do role supabase_admin (que
# a API cartorio usa direto em backend/.env DATABASE_URL) ficou fora de
# sync com o POSTGRES_PASSWORD do env do servico db-1.
#
# Root cause: na primeira implantacao, o initdb rodou com a senha REAL
# (e999b7439deb35dfe05c33f265dae1ea) gravada no volume cartorio_supabase_db-data.
# Porem, o env /etc/easypanel/projects/cartorio/supabase/.env ficou com o
# PLACEHOLDER do template Supabase (your-super-secret-and-long-postgres-password).
#
# Apos restart do db-1, o entrypoint.sh REOBSERVA que o cluster ja existe no
# volume e NAO re-inicializa (initdb idempotente). Mas o SCRAM hash no
# pg_authid continua sendo da senha REAL original. Resultado:
#   - Conexoes pre-restart continuam funcionando (pool cached)
#   - Conexoes novas (supavisor-1, auth-1, rest-1) falham 178/min
#   - /api/v1/health/radar GREEN (TCP only, falso positivo)
#
# Este script RE-ALINHA o SCRAM hash com o valor que esta em backend/.env.
# NAO mexe em volumes. NAO dropa dados. Idempotente (pode rodar N vezes).
#
# Para entender o contexto completo, leia:
#   docs/INCIDENT_2026-06-23_SUPABASE_AUTH.md
#   docs/adr/ADR-013-supabase-password-mismatch.md
#
# ----------------------------------------------------------------------------
#  USO
# ----------------------------------------------------------------------------
#
#   # Dry-run (default em CI): mostra o que SERIA feito, sem mutacao
#   ./fix-admin-password.sh
#
#   # Aplicar de verdade (EXIGE flag --i-know-what-im-doing + typing "FIX")
#   ./fix-admin-password.sh --apply --i-know-what-im-doing
#
#   # Mostrar RCA + explicacao detalhada
#   ./fix-admin-password.sh --explain
#
# Flags:
#   --dry-run            (default) Apenas mostra plano, sem ALTER USER
#   --apply              Aplica de verdade (exige --i-know-what-im-doing)
#   --i-know-what-im-doing  Skip confirmation prompt
#   --explain            Print RCA + why this script exists, then exit
#   --target-user USER   Override user (default: supabase_admin)
#   --target-password PWD  Override password (default: extract from backend/.env)
#   --help               Show this help
#
# Exit codes:
#   0  = success (dry-run OK or apply succeeded)
#   1  = pre-flight failed
#   2  = apply failed mid-way
#   3  = user aborted (confirmation declined)
#
# ----------------------------------------------------------------------------
#  ⚠️ GARANTIAS (NAO-AS-SERVICE)
# ----------------------------------------------------------------------------
#
# Este script NAO vai:
#   - Deletar/drop database, role, schema, table
#   - Recriar cluster (initdb)
#   - Mexer em volumes Docker
#   - Restart servicos (auth-1, rest-1, storage-1, supavisor-1) automaticamente
#   - Mexer em /etc/easypanel/projects/cartorio/supabase/.env
#
# Este script VAI (com --apply):
#   - docker exec db-1 psql -U postgres -c "ALTER USER supabase_admin PASSWORD '...'"
#   - Verificar sucesso via SELECT 1 com novo password
#   - Logar tudo em /tmp/cartorio-fix-admin-password.log
#
# ----------------------------------------------------------------------------

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
LOG_FILE="${CARTORIO_FIX_LOG:-/tmp/cartorio-fix-admin-password.log}"
BACKEND_ENV="${BACKEND_ENV:-/etc/easypanel/projects/cartorio/api/code/backend/.env}"
DB1_ENV="${DB1_ENV:-/etc/easypanel/projects/cartorio/supabase/.env}"
DOCKER_COMPOSE_PROJECT="${DOCKER_COMPOSE_PROJECT:-cartorio_supabase}"
DB_SERVICE_NAME="${DB_SERVICE_NAME:-db}"

MODE="dry-run"
SKIP_CONFIRM=0
TARGET_USER="supabase_admin"
TARGET_PASSWORD=""
SHOW_EXPLAIN=0

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

log() {
    local msg="[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

die() {
    log "ERRO: $*"
    exit 2
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "comando '$1' nao encontrado no PATH"
}

extract_password_from_backend_env() {
    if [[ -f "$BACKEND_ENV" ]]; then
        # DATABASE_URL=postgresql+psycopg://supabase_admin:PASSWORD@db:5432/cartorio
        local url
        url=$(grep -E "^DATABASE_URL=" "$BACKEND_ENV" | head -1 | cut -d= -f2-)
        if [[ -z "$url" ]]; then
            return 1
        fi
        # Extract password between ://user: and @db
        echo "$url" | sed -E 's|^postgresql(\+psycopg)?://[^:]+:([^@]+)@.*$|\2|'
        return 0
    fi
    return 1
}

check_docker_available() {
    require_cmd docker
    if ! docker info >/dev/null 2>&1; then
        die "Docker nao esta acessivel (docker info falhou)"
    fi
}

check_container_up() {
    local container="$DOCKER_COMPOSE_PROJECT-${DB_SERVICE_NAME}-1"
    local state
    state=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
    if [[ "$state" != "running" ]]; then
        die "container $container NAO esta UP (state=$state). Abortando."
    fi
    log "container $container esta UP"
}

check_backup_recent() {
    local backup_dir="/var/backups/cartorio"
    local max_age_hours=26
    if [[ ! -d "$backup_dir" ]]; then
        log "AVISO: $backup_dir nao existe (backup nao configurado)"
        return 1
    fi
    local latest
    latest=$(find "$backup_dir" -name "*.tar.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [[ -z "$latest" ]]; then
        log "AVISO: nenhum backup encontrado em $backup_dir"
        return 1
    fi
    local age_hours
    age_hours=$(( ( $(date +%s) - $(stat -c %Y "$latest") ) / 3600 ))
    if (( age_hours > max_age_hours )); then
        die "ULTIMO BACKUP muito antigo: $latest (${age_hours}h). Rode backup manual antes de fix. ADR-009."
    fi
    log "ultimo backup OK: $latest (${age_hours}h atras)"
    return 0
}

explain() {
    cat <<'EOF'

================================================================================
POR QUE ESTE SCRIPT EXISTE
================================================================================

Incidente P0 em 2026-06-23 14:23 BRT:

  cartorio_supabase-db-1 logs: "password authentication failed for user
  supabase_admin" 178 vezes/minuto CONTINUO

  cartorio_supabase-supavisor-1 em Restarting loop (~30s)

ROOT CAUSE:

  backend/.env (DATABASE_URL) tem a senha REAL:
    postgresql+psycopg://supabase_admin:e999b7439deb35dfe05c33f265dae1ea@db:5432/cartorio

  /etc/easypanel/projects/cartorio/supabase/.env (env do servico db-1) tem
  PLACEHOLDER do template Supabase:
    POSTGRES_PASSWORD=your-super-secret-and-long-postgres-password

  O cluster foi inicializado (initdb) com a senha REAL. O SCRAM hash dessa
  senha ficou gravado em pg_authid.rolpassword dentro do volume
  cartorio_supabase_db-data.

  Apos restart do db-1, o env com PLACEHOLDER nao consegue re-autenticar
  SCRAM (porque o hash gravado eh da senha REAL). Conexoes pre-restart
  continuam via pool cached, mas conexoes novas (supavisor-1, auth-1,
  rest-1, storage-1) falham.

O QUE ESTE SCRIPT FAZ:

  Roda dentro do container db-1 (como superuser 'postgres' via trust local):
    ALTER USER supabase_admin PASSWORD 'e999b7439deb35dfe05c33f265dae1ea'

  Isso REESCREVE o SCRAM hash em pg_authid com o hash da senha REAL
  (extraida de backend/.env DATABASE_URL).

  Conexoes cached permanecem funciona ndo (ja estavam autenticadas).
  Conexoes novas passam a funcionar (novo SCRAM hash bate com a senha
  que vao apresentar).

O QUE ESTE SCRIPT NAO FAZ:

  - NUNCA dropa database, role, schema
  - NUNCA recria cluster (initdb)
  - NUNCA mexe em volumes Docker
  - NUNCA restart servicos automaticamente
  - NUNCA altera /etc/easypanel/projects/cartorio/supabase/.env

DEPOIS DE APLICAR (ordem):

  1. docker service update --force cartorio_supabase_supavisor_1
  2. docker service update --force cartorio_supabase_auth_1
  3. docker service update --force cartorio_supabase_rest_1
  4. docker service update --force cartorio_supabase_storage_1
  5. Validar: curl http://localhost:8000/api/v1/health/radar
  6. Validar: curl http://localhost:8000/api/v1/audit/verify
  7. (Opcional, recomendado) ALTER env file db-1 com senha real para
     evitar drift em restart futuro. MAS ISSO NAO EH FEITO POR ESTE SCRIPT.

REFERENCIAS:
  - docs/INCIDENT_2026-06-23_SUPABASE_AUTH.md (runbook completo)
  - docs/adr/ADR-013-supabase-password-mismatch.md (decisao + RCA + lessons)

================================================================================
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --apply)
                MODE="apply"
                shift
                ;;
            --dry-run)
                MODE="dry-run"
                shift
                ;;
            --i-know-what-im-doing)
                SKIP_CONFIRM=1
                shift
                ;;
            --explain)
                SHOW_EXPLAIN=1
                shift
                ;;
            --target-user)
                TARGET_USER="$2"
                shift 2
                ;;
            --target-password)
                TARGET_PASSWORD="$2"
                shift 2
                ;;
            --backend-env)
                BACKEND_ENV="$2"
                shift 2
                ;;
            --db1-env)
                DB1_ENV="$2"
                shift 2
                ;;
            --project)
                DOCKER_COMPOSE_PROJECT="$2"
                shift 2
                ;;
            --db-service)
                DB_SERVICE_NAME="$2"
                shift 2
                ;;
            --help|-h)
                sed -n '2,/^set -euo pipefail/p' "$0" | head -90
                exit 0
                ;;
            *)
                die "Argumento desconhecido: $1 (use --help)"
                ;;
        esac
    done
}

confirm_apply() {
    if (( SKIP_CONFIRM == 1 )); then
        return 0
    fi
    echo ""
    echo "================================================================"
    echo "  ATENCAO: voce esta prestes a ALTER USER $TARGET_USER no cluster"
    echo "  db-1 do Supabase. Isso NAO deleta dados mas exige restart"
    echo "  manual de supavisor-1/auth-1/rest-1/storage-1 em seguida."
    echo "================================================================"
    echo ""
    echo "  Usuario alvo:    $TARGET_USER"
    echo "  Senha alvo:      ${TARGET_PASSWORD:0:4}...${TARGET_PASSWORD: -4} (length=${#TARGET_PASSWORD})"
    echo "  Container:       $DOCKER_COMPOSE_PROJECT-${DB_SERVICE_NAME}-1"
    echo "  Log file:        $LOG_FILE"
    echo "  Backend env:     $BACKEND_ENV"
    echo ""
    echo "  Para CONFIRMAR, digite exatamente: FIX"
    echo "  Para CANCELAR, pressione Enter"
    echo ""
    read -r -p "> " confirm
    if [[ "$confirm" != "FIX" ]]; then
        die "aplicacao cancelada pelo operador (confirm='$confirm')"
    fi
}

do_apply() {
    local container="$DOCKER_COMPOSE_PROJECT-${DB_SERVICE_NAME}-1"
    log "aplicando ALTER USER $TARGET_USER no container $container"
    log "comando: ALTER USER $TARGET_USER PASSWORD '<hidden>'"

    if ! docker exec "$container" \
        psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c \
        "ALTER USER $TARGET_USER WITH PASSWORD '$TARGET_PASSWORD';" \
        >> "$LOG_FILE" 2>&1; then
        die "ALTER USER falhou. Verifique $LOG_FILE."
    fi
    log "ALTER USER executado. Validando com novo password..."

    # Validacao: conecta via PG PASSWORD env var (nao conflita com psql args)
    if ! docker exec \
        -e PGPASSWORD="$TARGET_PASSWORD" \
        "$container" \
        psql -U "$TARGET_USER" -d postgres -c "SELECT 1 AS ok;" \
        >> "$LOG_FILE" 2>&1; then
        die "validacao falhou: novo password nao autenticou. Verifique $LOG_FILE."
    fi
    log "validacao OK: $TARGET_USER autentica com novo password"
    log "SUCESSO. Proximos passos:"
    log "  1. docker service update --force ${DOCKER_COMPOSE_PROJECT}_supavisor_1"
    log "  2. docker service update --force ${DOCKER_COMPOSE_PROJECT}_auth_1"
    log "  3. docker service update --force ${DOCKER_COMPOSE_PROJECT}_rest_1"
    log "  4. docker service update --force ${DOCKER_COMPOSE_PROJECT}_storage_1"
    log "  5. curl http://localhost:8000/api/v1/health/radar"
    log "  6. curl http://localhost:8000/api/v1/audit/verify"
}

do_dry_run() {
    log "DRY-RUN: nenhuma mutacao sera feita"
    log "PLANO:"
    log "  1. Pre-flight: docker OK, container UP, backup <26h"
    log "  2. Extrair senha real de $BACKEND_ENV"
    log "  3. Validar formato (esperado: 64 chars hex)"
    log "  4. Se --apply:"
    log "     - docker exec $DOCKER_COMPOSE_PROJECT-${DB_SERVICE_NAME}-1 \\"
    log "         psql -U postgres -c \"ALTER USER $TARGET_USER WITH PASSWORD '<hidden>'\""
    log "     - Validar: docker exec -e PGPASSWORD=... psql -U $TARGET_USER -c 'SELECT 1'"
    log "  5. NAO mexer em volumes, env files, restart services"
    log "DRY-RUN completo. Use --apply --i-know-what-im-doing para aplicar."
}

main() {
    parse_args "$@"

    log "================================================================"
    log "$SCRIPT_NAME iniciado (mode=$MODE user=$TARGET_USER pid=$$)"
    log "================================================================"

    if (( SHOW_EXPLAIN == 1 )); then
        explain
        exit 0
    fi

    # Pre-flight checks (sempre, mesmo em dry-run)
    check_docker_available
    check_container_up
    check_backup_recent || log "AVISO: pre-flight de backup falhou (continuando mesmo assim)"

    # Resolver senha alvo
    if [[ -z "$TARGET_PASSWORD" ]]; then
        if ! TARGET_PASSWORD=$(extract_password_from_backend_env); then
            die "nao foi possivel extrair senha de $BACKEND_ENV. Use --target-password."
        fi
        log "senha extraida de $BACKEND_ENV (length=${#TARGET_PASSWORD})"
    fi

    # Validar formato esperado: 64 chars hex
    if [[ ! "$TARGET_PASSWORD" =~ ^[a-f0-9]{64}$ ]]; then
        log "AVISO: senha nao parece ser 64-char hex SHA-256 hash. Continuando mesmo assim."
    fi

    if [[ "$MODE" == "apply" ]]; then
        confirm_apply
        do_apply
    else
        do_dry_run
    fi

    log "$SCRIPT_NAME finalizado OK"
}

main "$@"