import pytest
from unittest.mock import AsyncMock
from app.services.cartorio_agent import sanitize_bot_output
from app.api.v1.telegram import format_bot_text


@pytest.mark.asyncio
async def test_telegram_formatting_robustness():
    # Test text with valid URLs
    text_with_url = "Aprenda a formatar: https://api.2notasudi.com.br/docs"
    formatted = format_bot_text(text_with_url)
    assert "https://api.2notasudi.com.br/docs" in formatted

    # Test sanitize function
    sanitized = sanitize_bot_output(formatted)
    assert "https://api.2notasudi.com.br/docs" in sanitized, "URL legitima não deveria ser removida"

    # Test toxic URL removal
    toxic_text = "Veja isso https://xvideos.com/video e mais"
    assert sanitize_bot_output(toxic_text) == ""


@pytest.mark.asyncio
async def test_telegram_html_markdown_links():
    from app.api.v1.telegram import telegram_html

    text = "Link: [Cartorio](https://api.2notasudi.com.br/docs) e **negrito**"
    html_out = telegram_html(text)
    assert '<a href="https://api.2notasudi.com.br/docs">Cartorio</a>' in html_out
    assert "<b>negrito</b>" in html_out


@pytest.mark.asyncio
async def test_1000_human_like_interactions(mocker):
    """
    Simula 1000 interacoes do bot sem chamar a rede externa.
    """
    mock_post = mocker.patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"ok": True}

    from app.api.v1.telegram import _send_message

    # Executa as iteracoes para validar que nenhuma delas quebra a formatacao HTML
    success_count = 0
    for i in range(1000):
        test_msg = f"User test {i} message with [link](https://api.2notasudi.com.br/docs) **bold**"
        res = await _send_message(chat_id=123456, text=test_msg)
        assert res is True

        # Verify the call payload
        call_args = mock_post.call_args
        assert call_args is not None
        payload = call_args.kwargs.get("json", {})
        html_text = payload.get("text", "")

        # Verify markdown was parsed to HTML
        assert "href=" in html_text
        assert "<b>" in html_text

        success_count += 1

    assert success_count == 1000
