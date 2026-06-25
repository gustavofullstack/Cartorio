"""LGPD-015 — LLM Output Scrub Boundary Tests (Blocker #10 + #13 + #14).

Fechando o GAP critico: toda chamada LLM tem 2 boundaries de PII scrubbing.
- B1 INPUT: text -> scrub() -> LLM request [implementado]
- B2 OUTPUT: LLM response -> ??? -> caller [GAP — este teste cobre]

Defesa em profundidade: o wrapper `opencode_go.chat()` DEVE scrubar o output
internamente. Caller NAO pode confiar que LLM eh discreto — modelos ecoam
trechos do contexto.

Suites:
- A: opencode_go wrapper output scrub (5 tests TP)
- B: router webhook (2 tests TP — echo do LLM nao vaza)
- C: integrations smoke endpoint (1 test TP)
- D: audit log action=llm.output_scrubbed + request_id + IP truncado /24
- E: FP tests (5 tests) — documenta o que NAO deve ser redacted
       (comportamento atual; correcoes virão em D3 CNS-anchored)

Limites documentados (NAO escopo desta entrega):
- CNH sem regex -> nao eh redacted (D3 backlog)
- CNS sem regex -> nao eh redacted (D3 backlog)
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test env BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


# ============================================================================
# Fixtures compartilhados
# ============================================================================


@pytest.fixture
def client():
    """Cria TestClient com DB in-memory (sqlite + StaticPool)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from contextlib import contextmanager
    from app.models.base import Base
    import app.models  # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.atendimento  # noqa: F401
    import app.models.cliente  # noqa: F401
    import app.models.conversa  # noqa: F401
    import app.models.documento  # noqa: F401
    import app.models.protocolo  # noqa: F401
    import app.models.webhook_event  # noqa: F401
    import app.db  # noqa: E402  (re-atribui `app` no escopo local para o package)
    import app.main as app_main_module  # noqa: E402
    # NAO usar `from app.main import app` aqui dentro — sobrescreve o package

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)

    original_engine = app.db.engine
    original_session_scope = app.db.session_scope
    app.db.engine = test_engine
    app_main_module.engine = test_engine
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    @contextmanager
    def test_session_scope():
        s = TestSessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.db.SessionLocal = TestSessionLocal
    app.db.session_scope = test_session_scope

    # `app` no escopo local foi re-atribuido para o package via `import app.db`.
    # Usar `app_main_module.app` (FastAPI instance) explicitamente.
    fastapi_app = app_main_module.app

    try:
        with TestClient(fastapi_app) as c:
            yield c
    finally:
        app.db.engine = original_engine
        app_main_module.engine = original_engine
        app.db.session_scope = original_session_scope
        Base.metadata.drop_all(test_engine)


def _make_evolution_payload(text: str, sender: str = "5534998765432") -> dict:
    """Payload formato legado webhook Evolution."""
    return {
        "message": {"text": text},
        "sender": sender,
        "instance": "cartorio-2notas",
    }


# ============================================================================
# Suite A — opencode_go output scrub (5 tests TP)
# ============================================================================


@pytest.mark.asyncio
async def test_opencode_go_scrubs_cpf_in_output():
    """LLM ecoa CPF no output. Assert que ChatResponse.content NAO contem CPF.

    Estado atual: RED — wrapper NAO scrubba output.
    """
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Seu CPF e 123.456.789-09"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Qual meu CPF?"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.test/v1",
            consent_granted=True,
        )

    # LGPD-015: output deve estar scrubbed
    assert "123.456.789-09" not in result.content, (
        f"REGRESSAO LGPD-015: CPF bruto ECOADO no output: {result.content[:200]}"
    )
    assert result.output_pii_redacted_count >= 1, (
        "LGPD-015: output_pii_redacted_count deve refletir redacoes no output"
    )


@pytest.mark.asyncio
async def test_opencode_go_scrubs_email_in_output():
    """LLM ecoa email no output. Assert redacted.

    Estado atual: RED.
    """
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Seu email e joao.silva@exemplo.com.br"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Qual meu email?"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.test/v1",
            consent_granted=True,
        )

    assert "joao.silva@exemplo.com.br" not in result.content
    assert result.output_pii_redacted_count >= 1


@pytest.mark.asyncio
async def test_opencode_go_scrubs_phone_in_output():
    """LLM ecoa telefone no output. Assert redacted.

    Estado atual: RED.
    """
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Liguei para (34) 99999-8888"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Qual meu telefone?"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.test/v1",
            consent_granted=True,
        )

    assert "99999-8888" not in result.content
    assert result.output_pii_redacted_count >= 1


