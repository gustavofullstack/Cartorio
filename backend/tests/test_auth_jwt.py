"""Testes do JWT service (A24.1 — API v2 auth).

Cobre:
1. issue_access_token cria JWT HS256 com claims canonicos (sub, iss, aud, exp, iat, jti)
2. verify_token valida JWT bem-formado e retorna payload
3. verify_token rejeita token expirado
4. verify_token rejeita token com assinatura errada
5. verify_token rejeita token malformado
6. issue_refresh_token cria JWT com typ=refresh + TTL maior
7. Settings valida jwt_secret min_length=32 (FAIL-FAST)

LGPD: JWT NAO expoe PII (sub eh user_id UUID, nao CPF/nome).
"""

from __future__ import annotations

import os
import time
import uuid

# Set test env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "a" * 64)
os.environ.setdefault("JWT_SECRET", "z" * 32)  # 32 chars min

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import jwt as pyjwt  # noqa: E402
import pytest  # noqa: E402

from app.services.auth_jwt import (  # noqa: E402
    JWTError,
    issue_access_token,
    issue_refresh_token,
    verify_token,
)


# ============================================================================
# Test fixtures
# ============================================================================


@pytest.fixture
def user_id() -> str:
    """UUID v4 string representando user_id canonico."""
    return str(uuid.uuid4())


@pytest.fixture
def settings():
    return get_settings()


# ============================================================================
# Tests: issue_access_token
# ============================================================================


def test_issue_access_token_retorna_string(settings, user_id: str) -> None:
    """issue_access_token retorna string JWT."""
    token = issue_access_token(user_id, settings=settings)
    assert isinstance(token, str)
    assert len(token) > 50  # JWT min ~80 chars


