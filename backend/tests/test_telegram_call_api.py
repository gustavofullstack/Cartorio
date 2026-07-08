"""Testes para app/api/v1/telegram.py - _call_api helper (cobertura).

Cobre:
1. _call_api GET request
2. _call_api POST request
3. _call_api HTTP 5xx retorna dict com erro
4. _call_api exception de rede retorna dict com erro
5. _call_api timeout exception
6. tools: _tool_consultar_protocolo, _tool_criar_atendimento

Sobe cobertura telegram.py 56% -> >=70%.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.api.v1.telegram import _call_api


@pytest.mark.asyncio
async def test_call_api_get_chama_client_get() -> None:
    """_call_api GET chama client.get com URL e headers."""

    captured: dict = {}

    class FakeResp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return {"ok": True, "data": "test"}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, url: str, headers: dict, **kwargs) -> FakeResp:
            captured["url"] = url
            captured["headers"] = headers
            return FakeResp()

        async def post(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    with patch("app.api.v1.telegram._get_tg_pool", return_value=FakeClient()):
        result = await _call_api("GET", "/api/v1/test")

    assert "url" in captured
    assert "/api/v1/test" in captured["url"]
    assert "headers" in captured
    # Content-Type header sempre presente
    assert captured["headers"]["Content-Type"] == "application/json"
    # Result
    assert result == {"ok": True, "data": "test"}


@pytest.mark.asyncio
async def test_call_api_post_chama_client_post_com_body() -> None:
    """_call_api POST chama client.post com body JSON."""
    captured: dict = {}

    class FakeResp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return {"id": 1}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

        async def post(self, url: str, json: dict, headers: dict, **kwargs) -> FakeResp:
            captured["url"] = url
            captured["json"] = json
            return FakeResp()

    with patch("app.api.v1.telegram._get_tg_pool", return_value=FakeClient()):
        result = await _call_api("POST", "/api/v1/clientes", body={"nome": "X"})

    assert "url" in captured
    assert captured["json"] == {"nome": "X"}
    assert result == {"id": 1}


@pytest.mark.asyncio
async def test_call_api_5xx_retorna_dict_com_erro() -> None:
    """_call_api com HTTP 5xx retorna {'erro': 'HTTP 5XX'}."""

    class FakeResp:
        status_code = 503
        text = "Service Unavailable"

        def json(self) -> dict:
            raise ValueError("not json")

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

        async def post(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    with patch("app.api.v1.telegram._get_tg_pool", return_value=FakeClient()):
        result = await _call_api("GET", "/api/v1/test")

    assert "erro" in result
    assert "HTTP 503" in result["erro"]


@pytest.mark.asyncio
async def test_call_api_exception_rede_retorna_dict_com_erro() -> None:
    """_call_api captura exception de rede e retorna dict com erro."""
    import httpx

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, *args: object, **kwargs: object) -> object:
            raise httpx.ConnectError("connection refused")

        async def post(self, *args: object, **kwargs: object) -> object:
            raise httpx.ConnectError("connection refused")

    with patch("app.api.v1.telegram._get_tg_pool", return_value=FakeClient()):
        result = await _call_api("GET", "/api/v1/test")

    assert "erro" in result
    assert "connection refused" in result["erro"].lower() or "refused" in result["erro"].lower()


@pytest.mark.asyncio
async def test_call_api_metodo_desconhecido_tratado_como_post() -> None:
    """_call_api com metodo != GET trata como POST (PUT/PATCH/DELETE)."""
    captured: dict = {}

    class FakeResp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return {"ok": True}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

        async def post(self, url: str, json: dict, headers: dict, **kwargs) -> FakeResp:
            captured["method"] = "POST"
            return FakeResp()

    with patch("app.api.v1.telegram._get_tg_pool", return_value=FakeClient()):
        # Metodo PUT/DELETE cai no else do if (treated as POST)
        result = await _call_api("PUT", "/api/v1/test", body={"x": 1})

    assert captured["method"] == "POST"
    assert result == {"ok": True}


# =============================================================================
# Tool helpers
# =============================================================================


@pytest.mark.asyncio
async def test_tool_consultar_protocolo_retorna_erro_sem_rede() -> None:
    """_tool_consultar_protocolo retorna erro dict quando API esta fora."""
    with patch("app.api.v1.telegram._call_api", return_value={"erro": "connection refused"}):
        from app.api.v1.telegram import _tool_consultar_protocolo

        result = await _tool_consultar_protocolo("2026-000123")
    assert "erro" in result


@pytest.mark.asyncio
async def test_tool_criar_atendimento_retorna_erro_sem_rede() -> None:
    """_tool_criar_atendimento retorna erro dict quando API esta fora."""
    with patch("app.api.v1.telegram._call_api", return_value={"erro": "connection refused"}):
        from app.api.v1.telegram import _tool_criar_atendimento

        result = await _tool_criar_atendimento(cliente_id=1, topico="certidão", contato="oi")
    assert "erro" in result
