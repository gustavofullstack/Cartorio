"""Testes do middleware de Idempotency-Key (A6).

A6: POST com Idempotency-Key -> Redis SETNX com TTL 24h.
- Mesma key + mesmo body = mesma resposta (replay retorna 200 cached).
- Sem key = passa direto (sem cache).
- Key expirada (TTL 24h) = permite novo POST.
- Key duplicada com body diferente = 422.
- Key vazia = 400.
- LGPD: cache armazena APENAS o response (sem PII).
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import json  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402

from app.middleware.idempotency import IdempotencyMiddleware  # noqa: E402
from app.services.idempotency_store_fake import FakeIdempotencyStore  # noqa: E402


# ============================================================================
# IdempotencyStore (fake) — test base behavior
# ============================================================================


@pytest.mark.asyncio
async def test_fake_store_setnx_retorna_true_primeira_vez() -> None:
    store = FakeIdempotencyStore()
    result = await store.setnx(key="k1", value={"ok": True}, ttl_seconds=60)
    assert result is True


@pytest.mark.asyncio
async def test_fake_store_setnx_retorna_false_segunda_vez() -> None:
    store = FakeIdempotencyStore()
    await store.setnx(key="k1", value={"ok": True}, ttl_seconds=60)
    result = await store.setnx(key="k1", value={"ok": True}, ttl_seconds=60)
    assert result is False


@pytest.mark.asyncio
async def test_fake_store_get_retorna_valor_anterior() -> None:
    store = FakeIdempotencyStore()
    await store.setnx(key="k1", value={"status": "ok", "id": 1}, ttl_seconds=60)
    result = await store.get(key="k1")
    assert result == {"status": "ok", "id": 1}


@pytest.mark.asyncio
async def test_fake_store_get_key_inexistente_retorna_none() -> None:
    store = FakeIdempotencyStore()
    result = await store.get(key="missing")
    assert result is None


@pytest.mark.asyncio
async def test_fake_store_delete_remove_key() -> None:
    store = FakeIdempotencyStore()
    await store.setnx(key="k1", value={"ok": True}, ttl_seconds=60)
    await store.delete(key="k1")
    result = await store.get(key="k1")
    assert result is None


# ============================================================================
# IdempotencyMiddleware — test behavior
# ============================================================================


@pytest.fixture
def fake_store() -> FakeIdempotencyStore:
    return FakeIdempotencyStore()


@pytest.fixture
def mw_with_fake_store(fake_store: FakeIdempotencyStore) -> IdempotencyMiddleware:
    return IdempotencyMiddleware(
        app=MagicMock(),
        store=fake_store,
        paths_prefixes=("/api/v1/",),
    )


class _RealHeaders(dict):
    """dict que expoe .get() padrao e case-insensitive nao (testes so usam lowercase)."""

    def get(self, key: str, default: object = None) -> object:
        return super().get(key, default)


def _make_post_request(idempotency_key: str | None = None, body: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.method = "POST"
    request.url.path = "/api/v1/protocolo"
    request.headers = _RealHeaders()
    if idempotency_key is not None:
        request.headers["idempotency-key"] = idempotency_key
    request.body = AsyncMock(return_value=json.dumps(body or {}).encode())
    return request


@pytest.mark.asyncio
async def test_post_com_idempotency_key_armazena_resposta(mw_with_fake_store) -> None:
    """POST com Idempotency-Key: response eh cacheada."""
    request = _make_post_request(idempotency_key="abc-123", body={"nome": "Joao"})

    call_next = AsyncMock(return_value=MagicMock(status_code=201, body=b'{"id": 1}'))

    response = await mw_with_fake_store.dispatch(request, call_next)
    call_next.assert_called_once()
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_post_replay_com_mesma_key_retorna_resposta_cacheada(
    mw_with_fake_store, fake_store
) -> None:
    """POST 1: cacheia. POST 2 (mesma key): retorna cached SEM chamar handler."""
    request1 = _make_post_request(idempotency_key="abc-123", body={"nome": "Joao"})
    fake_response = MagicMock()
    fake_response.status_code = 201
    fake_response.body = b'{"id": 1}'
    call_next1 = AsyncMock(return_value=fake_response)
    await mw_with_fake_store.dispatch(request1, call_next1)

    # 2o request
    request2 = _make_post_request(idempotency_key="abc-123", body={"nome": "Joao"})
    call_next2 = AsyncMock()
    response2 = await mw_with_fake_store.dispatch(request2, call_next2)
    call_next2.assert_not_called()  # replay nao chama handler
    assert response2.status_code == 201


@pytest.mark.asyncio
async def test_post_sem_idempotency_key_passa_direto(mw_with_fake_store) -> None:
    """POST sem Idempotency-Key: passa direto (sem cache)."""
    request = _make_post_request(idempotency_key=None)
    call_next = AsyncMock(return_value=MagicMock(status_code=201))
    response = await mw_with_fake_store.dispatch(request, call_next)
    call_next.assert_called_once()
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_post_idempotency_key_vazia_retorna_400(mw_with_fake_store) -> None:
    """Idempotency-Key com string vazia = 400."""
    request = _make_post_request(idempotency_key="")
    call_next = AsyncMock()
    response = await mw_with_fake_store.dispatch(request, call_next)
    assert response.status_code == 400
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_post_idempotency_key_duplicada_com_body_diferente_retorna_422(
    mw_with_fake_store,
) -> None:
    """Mesma key + body diferente = 422 (conflito)."""
    request1 = _make_post_request(idempotency_key="abc-123", body={"nome": "Joao"})
    fake_response = MagicMock()
    fake_response.status_code = 201
    fake_response.body = b'{"id": 1}'
    call_next1 = AsyncMock(return_value=fake_response)
    await mw_with_fake_store.dispatch(request1, call_next1)

    # 2o request: mesma key mas body diferente
    request2 = _make_post_request(idempotency_key="abc-123", body={"nome": "Maria"})
    call_next2 = AsyncMock()
    response2 = await mw_with_fake_store.dispatch(request2, call_next2)
    assert response2.status_code == 422
    call_next2.assert_not_called()


@pytest.mark.asyncio
async def test_post_path_fora_prefix_nao_passa_middleware() -> None:
    """Paths fora de /api/v1/ passam direto (sem idempotency)."""
    mw = IdempotencyMiddleware(
        app=MagicMock(),
        store=FakeIdempotencyStore(),
        paths_prefixes=("/api/v1/",),
    )
    request = MagicMock()
    request.method = "POST"
    request.url.path = "/health"
    request.headers = {"idempotency-key": "abc"}
    call_next = AsyncMock(return_value=MagicMock(status_code=200))
    await mw.dispatch(request, call_next)
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_get_nao_passa_pelo_middleware_idempotency() -> None:
    """GET requests nao sao interceptados."""
    mw = IdempotencyMiddleware(
        app=MagicMock(),
        store=FakeIdempotencyStore(),
        paths_prefixes=("/api/v1/",),
    )
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/api/v1/protocolo/2026-00001"
    request.headers = {"idempotency-key": "abc"}
    call_next = AsyncMock(return_value=MagicMock(status_code=200))
    await mw.dispatch(request, call_next)
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_store_get_exception_fail_open() -> None:
    """Se store.get() lancar excecao, middleware faz fail-open (passa direto)."""
    broken_store = AsyncMock()
    broken_store.get.side_effect = RuntimeError("Redis offline")
    mw = IdempotencyMiddleware(
        app=MagicMock(),
        store=broken_store,
        paths_prefixes=("/api/v1/",),
    )
    request = _make_post_request(idempotency_key="fail-open-key", body={"x": 1})
    call_next = AsyncMock(return_value=MagicMock(status_code=200))
    response = await mw.dispatch(request, call_next)
    call_next.assert_called_once()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_store_setnx_exception_fail_open() -> None:
    """Se store.setnx() lancar excecao, middleware nao quebra o request."""
    failing_store = AsyncMock()
    failing_store.get.return_value = None
    failing_store.setnx.side_effect = RuntimeError("Redis write fail")
    mw = IdempotencyMiddleware(
        app=MagicMock(),
        store=failing_store,
        paths_prefixes=("/api/v1/",),
    )
    request = _make_post_request(idempotency_key="setnx-fail", body={"y": 2})

    async def _ok_response(req: MagicMock) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 201
        resp.headers = {}
        resp.media_type = "application/json"

        async def _iter():
            yield b'{"created": true}'

        resp.body_iterator = _iter()
        return resp

    response = await mw.dispatch(request, _ok_response)  # type: ignore[arg-type]
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_post_response_com_erro_5xx_nao_cacheia(mw_with_fake_store) -> None:
    """Resposta 5xx NAO eh cacheada (cliente pode tentar novamente)."""
    request = _make_post_request(idempotency_key="abc-123")
    fake_response = MagicMock()
    fake_response.status_code = 500
    fake_response.body = b'{"error": "fail"}'
    call_next = AsyncMock(return_value=fake_response)
    await mw_with_fake_store.dispatch(request, call_next)

    # 2o request com mesma key deve ser permitido (nao cacheou)
    request2 = _make_post_request(idempotency_key="abc-123")
    call_next2 = AsyncMock(return_value=MagicMock(status_code=200, body=b"ok"))
    response2 = await mw_with_fake_store.dispatch(request2, call_next2)
    call_next2.assert_called_once()
    assert response2.status_code == 200
