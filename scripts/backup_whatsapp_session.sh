#!/usr/bin/env bash
# ==============================================================================
# backup_whatsapp_session.sh — Super Backup de Conexão do WhatsApp (Evolution API)
# Cartório 2º Tabelionato de Notas de Uberlândia / MG (CNS 05.799-2)
# ==============================================================================
set -euo pipefail

BACKUP_DIR="/var/backups/cartorio/whatsapp"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="${BACKUP_DIR}/super_backup_whatsapp_${TIMESTAMP}"

echo "=============================================================================="
echo "[INFO] Iniciando Super Backup da Conexão WhatsApp (Evolution API)..."
echo "=============================================================================="

mkdir -p "${BACKUP_PATH}"

# 1. Export Postgres Evolution DB
echo "[1/3] Efetuando Dump do Banco de Dados PostgreSQL (evolution)..."
DB_CONTAINER=$(docker ps -q -f name=cartorio_banco_de_dados | head -n1)
if [ -n "$DB_CONTAINER" ]; then
    docker exec "$DB_CONTAINER" pg_dump -U admin evolution > "${BACKUP_PATH}/evolution_db.sql"
    echo "  -> Dump Postgres salvo em ${BACKUP_PATH}/evolution_db.sql ($(du -h "${BACKUP_PATH}/evolution_db.sql" | cut -f1))"
else
    echo "  [WARN] Container cartorio_banco_de_dados não encontrado!"
fi

# 2. Backup do Volume de Instâncias (Baileys keys / sessions)
echo "[2/3] Efetuando Backup dos arquivos de Sessão / Instâncias Baileys..."
INSTANCES_DIR="/var/lib/docker/volumes/cartorio_whatsapp-api_instances/_data"
if [ ! -d "$INSTANCES_DIR" ]; then
    INSTANCES_DIR="/etc/easypanel/projects/cartorio/evolution-api/volumes/instances"
fi

if [ -d "$INSTANCES_DIR" ]; then
    tar -czf "${BACKUP_PATH}/instances_files.tar.gz" -C "$INSTANCES_DIR" .
    echo "  -> Arquivos de instâncias salvos em ${BACKUP_PATH}/instances_files.tar.gz ($(du -h "${BACKUP_PATH}/instances_files.tar.gz" | cut -f1))"
else
    echo "  [WARN] Diretório de instâncias não encontrado!"
fi

# 3. Empacotar Super Backup Final em um único arquivo tar.gz imutável
FINAL_ARCHIVE="${BACKUP_DIR}/SUPER_BACKUP_WHATSAPP_CARTORIO_AGENT_${TIMESTAMP}.tar.gz"
tar -czf "$FINAL_ARCHIVE" -C "$BACKUP_PATH" .
rm -rf "$BACKUP_PATH"

echo "=============================================================================="
echo "[SUCCESS] Super Backup gerado com SUCESSO!"
echo "Arquivo final: $FINAL_ARCHIVE ($(du -h "$FINAL_ARCHIVE" | cut -f1))"
echo "=============================================================================="
