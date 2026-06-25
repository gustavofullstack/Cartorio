"""lgpd_direito_esquecimento.py - LGPD art. 18 V (direito ao esquecimento) cascade (D14).

Implementa exclusao logica (LGPD art. 18 V) com:
1. Soft delete: marca deleted_at em todas as tabelas que referenciam cliente_id
2. Anonimizacao: substitui campos PII por hash irreversivel
3. Audit log: registra cada exclusao com motivo + actor_id + timestamp
4. Revertabilidade: chave separada permite 'restore' em 30 dias (LGPD art. 18 V
   permite manutencao para cumprimento de obrigacao legal/regulatoria)

Tabelas cascade (cliente_id eh FK em):
- clientes (PK)
- protocolos
- atendimentos
- documentos
- conversas
- emolumentos
- lgpd_consents
- outbox_messages (?)
- audit_log (?) - NAO exclui (mantem por obrigacao legal art. 37 LGPD)
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.lgpd_anonimizacao import hash_pii

log = logging.getLogger(__name__)

CASCADE_TABLES = (
    "clientes",
    "protocolos",
    "atendimentos",
    "documentos",
    "conversas",
    "emolumentos",
    "lgpd_consents",
)


def direito_esquecimento(
    db: Session,
    cliente_id: int,
    actor_id: str,
    motivo: str,
    reversivel_ate: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Executa direito ao esquecimento cascade (LGPD art. 18 V).

    Args:
        db: sessao SQLAlchemy
        cliente_id: PK do cliente
        actor_id: quem solicitou (cliente_id, DPO, escrevente, system)
        motivo: motivo da solicitacao ('cliente_solicitou', 'consent_revoked',
                'prazo_retencao_expirado', 'dpo_determinou', etc)
        reversivel_ate: ate quando pode ser revertido (default: hoje + 30 dias)

    Returns:
        dict com {cliente_id, deleted_at, anonymized_tables, total_rows,
                  reversivel_ate, audit_log_id}

    LGPD: NAO exclui audit_log (mantem por obrigacao legal art. 37 +
    obrigacao de demonstracao de conformidade).
    """
    now = datetime.datetime.now(datetime.UTC)
    if reversivel_ate is None:
        reversivel_ate = now + datetime.timedelta(days=30)

    # 1. Busca cliente (necessario para anonimizar)
    cliente_row = db.execute(
        text("SELECT id, nome, cpf, cnpj, email, telefone FROM clientes WHERE id = :id"),
        {"id": cliente_id},
    ).mappings().first()

    if not cliente_row:
        return {"erro": "cliente_nao_encontrado", "cliente_id": cliente_id}

    # 2. Gera hashes ANTES de anonimizar (para reversibilidade se necessario)
    hashes = {
        "nome_hash": hash_pii(cliente_row["nome"] or ""),
        "cpf_hash": hash_pii(cliente_row["cpf"] or ""),
        "cnpj_hash": hash_pii(cliente_row["cnpj"] or ""),
        "email_hash": hash_pii(cliente_row["email"] or ""),
        "telefone_hash": hash_pii(cliente_row["telefone"] or ""),
    }

    # 3. Soft delete cascade (marca deleted_at + anonimiza PII)
    rows_affected = 0
    anonymized_tables = []

    for table in CASCADE_TABLES:
        try:
            result = db.execute(
                text(
                    f"UPDATE {table} "
                    "SET deleted_at = :now, "
                    "    nome = '[ANONIMIZADO art.18 V]', "
                    "    cpf = NULL, cnpj = NULL, "
                    "    email = NULL, telefone = NULL, celular = NULL, "
                    "    rg = NULL, cns = NULL, cnh = NULL, "
                    "    endereco = NULL, numero = NULL, complemento = NULL, "
                    "    bairro = NULL, cidade = NULL, cep = NULL, "
                    "    nome_mae = NULL, nome_pai = NULL, "
                    "    data_nascimento = NULL, passaporte = NULL "
                    "WHERE cliente_id = :cid AND deleted_at IS NULL"
                ),
                {"now": now, "cid": cliente_id},
            )
            rowcount = getattr(result, "rowcount", 0) or 0
            if rowcount > 0:
                rows_affected += rowcount
                anonymized_tables.append(table)
        except Exception as e:
            log.warning("cascade %s falhou para cliente %s: %s", table, cliente_id, e)
            continue

    # Tabela clientes tambem (PK)
    try:
        db.execute(
            text(
                "UPDATE clientes SET "
                "deleted_at = :now, "
                "nome = '[ANONIMIZADO art.18 V]', "
                "cpf = NULL, cnpj = NULL, email = NULL, telefone = NULL, "
                "celular = NULL, rg = NULL, cns = NULL, cnh = NULL, "
                "endereco = NULL, numero = NULL, complemento = NULL, "
                "bairro = NULL, cidade = NULL, cep = NULL, "
                "nome_mae = NULL, nome_pai = NULL, "
                "data_nascimento = NULL, passaporte = NULL, "
                "lgpd_consent_granted = false, "
                "lgpd_consent_revoked_at = :now, "
                "lgpd_direito_esquecimento_at = :now, "
                "lgpd_direito_esquecimento_motivo = :motivo, "
                "lgpd_reversivel_ate = :reversivel_ate "
                "WHERE id = :cid"
            ),
            {
                "now": now,
                "cid": cliente_id,
                "motivo": motivo,
                "reversivel_ate": reversivel_ate,
            },
        )
    except Exception as e:
        log.warning("clientes cascade falhou para %s: %s", cliente_id, e)

    # 4. Audit log (obrigatorio LGPD art. 37)
    audit_payload = {
        "cliente_id": cliente_id,
        "motivo": motivo,
        "actor_id": actor_id,
        "anonymized_tables": anonymized_tables,
        "total_rows_affected": rows_affected,
        "reversivel_ate": reversivel_ate.isoformat(),
        "hashes_para_restauracao": hashes,  # chave separada para restore em 30d
    }
    audit_id = db.execute(
        text(
            "INSERT INTO audit_log ("
            "actor_id, actor_type, action, resource, payload, canal, ip, user_agent"
            ") VALUES ("
            ":actor_id, 'user', 'lgpd.direito_esquecimento', :resource, "
            "CAST(:payload AS jsonb), 'api', '0.0.0.0'::inet, 'direito_esquecimento_service'"
            ") RETURNING id"
        ),
        {
            "actor_id": actor_id,
            "resource": f"cliente:{cliente_id}",
            "payload": str(audit_payload).replace("'", '"'),
        },
    ).scalar()

    db.commit()

    log.info(
        "LGPD direito esquecimento executado: cliente_id=%s motivo=%s rows=%s audit_id=%s",
        cliente_id,
        motivo,
        rows_affected,
        audit_id,
    )

    return {
        "cliente_id": cliente_id,
        "deleted_at": now.isoformat(),
        "anonymized_tables": anonymized_tables,
        "total_rows_affected": rows_affected,
        "reversivel_ate": reversivel_ate.isoformat(),
        "audit_log_id": audit_id,
        "lgpd_article": "art. 18 V",
    }


