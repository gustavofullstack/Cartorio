"""Testes para app/api/v1/telegram.py - _send_message + _send_poll/photo/document (cobertura).

Cobre:
1. _send_message sucesso 200
2. _send_message HTTP 400 retorna False
3. _send_message exception retorna False
4. _send_message com keyboard (json inline_keyboard)
5. _send_message com reply_markup (dict ja serializado)
6. _send_message trunca texto >MAX_RESPONSE_LEN
7. _send_message strip_emojis do texto
8. _send_poll sucesso
9. _send_poll erro
10. _send_photo sucesso
11. _send_photo erro
12. _send_document sucesso
13. _send_document erro
14. _menu_keyboard / _servicos_keyboard / _confirmar_keyboard retornam listas

Sobe cobertura telegram.py 59% -> >=75%.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.telegram import (
    LGPD_NOTICE,
    _confirmar_keyboard,
    _menu_keyboard,
    _send_document,
    _send_message,
    _send_photo,
    _send_poll,
    _servicos_keyboard,
    telegram_html,
)


def _make_resp(status_code: int = 200, text: str = "") -> MagicMock:
    """Cria mock de httpx Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


# =============================================================================
# _send_message
# =============================================================================


@pytest.mark.asyncio
async def test_send_message_sucesso_200() -> None:
    """_send_message retorna True quando API responde 200."""
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=_make_resp(200))
    mock_pool = MagicMock()
    mock_pool.post = AsyncMock(return_value=_make_resp(200))

    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        result = await _send_message(123, "Ola")

    assert result is True


@pytest.mark.asyncio
async def test_send_message_preserva_contato_dpo_oficial_no_payload() -> None:
    """O scrub final nao pode ocultar o canal publico de direitos LGPD."""
    captured: dict[str, object] = {}
    mock_pool = MagicMock()

    async def _post_capture(url: str, json: dict[str, object]) -> MagicMock:
        captured.update(json)
        return _make_resp(200)

    mock_pool.post = _post_capture
    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        result = await _send_message(
            123,
            f"{LGPD_NOTICE}\n\nDPO: dpo@2notasudi.com.br\n"
            "CPF 123.456.789-09 email pessoa@example.com",
        )

    assert result is True
    payload_text = str(captured["text"])
    assert "dpo@2notasudi.com.br" in payload_text
    assert "123.456.789-09" not in payload_text
    assert "pessoa@example.com" not in payload_text
    assert "[CPF_REDACTED]" in payload_text
    assert "[EMAIL_REDACTED]" in payload_text


@pytest.mark.asyncio
async def test_send_message_nao_allowlista_email_que_so_contem_dpo_oficial() -> None:
    """Somente o endereco exato do DPO pode atravessar o scrub de saida."""
    captured: dict[str, object] = {}
    mock_pool = MagicMock()

    async def _post_capture(url: str, json: dict[str, object]) -> MagicMock:
        captured.update(json)
        return _make_resp(200)

    mock_pool.post = _post_capture
    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        result = await _send_message(
            123,
            "Oficial dpo@2notasudi.com.br; "
            "falso fakedpo@2notasudi.com.br; "
            "hostil dpo@2notasudi.com.br.evil.com",
        )

    assert result is True
    payload_text = str(captured["text"])
    assert "dpo@2notasudi.com.br" in payload_text
    assert "fakedpo@2notasudi.com.br" not in payload_text
    assert "dpo@2notasudi.com.br.evil.com" not in payload_text


@pytest.mark.asyncio
async def test_send_message_migrate_supergroup_retry_ok() -> None:
    """FIX 2026-07-09: 400 migrate_to_chat_id deve reenviar e retornar True."""
    from unittest.mock import AsyncMock, MagicMock, patch

    fail = MagicMock()
    fail.status_code = 400
    fail.text = "migrated"
    fail.json.return_value = {
        "ok": False,
        "error_code": 400,
        "description": "Bad Request: group chat was upgraded to a supergroup chat",
        "parameters": {"migrate_to_chat_id": -1004331849032},
    }
    ok = MagicMock()
    ok.status_code = 200
    ok.text = "ok"

    client = MagicMock()
    client.post = AsyncMock(side_effect=[fail, ok])

    with patch("app.api.v1.telegram._get_tg_pool", return_value=client):
        result = await _send_message(-5319980720, "menu")
    assert result is True
    assert client.post.await_count == 2
    # post(url, json=payload)
    second_call = client.post.await_args_list[1]
    payload = second_call.kwargs.get("json") if second_call.kwargs else second_call[1].get("json")
    if payload is None:
        # positional: post(url, json=payload) via kwargs only in our code
        payload = second_call.kwargs["json"]
    assert payload["chat_id"] == -1004331849032


