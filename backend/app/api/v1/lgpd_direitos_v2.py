"""Endpoints LGPD D26-D32 — v2 com auth JWT + DPO role (LGPD art. 18).

Novos endpoints com autenticacao JWT (DPO role) e titular-or-DPO,
substituindo os stubs v1 que usavam apenas X-API-Key.

D26 — Dashboard DPO (KPIs agregados)
D27 — Consentimento granular (por finalidade)
D28 — Direito ao esquecimento (soft/hard delete real)
D29 — Portabilidade/export (real, via lgpd_export)
D30 — Correcao de dados pessoais
D31 — Revogacao de consentimento
D32 — Transparencia de audit log (por titular)

Padrao:
- Auth: JWT Bearer token (DPO ou titular-or-DPO)
- Audit log: registrar TODA operacao (LGPD art. 37)
- PII scrub: mascarar IP/PII antes de expor
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import require_dpo_role, require_cliente_or_dpo, _require_jwt_payload
from app.db import get_db
from app.services.audit import AuditService
from app.services.audit_context import audit_kwargs

logger = logging.getLogger(__name__)

lgpd_v2_router = APIRouter(tags=["lgpd-v2"])


# ============================================================================
# Pydantic request/response models
# ============================================================================


class ConsentRequest(BaseModel):
    """D27 — Consentimento granular por finalidade."""

    cliente_id: int
    finalidade: Literal[
        "atendimento",
        "marketing",
        "compartilhamento_terceiros",
        "analytics",
        "prospeccao",
    ]
    granted: bool
    canal: str = "web"


class CorrectionRequest(BaseModel):
    """D30 — Correcao de dados pessoais (LGPD art. 18 III)."""

    nome: str | None = None
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    observacoes: str | None = None


class RevogarConsentRequest(BaseModel):
    """D31 — Revogacao de consentimento."""

    cliente_id: int
    finalidades: list[str] | None = None
    canal: str = "web"


# Whitelist de campos corrigiveis (LGPD art. 18 III)
CORRECTABLE_FIELDS = frozenset({"nome", "email", "telefone", "endereco", "observacoes"})

# Mapeamento de campo do request -> coluna do DB (quando difere)
_DB_FIELD_MAP = {
    "nome": "nome",
    "email": "email",
    "telefone": "telefone_hash",
    # endereco e observacoes podem nao existir no schema atual —
    # sao tratados como best-effort no update
}

# Finalidades LGPD -> acoes de audit
_FINALIDADE_AUDIT_MAP = {
    "atendimento": "lgpd.consent.atendimento",
    "marketing": "lgpd.consent.marketing",
    "compartilhamento_terceiros": "lgpd.consent.compartilhamento_terceiros",
    "analytics": "lgpd.consent.analytics",
    "prospeccao": "lgpd.consent.prospeccao",
}


# ============================================================================
# D26 — Dashboard DPO (KPIs agregados)
# ============================================================================


@lgpd_v2_router.get(
    "/lgpd/dashboard",
    summary="Dashboard DPO — KPIs LGPD agregados",
    description=(
        "Retorna indicadores-chave de conformidade LGPD para o DPO.\n\n"
        "Inclui: total clientes ativos/revogados, consents ativos/revogados,\n"
        "exports solicitados, audit entries 24h e status da audit chain.\n\n"
        "Auth: JWT Bearer com claim dpo=True obrigatorio."
    ),
)
def lgpd_dashboard(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _dpo_payload: dict = Depends(require_dpo_role),  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Dashboard DPO — KPIs LGPD agregados (D26).

    Query raw SQL para performance (evita N+1 com ORM).
    """
    # 1. Total clientes ativos (deleted_at IS NULL)
    total_ativos = db.execute(
        text("SELECT COUNT(*) FROM clientes WHERE deleted_at IS NULL")
    ).scalar() or 0

    # 2. Total clientes revocados (deleted_at IS NOT NULL)
    total_revocados = db.execute(
        text("SELECT COUNT(*) FROM clientes WHERE deleted_at IS NOT NULL")
    ).scalar() or 0

    # 3. Consentimentos ativos (consentimento_lgpd = TRUE AND deleted_at IS NULL)
    consents_ativos = db.execute(
        text(
            "SELECT COUNT(*) FROM clientes "
            "WHERE consentimento_lgpd = TRUE AND deleted_at IS NULL"
        )
    ).scalar() or 0

    # Detect dialect (PostgreSQL prod vs SQLite test) for cross-compatible time
    dialect_name = db.bind.dialect.name if db.bind is not None else "postgresql"
    is_sqlite = dialect_name == "sqlite"
    if is_sqlite:
        ts_30d_expr = "datetime('now', '-30 days')"
        ts_1d_expr = "datetime('now', '-1 day')"
    else:
        ts_30d_expr = "NOW() - INTERVAL '30 days'"
        ts_1d_expr = "NOW() - INTERVAL '1 day'"

    # 4. Consentimentos revogados nos ultimos 30 dias
    consents_revogados_30d = db.execute(
        text(
            'SELECT COUNT(*) FROM audit_log '
            "WHERE action = 'lgpd.consent.revoked' "
            f'AND timestamp >= {ts_30d_expr}'
        )
    ).scalar() or 0

    # 5. Exports solicitados nos ultimos 30 dias
    exports_30d = db.execute(
        text(
            'SELECT COUNT(*) FROM audit_log '
            "WHERE action = 'lgpd.portabilidade.download' "
            f'AND timestamp >= {ts_30d_expr}'
        )
    ).scalar() or 0

    # 6. Audit entries nas ultimas 24h
    audit_24h = db.execute(
        text(
            'SELECT COUNT(*) FROM audit_log '
            f'WHERE timestamp >= {ts_1d_expr}'
        )
    ).scalar() or 0

    # 7. Audit chain status (verifica integridade basica)
    chain_ok, chain_length = AuditService.verify_chain(db)

    # Audit log do acesso ao dashboard
    AuditService.log(
        db,
        actor_id=_dpo_payload.get("sub", "dpo"),
        actor_type="dpo",
        action="lgpd.dashboard.access",
        resource="system",
        payload={"kpis_returned": True},
        **audit_kwargs(request),
    )

    return {
        "total_clientes_ativos": total_ativos,
        "total_clientes_revocados": total_revocados,
        "consents_ativos": consents_ativos,
        "consents_revogados_30d": consents_revogados_30d,
        "exports_solicitados_30d": exports_30d,
        "audit_entries_24h": audit_24h,
        "audit_chain_status": {
            "ok": chain_ok,
            "chain_length": chain_length,
        },
    }


