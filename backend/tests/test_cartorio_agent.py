"""Testes do Agent AI Cartorio (tools + intent + offline)."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.cartorio_agent import (
    SERVICOS_CATALOGO,
    _detect_intent,
    _match_servico,
    _offline_reply,
    _parse_action,
    _run_remote_tool,
    run_cartorio_agent,
)


def test_catalogo_publico_usa_valores_finais_tjmg_2026() -> None:
    """Itens simples só podem divulgar o valor final da fonte primária vigente."""
    assert SERVICOS_CATALOGO["reconhecimento_firma"][1] == "R$ 11,21"
    assert SERVICOS_CATALOGO["autenticacao"][1] == "R$ 11,21"
    assert SERVICOS_CATALOGO["procuracao"][1] == "R$ 68,94"
    assert SERVICOS_CATALOGO["testamento"][1] == "R$ 437,24"
    assert SERVICOS_CATALOGO["ata_notarial"][1] == "R$ 218,42"


def test_detect_intent_preco() -> None:
    assert _detect_intent("quanto custa autenticacao?") == "preco"


def test_detect_intent_agendar() -> None:
    assert _detect_intent("quero agendar uma procuracao") == "agendar"


def test_detect_intent_catalogo_serie() -> None:
    assert (
        _detect_intent("Me fale um pouco de cada em varias mensagens separadas 1 depois da outra")
        == "catalogo_serie"
    )


def test_detect_intent_memoria() -> None:
    assert _detect_intent("Uai perdeu a memoria da conversa agora?") == "memoria"


def test_offline_catalogo_serie_multi_msg() -> None:
    r = _offline_reply("cada um em mensagens separadas", "catalogo_serie", [])
    assert not r.extra_messages
    assert "Servicos oficiais" in r.text
    assert "Autenticação" in r.text
    assert r.provider == "offline:catalogo_serie"


def test_scrub_bad_llm_phrases() -> None:
    from app.services.cartorio_agent import _scrub_bad_llm_phrases

    assert _scrub_bad_llm_phrases("sou um modelo stateless") == ""
    assert "cartorio" in _scrub_bad_llm_phrases("O cartorio abre as 9h").lower()


def test_sanitize_blocks_porn_urls() -> None:
    from app.services.cartorio_agent import sanitize_bot_output

    dirty = "Veja mais em https://www.pornhub.com/video/123 e o cartorio"
    assert sanitize_bot_output(dirty) == ""
    clean = "Site oficial https://api.2notasudi.com.br/docs ok"
    assert "2notasudi" in sanitize_bot_output(clean)


def test_detect_intent_dados_cpf() -> None:
    assert _detect_intent("meu cpf e 123.456.789-09") == "dados"


@pytest.mark.asyncio
async def test_run_agent_never_returns_external_spam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _evil_llm(system: str, user: str) -> tuple[str, str]:
        return "Acesse https://xvideos.com/xxx agora", "evil"

    monkeypatch.setattr("app.services.cartorio_agent._llm_minimax", _evil_llm)
    # texto livre (intent livre) forca path LLM; scrub deve descartar e ir offline
    reply = await run_cartorio_agent(
        "Me explique com calma a diferenca pratica entre firma e autenticacao"
    )
    assert "xvideos" not in (reply.text or "").lower()
    assert "porn" not in (reply.text or "").lower()
    assert reply.text  # offline fallback util


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
    r = _offline_reply("oi", "saudacao", ["intent:saudacao"], history=None)
    assert r.keyboard is None
    assert "Ola" in r.text or "assistente" in r.text.lower()


def test_offline_nao_repete_welcome_em_loop() -> None:
    hist = [
        "user: Oi",
        "bot: Ola. Sou o assistente do cartorio...",
    ]
    r = _offline_reply("Tipo como?", "livre", ["intent:livre"], history=hist)
    assert "Pode falar em texto livre. Exemplos" not in r.text
    assert r.provider in ("offline:clarificacao", "offline:livre", "offline:curto")
    low = r.text.lower()
    assert "ajudo" in low or "preciso" in low or "servico" in low or "digite" in low


def test_offline_segunda_saudacao_curta() -> None:
    hist = ["user: Oi", "bot: Ola. Sou o assistente..."]
    r = _offline_reply("oi", "saudacao", [], history=hist)
    assert "posso" in r.text.lower() or "ajudar" in r.text.lower()
    assert len(r.text) < 120
    assert r.provider == "offline:saudacao"


def test_offline_smalltalk_e_tom() -> None:
    r = _offline_reply("Tudo bem?", "livre", [], history=["user: x", "bot: y"])
    assert r.provider == "offline:smalltalk"
    r2 = _offline_reply("Muito grosso", "livre", [], history=["user: x", "bot: y"])
    assert r2.provider == "offline:tom"
    assert "desculpa" in r2.text.lower()


@pytest.mark.asyncio
async def test_run_agent_offline_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fail_llm(system: str, user: str) -> tuple[str, str]:
        return "", "none"

    async def _fail_tools(
        *_args: object, **_kwargs: object
    ) -> tuple[str, str, str | None, list[str]]:
        return "", "none", None, []

    monkeypatch.setattr("app.services.cartorio_agent._llm_minimax", _fail_llm)
    monkeypatch.setattr("app.services.cartorio_agent._llm_agent_with_tools", _fail_tools)
    reply = await run_cartorio_agent("quanto custa autenticacao de documento?")
    assert reply.text
    assert (
        "11,21" in reply.text
        or "Autentic" in reply.text
        or "autentic" in reply.text.lower()
        or "emolumento" in reply.text.lower()
    )
    assert reply.provider in ("offline", "pietra_planner_fallback", "offline:provider_rate_limited")


@pytest.mark.asyncio
async def test_agendamento_tool_requires_human_confirmation() -> None:
    """HITL: dados do cliente nunca podem disparar um workflow pelo LLM."""
    result = await _run_remote_tool(
        "criar_agendamento_real",
        {
            "servico": "autenticacao",
            "data": "20/07/2026",
            "hora": "10:00",
            "nome": "Cliente 123.456.789-09",
        },
    )

    assert result is not None
    payload, action, used = result
    assert action == "humano"
    assert "draft_requires_human_confirmation" in payload
    assert "123.456.789-09" not in payload
    assert used == ["tool_remote:criar_agendamento_real"]


@pytest.mark.asyncio
async def test_llm_context_scrubs_history_and_attachment_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Histórico e metadados de mídia também cruzam a fronteira LLM sem PII."""
    captured: dict[str, str] = {}

    async def _mock_chat_comp(
        messages: list[dict[str, Any]], **kwargs: Any
    ) -> tuple[dict[str, Any] | None, str, str]:
        user_content = ""
        for m in messages:
            if m.get("role") == "user":
                user_content = m.get("content") or ""
        captured["user"] = user_content
        return {"content": "Seu CPF 123.456.789-09 foi recebido."}, "test", ""

    async def _llm(system: str, user: str) -> tuple[str, str]:
        captured["user"] = user
        return "Seu CPF 123.456.789-09 foi recebido.", "test"

    monkeypatch.setattr("app.services.cartorio_agent._chat_completion", _mock_chat_comp)
    monkeypatch.setattr("app.services.cartorio_agent._llm_minimax", _llm)
    reply = await run_cartorio_agent(
        "preciso de orientacao sobre autenticacao",
        history=["cliente informou CPF 123.456.789-09"],
        attachments=[
            {
                "type": "document",
                "file_name": "cpf-123.456.789-09.pdf",
                "local_path": "/private/tmp/cliente/123.456.789-09.pdf",
            }
        ],
    )

    assert "123.456.789-09" not in captured["user"]
    assert "/private/tmp" not in captured["user"]
    assert "123.456.789-09" not in reply.text