async def test_send_message_http_400_retorna_False() -> None:
    """_send_message retorna False quando API responde 400."""
    mock_pool = MagicMock()
    mock_pool.post = AsyncMock(return_value=_make_resp(400, "Bad Request"))

    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        result = await _send_message(123, "test")

    assert result is False


@pytest.mark.asyncio
async def test_send_message_exception_retorna_False() -> None:
    """_send_message captura exception e retorna False."""
    mock_pool = MagicMock()
    mock_pool.post = AsyncMock(side_effect=Exception("network down"))

    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        result = await _send_message(123, "test")

    assert result is False


@pytest.mark.asyncio
async def test_send_message_com_keyboard_inline() -> None:
    """_send_message com keyboard ignora botões inline no payload (diretiva 2026-07-12)."""
    mock_pool = MagicMock()
    captured: dict = {}
    resp = _make_resp(200)

    async def _post_capture(url: str, json: dict) -> MagicMock:
        captured["json"] = json
        return resp

    mock_pool.post = _post_capture

    keyboard = [[{"text": "Botao 1", "callback_data": "x"}]]
    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        await _send_message(123, "test", keyboard=keyboard)

    # reply_markup nao deve ser adicionado ao payload
    assert "reply_markup" not in captured["json"]


@pytest.mark.asyncio
async def test_send_message_com_reply_markup_dict() -> None:
    """_send_message com reply_markup dict ignora no payload (diretiva 2026-07-12)."""
    mock_pool = MagicMock()
    captured: dict = {}

    async def _post_capture(url: str, json: dict) -> MagicMock:
        captured["json"] = json
        return _make_resp(200)

    mock_pool.post = _post_capture

    reply_markup = {"keyboard": [[{"text": "x"}]], "one_time_keyboard": True}
    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        await _send_message(123, "test", reply_markup=reply_markup)

    # reply_markup nao deve ser adicionado ao payload
    assert "reply_markup" not in captured["json"]


@pytest.mark.asyncio
async def test_send_message_trunca_texto_muito_longo() -> None:
    """_send_message trunca texto >MAX_RESPONSE_LEN (4096 chars Telegram)."""
    mock_pool = MagicMock()
    captured: dict = {}

    async def _post_capture(url: str, json: dict) -> MagicMock:
        captured["json"] = json
        return _make_resp(200)

    mock_pool.post = _post_capture

    long_text = "A" * 5000  # > MAX_RESPONSE_LEN
    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        await _send_message(123, long_text)

    # Texto truncado para <= MAX_RESPONSE_LEN
    assert len(captured["json"]["text"]) <= 4096


@pytest.mark.asyncio
async def test_send_message_strip_emojis() -> None:
    """_send_message faz strip_emojis do texto antes de enviar."""
    mock_pool = MagicMock()
    captured: dict = {}

    async def _post_capture(url: str, json: dict) -> MagicMock:
        captured["json"] = json
        return _make_resp(200)

    mock_pool.post = _post_capture

    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        await _send_message(123, "Ola \U0001f44d cliente")

    # Texto nao contem thumbs-up emoji
    assert "\U0001f44d" not in captured["json"]["text"]


def test_telegram_html_escapes_untrusted_tags_and_formats_markdown() -> None:
    """Only the formatter's own documented Telegram HTML may reach the API."""
    rendered = telegram_html("<think>hidden</think> **valor** e *prazo* `R$ 8,50`")

    assert "&lt;think&gt;hidden&lt;/think&gt;" in rendered
    assert "<b>valor</b>" in rendered
    assert "<i>prazo</i>" in rendered
    assert "<code>R$ 8,50</code>" in rendered