# ============================================================================
# D23 — Direito de acesso (LGPD art. 18 II)
# ============================================================================


@lgpd_v2_router.get(
    "/lgpd/access/{cliente_id}",
    summary="Confirmacao de existencia e acesso aos dados (LGPD art. 18 II)",
    description=(
        "Confirma a existencia de tratamento e retorna resumo das categorias\n"
        "de dados pessoais tratados sobre o titular.\n\n"
        "Inclui: dados identificacao, contato, atos juridicos, consentimentos.\n"
        "Nao retorna valores PII — apenas categorias e contagens.\n\n"
        "Auth: JWT Bearer (titular ou DPO)."
    ),
)
def direito_acesso_v2(
    cliente_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _payload: dict = Depends(require_cliente_or_dpo),  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Confirma existencia de tratamento e categorias de dados (D23, LGPD art. 18 II)."""
    from app.models.cliente import Cliente
    from app.models.protocolo import Protocolo
    from app.models.audit_log import AuditLog

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "cliente_id": cliente_id},
        )

    # Conta protocolos do titular
    total_protocolos = db.execute(
        select(func.count(Protocolo.id)).where(Protocolo.cliente_id == cliente_id)
    ).scalar() or 0

    # Conta audit entries do titular
    total_audit = db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.resource.like(f"cliente:{cliente_id}%")
        )
    ).scalar() or 0

    # Categorias de dados tratados
    categorias_dados = [
        {"categoria": "identificacao", "campos": ["nome", "cpf_hash"], "status": "tratando"},
        {"categoria": "contato", "campos": ["email", "telefone_hash"], "status": "tratando"},
        {"categoria": "ato_juridico", "campos": ["protocolos"], "count": total_protocolos},
        {"categoria": "consentimento_lgpd", "campos": ["consentimento_lgpd", "consentimento_em"],
         "status": "concedido" if cliente.consentimento_lgpd else "nao_concedido"},
        {"categoria": "audit_trail", "campos": ["request_id", "ip_truncado", "user_agent"],
         "count": total_audit},
    ]

    # Audit log da propria consulta
    AuditService.log(
        db,
        actor_id=_payload.get("sub", "unknown"),
        actor_type="dpo" if _payload.get("dpo") else "cliente",
        action="lgpd.access.confirm",
        resource=f"cliente:{cliente_id}",
        payload={
            "lgpd_art": "18 II",
            "categorias_retornadas": len(categorias_dados),
        },
        **audit_kwargs(request),
    )

    return {
        "status": "ok",
        "cliente_id": cliente_id,
        "tratamento_confirmado": True,
        "categorias_dados": categorias_dados,
        "total_protocolos": total_protocolos,
        "total_audit_entries": total_audit,
        "copy_juridica": {
            "base_legal": "LGPD art. 18 II",
            "direito": "Confirmacao da existencia de tratamento + acesso aos dados",
            "prazo_resposta": "15 dias (art. 18 §5º)",
            "dpo_contact": "dpo@2notasudi.com.br",
        },
    }


# ============================================================================
# D27 — Consentimento granular (por finalidade)
# ============================================================================


@lgpd_v2_router.post(
    "/lgpd/consent",
    summary="Registrar consentimento granular LGPD",
    description=(
        "Registra consentimento do titular para uma finalidade especifica.\n\n"
        "Finalidades: atendimento, marketing, compartilhamento_terceiros,\n"
        "analytics, prospeccao.\n\n"
        "Auth: JWT Bearer (titular ou DPO)."
    ),
)
def registrar_consentimento_v2(
    request: Request,
    body: ConsentRequest,
    db: Annotated[Session, Depends(get_db)],
    _payload: dict = Depends(_require_jwt_payload),  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Registra consentimento granular LGPD (D27, art. 8 + art. 9)."""
    from app.models.cliente import Cliente
    from app.services.lgpd_consent import Finalidade

    # Auth: verificar se cliente_id do body coincide com sub do JWT
    # ou se o usuario tem role DPO
    sub = _payload.get("sub")
    is_dpo = _payload.get("dpo") is True
    if not is_dpo and str(sub) != str(body.cliente_id):
        raise HTTPException(
            status_code=403,
            detail={"erro": "FORBIDDEN", "mensagem": "Acesso restrito ao titular ou DPO."},
        )

    # Verificar se cliente existe
    cliente = db.get(Cliente, body.cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "cliente_id": body.cliente_id},
        )

    # Mapear finalidade do request para enum
    finalidade_map: dict[str, Finalidade] = {
        "atendimento": Finalidade.ATENDIMENTO_WHATSAPP,
        "marketing": Finalidade.MARKETING,
        "compartilhamento_terceiros": Finalidade.PESQUISA_SATISFACAO,
        "analytics": Finalidade.EMOLUMENTO_CONSULTA,
        "prospeccao": Finalidade.ATENDIMENTO_TELEGRAM,
    }

    finalidade_enum = finalidade_map.get(body.finalidade)
    if finalidade_enum is None:
        raise HTTPException(
            status_code=400,
            detail={
                "erro": "INVALID_FINALIDADE",
                "mensagem": f"Finalidade '{body.finalidade}' nao reconhecida.",
            },
        )

    if body.granted:
        from app.services.lgpd_consent import registrar_consentimento

        result = registrar_consentimento(
            db,
            body.cliente_id,
            [finalidade_enum],
            ip=request.headers.get("x-forwarded-for", "0.0.0.0"),
            canal=body.canal,
            user_agent=request.headers.get("user-agent"),
        )
        action = _FINALIDADE_AUDIT_MAP.get(body.finalidade, "lgpd.consent.granted")
    else:
        from app.services.lgpd_consent import revogar_consentimento

        result = revogar_consentimento(
            db,
            body.cliente_id,
            [finalidade_enum],
            ip=request.headers.get("x-forwarded-for", "0.0.0.0"),
            canal=body.canal,
            user_agent=request.headers.get("user-agent"),
        )
        action = "lgpd.consent.revoked"

    # Audit log
    AuditService.log(
        db,
        actor_id=_payload.get("sub", "unknown"),
        actor_type="dpo" if _payload.get("dpo") else "cliente",
        action=action,
        resource=f"cliente:{body.cliente_id}",
        payload={
            "finalidade": body.finalidade,
            "granted": body.granted,
            "canal": body.canal,
        },
        **audit_kwargs(request),
    )

    return {
        "status": "ok",
        "cliente_id": body.cliente_id,
        "finalidade": body.finalidade,
        "granted": body.granted,
        "consentido_em": (
            result.consentido_em.isoformat() if result.consentido_em else None
        ),
    }


