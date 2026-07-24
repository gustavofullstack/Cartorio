"""Endpoints internos para pacote CNJ agregado com dupla aprovacao DPO."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key, require_dpo_role
from app.db import get_db
from app.models.audit_log import AuditLog
from app.services.pii import scrub
from app.schemas.cnj_export import (
    CNJExportApprovalCreate,
    CNJExportArtifactResponse,
    CNJExportRequestCreate,
    CNJExportStatusResponse,
)
from app.services.audit import AuditService
from app.services.audit_context import audit_kwargs
from app.services.cnj_export import (
    CNJExportError,
    approve_request,
    build_approved_export,
    create_request,
    get_generated_export,
)

cnj_export_router = APIRouter(prefix="/lgpd/cnj-exports", tags=["lgpd-cnj-export"])
_CNJ_OPENAPI_SECURITY: list[dict[str, list[str]]] = [{"ApiKeyAuth": [], "BearerAuth": []}]


def _http_error(exc: CNJExportError) -> HTTPException:
    """Converte erro de dominio em resposta sem detalhes de dados internos."""
    message = str(exc)
    code = status.HTTP_404_NOT_FOUND if "inexistente" in message else status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=code, detail={"erro": "CNJ_EXPORT_INVALID_STATE", "mensagem": message}
    )


def _scrub_payload_value(value: Any) -> Any:
    """Scrub PII recursivo que preserva JSON valido no massive dump.

    Scrub sobre o JSON serializado (dumps -> scrub -> loads) mascara CPF
    numerico nao-quotado, mas o placeholder `[CPF_REDACTED]` fica sem
    aspas e o `json.loads` subsequente explode no meio do stream,
    entregando JSON truncado/invalido ao CNJ. Scrub por folha mantem a
    estrutura: numeros que parecem PII viram string mascarada; numeros
    sem PII permanecem numericos; bool/None passam intactos.
    """
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        result = scrub(str(value))
        return result.text if result.redaction_count else value
    if isinstance(value, str):
        return scrub(value).text
    if isinstance(value, list):
        return [_scrub_payload_value(item) for item in value]
    if isinstance(value, dict):
        return {scrub(str(key)).text: _scrub_payload_value(item) for key, item in value.items()}
    return scrub(str(value)).text


def _status_payload(export_request: Any) -> dict[str, Any]:
    """Serializa somente estado operacional e hashes do pedido CNJ."""
    return {
        "request_id": export_request.id,
        "status": export_request.status,
        "reference_period": export_request.reference_period,
        "requested_at": export_request.requested_at.isoformat(),
        "approved_at": export_request.approved_at.isoformat()
        if export_request.approved_at
        else None,
        "generated_at": export_request.generated_at.isoformat()
        if export_request.generated_at
        else None,
        "report_sha256": export_request.report_sha256,
        "manifest_sha256": export_request.manifest_sha256,
    }


@cnj_export_router.post(
    "/requests",
    status_code=status.HTTP_201_CREATED,
    response_model=CNJExportStatusResponse,
    openapi_extra={"security": _CNJ_OPENAPI_SECURITY},
)
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
    try:
        AuditService.log(
            db,
            actor_id=requester,
            actor_type="dpo",
            action="cnj.export.requested",
            resource=f"cnj_export:{export_request.id}",
            payload={"reference_period": export_request.reference_period},
            **audit_kwargs(request),
        )
    except Exception:
        db.rollback()
        raise
    return _status_payload(export_request)


@cnj_export_router.post(
    "/requests/{request_id}/approval",
    response_model=CNJExportStatusResponse,
    openapi_extra={"security": _CNJ_OPENAPI_SECURITY},
)
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
    try:
        AuditService.log(
            db,
            actor_id=approver,
            actor_type="dpo",
            action="cnj.export.approved",
            resource=f"cnj_export:{export_request.id}",
            payload={"reference_period": export_request.reference_period},
            **audit_kwargs(request),
        )
    except Exception:
        db.rollback()
        raise
    return _status_payload(export_request)


@cnj_export_router.post(
    "/requests/{request_id}/generate",
    response_model=CNJExportArtifactResponse,
    openapi_extra={"security": _CNJ_OPENAPI_SECURITY},
)
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
    try:
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
    except Exception:
        db.rollback()
        raise
    return artifact.as_dict()


@cnj_export_router.get(
    "/requests/{request_id}",
    response_model=CNJExportStatusResponse,
    openapi_extra={"security": _CNJ_OPENAPI_SECURITY},
)
def get_cnj_export_status(
    request_id: str,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    _dpo: dict[str, Any] = Depends(require_dpo_role),
) -> dict[str, Any]:
    """Consulta estado e hashes sem devolver o artefato nem PII operacional."""
    from app.models.cnj_export_request import CNJExportRequest

    export_request = db.get(CNJExportRequest, request_id)
    if export_request is None:
        raise _http_error(CNJExportError("pedido CNJ inexistente"))
    return _status_payload(export_request)


@cnj_export_router.get(
    "/requests/{request_id}/download",
    response_model=CNJExportArtifactResponse,
    openapi_extra={"security": _CNJ_OPENAPI_SECURITY},
)
def download_cnj_export(
    request_id: str,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    _dpo: dict[str, Any] = Depends(require_dpo_role),
) -> Response:
    """Baixa novamente artefato já gerado, sem regenerar indicadores."""
    try:
        artifact = get_generated_export(db, request_id=request_id)
    except CNJExportError as exc:
        raise _http_error(exc) from exc
    import json

    return Response(
        content=json.dumps(artifact.as_dict(), ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": (f'attachment; filename="cnj-lgpd-aggregated-{request_id}.json"')
        },
    )


@cnj_export_router.get(
    "/massive-dump",
    openapi_extra={"security": _CNJ_OPENAPI_SECURITY},
)
def massive_dump_cnj(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    _dpo: dict[str, Any] = Depends(require_dpo_role),
) -> StreamingResponse:
    """Exportação em massa do Audit Log preservando a cadeia SHA256 (Padrão CNJ).

    Exige API key e JWT de DPO. O payload e o IP integral permanecem
    mascarados no pacote destinado ao CNJ; a cadeia/hash de auditoria é
    preservada para verificação independente.
    """
    import json

    requester = str(_dpo.get("sub", ""))
    if not requester:
        raise HTTPException(status_code=403, detail={"erro": "DPO_SUB_REQUIRED"})
    try:
        AuditService.log(
            db,
            actor_id=requester,
            actor_type="dpo",
            action="cnj.export.massive_dump",
            resource="cnj_export:massive_dump",
            payload={"action": "streaming_started"},
            **audit_kwargs(request),
        )
    except Exception:
        # falha no audit -> impede o dump
        db.rollback()
        raise HTTPException(status_code=500, detail={"erro": "AUDIT_FAILURE"})

    def _stream_audit_logs():
        yield "[\n"
        first = True
        # yield_per iterando para nao estourar RAM com dump massivo
        for log in db.query(AuditLog).order_by(AuditLog.id.asc()).yield_per(1000):
            if not first:
                yield ",\n"
            first = False

            # Scrub por folha (nao dumps->scrub->loads): CPF numerico
            # nao-quotado viraria `[CPF_REDACTED]` sem aspas e quebraria
            # o json.loads no meio do stream (JSON truncado ao CNJ).
            scrubbed_payload = _scrub_payload_value(log.payload)

            # Campos top-level potencialmente identificadores (actor_id,
            # resource, user_agent, request_id, canal) tambem passam pelo
            # scrub antes de sair no stream. Campos de integridade
            # (prev_hash/hash/hmac_signature/hmac_kid) permanecem verbatim
            # para nao invalidar a cadeia SHA256/HMAC verificavel pelo CNJ.
            item = {
                "id": log.id,
                "actor_id": _scrub_payload_value(log.actor_id),
                "actor_type": log.actor_type,
                "action": log.action,
                "resource": _scrub_payload_value(log.resource),
                "payload": scrubbed_payload,
                "ip_truncated": log.ip_truncated,
                "user_agent": _scrub_payload_value(log.user_agent),
                "request_id": _scrub_payload_value(log.request_id),
                "canal": _scrub_payload_value(log.canal),
                "prev_hash": log.prev_hash,
                "hash": log.hash,
                "hmac_signature": log.hmac_signature,
                "hmac_kid": log.hmac_kid,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }

            yield json.dumps(item, ensure_ascii=False)
        yield "\n]"

    return StreamingResponse(_stream_audit_logs(), media_type="application/json")


__all__ = ["cnj_export_router"]
