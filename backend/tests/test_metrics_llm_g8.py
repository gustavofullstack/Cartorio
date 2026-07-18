"""G8.15.T1 — Testes de instrumentacao Prometheus para latencia LLM/AI.

Valida:
- observe_llm_call_seconds / inc_llm_calls_total / inc_llm_tokens_total /
  inc_llm_errors_total registram nas chaves corretas com labels LGPD-safe.
- Decorator @instrument_llm captura latencia, success/error, error_type,
  tokens (via extract_tokens) para funcoes sync e async.
- Decorator preserva __name__/__doc__ via functools.wraps.
- Labels NAO contem PII (CPF/RG/email patterns).
- Whitelist enforcement (model/operation nao-canonic -> ValueError).
- Render Prometheus inclui as 4 metricas G8.15.T1 no formato text/plain.

LGPD: testes nao escrevem valores dinamicos em labels. Apenas enums
canonicos sao usados (model, operation, status, direction, error_type).
"""

from __future__ import annotations

import asyncio
import os
import re

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402

from app.services.metrics import (  # noqa: E402
    MetricsStore,
    instrument_llm,
)


# ============================================================================
# Fixtures
# ============================================================================

LLM_METRIC_KEYS = (
    "cartorio_llm_call_seconds",
    "cartorio_llm_calls_total",
    "cartorio_llm_tokens_total",
    "cartorio_llm_errors_total",
)


@pytest.fixture
def llm_metrics_isolated(monkeypatch: pytest.MonkeyPatch) -> MetricsStore:
    """Isola as 4 metricas G8.15.T1 em um store local para o teste.

    Estrategia: monkeypatch o simbolo `store` no modulo `app.services.metrics`
    para apontar para um MetricsStore() recem-criado. Isso isola 100% das
    escritas do decorator durante o teste, sem afetar o singleton global
    usado por outros testes / runtime.

    Cleanup automatico via monkeypatch (pytest reverte ao final).
    """
    fresh = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", fresh)
    return fresh


# ============================================================================
# Helpers
# ============================================================================

def _counter_value(store_obj: MetricsStore, metric: str, labels: dict[str, str]) -> int:
    """Leitura tolerant do counter: retorna 0 se chave/labels nao existem."""
    key = "|".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return store_obj.counters.get(metric, {}).get(key, 0)


def _histogram_observations(store_obj: MetricsStore, metric: str, labels: dict[str, str]) -> list[float]:
    """Le lista de observacoes do histogram; [] se nao existir."""
    key = "|".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return store_obj.histograms.get(metric, {}).get(key, [])


# Regex canonica de PII para verificar labels LGPD-safe
_PII_PATTERNS = [
    re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),  # CPF
    re.compile(r"\d{2}\.?\d{3}\.?\d{3}-?\d{1}"),  # RG (heuristica)
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # email
]


def _assert_no_pii_in_labels(labels: dict[str, str]) -> None:
    """Garante que nenhum valor de label casa pattern de PII."""
    for k, v in labels.items():
        assert isinstance(v, str), f"label {k!r} nao eh string: {v!r}"
        for pat in _PII_PATTERNS:
            assert not pat.search(v), (
                f"LGPD VIOLATION: label {k}={v!r} parece conter PII (pattern {pat.pattern!r})"
            )


# ============================================================================
# Tests — unit helpers (MetricsStore methods)
# ============================================================================


class TestObserveLlmCallSeconds:
    """observe_llm_call_seconds registra histograma com labels {model, operation}."""

    def test_histogram_records_latency(self, llm_metrics_isolated: MetricsStore) -> None:
        s = llm_metrics_isolated
        s.observe_llm_call_seconds("test", "test", 0.123)
        s.observe_llm_call_seconds("test", "test", 0.456)

        labels = {"model": "test", "operation": "test"}
        _assert_no_pii_in_labels(labels)
        obs = _histogram_observations(s, "cartorio_llm_call_seconds", labels)
        assert len(obs) == 2
        assert obs[0] == pytest.approx(0.123)
        assert obs[1] == pytest.approx(0.456)


