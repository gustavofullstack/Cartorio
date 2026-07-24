"""G9 (2026-07-20) — contratos do cartorio_agent:

1. Slots opencode_free 1/2/3 herdam key+base_url+model da MESMA conta zen
   (OPENCODE_ZEN_ACCOUNT_X_*) quando OPENCODE_FREE_X_* ausentes (E2).
2. Payload 'thinking'/'tools' SOMENTE para minimax_direct; zen free e
   litellm recebem payload minimo (model/messages/max_tokens/temperature).
3. asyncio.wait_for global em run_cartorio_agent cai no offline reply
   quando o provider trava (usuario nunca fica 15min sem resposta).
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx

from app.services import cartorio_agent
from app.services.metrics import MetricsStore

_ZEN_ENV_VARS = [
    f"{prefix}{slot}_{suffix}"
    for prefix in ("OPENCODE_FREE_", "OPENCODE_ZEN_ACCOUNT_")
    for slot in (1, 2, 3)
    for suffix in ("API_KEY", "BASE_URL", "MODEL")
]

_OK_JSON = {"choices": [{"message": {"content": "ok"}}]}
_TOOLS = [{"type": "function", "function": {"name": "t", "parameters": {}}}]


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Isola cada teste de env vars e module attrs do ambiente real."""
    for var in _ZEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "")
    monkeypatch.setattr(cartorio_agent, "LITELLM_KEY", "")
    yield


# ---------------------------------------------------------------------------
# 1) Slots zen: fallback coerente chave+url+modelo da MESMA conta.
# ---------------------------------------------------------------------------
def test_slot_herda_base_url_e_model_da_mesma_conta_zen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_2_API_KEY", "zen-key-2")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_2_BASE_URL", "https://zen2.example/v1")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_2_MODEL", "model-zen-2")

    configs = cartorio_agent._opencode_free_configs()

    assert configs[1] == ("zen-key-2", "https://zen2.example/v1", "model-zen-2")
    # Demais slots intocados (sem env -> defaults historicos, sem chave).
    assert configs[0][0] == ""
    assert configs[2][0] == ""


def test_slot_sem_env_usa_defaults_historicos() -> None:
    configs = cartorio_agent._opencode_free_configs()
    assert configs == [
        ("", "https://opencode.ai/zen/v1", "nemotron-3-ultra-free"),
        ("", "https://opencode.ai/zen/v1", "mimo-v2.5-free"),
        ("", "https://opencode.ai/zen/v1", "deepseek-v4-flash-free"),
    ]