# ============================================================================
# D28 — Direito ao esquecimento (soft/hard delete real)
# ============================================================================


@lgpd_v2_router.delete(
    "/lgpd/cliente/{cliente_id}",
    summary="Direito ao esquecimento (LGPD art. 18 V)",
    description=(
        "Executa soft delete com anonimizacao de PII (LGPD art. 18 V).\n\n"
        " cascade em todas as tabelas que referenciam cliente_id.\n"
        "Reversivel ate 30 dias (LGPD art. 18 V §2).\n\n"
        "Auth: JWT Bearer (titular ou DPO)."
    ),
)
def direito_esquecimento_v2(
    cliente_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _payload: dict = Depends(require_cliente_or_dpo),  # type: ignore[type-arg]
    motivo: str = "cliente_solicitou",
) -> dict[str, Any]:
    """Direito ao esquecimento real (D28, LGPD art. 18 V)."""
    from app.services.lgpd_direito_esquecimento import direito_esquecimento

    result = direito_esquecimento(
        db,
        cliente_id,
        actor_id=_payload.get("sub", "unknown"),
        motivo=motivo,
    )

    if result.get("erro") == "cliente_nao_encontrado":
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "cliente_id": cliente_id},
        )

    # Audit log adicional do endpoint
    AuditService.log(
        db,
        actor_id=_payload.get("sub", "unknown"),
        actor_type="dpo" if _payload.get("dpo") else "cliente",
        action="lgpd.esquecimento.v2",
        resource=f"cliente:{cliente_id}",
        payload={
            "motivo": motivo,
            "total_rows_affected": result.get("total_rows_affected", 0),
            "reversivel_ate": result.get("reversivel_ate"),
        },
        **audit_kwargs(request),
    )

    return {
        "status": "ok",
        "direito": "esquecimento",
        "cliente_id": cliente_id,
        "deleted_at": result.get("deleted_at"),
        "anonymized_tables": result.get("anonymized_tables", []),
        "total_rows_affected": result.get("total_rows_affected", 0),
        "reversivel_ate": result.get("reversivel_ate"),
        "audit_log_id": result.get("audit_log_id"),
    }


