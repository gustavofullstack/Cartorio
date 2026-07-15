"""LGPD Privacy Policy Endpoint (D22).

Endpoint que retorna a Privacy Policy personalizada para um titular especifico
(GDPR art. 13/14 / LGPD art. 9 + art. 18).

GET /api/v1/lgpd/privacy-policy/{cliente_id}?format=markdown|json

- Markdown: pronto para envio via Telegram/WhatsApp pelo bot
- JSON: estruturado para integracao com front-end / N8N

Auth: X-API-Key (mesma chave padrao do cartorio). LGPD-by-design: nome + email
do titular sao mascarados no output.

References:
- LGPD art. 9 (consentimento especifico e esclarecido)
- LGPD art. 18 (direitos do titular)
- Recomendacao ANPD 04/2023 (politica personalizada)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key
from app.db import get_db

privacy_policy_router = APIRouter(tags=["lgpd-privacy-policy"])


@privacy_policy_router.get(
    "/lgpd/privacy-policy/{cliente_id}",
    summary="Privacy Policy personalizada para um titular (LGPD art. 9 + art. 18)",
    description=(
        "Retorna a Politica de Privacidade personalizada do titular, listando:\n"
        "- Dados pessoais tratados sobre esse titular (anonimizados)\n"
        "- Finalidades consentidas e revogadas\n"
        "- Os 6 direitos do art. 18 com endpoints reais\n"
        "- Contact do DPO (Gustavo Almeida, telegram 6682284055)\n"
        "- Politica de retencao especifica para esse titular\n\n"
        "Format: `markdown` (pronto para Telegram/WhatsApp) ou `json` "
        "(estruturado para integracoes).\n\n"
        "LGPD-by-design: nome e email do titular sao mascarados no output.\n\n"
        "Auth: X-API-Key obrigatorio."
    ),
)
def get_privacy_policy(
    cliente_id: Annotated[int, Path(ge=1, description="ID do titular")],
    request: Request,
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    format: str = Query("markdown", pattern="^(markdown|json)$"),
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> JSONResponse:
    """Gera Privacy Policy personalizada (D22)."""
    from app.services.lgpd_privacy_policy import (
        generate_privacy_policy,
        generate_privacy_policy_structured,
    )

    try:
        if format == "json":
            payload: dict[str, Any] | str = generate_privacy_policy_structured(db, cliente_id)
        else:
            payload = generate_privacy_policy(db, cliente_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "erro": "CLIENTE_NOT_FOUND",
                "cliente_id": cliente_id,
                "mensagem": str(exc),
            },
        )

    if format == "json":
        return JSONResponse(status_code=200, content=payload)
    return JSONResponse(
        status_code=200,
        content={
            "cliente_id": cliente_id,
            "format": "markdown",
            "policy_markdown": payload,
        },
    )


__all__ = ["privacy_policy_router"]