def test_slot_free_key_presente_ainda_herda_url_e_model_da_conta_zen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OPENCODE_FREE_1_API_KEY setada sem FREE_1_BASE_URL/_MODEL: herda de
    OPENCODE_ZEN_ACCOUNT_1_* (mesma conta) em vez de cair no default de slot."""
    monkeypatch.setenv("OPENCODE_FREE_1_API_KEY", "free-key-1")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_BASE_URL", "https://zen1.example/v1")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_MODEL", "model-zen-1")

    configs = cartorio_agent._opencode_free_configs()

    assert configs[0] == ("free-key-1", "https://zen1.example/v1", "model-zen-1")


# ---------------------------------------------------------------------------
# 2) Payload por provider: rico so no minimax_direct.
# ---------------------------------------------------------------------------
async def test_payload_minimax_contem_thinking_e_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "mm-key")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_MODEL", "MiniMax-M3")

    with respx.mock:
        route = respx.post("https://minimax.example/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_JSON)
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
            tools=_TOOLS,
        )

    assert err == ""
    assert msg == {"content": "ok"}
    assert provider == "minimax_direct:MiniMax-M3"
    body = json.loads(route.calls[0].request.content)
    assert body["thinking"] == {"type": "adaptive"}
    assert body["tools"] == _TOOLS
    assert body["tool_choice"] == "auto"


async def test_payload_zen_free_minimo_sem_thinking_nem_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_API_KEY", "zen-key-1")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_BASE_URL", "https://zen1.example/v1")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_MODEL", "model-zen-1")

    with respx.mock:
        route = respx.post("https://zen1.example/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_JSON)
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
            tools=_TOOLS,
        )

    assert err == ""
    assert provider == "opencode_free_1:model-zen-1"
    body: dict[str, Any] = json.loads(route.calls[0].request.content)
    assert "thinking" not in body
    assert "tools" not in body
    assert "tool_choice" not in body
    assert body["model"] == "model-zen-1"
    assert body["messages"] == [{"role": "user", "content": "oi"}]
    assert body["max_tokens"] == 4096
    assert body["temperature"] == 0.7


async def test_payload_litellm_minimo_sem_thinking_nem_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cartorio_agent, "LITELLM_KEY", "litellm-key")
    monkeypatch.setattr(cartorio_agent, "LITELLM_URLS", ["https://litellm.example"])
    monkeypatch.setattr(cartorio_agent, "LITELLM_MODEL", "litellm-model")

    with respx.mock:
        route = respx.post("https://litellm.example/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_JSON)
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
            tools=_TOOLS,
        )

    assert err == ""
    assert provider == "litellm:litellm-model"
    body = json.loads(route.calls[0].request.content)
    assert "thinking" not in body
    assert "tools" not in body
    assert body["model"] == "litellm-model"


# ---------------------------------------------------------------------------
# 3) Timeout global: provider travado -> offline reply rapido.
# ---------------------------------------------------------------------------
async def test_wait_for_global_cai_no_offline_reply_com_provider_travado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _stuck(system: str, user: str) -> tuple[str, str, str | None, list[str]]:
        await asyncio.sleep(30)
        return "nunca", "none", None, []

    monkeypatch.setattr(cartorio_agent, "_llm_agent_with_tools", _stuck)
    monkeypatch.setattr(cartorio_agent, "LLM_GLOBAL_TIMEOUT_S", 0.2)

    start = time.monotonic()
    reply = await cartorio_agent.run_cartorio_agent("quanto custa uma procuracao?")
    elapsed = time.monotonic() - start

    assert elapsed < 5, f"demorou {elapsed:.1f}s — wait_for global nao disparou"
    assert reply.provider.startswith("offline")
    assert reply.text.startswith("Nosso sistema de inteligência artificial está com lentidão")


async def test_global_timeout_cobre_fallback_simples_e_registra_metrica(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback sem tools nao pode iniciar outro ciclo completo de timeout."""

    async def _empty_tools(
        system: str, user: str
    ) -> tuple[str, str, str | None, list[str]]:
        return "", "none", None, []

    async def _stuck_fallback(system: str, user: str) -> tuple[str, str]:
        await asyncio.sleep(30)
        return "nunca", "none"

    metrics = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", metrics)
    monkeypatch.setattr(cartorio_agent, "_llm_agent_with_tools", _empty_tools)
    monkeypatch.setattr(cartorio_agent, "_llm_minimax", _stuck_fallback)
    monkeypatch.setattr(cartorio_agent, "LLM_GLOBAL_TIMEOUT_S", 0.2)

    start = time.monotonic()
    reply = await cartorio_agent.run_cartorio_agent("oi")
    elapsed = time.monotonic() - start

    assert elapsed < 5, f"fallback excedeu o teto global: {elapsed:.1f}s"
    assert reply.text.startswith("Nosso sistema de inteligência artificial está com lentidão")
    assert metrics.counters["cartorio_llm_calls_total"][
        "model=multi_provider|operation=chat|status=timeout"
    ] == 1