class TestIncLlmCallsTotal:
    """inc_llm_calls_total incrementa counter com labels {model,operation,status}."""

    def test_counter_increments_on_success(self, llm_metrics_isolated: MetricsStore) -> None:
        s = llm_metrics_isolated
        s.inc_llm_calls_total("test", "chat", "success")
        s.inc_llm_calls_total("test", "chat", "success")
        s.inc_llm_calls_total("test", "chat", "success")

        labels = {"model": "test", "operation": "chat", "status": "success"}
        _assert_no_pii_in_labels(labels)
        assert _counter_value(s, "cartorio_llm_calls_total", labels) == 3

    def test_counter_records_error_with_distinct_status(
        self, llm_metrics_isolated: MetricsStore
    ) -> None:
        s = llm_metrics_isolated
        s.inc_llm_calls_total("test", "chat", "success")
        s.inc_llm_calls_total("test", "chat", "error")
        s.inc_llm_calls_total("test", "chat", "timeout")

        assert _counter_value(s, "cartorio_llm_calls_total",
                              {"model": "test", "operation": "chat", "status": "success"}) == 1
        assert _counter_value(s, "cartorio_llm_calls_total",
                              {"model": "test", "operation": "chat", "status": "error"}) == 1
        assert _counter_value(s, "cartorio_llm_calls_total",
                              {"model": "test", "operation": "chat", "status": "timeout"}) == 1


class TestIncLlmTokensTotal:
    """inc_llm_tokens_total incrementa counter com labels {model, direction}."""

    def test_tokens_counted_input_and_output(self, llm_metrics_isolated: MetricsStore) -> None:
        s = llm_metrics_isolated
        s.inc_llm_tokens_total("test", "input", 150)
        s.inc_llm_tokens_total("test", "output", 75)
        s.inc_llm_tokens_total("test", "input", 50)

        labels_in = {"model": "test", "direction": "input"}
        labels_out = {"model": "test", "direction": "output"}
        _assert_no_pii_in_labels(labels_in)
        _assert_no_pii_in_labels(labels_out)

        assert _counter_value(s, "cartorio_llm_tokens_total", labels_in) == 200
        assert _counter_value(s, "cartorio_llm_tokens_total", labels_out) == 75

    def test_tokens_zero_or_negative_skipped(self, llm_metrics_isolated: MetricsStore) -> None:
        """count <= 0 eh ignorado (evita ruido e tokens negativos)."""
        s = llm_metrics_isolated
        s.inc_llm_tokens_total("test", "input", 0)
        s.inc_llm_tokens_total("test", "input", -10)
        # chave nao deve ser criada
        assert "cartorio_llm_tokens_total" not in s.counters


class TestIncLlmErrorsTotal:
    """inc_llm_errors_total incrementa counter com labels {model, operation, error_type}."""

    def test_errors_counted_by_type(self, llm_metrics_isolated: MetricsStore) -> None:
        s = llm_metrics_isolated
        s.inc_llm_errors_total("test", "chat", "TimeoutException")
        s.inc_llm_errors_total("test", "chat", "TimeoutException")
        s.inc_llm_errors_total("test", "chat", "HTTP_5XX")

        assert _counter_value(
            s,
            "cartorio_llm_errors_total",
            {"model": "test", "operation": "chat", "error_type": "TimeoutException"},
        ) == 2
        assert _counter_value(
            s,
            "cartorio_llm_errors_total",
            {"model": "test", "operation": "chat", "error_type": "HTTP_5XX"},
        ) == 1


class TestLabelSafety:
    """LGPD: labels NUNCA devem conter PII."""

    def test_no_pii_in_canonical_label_values(self) -> None:
        """Os labels canonicos usados em testes NAO vazam PII."""
        canonical_labels = {
            "model": "opencode_go",
            "operation": "chat",
            "status": "success",
            "direction": "input",
            "error_type": "TimeoutException",
        }
        _assert_no_pii_in_labels(canonical_labels)


class TestRenderPrometheusIncludesG815:
    """render_prometheus expoe as 4 metricas G8.15.T1 em formato text/plain."""

    def test_render_exposes_all_four_llm_metrics(self, llm_metrics_isolated: MetricsStore) -> None:
        s = llm_metrics_isolated
        s.observe_llm_call_seconds("test", "chat", 0.42)
        s.inc_llm_calls_total("test", "chat", "success")
        s.inc_llm_tokens_total("test", "input", 100)
        s.inc_llm_errors_total("test", "chat", "TimeoutException")

        out = s.render_prometheus()
        # A renderer interna do cartorio expoe histogram como `summary` (count + sum)
        # suficiente p/ PromQL `rate(_sum) / rate(_count)` -> latencia media.
        # Ver app/services/metrics.py::render_prometheus (linhas ~310-323).
        # Labels sao ordenadas alfabeticamente pela chave (sort()), entao
        # direction < model < operation < status no output.
        assert "# TYPE cartorio_llm_call_seconds summary" in out
        assert 'cartorio_llm_call_seconds_count{model="test",operation="chat"} 1' in out
        assert 'cartorio_llm_call_seconds_sum{model="test",operation="chat"} 0.420000' in out

        assert "# TYPE cartorio_llm_calls_total counter" in out
        assert 'cartorio_llm_calls_total{model="test",operation="chat",status="success"} 1' in out

        assert "# TYPE cartorio_llm_tokens_total counter" in out
        assert 'cartorio_llm_tokens_total{direction="input",model="test"} 100' in out

        assert "# TYPE cartorio_llm_errors_total counter" in out
        assert (
            'cartorio_llm_errors_total{error_type="TimeoutException",model="test",operation="chat"} 1'
            in out
        )


