"""Endpoints internos para pacote CNJ agregado com dupla aprovacao DPO."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key, require_dpo_role
from app.db import get_db
from app.schemas.cnj_export import CNJExportApprovalCreate, CNJExportRequestCreate
from app.services.audit import AuditService
from app.services.audit_context import audit_kwargs
from app.services.cnj_export import (
    CNJExportError,
    approve_request,
    build_approved_export,
    create_request,
)

cnj_export_router = APIRouter(prefix="/lgpd/cnj-exports", tags=["lgpd-cnj-export"])


def _http_error(exc: CNJExportError) -> HTTPException:
    """Converte erro de dominio em resposta sem detalhes de dados internos."""
    message = str(exc)
    code = status.HTTP_404_NOT_FOUND if "inexistente" in message else status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=code, detail={"erro": "CNJ_EXPORT_INVALID_STATE", "mensagem": message}
    )


@cnj_export_router.post("/requests", status_code=status.HTTP_201_CREATED)
def request_cnj_export(
    payload: CNJExportRequestCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    dpo: dict[str, Any] = Depends(require_dpo_role),
) -> dict[str, str]:
    """Registra pedido. A geracao permanece bloqueada ate outro DPO aprovar."""
    requester = str(dpo.get("sub", ""))
    if not requester:
        raise HTTPException(status_code=403, detail={"erro": "DPO_SUB_REQUIRED"})
    try:
        export_request = create_request(
            db, reference_period=payload.reference_period, requested_by=requester
        )
    except CNJExportError as exc:
        raise _http_error(exc) from exc
    AuditService.log(
        db,
        actor_id=requester,
        actor_type="dpo",
        action="cnj.export.requested",
        resource=f"cnj_export:{export_request.id}",
        payload={"reference_period": export_request.reference_period},
        **audit_kwargs(request),
    )
    return {"request_id": export_request.id, "status": export_request.status}


@cnj_export_router.post("/requests/{request_id}/approval")
def approve_cnj_export(
    request_id: str,
    payload: CNJExportApprovalCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    dpo: dict[str, Any] = Depends(require_dpo_role),
) -> dict[str, str]:
    """Aprovacao humana independente (quatro olhos), sem registrar justificativa no audit."""
    approver = str(dpo.get("sub", ""))
    if not approver:
        raise HTTPException(status_code=403, detail={"erro": "DPO_SUB_REQUIRED"})
    try:
        export_request = approve_request(
            db, request_id=request_id, approved_by=approver, reason=payload.reason
        )
    except CNJExportError as exc:
        raise _http_error(exc) from exc
    AuditService.log(
        db,
        actor_id=approver,
        actor_type="dpo",
        action="cnj.export.approved",
        resource=f"cnj_export:{export_request.id}",
        payload={"reference_period": export_request.reference_period},
        **audit_kwargs(request),
    )
    return {"request_id": export_request.id, "status": export_request.status}


@cnj_export_router.post("/requests/{request_id}/generate")
def generate_cnj_export(
    request_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    dpo: dict[str, Any] = Depends(require_dpo_role),
) -> dict[str, Any]:
    """Gera download JSON local; transmissao externa automatica e intencionalmente vedada."""
    generator = str(dpo.get("sub", ""))
    if not generator:
        raise HTTPException(status_code=403, detail={"erro": "DPO_SUB_REQUIRED"})
    try:
        artifact = build_approved_export(db, request_id=request_id)
    except CNJExportError as exc:
        raise _http_error(exc) from exc
    AuditService.log(
        db,
        actor_id=generator,
        actor_type="dpo",
        action="cnj.export.generated",
        resource=f"cnj_export:{request_id}",
        payload={
            "reference_period": artifact.report["reference_period"],
            "report_sha256": artifact.manifest["report_sha256"],
            "manifest_sha256": artifact.manifest["manifest_sha256"],
        },
        **audit_kwargs(request),
    )
    return artifact.as_dict()


__all__ = ["cnj_export_router"]