# ============================================================================
# D29 — Portabilidade / export (real)
# ============================================================================


@lgpd_v2_router.get(
    "/lgpd/export/{cliente_id}",
    summary="Exportar dados do titular (LGPD art. 18 V)",
    description=(
        "Exporta todos os dados pessoais do titular em formato JSON.\n\n"
        "Inclui: perfil, protocolos, atendimentos, documentos,\n"
        "audit logs e consentimentos. Hash SHA256 garante integridade.\n\n"
        "Auth: JWT Bearer (titular ou DPO)."
    ),
)
def exportar_dados_v2(
    cliente_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _payload: dict = Depends(require_cliente_or_dpo),  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Exporta dados do titular (D29, LGPD art. 18 V)."""
    from app.services.lgpd_export import (
        ClienteNotFoundError,
        exportar_dados_titular,
    )

    try:
        bundle = exportar_dados_titular(db, cliente_id)
    except ClienteNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "cliente_id": cliente_id},
        )

    # Audit log
    AuditService.log(
        db,
        actor_id=_payload.get("sub", "unknown"),
        actor_type="dpo" if _payload.get("dpo") else "cliente",
        action="lgpd.portabilidade.download",
        resource=f"cliente:{cliente_id}",
        payload={
            "export_hash": bundle.export_hash,
            "fields_exported": [
                "cliente",
                "protocolos",
                "atendimentos",
                "documentos",
                "audit_logs",
                "consentimentos",
            ],
        },
        **audit_kwargs(request),
    )

    return {
        "status": "ok",
        "direito": "portabilidade",
        "cliente_id": cliente_id,
        "exported_at": bundle.exported_at,
        "export_hash": bundle.export_hash,
        "dados": {
            "cliente": bundle.cliente,
            "protocolos": bundle.protocolos,
            "atendimentos": bundle.atendimentos,
            "documentos": bundle.documentos,
            "audit_logs": bundle.audit_logs,
            "consentimentos": bundle.consentimentos,
        },
    }


# ============================================================================
# D30 — Correcao de dados pessoais
# ============================================================================


@lgpd_v2_router.post(
    "/lgpd/correct/{cliente_id}",
    summary="Corrigir dados pessoais (LGPD art. 18 III)",
    description=(
        "Permite ao titular corrigir dados pessoais incorretos.\n\n"
        "Campos corrigiveis: nome, email, telefone, endereco, observacoes.\n"
        "Apenas campos fornecidos serao atualizados.\n\n"
        "Auth: JWT Bearer (titular ou DPO)."
    ),
)
def corrigir_dados_v2(
    cliente_id: int,
    request: Request,
    body: CorrectionRequest,
    db: Annotated[Session, Depends(get_db)],
    _payload: dict = Depends(require_cliente_or_dpo),  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Corrige dados pessoais do titular (D30, LGPD art. 18 III)."""
    from app.models.cliente import Cliente

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "cliente_id": cliente_id},
        )

    # Extrai campos do body que nao sao None
    updates = body.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail={
                "erro": "NO_FIELDS_PROVIDED",
                "mensagem": "Nenhum campo para corrigir fornecido.",
            },
        )

    # Valida que todos os campos sao da whitelist
    invalid_fields = set(updates.keys()) - CORRECTABLE_FIELDS
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "erro": "INVALID_FIELDS",
                "mensagem": f"Campos nao corrigiveis: {sorted(invalid_fields)}",
            },
        )

    updated_fields: list[str] = []
    old_values: dict[str, str | None] = {}

    # Atualiza campos que existem no model
    for field_name, value in updates.items():
        db_col = _DB_FIELD_MAP.get(field_name)
        if db_col and hasattr(cliente, db_col):
            old_val = getattr(cliente, db_col)
            old_values[field_name] = (
                str(old_val) if old_val is not None else None
            )
            setattr(cliente, db_col, value)
            updated_fields.append(field_name)
        else:
            # Campo nao existe no model (endereco, observacoes) —
            # loga mas nao atualiza
            logger.info(
                "Campo '%s' nao existe no model Cliente — correcao ignorada",
                field_name,
            )

    if updated_fields:
        cliente.updated_at = datetime.now(tz=timezone.utc)
        db.commit()

    # Audit log
    AuditService.log(
        db,
        actor_id=_payload.get("sub", "unknown"),
        actor_type="dpo" if _payload.get("dpo") else "cliente",
        action="lgpd.correct.v2",
        resource=f"cliente:{cliente_id}",
        payload={
            "updated_fields": updated_fields,
            "old_values_scrubbed": {
                k: v[:2] + "***" if v and len(v) > 2 else v
                for k, v in old_values.items()
            },
        },
        **audit_kwargs(request),
    )

    return {
        "status": "ok",
        "direito": "correcao",
        "cliente_id": cliente_id,
        "updated_fields": updated_fields,
        "corrigido_em": datetime.now(tz=timezone.utc).isoformat(),
    }