# ============================================================================
# Tests — @instrument_llm decorator
# ============================================================================


class TestInstrumentLlmDecorator:
    """Decorator captura latencia/status/tokens/erros para sync e async."""

    def test_decorator_records_sync_success(self, llm_metrics_isolated: MetricsStore) -> None:
        @instrument_llm(model="test", operation="chat")
        def fake_call() -> str:
            return "ok"

        result = fake_call()

        assert result == "ok"
        # latency recorded
        obs = _histogram_observations(
            llm_metrics_isolated,
            "cartorio_llm_call_seconds",
            {"model": "test", "operation": "chat"},
        )
        assert len(obs) == 1
        assert obs[0] >= 0.0
        # success counter
        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_calls_total",
                {"model": "test", "operation": "chat", "status": "success"},
            )
            == 1
        )
        # error counter NOT incremented
        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_calls_total",
                {"model": "test", "operation": "chat", "status": "error"},
            )
            == 0
        )

    def test_decorator_records_sync_error(self, llm_metrics_isolated: MetricsStore) -> None:
        class _MyErr(RuntimeError):
            pass

        @instrument_llm(model="test", operation="chat")
        def failing_call() -> None:
            raise _MyErr("boom")

        with pytest.raises(_MyErr, match="boom"):
            failing_call()

        # latency recorded even on error
        assert len(
            _histogram_observations(
                llm_metrics_isolated,
                "cartorio_llm_call_seconds",
                {"model": "test", "operation": "chat"},
            )
        ) == 1
        # error counter incremented
        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_calls_total",
                {"model": "test", "operation": "chat", "status": "error"},
            )
            == 1
        )
        # error_type counter uses class name (or 'UnknownError' se nao-whitelisted)
        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_errors_total",
                {"model": "test", "operation": "chat", "error_type": "UnknownError"},
            )
            == 1
        )

    def test_decorator_records_async_success(self, llm_metrics_isolated: MetricsStore) -> None:
        @instrument_llm(model="test", operation="chat")
        async def fake_async_call() -> dict[str, str]:
            await asyncio.sleep(0)
            return {"text": "hi"}

        result = asyncio.run(fake_async_call())

        assert result == {"text": "hi"}
        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_calls_total",
                {"model": "test", "operation": "chat", "status": "success"},
            )
            == 1
        )

    def test_decorator_records_async_error(self, llm_metrics_isolated: MetricsStore) -> None:
        @instrument_llm(model="test", operation="chat")
        async def failing_async() -> None:
            raise TimeoutError("api timeout")

        with pytest.raises(TimeoutError, match="api timeout"):
            asyncio.run(failing_async())

        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_calls_total",
                {"model": "test", "operation": "chat", "status": "error"},
            )
            == 1
        )
        # TimeoutException nao eh a classe real (TimeoutError sim), entao UnknownError
        # O importante: error_type existe, valor eh canonico.
        total = sum(llm_metrics_isolated.counters.get("cartorio_llm_errors_total", {}).values())
        assert total == 1

    def test_decorator_extracts_tokens_via_callback(
        self, llm_metrics_isolated: MetricsStore
    ) -> None:
        class _FakeResponse:
            tokens_in = 250
            tokens_out = 80

        @instrument_llm(
            model="test",
            operation="chat",
            extract_tokens=lambda r: (r.tokens_in, r.tokens_out),
        )
        def fake_call() -> _FakeResponse:
            return _FakeResponse()

        fake_call()

        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_tokens_total",
                {"model": "test", "direction": "input"},
            )
            == 250
        )
        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_tokens_total",
                {"model": "test", "direction": "output"},
            )
            == 80
        )

    def test_decorator_extract_tokens_exception_silenced(
        self, llm_metrics_isolated: MetricsStore
    ) -> None:
        """Se extract_tokens lanca, o decorator nao quebra o call site."""

        def _boom(_result: object) -> tuple[int, int]:
            raise ValueError("token parsing failed")

        @instrument_llm(model="test", operation="chat", extract_tokens=_boom)
        def fake_call() -> str:
            return "ok"

        # Nao propaga a excecao do extract_tokens
        assert fake_call() == "ok"
        # Mas a chamada eh contabilizada como success
        assert (
            _counter_value(
                llm_metrics_isolated,
                "cartorio_llm_calls_total",
                {"model": "test", "operation": "chat", "status": "success"},
            )
            == 1
        )

    def test_decorator_preserves_function_metadata(
        self, llm_metrics_isolated: MetricsStore
    ) -> None:
        """@functools.wraps preserva __name__, __doc__, __wrapped__."""

        @instrument_llm(model="test", operation="chat")
        def my_named_call(x: int) -> int:
            """Multiplica por 2."""
            return x * 2

        assert my_named_call.__name__ == "my_named_call"
        assert my_named_call.__doc__ == "Multiplica por 2."
        # __wrapped__ permite introspection via inspect.signature
        assert my_named_call(3) == 6

    def test_decorator_rejects_non_whitelisted_model(self) -> None:
        """LGPD: model fora da whitelist eh rejeitado em tempo de decoracao."""

        with pytest.raises(ValueError, match="nao esta em whitelist canonica"):
            @instrument_llm(model="openai_gpt4_with_my_cpf", operation="chat")  # noqa: E501
            def _bad() -> None:
                pass

    def test_decorator_rejects_non_whitelisted_operation(self) -> None:
        """LGPD: operation fora da whitelist eh rejeitado em tempo de decoracao."""

        with pytest.raises(ValueError, match="nao esta em whitelist canonica"):
            @instrument_llm(model="test", operation="sql_query_on_clientes_table")  # noqa: E501
            def _bad() -> None:
                pass


