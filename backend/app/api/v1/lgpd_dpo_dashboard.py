"""LGPD DPO Dashboard Endpoints (D25).

Endpoints administrativos para o DPO (Encarregado de Dados - LGPD art. 41):

1. `GET /api/v1/lgpd/dpo/metrics` — KPIs agregados (clientes, conversas, audit, retencao)
2. `GET /api/v1/lgpd/dpo/audit-trail/{cliente_id}` — historico de TODOS os acessos/mutacoes de um cliente
3. `GET /api/v1/lgpd/dpo/retention-queue` — itens elegiveis para retencao hoje

Todos protegidos por **dois fatores de auth** (LGPD art. 41):
- `X-API-Key` (rate limit 60/min — DPO tier)
- `Authorization: Bearer <JWT>` com claim `dpo=True`

LGPD-by-design:
- PII nunca sai raw (hashes, contagens, mascaramento)
- Audit log eh PRESERVADO (LGPD art. 37)
- Soft delete nao vaza dados de clientes anonimizados (deleted_at IS NULL filter)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key, require_dpo_role
from app.db import get_db

dpo_dashboard_router = APIRouter(tags=["lgpd-dpo-dashboard"], prefix="/lgpd/dpo")

# ============================================================================
# Helper: detectar dialecto (PostgreSQL prod vs SQLite test)
# ============================================================================

# ============================================================================
# Endpoint 1: /metrics
# ============================================================================


@dpo_dashboard_router.get(
    "/metrics",
    summary="DTO DPO — KPIs LGPD agregados",
    description=(
        "Retorna metricas agregadas para o painel do DPO.\n\n"
        "Inclui:\n"
        "- Total de clientes (ativos, anonimizados)\n"
        "- Total de conversas registradas\n"
        "- Audit chain length + ultima entry\n"
        "- Retention queue size (clientes elegiveis para anonimizacao hoje)\n"
        "- Rights exercised (art. 18) nos ultimos 30 dias\n\n"
        "Auth: X-API-Key + JWT Bearer com claim dpo=True (DOUBLE AUTH).\n"
        "LGPD-by-design: sem expor PII individual (apenas contagens agregadas)."
    ),
)
def get_dpo_metrics(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    _dpo_payload: dict = Depends(require_dpo_role),  # type: ignore[type-arg]
) -> dict[str, Any]:
    """Dashboard metrics (D25)."""
    from app.models.audit_log import AuditLog

    # Cross-dialect: usa expressoes raw compativeis
    ts_30d = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    ts_1d = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=1)

    # Clientes ativos vs anonimizados
    total_clientes = int(db.execute(text("SELECT COUNT(*) FROM clientes")).scalar() or 0)
    clientes_ativos = int(
        db.execute(text("SELECT COUNT(*) FROM clientes WHERE deleted_at IS NULL")).scalar() or 0
    )
    clientes_anonimizados = total_clientes - clientes_ativos

    # Conversas totais
    try:
        total_conversas = int(db.execute(text("SELECT COUNT(*) FROM conversas")).scalar() or 0)
    except Exception:
        total_conversas = 0

    # Audit entries: total + ultimas 24h
    total_audit = int(db.execute(text("SELECT COUNT(*) FROM audit_log")).scalar() or 0)
    audit_24h = int(
        db.execute(
            text("SELECT COUNT(*) FROM audit_log WHERE timestamp >= :ts_1d"), {"ts_1d": ts_1d}
        ).scalar()
        or 0
    )

    # Rights exercised (ultimos 30 dias) — ações LGPD no audit
    rights_30d = int(
        db.execute(
            text(
                "SELECT COUNT(*) FROM audit_log WHERE action LIKE 'lgpd.%' AND timestamp >= :ts_30d"
            ),
            {"ts_30d": ts_30d},
        ).scalar()
        or 0
    )

    # Retention queue size — clientes com ultimo protocolo >5y atras
    ts_5y = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=1825)
    retention_queue_size = int(
        db.execute(
            text(
                "SELECT COUNT(DISTINCT c.id) FROM clientes c "
                "LEFT JOIN protocolos p ON p.cliente_id = c.id "
                "WHERE c.deleted_at IS NULL "
                "AND (p.created_at IS NULL OR p.created_at < :ts_5y)"
            ),
            {"ts_5y": ts_5y},
        ).scalar()
        or 0
    )

    # Audit chain integrity
    from app.services.audit import AuditService

    chain_ok, chain_length = AuditService.verify_chain(db)

    # Last audit entry
    last_entry = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    last_audit = (
        {
            "id": last_entry.id,
            "action": last_entry.action,
            "resource": last_entry.resource,
            "actor_id": last_entry.actor_id,
            "timestamp": last_entry.timestamp.isoformat() if last_entry.timestamp else None,
        }
        if last_entry
        else None
    )

    # Audit log do acesso (LGPD art. 37)
    from app.services.audit import AuditService
    from app.services.audit_context import audit_kwargs

    AuditService.log(
        db,
        actor_id="dpo:dashboard_access",
        actor_type="dpo",
        action="lgpd.dpo.metrics.access",
        resource="system",
        payload={"sub": _dpo_payload.get("sub", "")},
        **audit_kwargs(request),
    )

    return {
        "gerado_em": datetime.now(tz=timezone.utc).isoformat(),
        "clientes": {
            "total": total_clientes,
            "ativos": clientes_ativos,
            "anonimizados": clientes_anonimizados,
        },
        "conversas": {
            "total": total_conversas,
        },
        "audit": {
            "chain_length": total_audit,
            "chain_ok": chain_ok,
            "chain_last_valid_position": chain_length,
            "entries_24h": audit_24h,
            "last_entry": last_audit,
        },
        "rights_art_18_exercidos_30d": rights_30d,
        "retention_queue_size": retention_queue_size,
        "retention_policy": {
            "clientes_com_protocolo_anos": 5,
            "clientes_sem_protocolo_anos": 5,
            "conversas_dias": 90,
            "audit_log_anos": 7,
            "base_legal": "Provimento CNJ 74/2018 + LGPD art. 37",
        },
    }


# ============================================================================
# Endpoint 2: /audit-trail/{cliente_id}
# ============================================================================


@dpo_dashboard_router.get(
    "/audit-trail/{cliente_id}",
    summary="DTO DPO — Audit trail completo de um cliente (LGPD art. 37)",
    description=(
        "Retorna historico completo de TODAS as operacoes envolvendo o titular:\n\n"
        "- Criacoes de protocolo\n"
        "- Atualizacoes\n"
        "- Acessos (LGPD rights exercidos)\n"
        "- Anonimizacao / soft delete\n"
        "- Exports\n\n"
        "**LGPD-by-design**: IP completo eh mostrado apenas para o DPO "
        "(cuja role eh a de Encarregado - art. 41). NAO expoe PII raw.\n\n"
        "Auth: X-API-Key + JWT Bearer com claim dpo=True."
    ),
)
def get_dpo_audit_trail(
    cliente_id: Annotated[int, Path(ge=1)],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    _dpo_payload: dict = Depends(require_dpo_role),  # type: ignore[type-arg]
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Audit trail consolidado para um cliente (D25)."""
    from app.models.audit_log import AuditLog
    from app.models.cliente import Cliente
    from app.services.audit import AuditService
    from app.services.audit_context import audit_kwargs

    # Verifica cliente existe
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail={"erro": "CLIENTE_NOT_FOUND", "cliente_id": cliente_id},
        )

    # Busca audit entries que referenciam esse cliente via:
    # (a) AuditLog.resource == f"cliente:{id}"
    # (b) AuditLog.resource == f"cliente/{id}" (lgpd_consent usa esse formato)
    # (c) AuditLog.actor_id == str(id) AND actor_type == "cliente"
    resource_patterns = [f"cliente:{cliente_id}", f"cliente/{cliente_id}"]

    entries_a = (
        db.query(AuditLog)
        .filter(AuditLog.resource.in_(resource_patterns))
        .order_by(AuditLog.timestamp.desc())
        .all()
    )
    entries_b = (
        db.query(AuditLog)
        .filter(AuditLog.actor_id == str(cliente_id))
        .filter(AuditLog.actor_type == "cliente")
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    # Merge + dedup por id
    seen = set()
    merged: list[AuditLog] = []
    for e in list(entries_a) + list(entries_b):
        if e.id not in seen:
            seen.add(e.id)
            merged.append(e)
    merged.sort(key=lambda e: e.timestamp, reverse=True)

    # Aplica paginacao
    total = len(merged)
    entries_paged = merged[offset : offset + limit]

    # Mascaramento PII no output (LGPD-by-design)
    trail: list[dict[str, Any]] = []
    for e in entries_paged:
        trail.append(
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "action": e.action,
                "resource": e.resource,
                "actor_id": e.actor_id,
                "actor_type": e.actor_type,
                "ip_truncated": getattr(e, "ip_truncated", None),
                "user_agent": (e.user_agent or "")[:100] if e.user_agent else None,
                "request_id": e.request_id,
                "canal": e.canal,
                # Hash chain — garantia de integridade
                "hash": e.hash[:16] + "...",  # truncado para DPO nao precisa ver tudo
                "prev_hash": (e.prev_hash[:16] + "...") if e.prev_hash else None,
                "lgpd_relevant": (e.action or "").startswith("lgpd."),
            }
        )

    # Log do acesso (DPO only)
    AuditService.log(
        db,
        actor_id="dpo:audit_trail_access",
        actor_type="dpo",
        action="lgpd.dpo.audit_trail.access",
        resource=f"cliente:{cliente_id}",
        payload={"total_entries": total, "returned": len(trail)},
        **audit_kwargs(request),
    )

    return {
        "cliente_id": cliente_id,
        "cliente_anonimizado": cliente.deleted_at is not None,
        "total_entries": total,
        "limit": limit,
        "offset": offset,
        "returned": len(trail),
        "audit_trail": trail,
    }


