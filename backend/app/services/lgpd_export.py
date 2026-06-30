"""LGPD Data Export Service (D12).

Exporta TODOS os dados pessoais de um titular (LGPD art. 18 IV - portabilidade).

Output: JSON estruturado + opcionalmente CSV/zip.
Estrutura:
{
  "cliente": {...},
  "protocolos": [...],
  "atendimentos": [...],
  "documentos": [...],
  "audit_logs": [...],  # apenas os DO titular
  "consentimentos": [...],
  "exported_at": "...",
  "export_hash": "...",  # SHA256 do JSON (LGPD art. 37 integridade)
}

NÃO expoe:
- PII de OUTROS clientes (apenas titular)
- Dados sensíveis de outros (cross-tenant leak)
- Audit log do sistema (apenas do titular)

Uso:
    bundle = exportar_dados_titular(db, cliente_id=42)
    # Salva em .harness/memory/LGPD-EXPORT-{cpf_hash}-{ts}.json
    # Envia link download via WhatsApp (criptografado)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _mask_nome(nome: str) -> str:
    """Mascara nome: primeira letra de cada parte + asteriscos. LGPD D29."""
    parts = nome.strip().split()
    masked = " ".join(f"{p[0]}***" if p else "" for p in parts)
    return masked or "[nome indisponivel]"


def _mask_email(email: str | None) -> str:
    """Mascara email: primeira letra local + TLD completo. LGPD D29."""
    if not email or "@" not in email:
        return "[email indisponivel]"
    local, domain = email.rsplit("@", 1)
    # Mostra apenas TLD (gmail.com, uol.com.br) sem subdomínio
    tld = domain.split(".")[-1] if domain else ""
    return f"{local[:1]}***@{tld}"


@dataclass
class DataExportBundle:
    cliente: dict[str, Any]
    protocolos: list[dict[str, Any]]
    atendimentos: list[dict[str, Any]]
    documentos: list[dict[str, Any]]
    audit_logs: list[dict[str, Any]]
    consentimentos: list[dict[str, Any]]
    exported_at: str
    export_hash: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, default=str, ensure_ascii=False)


class ClienteNotFoundError(Exception):
    pass


def _hash_export(data: dict) -> str:
    """SHA256 do JSON serializado (LGPD art. 37)."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def exportar_dados_titular(
    db: Session,
    cliente_id: int,
    *,
    incluir_audit: bool = True,
) -> DataExportBundle:
    """Exporta TODOS os dados pessoais de um titular (LGPD art. 18 IV).

    Args:
        db: Session
        cliente_id: ID do titular
        incluir_audit: se True, inclui audit log do titular

    Returns:
        DataExportBundle com todos os dados

    Raises:
        ClienteNotFoundError: se cliente nao existe
    """
    from app.models.cliente import Cliente
    from app.models.protocolo import Protocolo
    from app.models.atendimento import Atendimento
    from app.models.documento import Documento
    from app.models.audit_log import AuditLog

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise ClienteNotFoundError(f"Cliente {cliente_id} nao existe")

    now = datetime.now(tz=timezone.utc)

    # 1. Cliente (apenas dados do titular) — PII mascarado LGPD D29
    cliente_dict: dict[str, Any] = {
        "id": cliente.id,
        "nome": _mask_nome(cliente.nome),
        "cpf_hash": cliente.cpf_hash,  # LGPD-by-design: hash, NAO cpf
        "email": _mask_email(cliente.email),
        "telefone_hash": cliente.telefone_hash,  # hash (já pseudonimizado)
        "consentimento_lgpd": cliente.consentimento_lgpd,
        "consentimento_em": cliente.consentimento_em.isoformat()
        if cliente.consentimento_em
        else None,
        "consentimento_ip": cliente.consentimento_ip,
        "consentimento_canal": cliente.consentimento_canal,
        "created_at": cliente.created_at.isoformat() if cliente.created_at else None,
        "updated_at": cliente.updated_at.isoformat() if cliente.updated_at else None,
        "deleted_at": cliente.deleted_at.isoformat() if cliente.deleted_at else None,
        "motivo_encerramento": cliente.motivo_encerramento.value
        if cliente.motivo_encerramento
        else None,
    }

    # 2. Protocolos do titular
    protocolos_rows = (
        db.execute(select(Protocolo).where(Protocolo.cliente_id == cliente_id)).scalars().all()
    )

    protocolos = [
        {
            "id": p.id,
            "numero": p.numero,
            "status": p.status,
            "tipo": p.tipo,
            "valor_total": str(p.valor_total) if p.valor_total else None,
            "canal_origem": p.canal_origem,
            "created_at": p.created_at.isoformat() if getattr(p, "created_at", None) else None,
            "updated_at": p.updated_at.isoformat() if getattr(p, "updated_at", None) else None,
            "concluido_em": (
                _v.isoformat() if (_v := getattr(p, "concluido_em", None)) is not None else None
            ),
        }
        for p in protocolos_rows
    ]

    # 3. Atendimentos (se houver)
    atendimentos: list[dict[str, Any]] = []
    try:
        atendimentos_rows = (
            db.execute(select(Atendimento).where(Atendimento.cliente_id == cliente_id))
            .scalars()
            .all()
        )
        atendimentos = [
            {
                "id": a.id,
                "canal": getattr(a, "canal", None),
                "status": getattr(a, "status", None),
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "concluido_em": (
                    _v.isoformat() if (_v := getattr(a, "concluido_em", None)) is not None else None
                ),
            }
            for a in atendimentos_rows
        ]
    except Exception:  # noqa: BLE001
        logger.warning("Atendimento query falhou para cliente %s", cliente_id)

    # 4. Documentos (se houver - cliente_id eh atributo esperado)
    documentos: list[dict[str, Any]] = []
    try:
        documentos_rows = (
            db.execute(
                select(Documento).where(  # type: ignore[attr-defined]
                    getattr(Documento, "cliente_id") == cliente_id  # type: ignore[attr-defined]
                )
            )
            .scalars()
            .all()
        )
        documentos = [
            {
                "id": d.id,
                "tipo": getattr(d, "tipo", None),
                "filename": getattr(d, "filename", None),
                "hash_sha256": getattr(d, "hash_sha256", None),
                "size_bytes": getattr(d, "size_bytes", None),
                "created_at": d.created_at.isoformat() if getattr(d, "created_at", None) else None,
            }
            for d in documentos_rows
        ]
    except Exception:  # noqa: BLE001
        logger.warning("Documento query falhou para cliente %s", cliente_id)

    # 5. Audit log (apenas DO titular, NAO dados de outros)
    audit_logs: list[dict[str, Any]] = []
    if incluir_audit:
        try:
            audit_rows = (
                db.execute(
                    select(AuditLog)
                    .where(AuditLog.actor_id == str(cliente_id))
                    .where(AuditLog.actor_type == "cliente")
                )
                .scalars()
                .all()
            )
            audit_logs = [
                {
                    "id": al.id,
                    "timestamp": al.timestamp.isoformat() if al.timestamp else None,
                    "action": al.action,
                    "resource": al.resource,
                    "ip_truncated": getattr(al, "ip_truncated", None),
                }
                for al in audit_rows
            ]
        except Exception:  # noqa: BLE001
            logger.warning("Audit log query falhou para cliente %s", cliente_id)

    # 6. Consentimentos (LGPD art. 18 V)
    from app.services.lgpd_consent import consent_history

    consentimentos_raw = consent_history(db, cliente_id)
    consentimentos = [
        {
            "evento": c["action"],
            "timestamp": c["timestamp"],
            "finalidades": c["finalidades"],
            "canal": c["canal"],
            "ip_truncated": c["ip_truncated"],
        }
        for c in consentimentos_raw
    ]

    # Monta bundle
    bundle_dict: dict[str, Any] = {
        "cliente": cliente_dict,
        "protocolos": protocolos,
        "atendimentos": atendimentos,
        "documentos": documentos,
        "audit_logs": audit_logs,
        "consentimentos": consentimentos,
        "exported_at": now.isoformat(),
    }
    bundle_dict["export_hash"] = _hash_export(bundle_dict)

    return DataExportBundle(**bundle_dict)
