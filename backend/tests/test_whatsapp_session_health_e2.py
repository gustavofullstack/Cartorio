"""E2.08 (2026-07-24) — contrato whatsapp_health: sessao WA real separada da API.

Lesson 260: radar ``evolution=online`` NAO implica WhatsApp conectado
(instancia cartorio-2notas ficou connectionState=close por 22 dias com
Evolution API 200 OK). Estes testes FALHAM se o endpoint voltar a
confundir os dois estados.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.api.v1 import whatsapp


class _FakeClient:
    def __init__(self, response: httpx.Response | None = None, exc: Exception | None = None):
        self._response = response
        self._exc = exc

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


class _FakeAdapter:
    base_url = "https://evolution.example"
    instance = "cartorio-2notas"

    def __init__(self, client: _FakeClient):
        self._client = client

    async def _get_client(self) -> _FakeClient:
        return self._client


async def _fake_pipeline() -> dict[str, Any]:
    return {"status": "ok"}


def _mount(monkeypatch: pytest.MonkeyPatch, client: _FakeClient) -> None:
    monkeypatch.setattr(whatsapp, "get_adapter", lambda: _FakeAdapter(client))
    monkeypatch.setattr(whatsapp, "pipeline_health", _fake_pipeline)


@pytest.mark.asyncio
async def test_session_open_reporta_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    _mount(
        monkeypatch,
        _FakeClient(response=httpx.Response(200, json={"instance": {"state": "open"}})),
    )
    out = await whatsapp.whatsapp_health()
    assert out["evolution_api"] == "online"
    assert out["whatsapp_session"] == "open"
    assert out["session_connected"] is True
    assert out["status"] == "ok"


@pytest.mark.asyncio
async def test_session_close_nunca_reporta_ok_regressao_lesson_260(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evolution 200 + state=close -> degraded. REGRESSAO: antes era 'ok'."""
    _mount(
        monkeypatch,
        _FakeClient(response=httpx.Response(200, json={"instance": {"state": "close"}})),
    )
    out = await whatsapp.whatsapp_health()
    assert out["evolution_api"] == "online", "API respondeu 200 — API esta online"
    assert out["whatsapp_session"] == "close"
    assert out["session_connected"] is False
    assert out["status"] == "degraded", "sessao close NUNCA pode reportar ok"


@pytest.mark.asyncio
async def test_evolution_down_reporta_offline_e_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mount(monkeypatch, _FakeClient(exc=httpx.ConnectError("refused")))
    out = await whatsapp.whatsapp_health()
    assert out["evolution_api"] == "offline"
    assert out["whatsapp_session"] == "unknown"
    assert out["session_connected"] is False
    assert out["status"] == "degraded"


@pytest.mark.asyncio
async def test_200_sem_state_no_body_nao_confirma_sessao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """200 com payload inesperado: fail-closed no status (sessao nao confirmada)."""
    _mount(monkeypatch, _FakeClient(response=httpx.Response(200, json={"ok": True})))
    out = await whatsapp.whatsapp_health()
    assert out["evolution_api"] == "online"
    assert out["whatsapp_session"] == "unknown"
    assert out["session_connected"] is False
    assert out["status"] == "degraded"
