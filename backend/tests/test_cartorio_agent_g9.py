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


async def test_provider_rate_limit_vira_resposta_cartorial_sem_texto_tecnico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """429 de todos os providers nunca chega cru ao canal do cliente."""
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "mm-key")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_BASE_URL", "https://minimax.example/v1")
    metrics = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", metrics)

    async def _no_skip(provider: str) -> bool:
        return False

    async def _noop(provider: str) -> None:
        return None

    monkeypatch.setattr(cartorio_agent, "_circuit_skip", _no_skip)
    monkeypatch.setattr(cartorio_agent, "_circuit_failure", _noop)

    with respx.mock:
        respx.post("https://minimax.example/v1/chat/completions").mock(
            return_value=httpx.Response(429, text="The model provider is rate-limiting requests")
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
        )

    assert err == ""
    assert provider == "offline:provider_rate_limited"
    assert msg is not None
    assert "limite momentaneo" in str(msg["content"])
    assert "The model provider" not in str(msg["content"])
    assert metrics.counters["cartorio_llm_calls_total"][
        "model=MiniMax_direct|operation=chat|status=rate_limited"
    ] == 1
    assert metrics.counters["cartorio_llm_degraded_total"]["reason=provider_rate_limited"] == 1


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

    async def _empty_tools(system: str, user: str) -> tuple[str, str, str | None, list[str]]:
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
    assert (
        metrics.counters["cartorio_llm_calls_total"][
            "model=multi_provider|operation=chat|status=timeout"
        ]
        == 1
    )


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
    out = cartorio_agent.sanitize_bot_output("Seu CPF e 529.982.247-25 e esta ok.")
    assert "529.982.247-25" not in out
    assert out  # nao vazio


async def test_todos_providers_down_devolve_degraded_nunca_vazio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _empty_tools(system: str, user: str) -> tuple[str, str, str | None, list[str]]:
        return "", "none", None, []

    async def _empty_fb(system: str, user: str) -> tuple[str, str]:
        return "", "none"

    monkeypatch.setattr(cartorio_agent, "_llm_agent_with_tools", _empty_tools)
    monkeypatch.setattr(cartorio_agent, "_llm_minimax", _empty_fb)

    reply = await cartorio_agent.run_cartorio_agent("oi")
    assert reply.text
    assert "lentidão" in reply.text.lower() or len(reply.text) > 10
    assert reply.provider.startswith("offline")


# ---------------------------------------------------------------------------
# 6) E2.02 S3 — fail-open Redis, CB recovery, degraded counter, labels canonicos
# ---------------------------------------------------------------------------
async def test_circuit_skip_fail_open_quando_redis_lanca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis fora do ar: _circuit_skip NUNCA bloqueia provider (fail-open)."""
    import app.integrations.fallback as fb

    async def _redis_down(provider: str) -> bool:
        raise ConnectionError("redis unreachable")

    monkeypatch.setattr(fb, "_is_circuit_open", _redis_down)

    assert await cartorio_agent._circuit_skip("MiniMax_direct") is False


async def test_circuit_abre_apos_3_falhas_e_sucesso_recupera(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Threshold 3 abre o circuito (cb:open no Redis); _record_success fecha."""
    from fakeredis import aioredis as fakeredis_async

    fake = fakeredis_async.FakeRedis()

    class _FakeBus:
        client = fake

    monkeypatch.setattr("app.services.redis_bus.get_bus", lambda: _FakeBus())

    provider = "MiniMax_direct"
    # 2 falhas: ainda fechado
    await cartorio_agent._circuit_failure(provider)
    await cartorio_agent._circuit_failure(provider)
    assert await cartorio_agent._circuit_skip(provider) is False
    # 3a falha: abre
    await cartorio_agent._circuit_failure(provider)
    assert await cartorio_agent._circuit_skip(provider) is True
    # sucesso: recovery — fecha circuito e zera contador
    await cartorio_agent._circuit_success(provider)
    assert await cartorio_agent._circuit_skip(provider) is False
    assert await fake.get("cb:fail:MiniMax_direct") is None
    await fake.aclose()