# ---------------------------------------------------------------------------
# 4) Circuit breaker multi-provider (G9.S3.T4)
# ---------------------------------------------------------------------------
async def test_circuit_open_pula_minimax_e_usa_zen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MiniMax com circuito OPEN e pulado; zen free atende."""
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "mm-key")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_MODEL", "MiniMax-M3")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_API_KEY", "zen-key-1")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_BASE_URL", "https://zen1.example/v1")
    monkeypatch.setenv("OPENCODE_ZEN_ACCOUNT_1_MODEL", "model-zen-1")

    async def _open_only_minimax(provider: str) -> bool:
        return provider == "MiniMax_direct"

    monkeypatch.setattr(cartorio_agent, "_circuit_skip", _open_only_minimax)

    with respx.mock:
        mm = respx.post("https://minimax.example/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_JSON)
        )
        zen = respx.post("https://zen1.example/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_JSON)
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
        )

    assert err == ""
    assert provider == "opencode_free_1:model-zen-1"
    assert msg == {"content": "ok"}
    assert mm.call_count == 0, "MiniMax nao deveria ser chamado com circuit open"
    assert zen.call_count == 1


async def test_http_500_registra_circuit_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 5xx dispara _circuit_failure no provider."""
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "mm-key")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_MODEL", "MiniMax-M3")

    failures: list[str] = []

    async def _no_skip(provider: str) -> bool:
        return False

    async def _track_fail(provider: str) -> None:
        failures.append(provider)

    async def _track_ok(provider: str) -> None:
        pass

    monkeypatch.setattr(cartorio_agent, "_circuit_skip", _no_skip)
    monkeypatch.setattr(cartorio_agent, "_circuit_failure", _track_fail)
    monkeypatch.setattr(cartorio_agent, "_circuit_success", _track_ok)

    with respx.mock:
        respx.post("https://minimax.example/v1/chat/completions").mock(
            return_value=httpx.Response(500, text="boom")
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
        )

    assert msg is None
    assert provider == "none"
    assert "500" in err
    assert failures == ["MiniMax_direct"]


async def test_success_registra_circuit_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "mm-key")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_MODEL", "MiniMax-M3")

    ok: list[str] = []

    async def _no_skip(provider: str) -> bool:
        return False

    async def _track_ok(provider: str) -> None:
        ok.append(provider)

    async def _noop_fail(provider: str) -> None:
        return None

    monkeypatch.setattr(cartorio_agent, "_circuit_skip", _no_skip)
    monkeypatch.setattr(cartorio_agent, "_circuit_success", _track_ok)
    monkeypatch.setattr(cartorio_agent, "_circuit_failure", _noop_fail)

    with respx.mock:
        respx.post("https://minimax.example/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=_OK_JSON)
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
        )

    assert err == ""
    assert msg is not None
    assert ok == ["MiniMax_direct"]


# ---------------------------------------------------------------------------
# 5) Output scrub + degraded never silent (G9.S3.T8/T10)
# ---------------------------------------------------------------------------
def test_offline_degraded_sempre_tem_mensagem_e_scrub_pii() -> None:
    reply = cartorio_agent._offline_reply(
        "meu cpf e 529.982.247-25",
        "dados",
        [],
        degraded=True,
    )
    assert reply.text.startswith("Nosso sistema de inteligência artificial")
    assert "529.982.247-25" not in reply.text
    assert reply.provider.startswith("offline") or "offline" in reply.provider


def test_sanitize_bot_output_scrubs_cpf() -> None:
    out = cartorio_agent.sanitize_bot_output(
        "Seu CPF e 529.982.247-25 e esta ok."
    )
    assert "529.982.247-25" not in out
    assert out  # nao vazio


async def test_todos_providers_down_devolve_degraded_nunca_vazio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _empty_tools(
        system: str, user: str
    ) -> tuple[str, str, str | None, list[str]]:
        return "", "none", None, []

    async def _empty_fb(system: str, user: str) -> tuple[str, str]:
        return "", "none"

    monkeypatch.setattr(cartorio_agent, "_llm_agent_with_tools", _empty_tools)
    monkeypatch.setattr(cartorio_agent, "_llm_minimax", _empty_fb)

    reply = await cartorio_agent.run_cartorio_agent("oi")
    assert reply.text
    assert "lentidão" in reply.text.lower() or len(reply.text) > 10
    assert reply.provider.startswith("offline")
