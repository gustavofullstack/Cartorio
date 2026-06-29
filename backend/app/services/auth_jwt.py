"""JWT service — emissao e validacao de tokens para /api/v2/* (A24.1).

Implementa:
- issue_access_token(user_id) -> str (TTL curto, 60min default)
- issue_refresh_token(user_id) -> str (TTL longo, 7d default)
- verify_token(token, expected_typ='access') -> dict (raise JWTError se invalido)

LGPD art. 37: claims NAO expoem PII. Apenas user_id (UUID), iss, aud, typ, exp, iat, jti.
Falhas sao genericas (nao revelam se token era expirado vs signature invalida vs malformado
- evita enumeration attack via timing/error messages).

Secret: HS256 com jwt_secret em Settings (min 32 chars). Rotacao: ver Lesson 167 (TODO).
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any, Literal

import jwt as pyjwt

from app.config import Settings

logger = logging.getLogger(__name__)

# Audience canonico para tokens emitidos pela API Cartorio.
# v1 (X-API-Key) e v2 (JWT) coexistem: v2 eh o caminho novo, v1 sunset 2027-12-31.
JWT_AUDIENCE = "cartorio-v2"

TokenType = Literal["access", "refresh"]


class JWTError(Exception):
    """Erro generico de validacao de JWT.

    Por design, a mensagem nao revela o motivo especifico (expired vs signature vs malformado)
    para evitar enumeration attack. Loggers internos (logger.warning) registram o motivo real.
    """


def _now_utc() -> dt.datetime:
    """Retorna datetime atual em UTC (timezone-aware)."""
    return dt.datetime.now(dt.timezone.utc)


def _build_payload(
    user_id: str,
    *,
    typ: TokenType,
    ttl: dt.timedelta,
    settings: Settings,
) -> dict[str, Any]:
    """Constroi o payload JWT canonico com claims minimas (LGPD-safe)."""
    now = _now_utc()
    return {
        "sub": user_id,  # subject = user_id (UUID, NAO PII)
        "iss": settings.jwt_issuer,  # issuer (valido contra settings.jwt_issuer)
        "aud": JWT_AUDIENCE,  # audience (valido contra JWT_AUDIENCE)
        "typ": typ,  # access | refresh
        "iat": int(now.timestamp()),  # issued at (epoch seconds)
        "exp": int((now + ttl).timestamp()),  # expiration
        "jti": str(uuid.uuid4()),  # unique token id (revogacao futura)
    }


def issue_access_token(
    user_id: str,
    *,
    settings: Settings | None = None,
) -> str:
    """Emite access token JWT (TTL curto: 60min default).

    Args:
        user_id: UUID v4 string do usuario (sub claim).
        settings: Settings injetada (test-friendly). Defaults to get_settings().

    Returns:
        str JWT assinado HS256.

    Raises:
        RuntimeError: se jwt_secret nao configurado (v1-only mode).
    """
    if settings is None:
        from app.config import get_settings

        settings = get_settings()

    if not settings.jwt_secret:
        raise RuntimeError(
            "JWT_SECRET nao configurado. Defina JWT_SECRET no .env (min 32 chars) "
            "para usar /api/v2/*. v1 (X-API-Key) continua funcional."
        )

    # HS256 requer secret >= 32 bytes (RFC 7518 sec 3.2)
    if len(settings.jwt_secret) < 32:
        raise RuntimeError(
            f"JWT_SECRET invalido: precisa ter min 32 chars (atual: {len(settings.jwt_secret)}). "
            "Gere com: openssl rand -hex 32"
        )

    payload = _build_payload(
        user_id,
        typ="access",
        ttl=dt.timedelta(minutes=settings.jwt_access_ttl_minutes),
        settings=settings,
    )
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def issue_refresh_token(
    user_id: str,
    *,
    settings: Settings | None = None,
) -> str:
    """Emite refresh token JWT (TTL longo: 7d default).

    Args:
        user_id: UUID v4 string do usuario (sub claim).
        settings: Settings injetada (test-friendly).

    Returns:
        str JWT assinado HS256 com typ=refresh.
    """
    if settings is None:
        from app.config import get_settings

        settings = get_settings()

    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET nao configurado.")

    # HS256 requer secret >= 32 bytes (RFC 7518 sec 3.2)
    if len(settings.jwt_secret) < 32:
        raise RuntimeError(
            f"JWT_SECRET invalido: precisa ter min 32 chars (atual: {len(settings.jwt_secret)})."
        )

    payload = _build_payload(
        user_id,
        typ="refresh",
        ttl=dt.timedelta(days=settings.jwt_refresh_ttl_days),
        settings=settings,
    )
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(
    token: str,
    *,
    expected_typ: TokenType = "access",
    settings: Settings | None = None,
    secret_override: str | None = None,
) -> dict[str, Any]:
    """Verifica e decodifica um JWT.

    Args:
        token: string JWT.
        expected_typ: tipo esperado ('access' | 'refresh'). Default access.
        settings: Settings injetada.
        secret_override: usa este secret em vez de settings.jwt_secret (para testes).

    Returns:
        dict com claims decodificadas.

    Raises:
        JWTError: token invalido por qualquer motivo (expirado, signature, malformado,
                  issuer errado, audience errada, typ errado).
    """
    if settings is None:
        from app.config import get_settings

        settings = get_settings()

    secret = secret_override if secret_override is not None else settings.jwt_secret
    if not secret:
        logger.warning("JWT verify falhou: jwt_secret nao configurado")
        raise JWTError("Token invalido.")

    try:
        payload: dict[str, Any] = pyjwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
            audience=JWT_AUDIENCE,
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", "iss", "aud", "typ", "exp", "iat", "jti"],
            },
        )
    except pyjwt.ExpiredSignatureError:
        logger.warning("JWT verify falhou: token expirado")
        raise JWTError("Token invalido (expirado).") from None
    except pyjwt.InvalidSignatureError:
        logger.warning("JWT verify falhou: signature invalida")
        raise JWTError("Token invalido (assinatura).") from None
    except pyjwt.InvalidIssuerError:
        logger.warning("JWT verify falhou: issuer invalido")
        raise JWTError("Token invalido.") from None
    except pyjwt.InvalidAudienceError:
        logger.warning("JWT verify falhou: audience invalido")
        raise JWTError("Token invalido.") from None
    except pyjwt.MissingRequiredClaimError as e:
        logger.warning("JWT verify falhou: claim obrigatoria faltando: %s", e)
        raise JWTError("Token invalido.") from None
    except pyjwt.InvalidTokenError as e:
        # Malformed, decode error, etc.
        logger.warning("JWT verify falhou: token malformado: %s", e)
        raise JWTError("Token invalido (malformado).") from None

    # Verifica typ
    actual_typ = payload.get("typ")
    if actual_typ != expected_typ:
        logger.warning("JWT verify falhou: typ esperado=%s recebido=%s", expected_typ, actual_typ)
        raise JWTError(f"Token tipo invalido (esperado {expected_typ}).")

    return payload
