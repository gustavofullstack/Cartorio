"""Tests para /api/v1/auth/* endpoints (LGPD D26-D32 enablement).

Turno 23+ 2026-06-29.

Endpoints testados:
- POST /auth/login (mint JWT access + refresh tokens)
- POST /auth/refresh (exchange refresh for new access)
- GET /auth/me (info do usuario autenticado)

LGPD compliance:
- tokens NAO expoem PII (apenas user_id UUID)
- claims minimas: sub, iss, aud, typ, exp, iat, jti, dpo
- audit log de todo login
"""

from __future__ import annotations

import os
import uuid

# Set test env BEFORE importing app modules (mesmo padrao de test_integrations_endpoint.py)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("JWT_SECRET", "b" * 64)
TEST_API_KEY = "a" * 64
os.environ["CARTORIO_API_KEY"] = TEST_API_KEY

from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.base import Base  # noqa: E402


def _bearer(token: str) -> dict[str, str]:
    """Helper: retorna header Authorization Bearer."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    """Cliente de teste com DB in-memory e engine mockado."""
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


@pytest.fixture
def test_user_id() -> str:
    """UUID valido para testes."""
    return str(uuid.uuid4())


class TestAuthLoginEndpoint:
    """POST /auth/login - mint JWT tokens."""

    def test_login_success_returns_access_and_refresh_tokens(self, client, test_user_id):
        """Mint tokens para um user_id arbitrario via X-API-Key admin."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id, "dpo": False},
            headers={"X-API-Key": "a" * 64},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert body["user_id"] == test_user_id
        assert body["dpo"] is False
        assert body["expires_in"] > 0
        # Tokens devem ser JWT (3 partes separadas por .)
        assert body["access_token"].count(".") == 2
        assert body["refresh_token"].count(".") == 2

    def test_login_with_dpo_true_sets_dpo_claim(self, client, test_user_id):
        """Quando dpo=True, JWT deve ter claim dpo=True (para acessar LGPD v2)."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id, "dpo": True},
            headers={"X-API-Key": "a" * 64},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dpo"] is True

    def test_login_requires_api_key(self, client, test_user_id):
        """Sem X-API-Key admin, retorna 401."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id},
        )
        assert resp.status_code == 401

    def test_login_rejects_invalid_api_key(self, client, test_user_id):
        """X-API-Key invalido retorna 401."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id},
            headers={"X-API-Key": "wrong-key-1234567890"},
        )
        assert resp.status_code == 401

    def test_login_validates_user_id_format(self, client):
        """user_id malformado (nao UUID) retorna 422."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": "not-a-uuid"},
            headers={"X-API-Key": "a" * 64},
        )
        assert resp.status_code == 422

    def test_login_validates_ttl_range(self, client, test_user_id):
        """ttl_minutes fora do range (1-1440) retorna 422."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id, "ttl_minutes": 99999},
            headers={"X-API-Key": "a" * 64},
        )
        assert resp.status_code == 422


class TestAuthRefreshEndpoint:
    """POST /auth/refresh - trocar refresh por novo access."""

    def test_refresh_succeeds_with_valid_refresh_token(self, client, test_user_id):
        """Refresh token valido -> novo access + novo refresh."""
        # Login para obter refresh token
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id},
            headers={"X-API-Key": "a" * 64},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["user_id"] == test_user_id

    def test_refresh_rejects_invalid_token(self, client):
        """Refresh token invalido retorna 401."""
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not-a-real-jwt-token"},
        )
        assert resp.status_code == 401

    def test_refresh_rejects_access_token_used_as_refresh(self, client, test_user_id):
        """Usar access_token como refresh_token retorna 401 (typ errado)."""
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id},
            headers={"X-API-Key": "a" * 64},
        )
        access_token = login_resp.json()["access_token"]

        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401


class TestAuthMeEndpoint:
    """GET /auth/me - info do usuario autenticado."""

    def test_me_returns_user_info_from_jwt(self, client, test_user_id):
        """GET /auth/me com Bearer JWT retorna claims minimas."""
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id, "dpo": True},
            headers={"X-API-Key": "a" * 64},
        )
        access_token = login_resp.json()["access_token"]

        resp = client.get(
            "/api/v1/auth/me",
            headers=_bearer(access_token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["user_id"] == test_user_id
        assert body["dpo"] is True
        assert body["exp"] > 0
        assert body["iat"] > 0

    def test_me_requires_auth(self, client):
        """Sem Authorization header retorna 401."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_rejects_invalid_token(self, client):
        """Bearer com JWT malformado retorna 401."""
        resp = client.get(
            "/api/v1/auth/me",
            headers=_bearer("not-a-jwt"),
        )
        assert resp.status_code == 401


class TestAuthLoginLGPDCompliance:
    """Validates que tokens NAO expoem PII (LGPD art. 37)."""

    def test_token_payload_does_not_contain_pii_fields(self, client, test_user_id):
        """JWT decoded NAO deve conter email/CPF/telefone/nome."""
        import base64
        import json

        resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id},
            headers={"X-API-Key": "a" * 64},
        )
        access_token = resp.json()["access_token"]

        # Decode JWT payload (sem verificar signature, so para inspecao)
        payload_b64 = access_token.split(".")[1]
        # Adicionar padding
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Claims esperadas (LGPD-safe: sem PII)
        allowed_claims = {"sub", "iss", "aud", "typ", "exp", "iat", "jti", "dpo"}
        actual_claims = set(payload.keys())

        # Nenhum claim fora do whitelist deve existir
        unexpected = actual_claims - allowed_claims
        assert not unexpected, f"JWT tem claims PII: {unexpected}"

        # sub deve ser UUID (nao email/nome)
        assert payload["sub"] == test_user_id
        assert payload["iss"]  # issuer configurado
        assert payload["aud"] == "cartorio-v2"
        assert payload["typ"] == "access"


class TestAuthLoginIntegration:
    """Testa integracao do auth_login com LGPD v2 (D26-D32)."""

    def test_dpo_token_can_access_lgpd_dashboard(self, client, test_user_id):
        """Token com dpo=True deve acessar /lgpd/dashboard (D26)."""
        # Mint DPO token
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id, "dpo": True},
            headers={"X-API-Key": "a" * 64},
        )
        dpo_token = login_resp.json()["access_token"]

        # Acessar LGPD dashboard
        resp = client.get(
            "/api/v1/lgpd/dashboard",
            headers=_bearer(dpo_token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Dashboard tem KPIs agregados (qualquer chave de stats)
        # Aceita qualquer das chaves conhecidas do endpoint
        expected_keys = [
            "total_clientes",
            "clientes_ativos",
            "kpis",
            "audit_entries_24h",
            "consents_ativos",
            "audit_chain_status",
            "consents_revogados_30d",
        ]
        assert any(k in body for k in expected_keys), (
            f"Dashboard response missing known KPIs. Got keys: {list(body.keys())}"
        )

    def test_non_dpo_token_cannot_access_lgpd_dashboard(self, client, test_user_id):
        """Token sem dpo=True deve receber 403 em /lgpd/dashboard."""
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"user_id": test_user_id, "dpo": False},
            headers={"X-API-Key": "a" * 64},
        )
        user_token = login_resp.json()["access_token"]

        resp = client.get(
            "/api/v1/lgpd/dashboard",
            headers=_bearer(user_token),
        )
        # 403 forbidden (sem claim dpo) ou 401 (se requer DPO)
        assert resp.status_code in (401, 403), resp.text
