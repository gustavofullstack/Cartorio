"""Testes para app/integrations/supabase_client.py - helpers (cobertura).

Cobre:
1. _with_retry happy path (success on 1st try)
2. _with_retry retry on TimeoutException
3. _with_retry max retries exceeded raises RuntimeError
4. _headers service role vs anon
5. supabase_health success
6. supabase_health network failure returns False

Sobe cobertura supabase_client.py 80% -> >=90%.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.supabase_client import (
    _headers,
    _with_retry,
    supabase_health,
)


# =============================================================================
# _headers
# =============================================================================


def test_headers_service_role_use_service_key() -> None:
    """_headers(use_service_role=True) usa supabase_service_role_key."""
    with patch("app.integrations.supabase_client.settings") as mock_settings:
        mock_settings.supabase_service_role_key = "service-key-12345"
        mock_settings.supabase_anon_key = "anon-key-67890"

        h = _headers(use_service_role=True)
        assert h["apikey"] == "service-key-12345"
        assert h["Authorization"] == "Bearer service-key-12345"


def test_headers_anon_use_anon_key() -> None:
    """_headers(use_service_role=False) usa supabase_anon_key."""
    with patch("app.integrations.supabase_client.settings") as mock_settings:
        mock_settings.supabase_service_role_key = "service-key-12345"
        mock_settings.supabase_anon_key = "anon-key-67890"

        h = _headers(use_service_role=False)
        assert h["apikey"] == "anon-key-67890"
        assert h["Authorization"] == "Bearer anon-key-67890"


def test_headers_inclui_content_type_e_prefer() -> None:
    """_headers sempre inclui Content-Type e Prefer."""
    h = _headers()
    assert h["Content-Type"] == "application/json"
    assert h["Prefer"] == "return=representation"


# =============================================================================
# _with_retry
# =============================================================================


@pytest.mark.asyncio
async def test_with_retry_sucesso_primeira_tentativa() -> None:
    """_with_retry sucesso na 1a tentativa."""
    mock_fn = AsyncMock(return_value="ok")

    result = await _with_retry(mock_fn, "arg1", kwarg1="v1")

    assert result == "ok"
    assert mock_fn.call_count == 1


@pytest.mark.asyncio
async def test_with_retry_sucesso_apos_2_tentativas_timeout() -> None:
    """_with_retry retry apos TimeoutException e sucesso."""
    import httpx

    mock_fn = AsyncMock(
        side_effect=[
            httpx.TimeoutException("timeout 1"),
            "success-on-2nd",
        ]
    )

    # Patch asyncio.sleep para ser instantaneo
    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        result = await _with_retry(mock_fn)

    assert result == "success-on-2nd"
    assert mock_fn.call_count == 2


@pytest.mark.asyncio
async def test_with_retry_max_retries_exceeded_levanta_RuntimeError() -> None:
    """_with_retry esgota retries e levanta RuntimeError."""
    import httpx

    mock_fn = AsyncMock(side_effect=httpx.TimeoutException("always timeout"))

    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        with pytest.raises(RuntimeError, match="Supabase client falhou"):
            await _with_retry(mock_fn)


@pytest.mark.asyncio
async def test_with_retry_nao_retenta_para_HTTPError_generico() -> None:
    """_with_retry NAO retenta para HTTPError generico (apenas Timeout/Network)."""
    import httpx

    # HTTPError generico NAO esta na lista de retry
    mock_fn = AsyncMock(side_effect=httpx.HTTPError("http error"))

    with pytest.raises(httpx.HTTPError):
        await _with_retry(mock_fn)
    # Apenas 1 tentativa, sem retry
    assert mock_fn.call_count == 1


# =============================================================================
# supabase_health
# =============================================================================


@pytest.mark.asyncio
async def test_supabase_health_sucesso_200() -> None:
    """supabase_health retorna True quando HTTP 200."""

    class FakeResp:
        status_code = 200
        text = "ok"

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    with patch("app.integrations.supabase_client.httpx.AsyncClient", FakeClient):
        with patch("app.integrations.supabase_client.settings") as mock_settings:
            mock_settings.supabase_url = "https://supabase.example.com"
            mock_settings.supabase_service_role_key = "k"
            mock_settings.supabase_anon_key = "k"
            result = await supabase_health()

    assert result is True


@pytest.mark.asyncio
async def test_supabase_health_401_conta_como_UP() -> None:
    """supabase_health retorna True para 401 (requer auth, mas Supabase UP)."""

    class FakeResp:
        status_code = 401
        text = "auth required"

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, *args: object, **kwargs: object) -> FakeResp:
            return FakeResp()

    with patch("app.integrations.supabase_client.httpx.AsyncClient", FakeClient):
        with patch("app.integrations.supabase_client.settings") as mock_settings:
            mock_settings.supabase_url = "https://supabase.example.com"
            mock_settings.supabase_service_role_key = "k"
            mock_settings.supabase_anon_key = "k"
            result = await supabase_health()

    # 401 = auth required mas UP
    assert result is True


@pytest.mark.asyncio
async def test_supabase_health_exception_retorna_False() -> None:
    """supabase_health retorna False em caso de network error."""
    import httpx

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def get(self, *args: object, **kwargs: object) -> object:
            raise httpx.ConnectError("network down")

    with patch("app.integrations.supabase_client.httpx.AsyncClient", FakeClient):
        with patch("app.integrations.supabase_client.settings") as mock_settings:
            mock_settings.supabase_url = "https://supabase.example.com"
            mock_settings.supabase_service_role_key = "k"
            mock_settings.supabase_anon_key = "k"
            result = await supabase_health()

    assert result is False
