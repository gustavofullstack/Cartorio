# Modified by Gustavo Almeida
"""Matriz de testes de resiliência e degradação em caos (E3.09).

Cenários cobertos aqui (offline, sem infra real):
- Redis indisponível -> fail-open (health segue 200)
- Todos os providers LLM down -> resposta degradada, nunca silêncio, PII scrubbed
- Duplicate webhook storm -> idempotência rejeita replay
- Ato jurídico -> nasce em estado não-final (HITL), nunca concluído pelo bot

Asserções globais da matriz E3.09: sem crash, sem PII leak, sem silent failure,
sem ato jurídico automático.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import cartorio_agent
from app.services.pii import detect_only


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


def test_chaos_redis_unavailable_fail_open(test_client: TestClient) -> None:
    """Redis indisponível: rate limit fail-open mantém atendimento funcional."""
    with patch(
        "app.services.rate_limit_by_key.redis_async.from_url",
        side_effect=Exception("Redis connection refused"),
    ):
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


async def test_chaos_all_llm_providers_down_returns_degraded_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Todos os providers LLM falham: resposta degradada, nunca vazia, sem PII."""

    async def _empty_tools(
        system: str, user: str
    ) -> tuple[str, str, str | None, list[str]]:
        return "", "none", None, []

    async def _empty_fb(system: str, user: str) -> tuple[str, str]:
        return "", "none"

    monkeypatch.setattr(cartorio_agent, "_llm_agent_with_tools", _empty_tools)
    monkeypatch.setattr(cartorio_agent, "_llm_minimax", _empty_fb)

    reply = await cartorio_agent.run_cartorio_agent(
        "Meu CPF é 529.982.247-25, preciso de certidão"
    )
    assert reply is not None
    assert reply.text  # silent failure proibido
    assert "529.982.247-25" not in reply.text  # PII scrubbed
    assert detect_only(reply.text) == {}
    assert reply.provider.startswith("offline")


async def test_chaos_duplicate_webhook_storm_idempotent() -> None:
    """Disparo duplo com mesma chave de idempotência não gera ação duplicada."""
    from app.services.idempotency_store_fake import FakeIdempotencyStore

    store = FakeIdempotencyStore()
    key = "webhook-evt-9999"
    payload = {"status": "processed", "protocolo": "PROT-001"}

    assert await store.setnx(key, payload, ttl_seconds=60) is True
    assert await store.setnx(key, payload, ttl_seconds=60) is False  # replay
    assert await store.get(key) == payload


def test_chaos_legal_act_remains_non_final() -> None:
    """Atos jurídicos nascem em estado não-final: default de coluna nunca é
    'concluido'/'isento' — transição exige HITL, mesmo sob falha de integrador."""
    from app.models.protocolo import Protocolo

    status_col = Protocolo.__table__.c.status
    default = status_col.default.arg if status_col.default is not None else None
    estados_finais = {"concluido", "isento", "deferido", "emitido"}
    assert default not in estados_finais
    # E o estado inicial declarado é um estado de trabalho humano:
    assert default == "aberto"
