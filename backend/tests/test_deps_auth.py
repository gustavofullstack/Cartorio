"""Testes do dependency `require_cartorio_api_key` (B0.3 E0.AUTH fix, 2026-06-25).

Cobre 3 cenarios canonicos:
1. Header ausente -> 401
2. Header com valor errado -> 401
3. Header com valor correto -> sucesso

Mais:
- Header em lowercase (x-api-key) tambem funciona (compat HTTP)
- Configuracao estrita: cartorio_api_key NAO pode ser None/vazio (FAIL-FAST)

Referencia: cartorio-dev/AGENTS.md - toda mutacao grava audit log, toda saida
para LLM passa pelo PII scrubber. Auth gate eh a primeira linha de defesa
contra LGPD vazamentos (acesso nao autorizado a clientes/protocolos).
"""

from __future__ import annotations

import os

# Set test env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
# 64-char hex (validacao strict em config.py: B0.3 2026-06-25)
TEST_CARTORIO_API_KEY = "a" * 64
os.environ.setdefault("CARTORIO_API_KEY", TEST_CARTORIO_API_KEY)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi import FastAPI, Depends  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import require_cartorio_api_key  # noqa: E402


# ============================================================================
# Test app fixture
# ============================================================================


@pytest.fixture
def app() -> FastAPI:
    """App FastAPI minima so pra testar o dependency de auth."""

    def protected_endpoint(api_key: str = Depends(require_cartorio_api_key)) -> dict:
        return {"status": "ok", "actor": "authenticated"}

    test_app = FastAPI()
    test_app.get("/protected", dependencies=[Depends(require_cartorio_api_key)])(protected_endpoint)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ============================================================================
# Tests: 3 cenarios canonicos (Briefing E0.AUTH)
# ============================================================================


def test_require_api_key_ausente_retorna_401(client: TestClient) -> None:
    """Cenario 1: Header X-API-Key ausente -> 401 UNAUTHORIZED."""
    resp = client.get("/protected")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["erro"] == "UNAUTHORIZED"
    assert "X-API-Key" in body["detail"]["mensagem"]
    assert resp.headers.get("www-authenticate") == "ApiKey"


def test_require_api_key_errada_retorna_401(client: TestClient) -> None:
    """Cenario 2: Header X-API-Key com valor errado -> 401 UNAUTHORIZED."""
    wrong_key = "b" * 64  # 64 chars mas diferente
    resp = client.get("/protected", headers={"X-API-Key": wrong_key})
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["erro"] == "UNAUTHORIZED"


def test_require_api_key_correta_retorna_200(client: TestClient) -> None:
    """Cenario 3: Header X-API-Key correto -> 200 OK."""
    resp = client.get("/protected", headers={"X-API-Key": TEST_CARTORIO_API_KEY})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["actor"] == "authenticated"


# ============================================================================
# Tests: edge cases / regression
# ============================================================================


def test_require_api_key_aceita_lowercase(client: TestClient) -> None:
    """Header em lowercase (x-api-key) tambem funciona (HTTP case-insensitive)."""
    resp = client.get("/protected", headers={"x-api-key": TEST_CARTORIO_API_KEY})
    assert resp.status_code == 200


def test_require_api_key_empty_string_retorna_401(client: TestClient) -> None:
    """Header com string vazia -> 401 (NAO deve tratar como no-op)."""
    resp = client.get("/protected", headers={"X-API-Key": ""})
    assert resp.status_code == 401


def test_require_api_key_partial_match_retorna_401(client: TestClient) -> None:
    """Header com prefixo da chave (timing attack protection) -> 401.

    Garante que hmac.compare_digest nao aceita match parcial.
    """
    partial = TEST_CARTORIO_API_KEY[:32]
    resp = client.get("/protected", headers={"X-API-Key": partial})
    assert resp.status_code == 401


def test_settings_cartorio_api_key_validation_len_64() -> None:
    """Validacao strict: cartorio_api_key DEVE ter exatamente 64 chars.

    Defesa em profundidade: se alguem setar CARTORIO_API_KEY=<32 chars>
    (comprimento errado de hex), Settings() deve falhar no startup.
    """
    import os
    from pydantic import ValidationError

    os.environ["CARTORIO_API_KEY"] = "a" * 32  # WRONG: 32 chars

    try:
        get_settings.cache_clear()
        with pytest.raises(ValidationError) as exc_info:
            get_settings()
        # Pydantic v2: errors list com msg tipo "String should have at most 64 characters"
        assert any(
            "64" in str(e.get("msg", "")) or "at most" in str(e.get("msg", ""))
            for e in exc_info.value.errors()
        )
    finally:
        # Restore valid value pra outros tests
        os.environ["CARTORIO_API_KEY"] = TEST_CARTORIO_API_KEY
        get_settings.cache_clear()
