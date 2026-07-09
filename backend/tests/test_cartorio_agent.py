"""Testes do Agent AI Cartorio (tools + intent + offline)."""

from __future__ import annotations

import pytest

from app.services.cartorio_agent import (
    _detect_intent,
    _match_servico,
    _offline_reply,
    _parse_action,
    run_cartorio_agent,
)


def test_detect_intent_preco() -> None:
    assert _detect_intent("quanto custa autenticacao?") == "preco"


def test_detect_intent_agendar() -> None:
    assert _detect_intent("quero agendar uma procuracao") == "agendar"


def test_match_servico_firma() -> None:
    assert _match_servico("reconhecimento de firma") == "reconhecimento_firma"


def test_parse_action_strip() -> None:
    text, action = _parse_action("Claro, vamos agendar.\n[[ACTION:agendar]]")
    assert action == "agendar"
    assert "ACTION" not in text
    assert "agendar" in text.lower() or "Claro" in text


def test_offline_preco_lista() -> None:
    r = _offline_reply("quanto custa?", "preco", ["intent:preco"])
    assert "Autenticacao" in r.text or "autentic" in r.text.lower() or "Firma" in r.text
    # preco generico: lista em texto, sem forcar teclado de menu
    assert r.keyboard is None
    assert r.provider == "offline"


def test_offline_saudacao_sem_botoes() -> None:
    r = _offline_reply("oi", "saudacao", ["intent:saudacao"])
    assert r.keyboard is None
    assert "Agent AI" in r.text or "linguagem" in r.text.lower() or "Ola" in r.text


@pytest.mark.asyncio
async def test_run_agent_offline_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fail_llm(system: str, user: str) -> tuple[str, str]:
        return "", "none"

    monkeypatch.setattr("app.services.cartorio_agent._llm_minimax", _fail_llm)
    reply = await run_cartorio_agent("quanto custa autenticacao de documento?")
    assert reply.text
    assert "6,80" in reply.text or "Autentic" in reply.text or "autentic" in reply.text.lower()
    assert reply.provider == "offline"