async def test_circuit_record_fail_open_quando_redis_lanca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_circuit_failure/_circuit_success nunca propagam erro de Redis."""

    class _BrokenBus:
        @property
        def client(self) -> object:
            raise ConnectionError("redis unreachable")

    monkeypatch.setattr("app.services.redis_bus.get_bus", lambda: _BrokenBus())

    # Nao levanta — fail-open nos dois sentidos.
    await cartorio_agent._circuit_failure("MiniMax_direct")
    await cartorio_agent._circuit_success("MiniMax_direct")
    assert await cartorio_agent._circuit_skip("MiniMax_direct") is False


async def test_timeout_global_incrementa_timeout_e_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E2.02 S3: teto global estourado -> status=timeout E reason=timeout."""

    async def _stuck(system: str, user: str) -> tuple[str, str, str | None, list[str]]:
        await asyncio.sleep(30)
        return "nunca", "none", None, []

    metrics = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", metrics)
    monkeypatch.setattr(cartorio_agent, "_llm_agent_with_tools", _stuck)
    monkeypatch.setattr(cartorio_agent, "LLM_GLOBAL_TIMEOUT_S", 0.2)

    reply = await cartorio_agent.run_cartorio_agent("oi")

    assert reply.text.startswith("Nosso sistema de inteligência artificial está com lentidão")
    assert (
        metrics.counters["cartorio_llm_calls_total"][
            "model=multi_provider|operation=chat|status=timeout"
        ]
        == 1
    )
    assert metrics.counters["cartorio_llm_degraded_total"]["reason=timeout"] == 1


async def test_all_providers_down_degraded_counter_e_saida_sem_cpf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E2.02 S3: degraded reply NUNCA silencia, NUNCA vaza CPF, e e contada."""

    async def _empty_tools(system: str, user: str) -> tuple[str, str, str | None, list[str]]:
        return "", "none", None, []

    async def _empty_fb(system: str, user: str) -> tuple[str, str]:
        return "", "none"

    metrics = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", metrics)
    monkeypatch.setattr(cartorio_agent, "_llm_agent_with_tools", _empty_tools)
    monkeypatch.setattr(cartorio_agent, "_llm_minimax", _empty_fb)

    reply = await cartorio_agent.run_cartorio_agent(
        "meu cpf e 529.982.247-25, preciso de procuracao"
    )

    assert reply.text  # silencio nunca e resposta
    assert "529.982.247-25" not in reply.text  # final scrub defense
    assert metrics.counters["cartorio_llm_degraded_total"]["reason=all_providers_down"] == 1


async def test_erro_httpx_grava_error_type_canonico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """type(exc).__name__ cru NUNCA vira label: _classify_error -> whitelist."""
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "mm-key")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_MODEL", "MiniMax-M3")

    metrics = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", metrics)

    async def _no_skip(provider: str) -> bool:
        return False

    async def _noop(provider: str) -> None:
        return None

    monkeypatch.setattr(cartorio_agent, "_circuit_skip", _no_skip)
    monkeypatch.setattr(cartorio_agent, "_circuit_failure", _noop)
    monkeypatch.setattr(cartorio_agent, "_circuit_success", _noop)

    with respx.mock:
        respx.post("https://minimax.example/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("boom")
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
        )

    assert msg is None
    assert provider == "none"
    assert "ConnectError" in err  # log/erro local pode ter detalhe
    errors = metrics.counters["cartorio_llm_errors_total"]
    # label e canonico: ConnectError nao esta na whitelist -> UnknownError
    assert errors["error_type=UnknownError|model=MiniMax_direct|operation=chat"] == 1
    assert all("ConnectError" not in key for key in errors)


def test_scrub_bad_llm_phrases_suppresses_provider_403_and_rate_limit_errors() -> None:
    """Verifica que mensagens brutas de erro de 403/rate limit de provedor sao suprimidas."""
    raw_403 = (
        "HTTP 403: You've reached your usage limit for this billing cycle. "
        "Your quota will be refreshed in the next cycle. "
        "To continue now, purchase extra usage or upgrade your plan: kimi.com"
    )
    raw_rate_limit = "The model provider is rate-limiting requests. Please wait a moment and try again."

    assert cartorio_agent._scrub_bad_llm_phrases(raw_403) == ""
    assert cartorio_agent._scrub_bad_llm_phrases(raw_rate_limit) == ""


async def test_chat_completion_treats_403_as_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Status HTTP 403 e 429 marcam provider_rate_limited e retornam resposta amigavel."""
    monkeypatch.setattr(cartorio_agent, "MINIMAX_API_KEY", "mm-key")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_BASE_URL", "https://minimax.example/v1")
    monkeypatch.setattr(cartorio_agent, "MINIMAX_MODEL", "MiniMax-M3")

    async def _no_skip(provider: str) -> bool:
        return False

    async def _noop(provider: str) -> None:
        return None

    monkeypatch.setattr(cartorio_agent, "_circuit_skip", _no_skip)
    monkeypatch.setattr(cartorio_agent, "_circuit_failure", _noop)

    with respx.mock:
        respx.post("https://minimax.example/v1/chat/completions").mock(
            return_value=httpx.Response(403, text="Quota Exceeded")
        )
        msg, provider, err = await cartorio_agent._chat_completion(
            [{"role": "user", "content": "oi"}],
        )

    assert msg is not None
    assert "content" in msg
    assert "atendimento inteligente atingiu o limite momentaneo" in msg["content"]
    assert provider == "offline:provider_rate_limited"