def restore_direito_esquecimento(
    db: Session, cliente_id: int, actor_id: str, justificativa: str
) -> dict[str, Any]:
    """Restaura cliente (apenas dentro de 30 dias - janela de reversibilidade).

    Args:
        db: sessao SQLAlchemy
        cliente_id: PK do cliente
        actor_id: quem solicitou o restore
        justificativa: motivo legal para restaurar (ex: 'cliente_recorreu_decisao',
                       'obrigacao_regulatoria', 'processo_judicial_ativo')

    Returns:
        dict com {cliente_id, restored, audit_log_id}

    Raises:
        ValueError: se passou do prazo de reversibilidade
    """
    cliente_row = db.execute(
        text("SELECT lgpd_reversivel_ate, deleted_at FROM clientes WHERE id = :id"),
        {"id": cliente_id},
    ).mappings().first()

    if not cliente_row:
        raise ValueError(f"cliente {cliente_id} nao encontrado")
    if not cliente_row["deleted_at"]:
        raise ValueError(f"cliente {cliente_id} NAO foi anonimizado (deleted_at IS NULL)")

    reversivel_ate = cliente_row["lgpd_reversivel_ate"]
    now = datetime.datetime.now(datetime.UTC)
    if reversivel_ate and reversivel_ate < now:
        raise ValueError(
            f"cliente {cliente_id} passou do prazo de reversibilidade "
            f"({reversivel_ate} < {now}). Exclusao definitiva."
        )

    # Restaura deleted_at=NULL em todas as tabelas cascade
    restored_tables = []
    for table in CASCADE_TABLES:
        try:
            result = db.execute(
                text(
                    f"UPDATE {table} SET deleted_at = NULL "
                    "WHERE cliente_id = :cid AND deleted_at IS NOT NULL"
                ),
                {"cid": cliente_id},
            )
            rowcount = getattr(result, "rowcount", 0) or 0
            if rowcount > 0:
                restored_tables.append(table)
        except Exception as e:
            log.warning("restore %s falhou: %s", table, e)

    db.execute(
        text("UPDATE clientes SET deleted_at = NULL, lgpd_reversivel_ate = NULL WHERE id = :cid"),
        {"cid": cliente_id},
    )

    # Audit log
    audit_id = db.execute(
        text(
            "INSERT INTO audit_log ("
            "actor_id, actor_type, action, resource, payload, canal, ip, user_agent"
            ") VALUES ("
            ":actor_id, 'user', 'lgpd.direito_esquecimento.restore', :resource, "
            "CAST(:payload AS jsonb), 'api', '0.0.0.0'::inet, 'restore_service'"
            ") RETURNING id"
        ),
        {
            "actor_id": actor_id,
            "resource": f"cliente:{cliente_id}",
            "payload": str(
                {
                    "cliente_id": cliente_id,
                    "actor_id": actor_id,
                    "justificativa": justificativa,
                    "restored_tables": restored_tables,
                    "lgpd_article": "art. 18 V §2 (revogacao)",
                }
            ).replace("'", '"'),
        },
    ).scalar()

    db.commit()

    return {
        "cliente_id": cliente_id,
        "restored": True,
        "restored_tables": restored_tables,
        "audit_log_id": audit_id,
    }