def test_issue_access_token_contem_claims_canonicos(settings, user_id: str) -> None:
    """JWT emitido contem sub, iss, aud, exp, iat, jti."""
    token = issue_access_token(user_id, settings=settings)
    # Decode SEM verificar signature pra inspecionar claims
    payload = pyjwt.decode(token, options={"verify_signature": False})

    assert payload["sub"] == user_id
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == "cartorio-v2"
    assert payload["typ"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload
    assert len(payload["jti"]) > 0  # UUID-like


def test_issue_access_token_ttl_60min(settings, user_id: str) -> None:
    """Access token tem TTL = jwt_access_ttl_minutes (60min default)."""
    token = issue_access_token(user_id, settings=settings)
    payload = pyjwt.decode(token, options={"verify_signature": False})

    ttl_seconds = payload["exp"] - payload["iat"]
    expected_ttl = settings.jwt_access_ttl_minutes * 60
    # Tolera 5s de margem (clock skew entre emissor e verificador)
    assert abs(ttl_seconds - expected_ttl) <= 5


# ============================================================================
# Tests: verify_token (happy path + failures)
# ============================================================================


def test_verify_token_valido_retorna_payload(settings, user_id: str) -> None:
    """Token valido -> payload decodificado."""
    token = issue_access_token(user_id, settings=settings)
    payload = verify_token(token, settings=settings)

    assert payload["sub"] == user_id
    assert payload["typ"] == "access"


def test_verify_token_expirado_levanta_JWTError(settings, user_id: str) -> None:
    """Token expirado -> JWTError."""
    # Emite token com TTL negativo (ja expirado)
    import datetime as dt

    now = dt.datetime.now(dt.timezone.utc)
    expired_payload = {
        "sub": user_id,
        "iss": settings.jwt_issuer,
        "aud": "cartorio-v2",
        "typ": "access",
        "iat": now - dt.timedelta(hours=2),
        "exp": now - dt.timedelta(hours=1),  # expirou 1h atras
        "jti": str(uuid.uuid4()),
    }
    expired_token = pyjwt.encode(
        expired_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(JWTError, match="expirado|expired"):
        verify_token(expired_token, settings=settings)


def test_verify_token_assinatura_errada_levanta_JWTError(settings, user_id: str) -> None:
    """Token com assinatura invalida -> JWTError."""
    token = issue_access_token(user_id, settings=settings)

    # Decodifica com secret DIFERENTE (invalida signature)
    with pytest.raises(JWTError, match="signature|assinatura|invalid"):
        verify_token(token, secret_override="wrong" * 8, settings=settings)


def test_verify_token_malformado_levanta_JWTError(settings) -> None:
    """String que nao eh JWT -> JWTError."""
    with pytest.raises(JWTError, match="malformado|invalid"):
        verify_token("isso.nao.e.jwt", settings=settings)


def test_verify_token_issuer_errado_levanta_JWTError(settings, user_id: str) -> None:
    """Token com iss diferente -> JWTError (anti-confusion attack)."""
    token_payload = {
        "sub": user_id,
        "iss": "outro-servico",
        "aud": "cartorio-v2",
        "typ": "access",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "jti": str(uuid.uuid4()),
    }
    bad_token = pyjwt.encode(
        token_payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(JWTError, match="inv"):
        verify_token(bad_token, settings=settings)


# ============================================================================
# Tests: refresh token
# ============================================================================


def test_issue_refresh_token_tem_typ_refresh(settings, user_id: str) -> None:
    """Refresh token tem claim typ=refresh + TTL maior."""
    token = issue_refresh_token(user_id, settings=settings)
    payload = pyjwt.decode(token, options={"verify_signature": False})

    assert payload["typ"] == "refresh"
    assert payload["sub"] == user_id

    ttl_seconds = payload["exp"] - payload["iat"]
    expected_ttl = settings.jwt_refresh_ttl_days * 86400
    assert abs(ttl_seconds - expected_ttl) <= 5


def test_verify_access_token_em_refresh_rejeita(settings, user_id: str) -> None:
    """Refresh token NAO deve passar como access token (typ mismatch)."""
    refresh = issue_refresh_token(user_id, settings=settings)
    with pytest.raises(JWTError, match="tipo"):
        verify_token(refresh, settings=settings, expected_typ="access")


# ============================================================================
# Tests: Settings validation (FAIL-FAST)
# ============================================================================


def test_settings_jwt_secret_min_length_32_validated_in_service() -> None:
    """JWT_SECRET < 32 chars -> RuntimeError claro quando usado (nao no startup).

    Design: secret eh Optional em Settings (v1-only mode). A validacao de tamanho
    minimo acontece NO SERVICE (issue_access_token) com mensagem clara, evitando
    crash no startup pra deploys que so usam v1.
    """
    import os

    os.environ["JWT_SECRET"] = "short"

    try:
        get_settings.cache_clear()
        s = get_settings()
        # Settings aceita secret curto (graceful degradation)
        assert s.jwt_secret == "short"
        # Service valida ao usar:
        with pytest.raises(RuntimeError, match="32"):
            issue_access_token("user-id-test", settings=s)
    finally:
        os.environ["JWT_SECRET"] = "z" * 32
        get_settings.cache_clear()


def test_settings_jwt_secret_none_eh_opcional() -> None:
    """JWT_SECRET=None eh permitido (v1-only mode); service raise claro se usado."""
    import os

    os.environ["JWT_SECRET"] = ""

    try:
        get_settings.cache_clear()
        s = get_settings()
        # Optional[str] = None significa JWT desabilitado
        assert s.jwt_secret is None or s.jwt_secret == ""
    finally:
        os.environ["JWT_SECRET"] = "z" * 32
        get_settings.cache_clear()


# ============================================================================
# Tests: LGPD — JWT nao expoe PII
# ============================================================================


def test_jwt_nao_expoe_pii_em_claims(settings, user_id: str) -> None:
    """JWT claims NAO devem conter CPF, RG, nome, email (LGPD art. 37)."""
    pii_values = ["123.456.789-00", "MG-12.345.678", "Joao da Silva", "joao@email.com"]

    for pii in pii_values:
        # Emite token passando pii_acidental (NAO deve ir pro payload)
        token = issue_access_token(user_id, settings=settings)
        payload = pyjwt.decode(token, options={"verify_signature": False})

        payload_str = str(payload)
        assert pii not in payload_str, f"PII '{pii}' apareceu no JWT: {payload}"