# ============================================================================
# D31 — Revogacao de consentimento
# ============================================================================


@lgpd_v2_router.post(
    "/lgpd/revogar-consent",
    summary="Revogar consentimento LGPD (art. 9)",
    description=(
        "Revoga consentimento do titular (total ou por finalidade).\n\n"
        "Efeito colateral: se revogar tudo, consentimento_lgpd=False.\n\n"
        "Auth: JWT Bearer (titular ou DPO)."
    ),
)
def revogar_consent_v2(
    request: Request,
    body: RevogarConsentRequest,
    db: Annotated[Session, Depends(get_db)],
    _payload: dict = Depends(_require_jwt_payload),  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Revoga consentimento do titular (D31, LGPD art. 9)."""
    from app.models.cliente import Cliente
    from app.services.lgpd_consent import revogar_consentimento

    # Auth: verificar cliente_id do body vs JWT
    sub = _payload.get("sub")
    is_dpo = _payload.get("dpo") is True
    if not is_dpo and str(sub) != str(body.cliente_id):
        raise HTTPException(
            status_code=403,
            detail={"erro": "FORBIDDEN", "mensagem": "Acesso restrito ao titular ou DPO."},
        )

    cliente = db.get(Cliente, body.cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "cliente_id": body.cliente_id},
        )

    # Converte finalidades string para enum se fornecidas
    finalidades_enum = None
    if body.finalidades:
        from app.services.lgpd_consent import Finalidade

        finalidade_map = {
            "atendimento": Finalidade.ATENDIMENTO_WHATSAPP,
            "marketing": Finalidade.MARKETING,
            "compartilhamento_terceiros": Finalidade.PESQUISA_SATISFACAO,
            "analytics": Finalidade.EMOLUMENTO_CONSULTA,
            "prospeccao": Finalidade.ATENDIMENTO_TELEGRAM,
        }
        finalidades_enum = []
        for f in body.finalidades:
            fe = finalidade_map.get(f)
            if fe is not None:
                finalidades_enum.append(fe)

    result = revogar_consentimento(
        db,
        body.cliente_id,
        finalidades_enum,
        ip=request.headers.get("x-forwarded-for", "0.0.0.0"),
        canal=body.canal,
        user_agent=request.headers.get("user-agent"),
    )

    # Efeito colateral: setar consentimento_lgpd=False se revogou tudo
    if body.finalidades is None:
        cliente.consentimento_lgpd = False
        db.commit()

    # Audit log
    AuditService.log(
        db,
        actor_id=_payload.get("sub", "unknown"),
        actor_type="dpo" if _payload.get("dpo") else "cliente",
        action="lgpd.consent.revoked.v2",
        resource=f"cliente:{body.cliente_id}",
        payload={
            "finalidades_revogadas": body.finalidades or "all",
            "canal": body.canal,
            "consentimento_lgpd_after": cliente.consentimento_lgpd,
        },
        **audit_kwargs(request),
    )

    return {
        "status": "ok",
        "direito": "revogacao_consentimento",
        "cliente_id": body.cliente_id,
        "finalidades_revogadas": body.finalidades or "all",
        "consentimento_lgpd": cliente.consentimento_lgpd,
        "revogado_em": (
            result.revogado_em.isoformat() if result.revogado_em else None
        ),
    }


# ============================================================================
# D32 — Transparencia de audit log (por titular)
# ============================================================================


def _truncate_ip_for_response(ip: str | None) -> str | None:
    """Trunca IP para exposicao ao titular (LGPD art. 6 VIII - minimizacao)."""
    if not ip:
        return None
    if ":" in ip:  # IPv6
        parts = ip.split(":")
        return ":".join(parts[:3]) + "::"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
    return ip


def _parse_payload(raw: object) -> dict:
    """Converte payload de audit_log (JSON string ou dict) para dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}
    if raw is None:
        return {}
    return {}


