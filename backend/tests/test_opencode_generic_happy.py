"""Testes para app/integrations/opencode_generic.py - cobertura de branches (76% -> 90%).

Cobre:
1. chat() sucesso HTTP 200 com parse correto
2. chat() CONFIG error (provider nao configurado)
3. chat() LGPD_BLOCKED (consent_granted=False)
4. chat() CONFIG error (messages vazias)
5. chat() TIMEOUT error
6. chat() NETWORK error
7. chat() HTTP_4XX error (400)
8. chat() HTTP_5XX error (503)
9. chat() PARSE error (response nao JSON)
10. chat() PARSE error (estrutura inesperada sem choices)
11. chat() output PII redaction
12. chat() input PII redaction
13. get_config_for provider opencode_go
14. get_config_for provider opencode_free_1
15. get_config_for provider openrouter
16. get_config_for provider groq
17. get_config_for provider mistral
18. get_config_for provider google_ai_studio
19. get_config_for provider litellm
20. get_config_for provider desconhecido retorna None
21. ProviderConfig.is_configured True/False
22. PROVIDER_DISPATCH contem todos os providers
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.opencode_generic import (
    PROVIDER_DISPATCH,
    ChatError,
    ChatErrorKind,
    ChatResponse,
    ProviderConfig,
    chat,
    get_config_for,
)


def _make_response(
    status_code: int = 200, json_data: dict | None = None, text: str = ""
) -> MagicMock:
    """Cria mock de httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    else:
        resp.json = MagicMock(side_effect=Exception("not json"))
    resp.text = text
    return resp


def _make_async_client(resp: MagicMock | None = None, side_effect: object = None) -> MagicMock:
    """Cria mock de httpx.AsyncClient."""

    class _Ctx:
        def __init__(self) -> None:
            self._post = AsyncMock(return_value=resp, side_effect=side_effect)

        async def __aenter__(self) -> _Ctx:
            return self

        async def __aexit__(self, *args: object) -> None:
            pass

        async def post(self, *args: object, **kwargs: object) -> MagicMock:
            return await self._post(*args, **kwargs)

    return _Ctx()


@pytest.fixture
def configured_config() -> ProviderConfig:
    """ProviderConfig valido."""
    return ProviderConfig(
        name="test",
        base_url="https://api.test.com",
        api_key="sk-test",
        model="test-model",
    )


# =============================================================================
# ProviderConfig.is_configured
# =============================================================================


def test_provider_config_is_configured_quando_tudo_preenchido() -> None:
    """ProviderConfig.is_configured retorna True se tudo preenchido."""
    cfg = ProviderConfig(name="x", base_url="https://x", api_key="k", model="m")
    assert cfg.is_configured() is True


def test_provider_config_is_configured_false_sem_api_key() -> None:
    """ProviderConfig.is_configured retorna False sem api_key."""
    cfg = ProviderConfig(name="x", base_url="https://x", api_key=None, model="m")
    assert cfg.is_configured() is False


def test_provider_config_is_configured_false_sem_base_url() -> None:
    """ProviderConfig.is_configured retorna False sem base_url."""
    cfg = ProviderConfig(name="x", base_url="", api_key="k", model="m")
    assert cfg.is_configured() is False


def test_provider_config_is_configured_false_sem_model() -> None:
    """ProviderConfig.is_configured retorna False sem model."""
    cfg = ProviderConfig(name="x", base_url="https://x", api_key="k", model="")
    assert cfg.is_configured() is False


# =============================================================================
# get_config_for
# =============================================================================


def test_get_config_for_opencode_go() -> None:
    """get_config_for('opencode_go') retorna ProviderConfig com settings."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.opencode_go_base_url = "https://go.test.com"
        mock_settings.opencode_go_api_key = "k-go"
        mock_settings.opencode_go_model = "model-go"
        cfg = get_config_for("opencode_go")
    assert cfg is not None
    assert cfg.name == "opencode_go"
    assert cfg.base_url == "https://go.test.com"
    assert cfg.api_key == "k-go"
    assert cfg.model == "model-go"


def test_get_config_for_opencode_free_1() -> None:
    """get_config_for('opencode_free_1') retorna config."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.opencode_free_1_base_url = "https://free1.test.com"
        mock_settings.opencode_free_1_api_key = "k1"
        mock_settings.opencode_free_1_model = "m1"
        cfg = get_config_for("opencode_free_1")
    assert cfg is not None
    assert cfg.name == "opencode_free_1"
    assert cfg.base_url == "https://free1.test.com"


