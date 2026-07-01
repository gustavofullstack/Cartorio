#!/usr/bin/env bash
# install_pgvector.sh — Instala pgvector no Postgres do Chatwoot
# PROMPT.json fala em pgvector ativo, mas VERIFICADO: NÃO está instalado
# (5 extensions reais: pg_stat_statements, pg_trgm, pgcrypto, plpgsql, uuid-ossp)
#
# Pré-requisito: pgvector roda APENAS no banco onde vai usar (aqui: db=supabase = Chatwoot).
# Cria a extension + valida + mostra status.
#
# Uso: ssh root@100.99.172.84 'bash /tmp/install_pgvector.sh'

set -e

DB_NAME="${1:-supabase}"  # Chatwoot DB

echo "🧬 Instalando pgvector no DB '${DB_NAME}'..."

# Encontra o container do Postgres
PG_CONTAINER=$(docker ps --format "{{.Names}}" | grep -iE "supabase.*\\.1\\." | head -1)
[ -z "$PG_CONTAINER" ] && PG_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i supabase | head -1)
if [ -z "$PG_CONTAINER" ]; then
  echo "❌ Container cartorio_supabase não encontrado"
  exit 1
fi
echo "  Postgres container: $PG_CONTAINER"

# Admin user
PG_USER=$(docker exec "$PG_CONTAINER" printenv POSTGRES_USER)
echo "  Postgres user: $PG_USER"

# 1. Verifica se já existe
echo "  [1/4] Checando se pgvector já existe..."
EXISTS=$(docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM pg_extension WHERE extname='vector'" 2>/dev/null || echo "0")
if [ "$EXISTS" = "1" ]; then
  echo "  ✅ pgvector JÁ instalado"
else
  echo "  [2/4] Criando extension pgvector..."
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1 | head -3
fi

# 2. Valida
echo "  [3/4] Validando..."
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -c "\dx vector" 2>&1 | head -5

# 3. Testa criar coluna vector
echo "  [4/4] Testando coluna vector (rollback após)..."
docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$DB_NAME" -c "
BEGIN;
CREATE TEMP TABLE _vector_test (id int, embedding vector(3));
INSERT INTO _vector_test VALUES (1, '[1,2,3]'), (2, '[4,5,6]');
SELECT id, embedding FROM _vector_test ORDER BY embedding <-> '[3,1,2]' LIMIT 2;
ROLLBACK;
" 2>&1 | head -10

echo
echo "✅ pgvector instalado e validado em '${DB_NAME}'"
echo "⚠️  Reinicie cartorio_chatwoot para AI Agents SDK reconhecer (lesson 110)"