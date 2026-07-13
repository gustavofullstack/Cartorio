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


def test_detect_intent_catalogo_serie() -> None:
    assert (
        _detect_intent(
            "Me fale um pouco de cada em varias mensagens separadas 1 depois da outra"
        )
        == "catalogo_serie"
    )


def test_detect_intent_memoria() -> None:
    assert _detect_intent("Uai perdeu a memoria da conversa agora?") == "memoria"


def test_offline_catalogo_serie_multi_msg() -> None:
    r = _offline_reply("cada um em mensagens separadas", "catalogo_serie", [])
    assert not r.extra_messages
    assert "Servicos oficiais" in r.text
    assert "Autenticacao" in r.text
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

    monkeypatch.setattr("app.services.cartorio_agent._llm_minimax", _fail_llm)
    reply = await run_cartorio_agent("quanto custa autenticacao de documento?")
    assert reply.text
    assert "6,80" in reply.text or "Autentic" in reply.text or "autentic" in reply.text.lower()
    assert reply.provider == "offline"
