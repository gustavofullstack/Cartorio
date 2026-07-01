#!/usr/bin/env bash
# audit_chain_verify.sh — Verifica integridade da audit chain (hash + HMAC)
# Conforme ADR-009 (audit log imutável SHA256 + HMAC).
#
# Roda fn_audit_chain_verify do banco OU recalcula via API.
# Uso: bash scripts/audit_chain_verify.sh [db_target]

set -u

DB_NAME="${1:-postgres}"

echo "🔗 Audit chain verify (DB: ${DB_NAME})"
echo

# 1. Verifica se tabela audit_log existe
# Acha Postgres container por label, imagem, ou nome
PG_CONTAINER=$(docker ps --filter "ancestor=postgres:17" --format "{{.Names}}" | head -1)
[ -z "$PG_CONTAINER" ] && PG_CONTAINER=$(docker ps --filter "label=com.docker.swarm.service.name=cartorio_supabase" --format "{{.Names}}" | head -1)
[ -z "$PG_CONTAINER" ] && PG_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i supabase | head -1)
[ -z "$PG_CONTAINER" ] && { echo "❌ Nenhum container Postgres encontrado. Listando:"; docker ps --format "table {{.Names}}\t{{.Image}}" | head -10; exit 1; }
echo "  PG container: $PG_CONTAINER"

PG_USER=$(docker exec "$PG_CONTAINER" printenv POSTGRES_USER)
EXISTS=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM pg_tables WHERE tablename='audit_log'" 2>/dev/null || echo "0")

if [ "$EXISTS" = "1" ]; then
  echo "  ✅ Tabela audit_log existe em '${DB_NAME}'"

  # Conta entries
  TOTAL=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM audit_log" 2>/dev/null)
  echo "  Total entries: ${TOTAL:-?}"

  # Verifica função de verificação
  HAS_FN=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM pg_proc WHERE proname='fn_audit_chain_verify'" 2>/dev/null || echo "0")
  if [ "$HAS_FN" = "1" ]; then
    echo "  [1/2] Rodando fn_audit_chain_verify()..."
    docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -c "SELECT * FROM fn_audit_chain_verify();" 2>&1 | head -10
  else
    echo "  ⚠️ fn_audit_chain_verify NÃO existe"
  fi

  # Última entrada
  echo "  [2/2] Última entrada audit_log:"
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -c "SELECT id, acao, created_at FROM audit_log ORDER BY id DESC LIMIT 5;" 2>&1 | head -10
else
  echo "  ⚠️ Tabela audit_log NÃO existe em '${DB_NAME}'"
  echo "  API tem create_all() no lifespan, mas pode não ter rodado"
  echo "  Workaround: chamar POST /health/startup ou restart API"
fi

echo
echo "→ Para validar via API: curl https://api.2notasudi.com.br/api/v1/audit/verify"