# =============================================================================
# E2.04 — truncamento HTML-safe (Telegram 400 "can't parse entities")
# =============================================================================


def test_truncate_html_safe_no_truncation_when_short() -> None:
    """Texto curto passa intacto."""
    from app.api.v1.telegram import _truncate_html_safe

    assert _truncate_html_safe("<b>oi</b>", 100) == "<b>oi</b>"


def test_truncate_html_safe_never_cuts_inside_tag() -> None:
    """Corte nunca pode cair no meio de '<...>' (tag malformada = 400)."""
    from app.api.v1.telegram import MAX_RESPONSE_LEN, _truncate_html_safe

    rendered = telegram_html("**" + "x" * 6000 + "**")
    truncated = _truncate_html_safe(rendered, MAX_RESPONSE_LEN)

    # Nenhum '<' sem '>' correspondente no final (tag cortada)
    assert truncated.rfind("<") <= truncated.rfind(">")
    # Toda tag aberta foi fechada
    for tag in ("b", "i", "u", "code", "a"):
        opens = truncated.count(f"<{tag}>")
        closes = truncated.count(f"</{tag}>")
        assert opens == closes, f"tag <{tag}> desbalanceada apos truncamento"


def test_truncate_html_safe_closes_open_tags() -> None:
    """Tag aberta pelo corte recebe fechamento explicito."""
    from app.api.v1.telegram import _truncate_html_safe

    rendered = telegram_html("**valor** " + "y" * 100)
    # corta no meio do conteudo do <b>
    truncated = _truncate_html_safe(rendered, 6)
    assert truncated.startswith("<b>")
    assert truncated.endswith("</b>")
    assert truncated.count("<b>") == truncated.count("</b>")


def test_truncate_html_safe_balances_link_tag() -> None:
    """<a href=...> aberta pelo corte tambem e fechada."""
    from app.api.v1.telegram import _truncate_html_safe

    rendered = telegram_html("[site](https://2notasudi.com.br) " + "z" * 500)
    truncated = _truncate_html_safe(rendered, 40)
    opens = truncated.count("<a ")
    closes = truncated.count("</a>")
    assert opens == closes


@pytest.mark.asyncio
async def test_send_message_truncacao_html_valida_end_to_end() -> None:
    """E2.04 regression: payload enviado ao Telegram nunca tem HTML malformado.

    Falha se a implementacao voltar a truncar com fatia crua [:MAX].
    """
    import re as _re

    from app.api.v1.telegram import MAX_RESPONSE_LEN

    mock_pool = MagicMock()
    captured: dict = {}

    async def _post_capture(url: str, json: dict) -> MagicMock:
        captured["json"] = json
        return _make_resp(200)

    mock_pool.post = _post_capture

    long_bold = "**Resposta longa do agente " + "palavra " * 600 + "**"
    with patch("app.api.v1.telegram._get_tg_pool", return_value=mock_pool):
        result = await _send_message(123, long_bold)

    assert result is True
    sent = captured["json"]["text"]
    # respeita o teto do Telegram (4096) mesmo apos fechar tags
    assert len(sent) <= 4096
    # nenhum tag fragmentado: todo '<' tem '>' depois
    for m in _re.finditer(r"<", sent):
        assert ">" in sent[m.start() :], f"tag fragmentada em ...{sent[m.start() : m.start() + 20]}"
    # tags balanceadas
    for tag in ("b", "i", "u", "code", "a"):
        opens = len(_re.findall(rf"<{tag}(?:\s[^>]*)?>", sent))
        closes = sent.count(f"</{tag}>")
        assert opens == closes, f"<{tag}> desbalanceada no payload"
    # tamanho efetivo respeita o budget (pode passar MAX por fecha-tags)
    assert len(sent) <= MAX_RESPONSE_LEN + 20


# =============================================================================
# _send_poll
# =============================================================================


