"""G7 Wave 20 — Telegram multi-turn Redis hist + catalog intent.

Modified by Gustavo Almeida — G7 Wave 20.
"""

from __future__ import annotations


import pytest

from app.api.v1 import telegram as tg
from app.services.cartorio_agent import (
    _build_catalog_series,
    _detect_intent,
    _wants_catalog_continue,
    _wants_catalog_series,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        return True

    async def delete(self, key: str):
        self.store.pop(key, None)
        return 1


class FakeBus:
    def __init__(self) -> None:
        self.client = FakeRedis()


@pytest.mark.asyncio
async def test_hist_append_and_get_multi_turn() -> None:
    bus = FakeBus()
    key = 424242
    await tg._hist_append(bus, key, "user", "quanto custa procuracao?")
    await tg._hist_append(bus, key, "bot", "Procuracao custa R$ ...")
    hist = await tg._hist_get(bus, key)
    assert len(hist) == 2
    assert hist[0].startswith("user:")
    assert hist[1].startswith("bot:")
    assert "procuracao" in hist[0].lower() or "CPF" in hist[0] or "user:" in hist[0]
    # redis key namespace
    assert f"tg:hist:{key}" in bus.client.store


@pytest.mark.asyncio
async def test_hist_scrubs_cpf_before_store() -> None:
    bus = FakeBus()
    await tg._hist_append(bus, 1, "user", "meu cpf e 529.982.247-25")
    hist = await tg._hist_get(bus, 1)
    assert len(hist) == 1
    blob = hist[0]
    assert "529.982.247-25" not in blob
    assert "52998224725" not in blob.replace(".", "").replace("-", "")


@pytest.mark.asyncio
async def test_hist_caps_at_hist_max() -> None:
    bus = FakeBus()
    for i in range(tg.HIST_MAX + 15):
        await tg._hist_append(bus, 7, "user", f"msg {i}")
    hist = await tg._hist_get(bus, 7)
    assert len(hist) == tg.HIST_MAX


@pytest.mark.asyncio
async def test_hist_get_empty_without_bus() -> None:
    assert await tg._hist_get(None, 1) == []


def test_catalog_series_intent() -> None:
    assert _wants_catalog_series("me fale um pouco de cada servico")
    assert _wants_catalog_continue("continua por favor")
    assert _detect_intent("lista completa dos servicos") == "catalogo_serie"


def test_catalog_series_is_single_message_not_flood() -> None:
    """G7.03.T4 / lesson: catalog consolidado em 1 msg (anti-spam)."""
    series = _build_catalog_series()
    assert len(series) == 1
    assert "Catalogo" in series[0] or "Catálogo" in series[0] or "Servicos" in series[0]
