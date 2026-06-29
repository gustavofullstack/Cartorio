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
os.environ["CARTORIO_API_KEY"] = TEST_CARTORIO_API_KEY

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


# ============================================================================
# Tests: P1.1 (LGPD review) — hex pattern strict
# ============================================================================


def test_settings_cartorio_api_key_validation_pattern_hex() -> None:
    """Validacao strict: cartorio_api_key DEVE ser hex lowercase 64 chars.

    Defesa em profundidade P1.1 (LGPD review 2026-06-25): uppercase, espacos,
    ou chars nao-hex DEVEM falhar Settings() no startup.
    """
    import os
    from pydantic import ValidationError

    # Uppercase hex NAO passa (regex so aceita [a-f0-9])
    os.environ["CARTORIO_API_KEY"] = "A" * 64

    try:
        get_settings.cache_clear()
        with pytest.raises(ValidationError) as exc_info:
            get_settings()
        assert any(
            "pattern" in str(e.get("msg", "")).lower()
            or "string should match pattern" in str(e.get("msg", "")).lower()
            for e in exc_info.value.errors()
        )
    finally:
        os.environ["CARTORIO_API_KEY"] = TEST_CARTORIO_API_KEY
        get_settings.cache_clear()


def test_settings_cartorio_api_key_pattern_aceita_hex_lowercase() -> None:
    """Pattern aceita hex lowercase real (com mix de a-f e 0-9)."""
    import os

    # Hex realista: 0-9 e a-f mixados
    real_hex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    os.environ["CARTORIO_API_KEY"] = real_hex

    try:
        get_settings.cache_clear()
        s = get_settings()
        assert s.cartorio_api_key == real_hex
    finally:
        os.environ["CARTORIO_API_KEY"] = TEST_CARTORIO_API_KEY
        get_settings.cache_clear()


# ============================================================================
# Tests: P0.2 (LGPD review) — AuditService.log() chamado em auth failure
# ============================================================================


def test_audit_service_log_chamado_em_401_missing(client: TestClient, monkeypatch) -> None:
    """Falha de auth (401 missing) DEVE gravar audit log (LGPD art. 37 + P0.2).

    Compliance theater fix: a docstring promete, mas a implementacao DEVE
    chamar AuditService.log(). Mock do AuditService.log verifica a chamada.
    """
    from unittest.mock import MagicMock, patch

    # Track chamadas via mock. O AuditService.log eh chamado dentro de uma
    # session_scope() separada, entao mockamos o metodo estatico.
    mock_log = MagicMock()

    with patch("app.api.deps.AuditService") as mock_service:
        mock_service.log = mock_log

        resp = client.get(
            "/protected",
            headers={"x-request-id": "test-req-001", "user-agent": "pytest-agent"},
        )

    assert resp.status_code == 401
    # AuditService.log foi chamado pelo menos 1x (fail de missing)
    assert mock_log.call_count >= 1
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs["actor_id"] == "anonymous"
    assert call_kwargs["actor_type"] == "unauthorized"
    assert call_kwargs["action"] == "auth.failed"
    assert call_kwargs["resource"] == "/protected"
    payload = call_kwargs["payload"]
    assert payload["endpoint"] == "/protected"
    assert payload["reason"] == "missing"
    assert payload["key_fingerprint"] == "missing"
    assert call_kwargs["request_id"] == "test-req-001"
    assert call_kwargs["user_agent"] == "pytest-agent"


def test_audit_service_log_chamado_em_401_invalid(client: TestClient, monkeypatch) -> None:
    """Falha de auth (401 invalid key) DEVE gravar audit log com key_fingerprint."""
    from unittest.mock import MagicMock, patch

    wrong_key = "b" * 64
    mock_log = MagicMock()

    with patch("app.api.deps.AuditService") as mock_service:
        mock_service.log = mock_log

        resp = client.get("/protected", headers={"X-API-Key": wrong_key})

    assert resp.status_code == 401
    assert mock_log.call_count >= 1
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs["actor_type"] == "unauthorized"
    payload = call_kwargs["payload"]
    assert payload["reason"] == "invalid"
    # fingerprint NAO eh a chave em si — eh hash[:8]
    assert payload["key_fingerprint"] != wrong_key
    assert len(payload["key_fingerprint"]) == 8  # sha256[:8]


