"""LGPD Consent API endpoint (G6.C.T9).

Endpoint POST /api/v1/lgpd/consent:
- Recebe consentimento via sendBeacon ou fetch do banner
- Persiste no banco (LGPD audit trail, art. 37)
- Retorna 204 No Content (sendBeacon friendly)

Endpoint GET /api/v1/lgpd/consent/stats:
- Estatisticas agregadas (LGPD art. 37)
- Apenas para DPO/admin

LGPD:
- art. 7 I (consentimento opt-in)
- art. 8 (confirmacao clara)
- art. 18 IX (oposicao)
- art. 37 (registro de operacoes)

Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 20.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.lgpd_consent import LGPDConsentLog
from app.schemas.lgpd_consent import (
    LGPDConsentRequest,
    LGPDConsentStats,
)

# Import model para Base.metadata.create_all() registrar tabela

router = APIRouter(prefix="/api/v1/lgpd/consent", tags=["lgpd"])


@router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Registra consentimento LGPD do titular",
)
def create_consent(
    payload: LGPDConsentRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """Registra consentimento LGPD enviado pelo banner widget.

    - Aceita payload minimo (accepted bool + versao)
    - Persiste hash do IP (LGPD: nao armazenar IP cru)
    - Audit log entry (LGPD art. 37)
    - Resposta 204 (sendBeacon friendly)
    """
    # Hash IP (LGPD art. 46: nao armazenar IP cru)
    import hashlib

    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]

    # User agent (truncado para evitar PII)
    user_agent = (request.headers.get("user-agent") or "")[:200]

    log_entry = LGPDConsentLog(
        accepted=payload.accepted,
        analytics=payload.analytics,
        marketing=payload.marketing,
        version=payload.version,
        ip_hash=ip_hash,
        user_agent=user_agent,
        timestamp=datetime.now(timezone.utc),
        session_id=payload.session_id,
    )
    db.add(log_entry)

    # LGPDConsentLog ja eh o audit trail (art. 37)
    # Nao duplicar com AuditService.log() para evitar overhead

    db.commit()


@router.get(
    "/stats",
    response_model=LGPDConsentStats,
    summary="Estatisticas agregadas de consentimento (DPO only)",
)
def get_consent_stats(db: Session = Depends(get_db)) -> LGPDConsentStats:
    """Retorna taxa de consentimento e oposicao agregados.

    Apenas DPO/admin deveria acessar (em prod, adicionar auth).
    """
    from sqlalchemy import func

    total = db.query(func.count(LGPDConsentLog.id)).scalar() or 0
    accepted = (
        db.query(func.count(LGPDConsentLog.id)).filter(LGPDConsentLog.accepted.is_(True)).scalar()
        or 0
    )
    rejected = (
        db.query(func.count(LGPDConsentLog.id)).filter(LGPDConsentLog.accepted.is_(False)).scalar()
        or 0
    )
    analytics_opt_in = (
        db.query(func.count(LGPDConsentLog.id)).filter(LGPDConsentLog.analytics.is_(True)).scalar()
        or 0
    )
    marketing_opt_in = (
        db.query(func.count(LGPDConsentLog.id)).filter(LGPDConsentLog.marketing.is_(True)).scalar()
        or 0
    )

    consent_ratio = accepted / total if total > 0 else 0

    return LGPDConsentStats(
        total=total,
        accepted=accepted,
        rejected=rejected,
        analytics_opt_in=analytics_opt_in,
        marketing_opt_in=marketing_opt_in,
        consent_ratio=consent_ratio,
        breakdown=[],
    )