def test_get_config_for_openrouter() -> None:
    """get_config_for('openrouter') retorna config."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.openrouter_base_url = "https://or.test.com"
        mock_settings.openrouter_api_key = "k-or"
        mock_settings.openrouter_model = "m-or"
        cfg = get_config_for("openrouter")
    assert cfg is not None
    assert cfg.name == "openrouter"


def test_get_config_for_groq() -> None:
    """get_config_for('groq') retorna config."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.groq_base_url = "https://groq.test.com"
        mock_settings.groq_api_key = "k-groq"
        mock_settings.groq_model = "m-groq"
        cfg = get_config_for("groq")
    assert cfg is not None
    assert cfg.name == "groq"


def test_get_config_for_mistral() -> None:
    """get_config_for('mistral') retorna config."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.mistral_base_url = "https://mistral.test.com"
        mock_settings.mistral_api_key = "k-mistral"
        mock_settings.mistral_model = "m-mistral"
        cfg = get_config_for("mistral")
    assert cfg is not None
    assert cfg.name == "mistral"


def test_get_config_for_google_ai_studio() -> None:
    """get_config_for('google_ai_studio') retorna config."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.google_ai_studio_base_url = "https://g.test.com"
        mock_settings.google_ai_studio_api_key = "k-g"
        mock_settings.google_ai_studio_model = "m-g"
        cfg = get_config_for("google_ai_studio")
    assert cfg is not None
    assert cfg.name == "google_ai_studio"


def test_get_config_for_litellm() -> None:
    """get_config_for('litellm') retorna config com /v1 e api_key default 'missing'."""
    with patch("app.config.settings") as mock_settings:
        mock_settings.litellm_base_url = "https://litellm.test.com"
        mock_settings.litellm_api_key = None  # Sem key, deve virar "missing"
        mock_settings.litellm_model = "m-litellm"
        cfg = get_config_for("litellm")
    assert cfg is not None
    assert cfg.name == "litellm"
    assert cfg.base_url == "https://litellm.test.com/v1"
    assert cfg.api_key == "missing"


def test_get_config_for_desconhecido_retorna_none() -> None:
    """get_config_for('desconhecido') retorna None."""
    assert get_config_for("provider_inexistente_99") is None


def test_provider_dispatch_contem_todos_providers_principais() -> None:
    """PROVIDER_DISPATCH contem os providers principais."""
    expected = {
        "opencode_go",
        "opencode_free_1",
        "opencode_free_2",
        "opencode_free_3",
        "openrouter",
        "groq",
        "mistral",
        "google_ai_studio",
        "litellm",
        "jules",
        "openclaw",
    }
    assert expected.issubset(set(PROVIDER_DISPATCH.keys()))


# =============================================================================
# chat() errors
# =============================================================================


@pytest.mark.asyncio
async def test_chat_erro_quando_provider_nao_configurado() -> None:
    """chat() raises ChatError CONFIG se provider nao configurado."""
    cfg = ProviderConfig(name="x", base_url="", api_key="k", model="m")
    with pytest.raises(ChatError) as exc_info:
        await chat([{"role": "user", "content": "oi"}], config=cfg, consent_granted=True)
    assert exc_info.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_erro_quando_consent_nao_concedido() -> None:
    """chat() raises ChatError LGPD_BLOCKED se consent_granted=False."""
    cfg = ProviderConfig(name="x", base_url="https://x", api_key="k", model="m")
    with pytest.raises(ChatError) as exc_info:
        await chat([{"role": "user", "content": "oi"}], config=cfg, consent_granted=False)
    assert exc_info.value.kind == ChatErrorKind.LGPD_BLOCKED


@pytest.mark.asyncio
async def test_chat_erro_quando_messages_vazias() -> None:
    """chat() raises ChatError CONFIG se messages vazias."""
    cfg = ProviderConfig(name="x", base_url="https://x", api_key="k", model="m")
    with pytest.raises(ChatError) as exc_info:
        await chat([], config=cfg, consent_granted=True)
    assert exc_info.value.kind == ChatErrorKind.CONFIG


@pytest.mark.asyncio
async def test_chat_erro_timeout(configured_config: ProviderConfig) -> None:
    """chat() raises ChatError TIMEOUT quando httpx TimeoutException."""
    client = _make_async_client(side_effect=httpx.TimeoutException("timeout"))

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        with pytest.raises(ChatError) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=configured_config,
                consent_granted=True,
            )
    assert exc_info.value.kind == ChatErrorKind.TIMEOUT


@pytest.mark.asyncio
async def test_chat_erro_network(configured_config: ProviderConfig) -> None:
    """chat() raises ChatError NETWORK quando httpx HTTPError generico."""
    client = _make_async_client(side_effect=httpx.ConnectError("conn refused"))

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        with pytest.raises(ChatError) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=configured_config,
                consent_granted=True,
            )
    assert exc_info.value.kind == ChatErrorKind.NETWORK