@pytest.mark.asyncio
async def test_opencode_go_scrubs_cnpj_in_output():
    """LLM ecoa CNPJ no output. Assert redacted.

    Estado atual: RED.
    """
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "CNPJ: 12.345.678/0001-90"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Qual o CNPJ?"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.test/v1",
            consent_granted=True,
        )

    assert "12.345.678/0001-90" not in result.content
    assert result.output_pii_redacted_count >= 1


@pytest.mark.asyncio
async def test_opencode_go_output_clean_when_no_echo():
    """LLM NAO ecoa PII -> output_pii_redacted_count == 0.

    Estado atual: GREEN (sanity baseline). Comportamento esperado continua.
    """
    from app.integrations.opencode_go import chat

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Bom dia, em que posso ajudar?"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_cls.return_value = mock_client

        result = await chat(
            messages=[{"role": "user", "content": "Ola"}],
            model="deepseek-v4-flash",
            api_key="sk-test",
            base_url="https://api.test/v1",
            consent_granted=True,
        )

    assert result.content == "Bom dia, em que posso ajudar?"
    assert result.output_pii_redacted_count == 0


# ============================================================================
# Suite B — router webhook (2 tests TP — echo do LLM nao vaza no response)
# ============================================================================


def test_webhook_evolution_response_scrubs_cpf_echo(client):
    """LLM ecoa CPF no output. Response do webhook NAO contem CPF.

    Estado atual: RED — webhook repassa llm_resp.content direto.
    """
    with (
        patch("app.config.settings.opencode_go_api_key", "sk-test"),
        patch("app.config.settings.opencode_go_base_url", "https://api.test/v1"),
    ):
        # Mock LLM que ecoa CPF no output
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Seu CPF e 123.456.789-09"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            payload = _make_evolution_payload("Ola, bom dia")
            resp = client.post("/api/v1/webhook/evolution", json=payload)

    assert resp.status_code == 200
    body_str = str(resp.json())
    assert "123.456.789-09" not in body_str, (
        f"LGPD-015: CPF ECOADO PELO LLM VAZOU NO RESPONSE: {body_str[:500]}"
    )