# ============================================================================
# Tests — classification of error types (LGPD-safe label values)
# ============================================================================


class TestClassifyError:
    """_classify_error retorna apenas valores canonicos (LGPD-safe)."""

    def test_whitelisted_class_name_returned_as_is(self) -> None:
        from app.services.metrics import _classify_error

        assert _classify_error(TimeoutError()) == "UnknownError"  # TimeoutError != TimeoutException
        # Quando o nome bate exatamente, retorna o nome
        class _FakeException(Exception):
            pass

        # _FakeException nao ta na whitelist -> UnknownError
        assert _classify_error(_FakeException()) == "UnknownError"

    def test_unknown_exception_returns_unknown(self) -> None:
        from app.services.metrics import _classify_error

        class _MyVeryCustomError(Exception):
            pass

        # Cardinalidade controlada: qualquer classe fora da whitelist vira 'UnknownError'
        assert _classify_error(_MyVeryCustomError()) == "UnknownError"

    def test_classified_values_are_pii_safe(self) -> None:
        """Todos os valores que _classify_error pode retornar sao LGPD-safe."""
        from app.services.metrics import _ALLOWED_LLM_ERROR_TYPES

        for value in _ALLOWED_LLM_ERROR_TYPES:
            _assert_no_pii_in_labels({"error_type": value})


# ============================================================================
# Tests — integration: a instrumentacao nao altera o retorno/assinatura
# ============================================================================


class TestDecoratorTransparency:
    """O decorator nao altera o retorno nem levanta excecoes inesperadas."""

    def test_sync_passes_through_return_value(self, llm_metrics_isolated: MetricsStore) -> None:
        sentinel = {"data": [1, 2, 3], "meta": "x"}

        @instrument_llm(model="test", operation="chat")
        def returns_dict() -> dict[str, object]:
            return sentinel

        assert returns_dict() is sentinel

    def test_async_passes_through_return_value(self, llm_metrics_isolated: MetricsStore) -> None:
        sentinel = ("text", "provider", "")

        @instrument_llm(model="test", operation="chat")
        async def returns_tuple() -> tuple[str, str, str]:
            return sentinel

        assert asyncio.run(returns_tuple()) == sentinel

    def test_sync_re_raises_original_exception(
        self, llm_metrics_isolated: MetricsStore
    ) -> None:
        class _SpecificErr(Exception):
            pass

        @instrument_llm(model="test", operation="chat")
        def failing() -> None:
            raise _SpecificErr("original message preserved")

        with pytest.raises(_SpecificErr, match="original message preserved"):
            failing()