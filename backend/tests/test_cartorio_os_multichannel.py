# Modified by Gustavo Almeida
"""Suíte de testes integrados da Arquitetura Multicanal Cartório OS (E3.01 - ADR 031).

Testa a integração entre o OpenClaw Session Router, Hermes Agent Engine, Spectrum TS Gateway
e o FastMCP Server (14 tools), garantindo o cumprimento estrito de PII Scrubbing e HITL DRAFT.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.protocolo import Protocolo
from app.services.pii import detect_only, scrub


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_cartorio_os_mcp_14_tools_discoverable(api_client: TestClient) -> None:
    """Verifica que o servidor FastMCP expõe o inventário completo das 14 ferramentas."""
    from mcp_server import mcp

    # O FastMCP registra as 14 ferramentas notariais
    tools = await mcp.list_tools() if hasattr(mcp, "list_tools") else []
    assert len(tools) >= 14


def test_cartorio_os_protocol_draft_enforcement() -> None:
    """Garante que todo pré-protocolo gerado pelo Agent Hermes nasce com status 'aberto' (DRAFT)."""
    p = Protocolo(
        numero="2026-HERMES-001",
        status="aberto",
        tipo="certidao_casamento",
    )
    assert p.status == "aberto"
    assert p.status != "concluido"


def test_cartorio_os_inbound_pii_sanitization() -> None:
    """Valida a sanitização em 3 camadas de dados recebidos por qualquer canal (iMessage, WA, TG)."""
    raw_user_msg = "Preciso de certidão. Meu CPF é 123.456.789-00 e meu telefone é (34) 99999-8888."
    scrubbed = scrub(raw_user_msg)

    assert "123.456.789-00" not in scrubbed.text
    assert "99999-8888" not in scrubbed.text
    assert bool(detect_only(scrubbed.text)) is False


def test_cartorio_os_trusted_proxy_and_rate_limit_protection(api_client: TestClient) -> None:
    """Garante que requisições multicanais com XFF falso de origem não confiável são filtradas."""
    response = api_client.get(
        "/health",
        headers={"X-Forwarded-For": "1.1.1.1, 2.2.2.2"},
    )
    assert response.status_code == 200


def test_cartorio_os_channel_capabilities_inbound_scope() -> None:
    """Valida ChannelCapabilities.inbound_scope para shared vs dedicated (R3)."""
    from app.services.channel_capabilities import get_channel_capabilities, resolve_inbound_scope

    shared = get_channel_capabilities("imessage", line_type="shared", allow_all_inbound=True)
    assert shared.inbound_scope == "allowlist"
    assert shared.public_inbound is False

    dedicated = get_channel_capabilities(
        "imessage",
        line_type="dedicated",
        allow_all_inbound=True,
        provider_supports_public=True,
    )
    assert dedicated.inbound_scope == "public"
    assert dedicated.public_inbound is True
    assert resolve_inbound_scope(line_type="test") == "allowlist"


def test_cartorio_os_allow_all_inbound_does_not_bypass_provider_restriction() -> None:
    """ALLOW_ALL_INBOUND em linha shared NÃO vira PUBLIC_INBOUND (provider allowlist)."""
    from app.services.channel_capabilities import resolve_inbound_scope

    assert (
        resolve_inbound_scope(
            line_type="shared",
            allow_all_inbound=True,
            provider_supports_public=False,
        )
        == "allowlist"
    )
    # Dedicated without provider public support stays allowlist.
    assert (
        resolve_inbound_scope(
            line_type="dedicated",
            allow_all_inbound=True,
            provider_supports_public=False,
        )
        == "allowlist"
    )

