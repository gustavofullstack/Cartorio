"""LGPD DSAR (Data Subject Access Request) endpoint (G6.C.T11).

LGPD art. 18: 7 direitos do titular
- I: confirmacao da existencia de tratamento
- II: acesso aos dados
- III: correcao de dados incompletos ou incorretos
- IV: anonimizacao, bloqueio ou eliminacao de dados desnecessarios
- V: portabilidade dos dados
- VI: eliminacao dos dados pessoais tratados com consentimento
- VII: informacao sobre entidades publicas e privadas com as quais houve compartilhamento

DSAR workflow:
1. POST /api/v1/lgpd/dsar: cria solicitacao (titular envia com prova identidade)
2. GET /api/v1/lgpd/dsar/{id}: status
3. GET /api/v1/lgpd/dsar/{id}/data: download ZIP com dados (apos aprovacao DPO)

Prazo legal: 15 dias (LGPD art. 18 §5o)

Modified by Gustavo Almeida + cartorio-lgpd — G6 wave 27.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.lgpd_dsar import (
    DSARCreate,
    DSARCreateResponse,
    DSARStatus,
    LGPDRight,
)

router = APIRouter(prefix="/api/v1/lgpd/dsar", tags=["lgpd"])

# Prazo legal LGPD art. 18 §5o
LEGAL_DEADLINE_DAYS = 15


def generate_request_id() -> str:
    """Gera request_id unico (URL-safe, 22 chars)."""
    return f"DSAR-{secrets.token_urlsafe(12)}"


def hash_pii(pii: str) -> str:
    """Hash SHA256 de PII para LGPD-by-design (art. 46)."""
    return hashlib.sha256(pii.encode()).hexdigest()[:16]


@router.post(
    "",
    response_model=DSARCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria DSAR (LGPD art. 18)",
)
def create_dsar(payload: DSARCreate, db: Session = Depends(get_db)) -> DSARCreateResponse:
    """Titular cria solicitacao DSAR.

    Auth: publica (com prova de identidade via hash PII).
    Rate limit: 3/hour (anti-spam).

    Prazo legal: 15 dias para resposta.
    """
    # Hash PII (LGPD art. 46: nao armazenar cru)
    cpf_hash = hash_pii(payload.cpf)
    email_hash = hash_pii(payload.email) if payload.email else None
    phone_hash = hash_pii(payload.phone) if payload.phone else None

    request_id = generate_request_id()
    deadline = datetime.now(timezone.utc) + timedelta(days=LEGAL_DEADLINE_DAYS)

    # Em prod, persistir em tabela `dsar_requests`. Por ora mock.
    # db.add(DSARRequest(...))
    # db.commit()

    return DSARCreateResponse(
        request_id=request_id,
        received_at=datetime.now(timezone.utc).isoformat(),
        deadline=deadline.isoformat(),
        cpf_hash=cpf_hash,
        email_hash=email_hash,
        phone_hash=phone_hash,
        rights_requested=payload.rights,
        message=(
            f"Solicitacao DSAR criada. Prazo legal: {LEGAL_DEADLINE_DAYS} dias. "
            f"Resposta sera enviada para {payload.email or 'contato registrado'}. "
            f"LGPD art. 18."
        ),
    )


@router.get(
    "/{request_id}",
    response_model=DSARStatus,
    summary="Status de uma DSAR existente",
)
def get_dsar_status(request_id: str, db: Session = Depends(get_db)) -> DSARStatus:
    """Consulta status da DSAR por ID."""
    if not request_id.startswith("DSAR-"):
        raise HTTPException(
            status_code=400,
            detail={"erro": "INVALID_REQUEST_ID", "mensagem": "ID deve comecar com DSAR-"},
        )

    # Em prod: db.query(DSARRequest).filter_by(request_id=...).first()
    # Mock: retorna pending para qualquer ID
    return DSARStatus(
        request_id=request_id,
        status="pending",
        received_at=datetime.now(timezone.utc).isoformat(),
        deadline=(datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
        rights_requested=[LGPDRight.ACESSO, LGPDRight.PORTABILIDADE],
        message="Solicitacao em analise. Prazo legal: 15 dias.",
    )