def test_webhook_evolution_response_scrubs_email_echo(client):
    """LLM ecoa email no output. Response do webhook NAO contem email.

    Estado atual: RED.
    """
    with (
        patch("app.config.settings.opencode_go_api_key", "sk-test"),
        patch("app.config.settings.opencode_go_base_url", "https://api.test/v1"),
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Email: maria@test.com"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            payload = _make_evolution_payload("Ola, bom dia")
            resp = client.post("/api/v1/webhook/evolution", json=payload)

    assert resp.status_code == 200
    body_str = str(resp.json())
    assert "maria@test.com" not in body_str


# ============================================================================
# Suite C — integrations smoke endpoint (1 test TP)
# ============================================================================


def test_opencode_test_endpoint_scrubs_output(client):
    """Smoke test endpoint NAO devolve PII ecoado pelo LLM.

    Estado atual: RED — integrations.py:191 retorna resp.content direto.
    """
    with (
        patch("app.config.settings.opencode_go_api_key", "sk-test"),
        patch("app.config.settings.opencode_go_base_url", "https://api.test/v1"),
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Seu CPF e 123.456.789-09"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/v1/integrations/opencode/test",
                headers={"X-API-Key": "a" * 64},
                json={"message": "meu CNS", "consent_granted": True},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert "123.456.789-09" not in str(data), (
        f"LGPD-015: CPF ECOADO no smoke test: {data}"
    )
    # output_pii_redacted_count deve aparecer no response do endpoint
    assert "output_pii_redacted_count" in data
    assert data["output_pii_redacted_count"] >= 1


# ============================================================================
# Suite D — audit log + request_id + IP truncado /24
# ============================================================================


@pytest.mark.asyncio
async def test_output_scrub_creates_audit_log_with_request_id_and_ip_truncation():
    """output_pii_redacted_count > 0 DEVE gerar audit log action=llm.output_scrubbed
    com request_id e IP truncado em /24 (LGPD art. 37 + D5).

    Estado atual: RED — nao existe audit log para output scrub.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.models.base import Base
    import app.models  # noqa: F401
    from app.integrations.opencode_go import chat
    from app.models.audit_log import AuditLog

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    db = TestSessionLocal()

    try:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Seu CPF e 123.456.789-09"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

        with patch("app.integrations.opencode_go.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_cls.return_value = mock_client

            await chat(
                messages=[{"role": "user", "content": "Qual meu CPF?"}],
                model="deepseek-v4-flash",
                api_key="sk-test",
                base_url="https://api.test/v1",
                consent_granted=True,
                actor_id="cliente:42",
                db=db,
                request_id="req-test-001",
                client_ip="192.168.1.123",  # /24 esperado: 192.168.1.0/24
            )

        # Verifica audit log: 2 entradas (opencode_go.chat + llm.output_scrubbed)
        entries = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        actions = [e.action for e in entries]
        assert "llm.output_scrubbed" in actions, (
            f"LGPD-015: audit log llm.output_scrubbed ausente. Acoes: {actions}"
        )

        # Encontra a entrada de output_scrubbed
        scrub_entry = next(e for e in entries if e.action == "llm.output_scrubbed")
        # LGPD art. 37: request_id no audit
        assert scrub_entry.request_id == "req-test-001", (
            f"LGPD-015: request_id ausente/errado no audit: {scrub_entry.request_id}"
        )
        # D5 (T9-CRIT-1): IP FULL preservado em .ip (DPO forensics),
        # IP truncado em .ip_truncated (output default).
        assert scrub_entry.ip == "192.168.1.123", (
            f"T9-CRIT-1: IP FULL nao preservado: {scrub_entry.ip}"
        )
        assert scrub_entry.ip_truncated == "192.168.1.0/24", (
            f"D5: IP truncado ausente/errado: {scrub_entry.ip_truncated}"
        )
        # Payload deve ter count + length (NAO o conteudo bruto)
        assert scrub_entry.payload["redacted_count"] >= 1
        assert "output_length" in scrub_entry.payload
        assert scrub_entry.payload["model"] == "deepseek-v4-flash"
    finally:
        db.close()
        Base.metadata.drop_all(test_engine)


# ============================================================================
# Suite E — FP tests (5 tests) — documentam o comportamento ATUAL do scrubber
# ============================================================================


def test_scrub_cep_puro_is_redacted():
    """CEP puro (ex: '38400-000') EH redacted (TP). Documentado para D3."""
    from app.services.pii import scrub

    text = "Vou enviar para o CEP 38400-000"
    result = scrub(text)
    # CEP puro deve ser redacted (FP behavior documentado)
    assert "38400-000" not in result.text
    assert result.findings.get("cep", 0) >= 1


def test_scrub_isbn_is_not_redacted():
    """ISBN de livro NAO deve ser redacted (FP test — NAO eh PII).

    Estado atual: GREEN esperado (ISBN nao casa com nenhum pattern).
    """
    from app.services.pii import scrub

    # ISBN-13 formato: 978-85-1234-567-8
    text = "O livro de referencia ISBN 978-85-1234-567-8 esta esgotado"
    result = scrub(text)
    # ISBN nao eh PII, deve passar intacto
    assert "978-85-1234-567-8" in result.text, (
        f"FP: ISBN foi incorretamente redacted. Findings: {result.findings}"
    )


def test_scrub_oab_inscricao_is_not_redacted():
    """Numero de inscricao OAB NAO deve ser redacted como RG (FP test).

    Estado atual: GREEN esperado. Formato OAB 'OAB/SP 123.456' NAO casa com RG
    (que exige pelo menos 7-9 digitos + verificador com X/digito).
    """
    from app.services.pii import scrub

    text = "Dra. Maria inscrita na OAB/SP 123.456"
    result = scrub(text)
    # Inscricao OAB nao eh PII
    assert "OAB/SP 123.456" in result.text, (
        f"FP: OAB foi incorretamente redacted. Findings: {result.findings}"
    )


def test_scrub_processo_cnj_is_not_redacted():
    """Numero de processo CNJ NAO deve ser redacted (FP test).

    Estado atual: GREEN esperado. Formato CNJ '0000000-00.0000.0.00.0000'
    eh identificador publico de processo (sigiloso em casos especificos, mas
    o padrao NAO eh PII generico).
    """
    from app.services.pii import scrub

    text = "Processo numero 5001234-56.2024.8.13.0024 em andamento"
    result = scrub(text)
    # CNJ nao eh PII generico
    assert "5001234-56.2024.8.13.0024" in result.text, (
        f"FP: CNJ foi incorretamente redacted. Findings: {result.findings}"
    )


def test_scrub_conta_bancaria_is_not_redacted():
    """Conta bancaria com digitos NAO deve ser redacted (FP test).

    Estado atual: GREEN esperado. Formato 'ag 1234 cc 56789-0' NAO casa
    com CPF (que exige formato 3-3-3-2) nem com cartao.
    """
    from app.services.pii import scrub

    text = "Depositar na ag 1234 cc 56789-0"
    result = scrub(text)
    # Conta bancaria NAO eh PII generico (sem cpf/cnpj do titular)
    assert "ag 1234 cc 56789-0" in result.text, (
        f"FP: conta bancaria foi incorretamente redacted. Findings: {result.findings}"
    )
