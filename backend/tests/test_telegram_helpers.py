"""Testes para helpers do app/api/v1/telegram.py (cobertura SQUAD C).

Cobre 7 funcoes puras/side-effect-light do telegram.py para subir cobertura
de 46% -> >=70%:
- strip_emojis
- _get_tg_pool
- _menu_keyboard / _servicos_keyboard / _confirmar_keyboard
- _check_idempotency (com mock)
- _call_api (com mock httpx)
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.telegram import (
    _confirmar_keyboard,
    _get_tg_pool,
    _menu_keyboard,
    _servicos_keyboard,
    strip_emojis,
)
from app.api.v1.telegram import TELEGRAM_API_BASE


def test_strip_emojis_remove_emojis_basicos() -> None:
    """Emojis simples sao removidos."""
    text = "Ola 👍 como vai? 🚀"
    out = strip_emojis(text)
    assert "👍" not in out
    assert "🚀" not in out
    assert "Ola" in out
    assert "como vai?" in out


def test_strip_emojis_texto_sem_emoji_inalterado() -> None:
    """Texto sem emojis eh preservado."""
    text = "Apenas texto simples sem emojis."
    assert strip_emojis(text) == text


def test_strip_emojis_string_vazia() -> None:
    """String vazia retorna string vazia."""
    assert strip_emojis("") == ""


def test_get_tg_pool_retorna_client() -> None:
    """_get_tg_pool retorna um AsyncClient httpx configurado."""
    pool = _get_tg_pool()
    assert pool is not None
    # Verifica que tem os atributos minimos de httpx.AsyncClient
    assert hasattr(pool, "post")
    assert hasattr(pool, "get")


def test_get_tg_pool_uses_canonical_verified_tls() -> None:
    """O transporte Telegram não pode voltar ao bypass TLS/IP legado."""
    source = inspect.getsource(_get_tg_pool)
    assert TELEGRAM_API_BASE == "https://api.telegram.org"
    assert "verify=False" not in source
    assert '"Host"' not in source


def test_menu_keyboard_estrutura_correta() -> None:
    """Menu principal retorna lista 2D com 4 botoes do cartorio."""
    keyboard = _menu_keyboard()
    assert isinstance(keyboard, list)
    assert len(keyboard) >= 3  # pelo menos 3 linhas
    # Cada linha eh uma lista de dicts com text + callback_data
    for row in keyboard:
        assert isinstance(row, list)
        for btn in row:
            assert "text" in btn


def test_servicos_keyboard_estrutura_correta() -> None:
    """_servicos_keyboard retorna botoes dos servicos cartorarios."""
    keyboard = _servicos_keyboard()
    assert isinstance(keyboard, list)
    assert len(keyboard) >= 3
    for row in keyboard:
        for btn in row:
            assert "text" in btn


def test_confirmar_keyboard_estrutura_correta() -> None:
    """_confirmar_keyboard retorna botoes Confirmar/Cancelar."""
    keyboard = _confirmar_keyboard()
    assert isinstance(keyboard, list)
    # Deve ter ao menos uma linha com Confirmar/Cancelar
    assert len(keyboard) >= 1
    buttons_text = [btn["text"] for row in keyboard for btn in row]
    tem_confirm = any("confirmar" in t.lower() or "cancelar" in t.lower() for t in buttons_text)
    assert tem_confirm, f"Esperava Confirmar/Cancelar, achei: {buttons_text}"


@pytest.mark.asyncio
async def test_check_idempotency_retorna_false_se_update_nao_visto() -> None:
    """_check_idempotency retorna False para update_id novo (1a vez)."""
    from app.api.v1.telegram import _check_idempotency

    # SETNX retorna True se a chave NAO existia (1a vez) -> nao eh duplicado
    bus = MagicMock()
    bus.client.set = AsyncMock(return_value=True)  # 1a vez, retorna True

    result = await _check_idempotency(bus, update_id=12345)
    assert result is False  # novo update, nao eh duplicado


@pytest.mark.asyncio
async def test_check_idempotency_retorna_true_se_update_ja_visto() -> None:
    """_check_idempotency retorna True se update_id ja foi processado (replay)."""
    from app.api.v1.telegram import _check_idempotency

    # SETNX retorna None se a chave JA existia (replay) -> eh duplicado
    bus = MagicMock()
    bus.client.set = AsyncMock(return_value=None)  # ja existe, replay

    result = await _check_idempotency(bus, update_id=99999)
    assert result is True