class _AsyncCtxMgr:
    """Fake httpx.AsyncClient como context manager."""

    def __init__(self, post_return: object = None, post_side_effect: object = None) -> None:
        self._post = AsyncMock(
            return_value=post_return,
            side_effect=post_side_effect,
        )

    async def __aenter__(self) -> "_AsyncCtxMgr":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def post(self, *args: object, **kwargs: object) -> object:
        return await self._post(*args, **kwargs)


@pytest.mark.asyncio
async def test_send_poll_sucesso() -> None:
    """_send_poll retorna True quando API responde 200."""
    client = _AsyncCtxMgr(post_return=_make_resp(200))

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=client):
        result = await _send_poll(123, "Qual servico?", ["A", "B", "C"])

    assert result is True


@pytest.mark.asyncio
async def test_send_poll_erro_retorna_False() -> None:
    """_send_poll retorna False em caso de erro."""
    client = _AsyncCtxMgr(post_side_effect=Exception("fail"))

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=client):
        result = await _send_poll(123, "Pergunta?", ["A", "B"])

    assert result is False


# =============================================================================
# _send_photo
# =============================================================================


@pytest.mark.asyncio
async def test_send_photo_sucesso_sem_caption() -> None:
    """_send_photo retorna True sem caption."""
    client = _AsyncCtxMgr(post_return=_make_resp(200))

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=client):
        result = await _send_photo(123, "https://example.com/photo.jpg")

    assert result is True


@pytest.mark.asyncio
async def test_send_photo_sucesso_com_caption() -> None:
    """_send_photo retorna True com caption."""
    client = _AsyncCtxMgr(post_return=_make_resp(200))

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=client):
        result = await _send_photo(123, "https://example.com/photo.jpg", caption="Olha essa foto")

    assert result is True


@pytest.mark.asyncio
async def test_send_photo_erro_retorna_False() -> None:
    """_send_photo retorna False em caso de erro."""
    client = _AsyncCtxMgr(post_side_effect=Exception("network"))

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=client):
        result = await _send_photo(123, "https://example.com/photo.jpg")

    assert result is False


# =============================================================================
# _send_document
# =============================================================================


@pytest.mark.asyncio
async def test_send_document_sucesso() -> None:
    """_send_document retorna True com sucesso."""
    client = _AsyncCtxMgr(post_return=_make_resp(200))

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=client):
        result = await _send_document(123, "https://example.com/doc.pdf", "doc.pdf")

    assert result is True


@pytest.mark.asyncio
async def test_send_document_erro_retorna_False() -> None:
    """_send_document retorna False em caso de erro."""
    client = _AsyncCtxMgr(post_side_effect=Exception("timeout"))

    with patch("app.api.v1.telegram.httpx.AsyncClient", return_value=client):
        result = await _send_document(123, "https://example.com/doc.pdf", "doc.pdf")

    assert result is False


# =============================================================================
# Keyboards helpers
# =============================================================================


def test_menu_keyboard_retorna_lista_de_listas() -> None:
    """_menu_keyboard retorna lista de listas de dicts."""
    kb = _menu_keyboard()
    assert isinstance(kb, list)
    assert all(isinstance(row, list) for row in kb)
    assert all(isinstance(btn, dict) for row in kb for btn in row)


def test_servicos_keyboard_retorna_lista_de_listas() -> None:
    """_servicos_keyboard retorna lista de listas de dicts."""
    kb = _servicos_keyboard()
    assert isinstance(kb, list)
    assert all(isinstance(row, list) for row in kb)


def test_confirmar_keyboard_retorna_lista_de_listas() -> None:
    """_confirmar_keyboard retorna lista de listas de dicts."""
    kb = _confirmar_keyboard()
    assert isinstance(kb, list)
    assert all(isinstance(row, list) for row in kb)
    # Deve ter botoes Confirmar/Cancelar
    flat = [btn for row in kb for btn in row]
    has_yes = any(
        "confirmar" in (btn.get("text", "") or "").lower()
        or "agendar" in (btn.get("callback_data", "") or "").lower()
        for btn in flat
    )
    has_no = any(
        "cancelar" in (btn.get("text", "") or "").lower()
        or "menu" in (btn.get("callback_data", "") or "").lower()
        for btn in flat
    )
    assert has_yes
    assert has_no
