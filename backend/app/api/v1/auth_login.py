"""auth_login.py - endpoints de autenticacao para JWT (LGPD D26-D32).

Turno 22+ (2026-06-29): Sprint 3 implementacao.

POST /api/v1/auth/login -> emite access token + refresh token
POST /api/v1/auth/refresh -> emite novo access token usando refresh
GET  /api/v1/auth/me -> info do usuario autenticado

Auth:
- v1 (X-API-Key admin) -> pode mintar JWT para qualquer user_id (uso operacional)
- v2 (POST /login) -> user/password contra Supabase Auth (futuro, Sprint 4)

LGPD:
- tokens NAO expoem PII (apenas user_id UUID)
- claims minimas: sub, iss, aud, typ, exp, iat, jti, dpo
- audit log de todo login (login_attempt, success/failure, user_id, ip)

Rate limit: 10 req/min por IP (protege contra brute force).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps import require_cartorio_api_key
from app.config import Settings, get_settings
from app.services.auth_jwt import (
    JWTError,
    issue_access_token,
    issue_refresh_token,
    verify_token,
)
from app.services.audit_context import audit_kwargs

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Request do /auth/login - modo admin (mint JWT para user arbitrario).

    Auth: requer X-API-Key admin (B0.3.SEC 2026-06-25).
    LGPD: user_id nao expoe PII, apenas UUID.
    """

    user_id: str = Field(
        ...,
        description="UUID do usuario para quem o JWT sera emitido",
        min_length=36,
        max_length=36,
    )
    dpo: bool = Field(
        default=False,
        description="Se True, emite JWT com claim dpo=True (acesso LGPD)",
    )
    ttl_minutes: int | None = Field(
        default=None,
        ge=1,
        le=1440,
        description="Override TTL access token (1min-24h). Default = settings.jwt_access_ttl_minutes",
    )


class RefreshRequest(BaseModel):
    """Request do /auth/refresh - troca refresh token por novo access."""

    refresh_token: str = Field(
        ...,
        description="Refresh token JWT obtido via /auth/login",
        min_length=20,
    )


class TokenResponse(BaseModel):
    """Response padrao para /auth/login e /auth/refresh."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int  # seconds
    user_id: str
    dpo: bool


class MeResponse(BaseModel):
    """Response do /auth/me - info do titular do JWT."""

    user_id: str
    dpo: bool
    exp: int
    iat: int


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Mint JWT para um user_id (modo admin)",
    description=(
        "Emite access token + refresh token JWT para o user_id informado. "
        "Requer X-API-Key admin. Sprint 4: substituir por login Supabase Auth "
        "(POST /auth/v1/token?grant_type=password) e lookup de user_id. "
        "LGPD: tokens NAO expoem PII."
    ),
    responses={
        200: {"description": "Tokens emitidos com sucesso"},
        401: {"description": "X-API-Key invalido ou ausente"},
        422: {"description": "user_id malformado ou ttl fora do range"},
    },
)
async def login(
    payload: LoginRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
) -> TokenResponse:
    """Mint JWT access + refresh tokens."""
    # Audit log
    from app.services.audit import AuditService
    from app.db import session_scope

    try:
        with session_scope() as db:
            access_ttl_min = payload.ttl_minutes or settings.jwt_access_ttl_minutes

            access_token = issue_access_token(
                payload.user_id,
                dpo=payload.dpo,
                settings=settings,
            )
            refresh_token = issue_refresh_token(
                payload.user_id,
                settings=settings,
            )

            ctx = audit_kwargs(request)
            ctx["canal"] = "admin"  # override: auth endpoint é sempre canal=admin
            AuditService.log(
                db,
                actor_id="auth_login_admin",
                actor_type="system",
                action="auth.login.mint",
                resource=f"user:{payload.user_id}",
                payload={
                    "dpo": payload.dpo,
                    "ttl_minutes": access_ttl_min,
                },
                **ctx,
            )
    except Exception as e:
        logger.exception("Erro ao mintar JWT: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"erro": "INTERNAL_ERROR", "mensagem": "Falha ao gerar token."},
        ) from e

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user_id=payload.user_id,
        dpo=payload.dpo,
    )


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Trocar refresh token por novo access token",
    description=(
        "Recebe refresh_token valido (typ=refresh) e retorna novo access token. "
        "Refresh token rotation: novo refresh_token retornado a cada uso (Sprint 4)."
    ),
)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Troca refresh por novo access."""
    try:
        refresh_payload = verify_token(
            payload.refresh_token,
            expected_typ="refresh",
            settings=settings,
        )
    except JWTError as e:
        logger.warning("Refresh token invalido: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"erro": "INVALID_REFRESH", "mensagem": "Refresh token invalido ou expirado."},
        ) from e

    user_id = refresh_payload["sub"]

    access_token = issue_access_token(user_id, settings=settings)
    new_refresh = issue_refresh_token(user_id, settings=settings)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="Bearer",
        expires_in=settings.jwt_access_ttl_minutes * 60,
        user_id=user_id,
        dpo=False,
    )


@auth_router.get(
    "/me",
    response_model=MeResponse,
    summary="Info do usuario autenticado via JWT",
    description="Retorna claims minimas do JWT (user_id, dpo, exp, iat).",
)
async def me(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> MeResponse:
    """Retorna payload do JWT atual."""
    from app.api.deps import _extract_bearer_token, _verify_jwt_payload

    token = _extract_bearer_token(request)
    try:
        payload = _verify_jwt_payload(token)
    except HTTPException:
        raise
    return MeResponse(
        user_id=payload.get("sub", ""),
        dpo=payload.get("dpo", False),
        exp=payload.get("exp", 0),
        iat=payload.get("iat", 0),
    )