# ============================================================================
# Endpoint 3: /retention-queue
# ============================================================================


@dpo_dashboard_router.get(
    "/retention-queue",
    summary="DPO DPO — Itens elegiveis para retencao LGPD hoje",
    description=(
        "Lista clientes que podem ser anonimizados HOJE segundo a politica:\n\n"
        "- Cliente COM protocolo: 5 anos pos-ultimo protocolo (Provimento CNJ 74/2018)\n"
        "- Cliente SEM protocolo: 5 anos pos-cadastro (LGPD art. 6 II — minimizacao)\n\n"
        "Retorna ate 200 IDs (mascarados como C{id:04d} por LGPD-by-design) "
        "para o DPO revisar antes de acionar o orquestrador de erasure.\n\n"
        "Auth: X-API-Key + JWT Bearer com claim dpo=True."
    ),
)
def get_dpo_retention_queue(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    _dpo_payload: dict = Depends(require_dpo_role),  # type: ignore[type-arg]
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> dict[str, Any]:
    """Lista clientes elegiveis para retencao hoje (D25)."""
    from app.services.audit import AuditService
    from app.services.audit_context import audit_kwargs

    ts_5y = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(days=1825)

    # Cross-dialect query — clientes que NAO foram tocados por 5+ anos
    stmt = text(
        "SELECT c.id, c.nome, c.cpf_hash, c.created_at, "
        "MAX(p.created_at) AS ultimo_protocolo "
        "FROM clientes c "
        "LEFT JOIN protocolos p ON p.cliente_id = c.id "
        "WHERE c.deleted_at IS NULL "
        "AND (c.created_at < :ts_5y OR p.created_at < :ts_5y "
        "OR (p.created_at IS NULL AND c.created_at < :ts_5y)) "
        "GROUP BY c.id "
        "ORDER BY c.created_at ASC LIMIT :limit"
    )

    rows = db.execute(stmt, {"limit": int(limit), "ts_5y": ts_5y}).mappings().all()

    # Mascaramento PII (LGPD-by-design)
    def _coerce_dt(value: Any) -> datetime | None:
        """Converte string ISO ou datetime para datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return None
        return None

    items = []
    for r in rows:
        created_at = _coerce_dt(r.get("created_at"))
        ultimo_protocolo = _coerce_dt(r.get("ultimo_protocolo"))
        if ultimo_protocolo:
            dias_inativo = (
                datetime.now(tz=timezone.utc).replace(tzinfo=None) - ultimo_protocolo
            ).days
        elif created_at:
            dias_inativo = (datetime.now(tz=timezone.utc).replace(tzinfo=None) - created_at).days
        else:
            dias_inativo = None

        items.append(
            {
                "cliente_id_mascarado": f"C{int(r['id']):04d}",
                "cpf_hash_mascarado": ((r["cpf_hash"][:8] + "...") if r.get("cpf_hash") else None),
                "created_at": created_at.isoformat() if created_at else None,
                "ultimo_protocolo": (ultimo_protocolo.isoformat() if ultimo_protocolo else None),
                "dias_inativo": dias_inativo,
                "base_legal_retencao": "Provimento CNJ 74/2018 art. 14 (5 anos)",
            }
        )

    # Audit log do acesso
    AuditService.log(
        db,
        actor_id="dpo:retention_queue_access",
        actor_type="dpo",
        action="lgpd.dpo.retention_queue.access",
        resource="system",
        payload={"total_items": len(items)},
        **audit_kwargs(request),
    )

    return {
        "gerado_em": datetime.now(tz=timezone.utc).isoformat(),
        "policy": {
            "clientes_com_protocolo_anos": 5,
            "clientes_sem_protocolo_anos": 5,
            "base_legal": "Provimento CNJ 74/2018 + LGPD art. 6o II",
        },
        "total_items": len(items),
        "limit": limit,
        "items": items,
        "aviso": (
            "Para anonimizar de fato, acione o orquestrador "
            "(POST /api/v1/lgpd/erasure/erase/{cliente_id} - em construcao) "
            "ou use a CLI retencao_diaria."
        ),
    }


__all__ = ["dpo_dashboard_router"]