def _scrub_payload_pii(payload: dict) -> dict:
    """Remove PII sensiveis de payload antes de expor ao titular.

    Mantem: action, resource, canal, timestamp.
    Remove: ip completo, user_agent detalhado, request_id.
    """
    if not payload:
        return {}
    scrubbed = dict(payload)
    # Remove campos sensiveis
    for key in ("ip", "user_agent", "request_id", "ip_truncated"):
        scrubbed.pop(key, None)
    # Mantem apenas campos nao-PII do payload
    safe_keys = {
        "action",
        "resource",
        "canal",
        "finalidade",
        "granted",
        "motivo",
        "updated_fields",
        "total_rows_affected",
        "export_hash",
        "fields_exported",
        "finalidades",
        "finalidades_revogadas",
        "revoga_obrigatorias",
    }
    return {k: v for k, v in scrubbed.items() if k in safe_keys}


@lgpd_v2_router.get(
    "/lgpd/audit/{cliente_id}",
    summary="Audit log do titular (LGPD art. 37 — transparencia)",
    description=(
        "Retorna o historico de tratamento de dados do titular.\n\n"
        "IPs sao truncados e PII e removida dos payloads.\n"
        "Util para responder solicitacoes de transparencia.\n\n"
        "Auth: JWT Bearer (titular ou DPO)."
    ),
)
def audit_log_titular(
    cliente_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _payload: dict = Depends(require_cliente_or_dpo),  # type: ignore[type-arg]
    limit: int = Query(default=100, le=500, ge=1),
) -> dict[str, Any]:
    """Retorna audit log do titular com PII scrubbed (D32, LGPD art. 37)."""
    # Busca audit entries que referenciam o cliente
    stmt = (
        text(
            "SELECT id, actor_id, actor_type, action, resource, "
            "payload, ip, ip_truncated, user_agent, canal, timestamp "
            "FROM audit_log "
            "WHERE resource LIKE :resource_pattern "
            "ORDER BY timestamp DESC "
            "LIMIT :lim"
        )
    )
    rows = db.execute(
        stmt,
        {"resource_pattern": f"cliente:{cliente_id}%", "lim": limit},
    ).mappings().all()

    entries: list[dict[str, Any]] = []
    for row in rows:
        ts = row["timestamp"]
        # SQLite retorna string, Postgres retorna datetime — normaliza
        if isinstance(ts, str):
            timestamp_str = ts
        elif ts is not None:
            timestamp_str = ts.isoformat()
        else:
            timestamp_str = None
        entry = {
            "id": row["id"],
            "action": row["action"],
            "canal": row["canal"],
            "timestamp": timestamp_str,
            # IP truncado (apenas /24 para IPv4)
            "ip_truncated": _truncate_ip_for_response(row.get("ip")),
            # Payload scrubbed (sem PII)
            "payload": _scrub_payload_pii(
                _parse_payload(row.get("payload"))
            ),
        }
        entries.append(entry)

    # Audit log DA PROPRIA consulta de audit (LGPD art. 37 — meta-audit)
    AuditService.log(
        db,
        actor_id=_payload.get("sub", "unknown"),
        actor_type="dpo" if _payload.get("dpo") else "cliente",
        action="lgpd.audit_transparency.access",
        resource=f"cliente:{cliente_id}",
        payload={
            "entries_returned": len(entries),
            "limit_requested": limit,
        },
        **audit_kwargs(request),
    )

    return {
        "status": "ok",
        "cliente_id": cliente_id,
        "entries_count": len(entries),
        "entries": entries,
    }