def test_audit_service_log_chamado_em_503_config_missing() -> None:
    """Falha de config (503 CARTORIO_API_KEY None) DEVE gravar audit log.

    Safety net: mesmo quando settings desserializa com chave vazia/None
    (bug hipotetico), ainda logamos a falha. Aqui testamos o HELPER
    _audit_auth_failure diretamente, ja que a config.py validacao strict
    impede chegar ao 503 via HTTP em producao.
    """
    from unittest.mock import MagicMock, patch

    from fastapi import Request

    from app.api.deps import _audit_auth_failure

    mock_log = MagicMock()
    mock_req = MagicMock(spec=Request)
    mock_req.url.path = "/api/v1/integrations/opencode/test"
    mock_req.method = "POST"
    mock_req.client.host = "192.168.1.42"
    mock_req.headers = {
        "x-forwarded-for": "203.0.113.42",
        "user-agent": "test-agent/1.0",
        "x-request-id": "req-503-test",
    }

    with patch("app.api.deps.AuditService") as mock_service:
        mock_service.log = mock_log
        _audit_auth_failure(mock_req, reason="config_missing", provided="anything")

    assert mock_log.call_count >= 1
    call_kwargs = mock_log.call_args.kwargs
    assert call_kwargs["actor_id"] == "anonymous"
    assert call_kwargs["actor_type"] == "unauthorized"
    assert call_kwargs["action"] == "auth.failed"
    assert call_kwargs["resource"] == "/api/v1/integrations/opencode/test"
    payload = call_kwargs["payload"]
    assert payload["reason"] == "config_missing"
    assert payload["key_fingerprint"] != "anything"  # NAO loga valor da chave
    assert call_kwargs["ip"] == "203.0.113.42"  # XFF honored
    assert call_kwargs["user_agent"] == "test-agent/1.0"
    assert call_kwargs["request_id"] == "req-503-test"


def test_audit_service_log_NAO_chamado_em_200_sucesso(client: TestClient) -> None:
    """Sucesso (200 com key correta) NAO deve gravar audit de auth.failed.

    Audit de auth SUCESSO eh responsabilidade do handler (ex: n8n_workflow_25
    loga seu proprio audit ao executar). Nosso gate so loga FALHAS.
    """
    from unittest.mock import MagicMock, patch

    mock_log = MagicMock()
    with patch("app.api.deps.AuditService") as mock_service:
        mock_service.log = mock_log

        resp = client.get("/protected", headers={"X-API-Key": TEST_CARTORIO_API_KEY})

    assert resp.status_code == 200
    # NAO foi chamado audit de auth (sucesso nao gera log de falha)
    for call in mock_log.call_args_list:
        kwargs = call.kwargs
        if kwargs.get("action") == "auth.failed":
            pytest.fail(f"audit de auth.failed nao deve rodar em 200: {kwargs}")


def test_audit_log_failure_nao_mascara_401(client: TestClient) -> None:
    """Se o DB cair durante audit log, 401 ORIGINAL ainda retorna.

    Defesa em profundidade: o try/except dentro de _audit_auth_failure
    garante que erros de audit NAO vazem pro cliente como 500.
    """
    from unittest.mock import patch

    with patch("app.api.deps.AuditService.log") as mock_log:
        mock_log.side_effect = RuntimeError("DB offline")

        resp = client.get("/protected")

    # 401 ainda retorna (NAO vira 500 por causa de audit failure)
    assert resp.status_code == 401
    assert resp.json()["detail"]["erro"] == "UNAUTHORIZED"
