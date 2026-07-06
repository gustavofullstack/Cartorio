"""Testes para app.core.redis_client — singleton assíncrono Redis.

Cobre:
- get_redis() retorna None quando redis não disponível (graceful degradation)
- close_redis() funciona sem estado (sem crash)
- Módulo importável sem conexão real
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_get_redis_graceful_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_redis() retorna None quando redis.asyncio não disponível."""
    import sys

    # Garante reload do módulo (reset singleton)
    if "app.core.redis_client" in sys.modules:
        del sys.modules["app.core.redis_client"]

    # Simula ausência do pacote redis.asyncio
    import builtins

    original_import = builtins.__import__

    def mock_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "redis.asyncio":
            raise ImportError("redis asyncio not available")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Reload do módulo para garantir estado limpo
    if "app.core.redis_client" in sys.modules:
        del sys.modules["app.core.redis_client"]

    from app.core import redis_client as rc

    # Reset singleton
    rc._redis_client = None

    result = await rc.get_redis()
    assert result is None


@pytest.mark.asyncio
async def test_close_redis_sem_estado_nao_crasha() -> None:
    """close_redis() sem estado prévio não levanta exceção."""
    import sys

    if "app.core.redis_client" in sys.modules:
        del sys.modules["app.core.redis_client"]

    from app.core import redis_client as rc

    rc._redis_client = None
    # Não deve lançar exceção
    await rc.close_redis()
    assert rc._redis_client is None


def test_modulo_importavel_sem_conexao() -> None:
    """app.core.redis_client é importável sem conexão Redis real."""
    from app.core import redis_client  # noqa: F401

    assert hasattr(redis_client, "get_redis")
    assert hasattr(redis_client, "close_redis")
    assert callable(redis_client.get_redis)
    assert callable(redis_client.close_redis)


@pytest.mark.asyncio
async def test_close_redis_com_mock_client() -> None:
    """close_redis() chama aclose() no client e reseta o singleton."""
    from app.core import redis_client as rc

    class FakeClient:
        closed = False

        async def aclose(self) -> None:
            self.closed = True

    fake = FakeClient()
    rc._redis_client = fake  # type: ignore[assignment]
    await rc.close_redis()
    assert fake.closed is True
    assert rc._redis_client is None
