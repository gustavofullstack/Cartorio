#!/usr/bin/env bash
# ==============================================================================
# restore_whatsapp_session.sh — Restauração de Emergência de Sessão WhatsApp (Evolution API)
# Cartório 2º Tabelionato de Notas de Uberlândia / MG (CNS 05.799-2)
# ==============================================================================
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Uso: $0 <caminho_do_arquivo_super_backup.tar.gz>"
    exit 1
fi

ARCHIVE_FILE="$1"
if [ ! -f "$ARCHIVE_FILE" ]; then
    echo "[ERRO] Arquivo de backup não encontrado: $ARCHIVE_FILE"
    exit 1
fi

TMP_DIR="/tmp/restore_whatsapp_$(date +%s)"
mkdir -p "$TMP_DIR"
tar -xzf "$ARCHIVE_FILE" -C "$TMP_DIR"

echo "[INFO] Restaurando banco PostgreSQL 'evolution'..."
DB_CONTAINER=$(docker ps -q -f name=cartorio_banco_de_dados | head -n1)
if [ -n "$DB_CONTAINER" ] && [ -f "${TMP_DIR}/evolution_db.sql" ]; then
    docker exec -i "$DB_CONTAINER" psql -U admin -d evolution < "${TMP_DIR}/evolution_db.sql"
    echo "  -> Banco PostgreSQL 'evolution' restaurado."
fi

echo "[INFO] Restaurando arquivos de instâncias Baileys..."
INSTANCES_DIR="/etc/easypanel/projects/cartorio/evolution-api/volumes/instances"
if [ -f "${TMP_DIR}/instances_files.tar.gz" ]; then
    mkdir -p "$INSTANCES_DIR"
    tar -xzf "${TMP_DIR}/instances_files.tar.gz" -C "$INSTANCES_DIR"
    echo "  -> Arquivos de instâncias restaurados."
fi

rm -rf "$TMP_DIR"
echo "[SUCCESS] Restauração concluída com SUCESSO!"
