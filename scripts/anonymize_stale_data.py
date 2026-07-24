#!/usr/bin/env python3
"""Script de emergência para purga e anonimização manual de dados de clientes (LGPD S2.T4).

Faz backup local preventivo da tabela 'cliente' em JSON, executa a purga e
anonimização de inativos, e registra o evento no audit_log. Em caso de falha,
aplica rollback transacional.

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Adiciona o diretório backend ao sys.path para permitir imports do app
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.db import session_scope
from app.models.cliente import Cliente
from app.jobs.retencao import run_retencao
from app.services.audit import AuditService

BACKUP_DIR = "/tmp"
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
BACKUP_PATH = os.path.join(BACKUP_DIR, f"backup_clientes_before_purge_{TIMESTAMP}.json")


def export_backup_preventivo(db) -> int:
    """Gera um arquivo JSON contendo o estado atual de todos os clientes no DB antes da purga."""
    clientes = db.query(Cliente).all()
    data = []
    for c in clientes:
        data.append({
            "id": c.id,
            "nome": c.nome,
            "cpf": c.cpf,
            "rg": c.rg,
            "email": c.email,
            "telefone": c.telefone,
            "cnh": c.cnh,
            "cns": c.cns,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "deleted_at": c.deleted_at.isoformat() if c.deleted_at else None,
            "motivo_encerramento": c.motivo_encerramento.value if c.motivo_encerramento else None,
        })

    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[BACKUP] Backup preventivo salvo em {BACKUP_PATH}")
    return len(data)


def run_manual_purge():
    print("==============================================================")
    print("      LIMPADEIRA LGPD - PURGA E ANONIMIZAÇÃO MANUAL DE EMERGÊNCIA")
    print("==============================================================")

    try:
        with session_scope() as db:
            # 1. Backup de Segurança
            total_records = export_backup_preventivo(db)
            print(f"[INFO] Registros pré-purga na tabela cliente: {total_records}")

            # 2. Executa a Retenção de Emergência
            print("[RUN] Executando processo de retenção (Fase 1 e Fase 2)...")
            result = run_retencao(db)

            # 3. Registra no Audit Log
            audit_payload = {
                "batch_id": result.batch_id,
                "scanned": result.scanned,
                "soft_deleted_5y_count": len(result.soft_deleted_5y),
                "soft_deleted_inativo_count": len(result.soft_deleted_inativo),
                "hard_deleted_count": len(result.hard_deleted_ids),
                "backup_file": BACKUP_PATH,
                "trigger": "manual_vps_cli",
            }
            
            AuditService.log_system_action(
                action="system.manual_purge",
                payload=audit_payload,
            )

            print("[SUCCESS] Processo de purga e anonimização concluído com sucesso!")
            print(f"  - Escaneados: {result.scanned}")
            print(f"  - Soft Deleted (5 anos): {len(result.soft_deleted_5y)}")
            print(f"  - Soft Deleted (Inativo): {len(result.soft_deleted_inativo)}")
            print(f"  - Hard Deleted (Físico): {len(result.hard_deleted_ids)}")
            print(f"  - Erros encontrados: {len(result.errors)}")
            for err in result.errors:
                print(f"    * {err}")

    except Exception as e:
        print(f"[FATAL ERROR] Execução abortada! Aplicado rollback transacional. Motivo: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_manual_purge()