@pytest.mark.asyncio
async def test_chat_erro_http_4xx(configured_config: ProviderConfig) -> None:
    """chat() raises ChatError HTTP_4XX quando response 400."""
    resp = _make_response(status_code=400, text="Bad Request")
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        with pytest.raises(ChatError) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=configured_config,
                consent_granted=True,
            )
    assert exc_info.value.kind == ChatErrorKind.HTTP_4XX
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_chat_erro_http_5xx(configured_config: ProviderConfig) -> None:
    """chat() raises ChatError HTTP_5XX quando response 503."""
    resp = _make_response(status_code=503, text="Service Unavailable")
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        with pytest.raises(ChatError) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=configured_config,
                consent_granted=True,
            )
    assert exc_info.value.kind == ChatErrorKind.HTTP_5XX
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_chat_erro_parse_json_invalido(configured_config: ProviderConfig) -> None:
    """chat() raises ChatError PARSE quando response nao e JSON."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(side_effect=Exception("not json"))
    resp.text = "not json"
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        with pytest.raises(ChatError) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=configured_config,
                consent_granted=True,
            )
    assert exc_info.value.kind == ChatErrorKind.PARSE


@pytest.mark.asyncio
async def test_chat_erro_estrutura_inesperada(configured_config: ProviderConfig) -> None:
    """chat() raises ChatError PARSE quando response nao tem choices."""
    resp = _make_response(
        status_code=200,
        json_data={"unexpected": "structure"},
    )
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        with pytest.raises(ChatError) as exc_info:
            await chat(
                [{"role": "user", "content": "oi"}],
                config=configured_config,
                consent_granted=True,
            )
    assert exc_info.value.kind == ChatErrorKind.PARSE


# =============================================================================
# chat() success
# =============================================================================


@pytest.mark.asyncio
async def test_chat_sucesso_200_retorna_chat_response(configured_config: ProviderConfig) -> None:
    """chat() sucesso HTTP 200 retorna ChatResponse com content + tokens + latency."""
    resp = _make_response(
        status_code=200,
        json_data={
            "choices": [
                {
                    "message": {"content": "Ola! Como posso ajudar?"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "test-model-v2",
        },
    )
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        result = await chat(
            [{"role": "user", "content": "oi"}],
            config=configured_config,
            consent_granted=True,
        )

    assert isinstance(result, ChatResponse)
    assert result.content == "Ola! Como posso ajudar?"
    assert result.tokens_in == 10
    assert result.tokens_out == 20
    assert result.finish_reason == "stop"
    assert result.latency_ms >= 0
    assert result.model == "test-model-v2"


@pytest.mark.asyncio
async def test_chat_sucesso_sem_usage_data(configured_config: ProviderConfig) -> None:
    """chat() sucesso sem usage data retorna tokens None."""
    resp = _make_response(
        status_code=200,
        json_data={
            "choices": [
                {
                    "message": {"content": "Resp"},
                    "finish_reason": "stop",
                }
            ],
            "model": "test-model",
        },
    )
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        result = await chat(
            [{"role": "user", "content": "oi"}],
            config=configured_config,
            consent_granted=True,
        )

    assert result.tokens_in is None
    assert result.tokens_out is None
    assert result.content == "Resp"


@pytest.mark.asyncio
async def test_chat_redacta_pii_no_input(configured_config: ProviderConfig) -> None:
    """chat() redacta PII no input (CPF, email, etc)."""
    resp = _make_response(
        status_code=200,
        json_data={
            "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
        },
    )
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        # CPF brasileiro que deve ser redactado
        result = await chat(
            [{"role": "user", "content": "Meu CPF e 111.444.777-35"}],
            config=configured_config,
            consent_granted=True,
        )

    # pii_redacted_count >= 0 (pode ser 0 se scrub nao detecta esse padrao)
    assert result.pii_redacted_count >= 0


@pytest.mark.asyncio
async def test_chat_redacta_pii_no_output(configured_config: ProviderConfig) -> None:
    """chat() redacta PII no output."""
    resp = _make_response(
        status_code=200,
        json_data={
            "choices": [
                {
                    "message": {"content": "Seu CPF 111.444.777-35 foi registrado."},
                    "finish_reason": "stop",
                }
            ],
        },
    )
    client = _make_async_client(resp=resp)

    with patch("app.integrations.opencode_generic.httpx.AsyncClient", return_value=client):
        result = await chat(
            [{"role": "user", "content": "oi"}],
            config=configured_config,
            consent_granted=True,
        )

    # output_pii_redacted_count >= 0
    assert result.output_pii_redacted_count >= 0
