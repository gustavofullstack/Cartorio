"""Testes do envelope de retry 3x20s (P0 Gustavo 2026-07-27).

P0 Gustavo: "TENTA UNAS 3X EM 20S NO BACKEND TROCAR SOZINHO E MANDAR DNV A
MENSAGEM DO CLIENTE P/ O NOVO ENDPOINT AI E MANDAR A RESPOSTAS DOS MODELOS P/
O CLIENTE PORRA TA MALUCO!! FAZ DIREITO!!"

O envelope (``_retry_envelope_3x20s``) deve:
1. Tentar ate 3 vezes dentro de 20s budget.
2. Cada tentativa roda a chain completa (MiniMax_direct -> litellm ->
   opencode_free_1/2/3) — provedor que falhou no attempt N sera pulado no
   proximo attempt (circuit breaker).
3. Em sucesso, retornar imediatamente — cliente recebe resposta do modelo.
4. Em todas as tentativas falharem (content vazio OU exception), retornar None
   + meta com outcome="exhausted" para o caller disparar offline reply.
5. Budget 20s respeitado mesmo se attempts nao completarem.

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.cartorio_agent import _retry_envelope_3x20s


# ---- Helpers ----------------------------------------------------------------


def _ok_result(text: str = "oi", provider: str = "minimax_direct:MiniMax-M3") -> tuple:
    """Resultado bem-sucedido tipico de _run_llm_with_fallback."""
    return (text, provider, None, [])


def _empty_result() -> tuple:
    """Resultado vazio (chain exhausted sem exception)."""
    return ("", "none", None, [])


# ---- 1. Success path --------------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_returns_first_success() -> None:
    """Primeira tentativa bem-sucedida — envelope retorna sem retry."""

    async def inner() -> tuple:
        return _ok_result("primeira tentativa ok")

    result, meta = await _retry_envelope_3x20s(inner)
    assert result is not None
    assert result[0] == "primeira tentativa ok"
    assert meta["outcome"] == "success"
    assert meta["attempts"] == 1
    assert meta["elapsed_s"] < 0.1
    assert meta["last_err"] == ""


@pytest.mark.asyncio
async def test_envelope_recovers_on_second_attempt() -> None:
    """Primeira falhou (chain exhausted), segunda succeeded — client NAO ve falha."""

    calls = {"n": 0}

    async def inner() -> tuple:
        calls["n"] += 1
        if calls["n"] == 1:
            return _empty_result()
        return _ok_result("recuperado no segundo")

    result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    assert result is not None
    assert result[0] == "recuperado no segundo"
    assert meta["outcome"] == "success"
    assert meta["attempts"] == 2
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_envelope_recovers_on_third_attempt() -> None:
    """Falha 2x, sucesso no 3o — budget permite o terceiro."""

    calls = {"n": 0}

    async def inner() -> tuple:
        calls["n"] += 1
        if calls["n"] < 3:
            return _empty_result()
        return _ok_result("recuperado no terceiro")

    result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    assert result is not None
    assert result[0] == "recuperado no terceiro"
    assert meta["outcome"] == "success"
    assert meta["attempts"] == 3
    assert calls["n"] == 3


# ---- 2. Exhaustion path -----------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_exhausted_returns_none() -> None:
    """3 tentativas todas vazias — caller recebe None + meta=exhausted."""

    async def inner() -> tuple:
        return _empty_result()

    result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    assert result is None
    assert meta["outcome"] == "exhausted"
    assert meta["attempts"] == 3
    assert meta["elapsed_s"] < 0.5
    assert meta["last_err"] == "chain_exhausted_no_content"


@pytest.mark.asyncio
async def test_envelope_handles_exception_in_attempt() -> None:
    """Exception dentro do inner() NAO derruba o envelope — tenta de novo."""

    calls = {"n": 0}

    async def inner() -> tuple:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("provider offline")
        return _ok_result("ok apos exception")

    result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    assert result is not None
    assert result[0] == "ok apos exception"
    assert meta["outcome"] == "success"
    assert meta["attempts"] == 2


@pytest.mark.asyncio
async def test_envelope_exhausted_after_3_exceptions() -> None:
    """3 exceptions seguidas — exhausted e nunca deixa cliente ver falha solta."""

    calls = {"n": 0}

    async def inner() -> tuple:
        calls["n"] += 1
        raise RuntimeError(f"always fails #{calls['n']}")

    result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    assert result is None
    assert meta["outcome"] == "exhausted"
    assert meta["attempts"] == 3
    assert "RuntimeError" in meta["last_err"]
    assert "always fails #3" in meta["last_err"]


# ---- 3. Budget enforcement --------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_respects_20s_budget() -> None:
    """Quando budget ja foi consumido, para de tentar — NAO estoura limite."""

    calls = {"n": 0}
    started = time.perf_counter()

    async def inner() -> tuple:
        calls["n"] += 1
        # Simula provider lento: 12s por tentativa (cabe 1+ dentro de 20s budget)
        await asyncio.sleep(12.0)
        return _empty_result()

    result, meta = await _retry_envelope_3x20s(
        inner, max_attempts=3, budget_s=20.0, inter_sleep_s=0.0
    )
    elapsed = time.perf_counter() - started
    assert result is None
    # Budget 20s respeitado (com margem para latencia real)
    assert elapsed < 25.0, f"budget estourou: elapsed={elapsed:.2f}s"
    # 1 ou 2 attempts apenas (3 nao cabe em 20s)
    assert meta["attempts"] <= 2
    assert meta["outcome"] == "exhausted"


@pytest.mark.asyncio
async def test_envelope_no_attempts_when_budget_zero() -> None:
    """Budget 0 = 0 attempts — caller recebe exhausted imediatamente."""

    async def inner() -> tuple:
        pytest.fail("inner NAO deveria ser chamado com budget=0")

    result, meta = await _retry_envelope_3x20s(
        inner, max_attempts=3, budget_s=0.0, inter_sleep_s=0.0
    )
    assert result is None
    assert meta["outcome"] == "exhausted"
    assert meta["attempts"] == 0


# ---- 4. Inter-attempt sleep -------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_inter_sleep_respected() -> None:
    """Quando inter_sleep_s > 0, dorme entre tentativas."""

    calls = {"n": 0}
    timestamps: list[float] = []

    async def inner() -> tuple:
        timestamps.append(time.perf_counter())
        calls["n"] += 1
        if calls["n"] < 3:
            return _empty_result()
        return _ok_result("ok")

    result, meta = await _retry_envelope_3x20s(
        inner, max_attempts=3, budget_s=20.0, inter_sleep_s=0.3
    )
    assert result is not None
    # Intervalo entre attempt 1 e 2 >= 0.3s
    assert (timestamps[1] - timestamps[0]) >= 0.25
    # Intervalo entre attempt 2 e 3 >= 0.3s
    assert (timestamps[2] - timestamps[1]) >= 0.25


# ---- 5. Metrics integration -------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_increments_metric_on_success() -> None:
    """Sucesso dentro do envelope incrementa o contador ``multi_provider``."""

    mock_store = MagicMock()
    mock_store.inc_llm_calls_total = MagicMock()

    async def inner() -> tuple:
        return _ok_result("ok metric")

    with patch("app.services.cartorio_agent._retry_envelope_3x20s.__module__", create=True):
        # Patch do import dentro da funcao (lazy import app.services.metrics.store)
        with patch.dict("sys.modules", {"app.services.metrics": MagicMock(store=mock_store)}):
            # Forca lazy import resolver para nosso mock
            import sys

            original_metrics = sys.modules.get("app.services.metrics")
            mock_metrics_module = MagicMock()
            mock_metrics_module.store = mock_store
            sys.modules["app.services.metrics"] = mock_metrics_module
            try:
                result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
            finally:
                if original_metrics is not None:
                    sys.modules["app.services.metrics"] = original_metrics
                else:
                    sys.modules.pop("app.services.metrics", None)

    assert result is not None
    # Deve ter incrementado pelo menos uma vez com label retry_envelope_success_attempt1
    success_calls = [
        call_args
        for call_args in mock_store.inc_llm_calls_total.call_args_list
        if "retry_envelope_success" in str(call_args)
    ]
    assert len(success_calls) >= 1


@pytest.mark.asyncio
async def test_envelope_increments_exhausted_metric() -> None:
    """Exhaustion incrementa contador ``retry_envelope_exhausted``."""

    mock_store = MagicMock()
    mock_store.inc_llm_calls_total = MagicMock()

    async def inner() -> tuple:
        return _empty_result()

    import sys

    original_metrics = sys.modules.get("app.services.metrics")
    mock_metrics_module = MagicMock()
    mock_metrics_module.store = mock_store
    sys.modules["app.services.metrics"] = mock_metrics_module
    try:
        result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    finally:
        if original_metrics is not None:
            sys.modules["app.services.metrics"] = original_metrics
        else:
            sys.modules.pop("app.services.metrics", None)

    assert result is None
    exhausted_calls = [
        call_args
        for call_args in mock_store.inc_llm_calls_total.call_args_list
        if "retry_envelope_exhausted" in str(call_args)
    ]
    assert len(exhausted_calls) == 1


# ---- 6. Custom max_attempts ------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_custom_max_attempts_2() -> None:
    """max_attempts=2 → 2 tentativas apenas, depois exhausted."""

    calls = {"n": 0}

    async def inner() -> tuple:
        calls["n"] += 1
        return _empty_result()

    result, meta = await _retry_envelope_3x20s(inner, max_attempts=2, inter_sleep_s=0.0)
    assert result is None
    assert meta["attempts"] == 2
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_envelope_max_attempts_1_is_single_try() -> None:
    """max_attempts=1 → envelope degenera em single shot (sem retry)."""

    calls = {"n": 0}

    async def inner() -> tuple:
        calls["n"] += 1
        return _ok_result("ok")

    result, meta = await _retry_envelope_3x20s(inner, max_attempts=1, inter_sleep_s=0.0)
    assert result is not None
    assert meta["attempts"] == 1
    assert calls["n"] == 1


# ---- 7. Truthy content variants (retro-compat) ------------------------------


@pytest.mark.asyncio
async def test_envelope_accepts_non_tuple_truthy_result() -> None:
    """Retro-compat: inner() que retorna string pura tb e tratada como sucesso."""

    async def inner() -> str:
        return "ok string"

    result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    assert result == "ok string"
    assert meta["outcome"] == "success"
    assert meta["attempts"] == 1


@pytest.mark.asyncio
async def test_envelope_truthy_non_tuple_with_provider() -> None:
    """Tuple com 2 elementos (content, provider) tb e aceito."""

    async def inner() -> tuple[str, str]:
        return ("hello", "opencode_free_1")

    result, meta = await _retry_envelope_3x20s(inner, inter_sleep_s=0.0)
    assert isinstance(result, tuple)
    assert result[0] == "hello"
    assert result[1] == "opencode_free_1"
    assert meta["outcome"] == "success"
