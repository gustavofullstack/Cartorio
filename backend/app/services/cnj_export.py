"""Exportacao CNJ agregada, minimizada e sujeita a dupla aprovacao humana.

Este modulo deliberadamente nao conhece payloads de audit, dados de clientes,
documentos, conversas, IPs nem identificadores de titulares. O artefato e um
JSON local de indicadores agregados; o envio ao CNJ fica fora deste servico e
exige procedimento operacional e canal institucional autorizado.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.cnj_export_request import CNJExportRequest
from app.models.cliente import Cliente
from app.models.protocolo import Protocolo
from app.services.audit import AuditService


class CNJExportError(ValueError):
    """Erro de dominio para fluxo CNJ sem vazar dados internos."""


def _canonical_sha256(data: dict[str, Any]) -> str:
    """Calcula SHA-256 de JSON canonico e reproduzivel."""
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_period(reference_period: str) -> tuple[int, int]:
    """Aceita exclusivamente o periodo calendario YYYY-MM."""
    try:
        year_text, month_text = reference_period.split("-", maxsplit=1)
        year, month = int(year_text), int(month_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise CNJExportError("reference_period deve seguir YYYY-MM") from exc
    if not 2000 <= year <= 2100 or not 1 <= month <= 12:
        raise CNJExportError("reference_period fora do intervalo permitido")
    return year, month


def _count_for_month(db: Session, column: Any, year: int, month: int) -> int:
    """Conta registros por mes sem selecionar linhas ou campos pessoais."""
    return int(
        db.execute(
            select(func.count()).where(
                func.extract("year", column) == year,
                func.extract("month", column) == month,
            )
        ).scalar_one()
        or 0
    )


def _count_action(db: Session, action: str, year: int, month: int) -> int:
    """Conta uma acao controlada pelo sistema; nao exporta o log correspondente."""
    return int(
        db.execute(
            select(func.count()).where(
                AuditLog.action == action,
                func.extract("year", AuditLog.timestamp) == year,
                func.extract("month", AuditLog.timestamp) == month,
            )
        ).scalar_one()
        or 0
    )


@dataclass(frozen=True)
class CNJExportArtifact:
    """Artefato local pronto para download por DPO, nunca para envio automatico."""

    report: dict[str, Any]
    manifest: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"report": self.report, "manifest": self.manifest}


def create_request(db: Session, *, reference_period: str, requested_by: str) -> CNJExportRequest:
    """Abre pedido de exportacao que ainda nao pode gerar nem baixar arquivo."""
    _validate_period(reference_period)
    request = CNJExportRequest(
        reference_period=reference_period,
        status="requested",
        requested_by=requested_by,
        requested_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def approve_request(
    db: Session,
    *,
    request_id: str,
    approved_by: str,
    reason: str,
) -> CNJExportRequest:
    """Aprova pedido pendente; solicitante e aprovador precisam ser pessoas distintas."""
    request = db.get(CNJExportRequest, request_id)
    if request is None:
        raise CNJExportError("pedido CNJ inexistente")
    if request.status != "requested":
        raise CNJExportError("pedido CNJ nao esta pendente de aprovacao")
    if request.requested_by == approved_by:
        raise CNJExportError("aprovacao exige DPO diferente do solicitante")
    if len(reason.strip()) < 10:
        raise CNJExportError("justificativa de aprovacao deve ter ao menos 10 caracteres")

    request.status = "approved"
    request.approved_by = approved_by
    request.approved_at = datetime.now(UTC).replace(tzinfo=None)
    request.approval_reason = reason.strip()
    db.commit()
    db.refresh(request)
    return request


def build_approved_export(db: Session, *, request_id: str) -> CNJExportArtifact:
    """Gera artefato minimizado somente para pedido previamente aprovado.

    O resultado nao inclui os IDs dos DPOs nem a justificativa de aprovacao,
    pois ambos sao metadados internos e nao sao necessarios ao destinatario.
    """
    request = db.get(CNJExportRequest, request_id)
    if request is None:
        raise CNJExportError("pedido CNJ inexistente")
    if request.status != "approved" or request.approved_at is None:
        raise CNJExportError("pedido CNJ exige aprovacao humana independente")

    year, month = _validate_period(request.reference_period)
    generated_at = datetime.now(UTC).isoformat()
    chain_ok, chain_length = AuditService.verify_chain(db)
    chain_head = db.execute(
        select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1)
    ).scalar_one_or_none()

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "report_type": "CNJ_LGPD_AGGREGATED",
        "reference_period": request.reference_period,
        "generated_at": generated_at,
        "data_classification": "RESTRICTED_AGGREGATED",
        "minimization": {
            "contains_personal_data": False,
            "excluded_fields": [
                "nomes",
                "cpf_cnpj",
                "telefones",
                "emails",
                "enderecos",
                "ips",
                "mensagens",
                "documentos",
                "payloads_audit",
                "identificadores_de_titulares",
            ],
            "method": "contagens agregadas por periodo; nenhuma linha de origem e selecionada",
        },
        "indicators": {
            "new_data_subjects": _count_for_month(db, Cliente.created_at, year, month),
            "notarial_protocols_created": _count_for_month(db, Protocolo.created_at, year, month),
            "audit_events": _count_for_month(db, AuditLog.timestamp, year, month),
            "rights_exercised": int(
                db.execute(
                    select(func.count()).where(
                        AuditLog.action.like("lgpd.%"),
                        func.extract("year", AuditLog.timestamp) == year,
                        func.extract("month", AuditLog.timestamp) == month,
                    )
                ).scalar_one()
                or 0
            ),
            "security_incidents": int(
                db.execute(
                    select(func.count()).where(
                        AuditLog.action.like("security.%"),
                        func.extract("year", AuditLog.timestamp) == year,
                        func.extract("month", AuditLog.timestamp) == month,
                    )
                ).scalar_one()
                or 0
            ),
            "exports_generated": _count_action(db, "cnj.export.generated", year, month),
        },
        "audit_integrity": {
            "chain_valid": chain_ok,
            "chain_length": chain_length,
            "chain_head_sha256": chain_head,
        },
        "controls": {
            "human_approval": "dual_control_required",
            "automatic_external_transmission": False,
            "integrity": "sha256_manifest_plus_append_only_audit_log",
        },
    }
    report_sha256 = _canonical_sha256(report)
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "artifact_type": "CNJ_LGPD_AGGREGATED_MANIFEST",
        "report_sha256": report_sha256,
        "generated_at": generated_at,
        "reference_period": request.reference_period,
        "files": [{"name": "cnj-lgpd-aggregated.json", "sha256": report_sha256}],
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)

    request.status = "generated"
    request.generated_at = datetime.now(UTC).replace(tzinfo=None)
    request.report_sha256 = report_sha256
    request.manifest_sha256 = manifest["manifest_sha256"]
    db.commit()
    return CNJExportArtifact(report=report, manifest=manifest)


__all__ = [
    "CNJExportArtifact",
    "CNJExportError",
    "approve_request",
    "build_approved_export",
    "create_request",
]
