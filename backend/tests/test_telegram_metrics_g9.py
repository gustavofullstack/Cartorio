"""G9.S2 (E3.07) — metricas do pipeline Telegram: emissao + labels LGPD.

Cobre:
- T3: contadores `telegram_webhook_total{result=200|401|5xx}`,
  `telegram_debounce_scheduled_total`, `telegram_response_sent_total`.
- T4: histograma `telegram_webhook_response_seconds` (latencia webhook ->
  resposta, INCLUINDO a janela de debounce de 1.2s).
- T5: gate LGPD — chat_id/username/user_id NUNCA viram label; teste FALHA
  se label proibida aparecer no render ou se valor dinamico/PII vazar.

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import json
import os
import re
import time
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi import BackgroundTasks, HTTPException  # noqa: E402

import app.api.v1.telegram as tg  # noqa: E402
from app.services.metrics import MetricsStore  # noqa: E402


# ============================================================================
# Fixtures / fakes (mesmo padrao de test_telegram_regressions_g9.py)
# ============================================================================


@pytest.fixture
def store_isolado(monkeypatch: pytest.MonkeyPatch) -> MetricsStore:
    fresh = MetricsStore()
    monkeypatch.setattr("app.services.metrics.store", fresh)
    return fresh


@pytest.fixture(autouse=True)
def _clean_latency_marks():
    tg._RESPONSE_LATENCY_START.clear()
    yield
    tg._RESPONSE_LATENCY_START.clear()


class _FakePipeline:
    def __init__(self, bus: _FakeBus) -> None:
        self._bus = bus
        self._ops: list[tuple[str, str]] = []

    async def __aenter__(self) -> _FakePipeline:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def get(self, key: str) -> None:
        self._ops.append(("get", key))

    async def delete(self, key: str) -> None:
        self._ops.append(("del", key))

    async def execute(self) -> list:
        out: list = []
        for op, key in self._ops:
            if op == "get":
                out.append(self._bus.store.get(key))
            else:
                out.append(1 if self._bus.store.pop(key, None) is not None else 0)
        return out


class _FakeBus:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.client = self

    async def set(
        self, key: str, value: str, *, ex: int | None = None, nx: bool = False
    ) -> str | None:
        if nx and key in self.store:
            return None
        self.store[key] = value
        return "OK"

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    def pipeline(self, transaction: bool = True) -> _FakePipeline:
        return _FakePipeline(self)


def _make_request(payload: dict) -> MagicMock:
    req = MagicMock()
    req.json = AsyncMock(return_value=payload)
    return req


def _private_text_update(update_id: int, text: str, chat_id: int = 4242) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "from": {"id": chat_id, "first_name": "Maria"},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
            "date": 1721308800,
        },
    }


def _counter(s: MetricsStore, metric: str, labels: dict[str, str] | None = None) -> int:
    key = "|".join(f"{k}={v}" for k, v in sorted((labels or {}).items()))
    return s.counters.get(metric, {}).get(key, 0)


def _observations(s: MetricsStore, metric: str) -> list[float]:
    return s.histograms.get(metric, {}).get("", [])


def _pool_ok() -> MagicMock:
    pool = MagicMock()
    pool.post = AsyncMock(return_value=MagicMock(status_code=200))
    return pool


# ============================================================================
# Cold-start (Grafana no-data guard)
# ============================================================================


def test_cold_start_series_telegram_existem_zeradas() -> None:
    s = MetricsStore()
    for result in ("200", "401", "5xx"):
        assert _counter(s, "telegram_webhook_total", {"result": result}) == 0
    assert _counter(s, "telegram_debounce_scheduled_total") == 0
    assert _counter(s, "telegram_response_sent_total") == 0


# ============================================================================
# T3 — telegram_webhook_total{result}
# ============================================================================


@pytest.mark.asyncio
async def test_webhook_200_contabiliza_result(store_isolado: MetricsStore) -> None:
    """Webhook processado (Redis down -> fallback sincrono degraded) -> 200."""
    update = _private_text_update(7001, "quanto custa uma procuracao?")
    with (
        patch.object(tg, "get_bus", side_effect=ConnectionError("redis down")),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Resposta", None))),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)),
    ):
        resp = await tg.telegram_webhook(
            _make_request(update), BackgroundTasks(), None, MagicMock()
        )
    assert resp["status"] == "ok"  # comportamento preservado
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "200"}) == 1
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "401"}) == 0
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "5xx"}) == 0


@pytest.mark.asyncio
async def test_webhook_401_contabiliza_result_e_auth_failure(
    store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Secret configurado + token errado/ausente -> 401 + auth failure."""
    monkeypatch.setattr(tg, "TELEGRAM_WEBHOOK_SECRET", "segredo-teste")
    update = _private_text_update(7002, "oi")
    for header in (None, "token-errado"):
        with pytest.raises(HTTPException) as exc:
            await tg.telegram_webhook(_make_request(update), BackgroundTasks(), header, MagicMock())
        assert exc.value.status_code == 401
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "401"}) == 2
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "200"}) == 0
    assert (
        _counter(store_isolado, "cartorio_webhook_auth_failures_total", {"channel": "telegram"})
        == 2
    )
    # Com o token certo: passa e contabiliza 200 (Redis fora -> degraded ok)
    with (
        patch.object(tg, "get_bus", side_effect=ConnectionError("redis down")),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Resposta", None))),
        patch.object(tg, "_send_message", new=AsyncMock(return_value=True)),
    ):
        resp = await tg.telegram_webhook(
            _make_request(update), BackgroundTasks(), "segredo-teste", MagicMock()
        )
    assert resp["status"] == "ok"
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "200"}) == 1


@pytest.mark.asyncio
async def test_webhook_5xx_contabiliza_result_e_preserva_excecao(
    store_isolado: MetricsStore,
) -> None:
    """Excecao nao tratada no handler -> result=5xx E a excecao propaga
    (comportamento preservado: FastAPI devolve 500)."""
    update = _private_text_update(7003, "oi")
    with (
        patch.object(tg, "_telegram_webhook_impl", new=AsyncMock(side_effect=RuntimeError("boom"))),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await tg.telegram_webhook(_make_request(update), BackgroundTasks(), None, MagicMock())
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "5xx"}) == 1
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "200"}) == 0


@pytest.mark.asyncio
async def test_webhook_invalid_json_conta_200_nao_5xx(store_isolado: MetricsStore) -> None:
    """JSON invalido vira 200 degraded (regra: SEMPRE 200) — nunca 5xx."""
    req = MagicMock()
    req.json = AsyncMock(side_effect=json.JSONDecodeError("Expecting value", "doc", 0))
    resp = await tg.telegram_webhook(req, BackgroundTasks(), None, MagicMock())
    assert resp["status"] == "degraded"
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "200"}) == 1
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "5xx"}) == 0


# ============================================================================
# T3 — telegram_debounce_scheduled_total
# ============================================================================


@pytest.mark.asyncio
async def test_debounce_agendado_contabiliza(store_isolado: MetricsStore) -> None:
    bus = _FakeBus()
    update = _private_text_update(7004, "quero agendar uma escritura")
    bt = BackgroundTasks()
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch("app.api.v1.telegram._get_lgpd_consent", new_callable=AsyncMock, return_value=True),
    ):
        resp = await tg.telegram_webhook(_make_request(update), bt, None, MagicMock())
    assert resp["scheduled"] is True
    assert len(bt.tasks) == 1
    assert _counter(store_isolado, "telegram_debounce_scheduled_total") == 1
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "200"}) == 1


@pytest.mark.asyncio
async def test_segunda_msg_na_janela_nao_agenda_novo_debounce(
    store_isolado: MetricsStore,
) -> None:
    """Lock presente -> acumula na fila SEM novo agendamento (1 por janela)."""
    bus = _FakeBus()
    bus.store["tg:lock:4242"] = "1"  # janela ja aberta
    update = _private_text_update(7005, "mais uma mensagem na mesma janela")
    bt = BackgroundTasks()
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch("app.api.v1.telegram._get_lgpd_consent", new_callable=AsyncMock, return_value=True),
    ):
        resp = await tg.telegram_webhook(_make_request(update), bt, None, MagicMock())
    assert resp["accumulated"] is True
    assert _counter(store_isolado, "telegram_debounce_scheduled_total") == 0


# ============================================================================
# T3/T4 — telegram_response_sent_total + telegram_webhook_response_seconds
# ============================================================================


@pytest.mark.asyncio
async def test_send_message_sucesso_conta_response_sent_e_latencia(
    store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tg, "_get_tg_pool", _pool_ok)
    tg._mark_response_start(4242)
    ok = await tg._send_message(4242, "Resposta de teste")
    assert ok is True
    assert _counter(store_isolado, "telegram_response_sent_total") == 1
    obs = _observations(store_isolado, "telegram_webhook_response_seconds")
    assert len(obs) == 1
    assert 0.0 <= obs[0] < 5.0  # caminho sincrono e rapido
    # Marca consumida: segundo envio sem marca nao observa latencia
    assert 4242 not in tg._RESPONSE_LATENCY_START


@pytest.mark.asyncio
async def test_latencia_inclui_janela_debounce_1_2s(
    store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inicio na 1a msg da janela -> observacao cobre o debounce de 1.2s."""
    monkeypatch.setattr(tg, "_get_tg_pool", _pool_ok)
    tg._RESPONSE_LATENCY_START[4242] = time.monotonic() - 1.2  # janela decorrida
    ok = await tg._send_message(4242, "Resposta consolidada do debounce")
    assert ok is True
    obs = _observations(store_isolado, "telegram_webhook_response_seconds")
    assert len(obs) == 1
    assert obs[0] >= 1.2


@pytest.mark.asyncio
async def test_primeira_msg_da_janela_vence_setdefault() -> None:
    tg._mark_response_start(4242)
    primeiro = tg._RESPONSE_LATENCY_START[4242]
    tg._mark_response_start(4242)  # 2a msg na mesma janela NAO sobrescreve
    assert tg._RESPONSE_LATENCY_START[4242] == primeiro


@pytest.mark.asyncio
async def test_send_message_falha_nao_conta_response_sent_mas_preserva_marca(
    store_isolado: MetricsStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falha no envio: sem response_sent, marca PRESERVADA — uma resposta de
    fallback tardia ainda fecha a janela (latencia percebida pelo usuario)."""
    pool_500 = MagicMock()
    resp_500 = MagicMock(status_code=500)
    resp_500.json.return_value = {}
    resp_500.text = "internal error"
    pool_500.post = AsyncMock(return_value=resp_500)
    monkeypatch.setattr(tg, "_get_tg_pool", lambda: pool_500)
    tg._mark_response_start(4242)
    ok = await tg._send_message(4242, "tentativa que falha")
    assert ok is False
    assert _counter(store_isolado, "telegram_response_sent_total") == 0
    assert _observations(store_isolado, "telegram_webhook_response_seconds") == []
    assert 4242 in tg._RESPONSE_LATENCY_START  # marca preservada
    # Envio de fallback tardio (ex.: msg de erro do debounce) fecha a janela
    monkeypatch.setattr(tg, "_get_tg_pool", _pool_ok)
    ok2 = await tg._send_message(4242, "resposta de fallback tardia")
    assert ok2 is True
    assert _counter(store_isolado, "telegram_response_sent_total") == 1
    assert len(_observations(store_isolado, "telegram_webhook_response_seconds")) == 1


@pytest.mark.asyncio
async def test_fluxo_webhook_debounce_e2e_emite_todas_series(
    store_isolado: MetricsStore,
) -> None:
    """Webhook (200 + schedule) -> debounce task -> send: pipeline completo."""
    bus = _FakeBus()
    update = _private_text_update(7006, "qual o valor da autenticacao?")
    bt = BackgroundTasks()
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch("app.api.v1.telegram._get_lgpd_consent", new_callable=AsyncMock, return_value=True),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Resposta", None))),
        patch.object(tg, "_get_tg_pool", return_value=_pool_ok()),
    ):
        resp = await tg.telegram_webhook(_make_request(update), bt, None, MagicMock())
        assert resp["scheduled"] is True
        for task in bt.tasks:
            await task()
    assert _counter(store_isolado, "telegram_webhook_total", {"result": "200"}) == 1
    assert _counter(store_isolado, "telegram_debounce_scheduled_total") == 1
    assert _counter(store_isolado, "telegram_response_sent_total") == 1
    assert len(_observations(store_isolado, "telegram_webhook_response_seconds")) == 1


# ============================================================================
# T5 — Gate LGPD: labels proibidas NUNCA aparecem
# ============================================================================

# Chaves de label proibidas (PII / alta cardinalidade).
FORBIDDEN_LABEL_KEYS = {
    "chat_id",
    "username",
    "user_id",
    "first_name",
    "last_name",
    "telefone",
    "phone",
    "cpf",
    "rg",
    "email",
    "protocolo",
    "token",
    "secret",
    "message_id",
    "update_id",
}

TELEGRAM_G9_SERIES = (
    "telegram_webhook_total",
    "telegram_debounce_scheduled_total",
    "telegram_response_sent_total",
    "telegram_webhook_response_seconds",
)

_PII_VALUE_PATTERNS = [
    re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),  # CPF
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # email
    re.compile(r"\b\d{10,11}\b"),  # telefone/chat_id cru
]


def test_result_fora_do_enum_coage_para_unknown(store_isolado: MetricsStore) -> None:
    """Tentativa de injetar valor dinamico (chat_id) como result -> unknown."""
    s = store_isolado
    s.inc_telegram_webhook_total("6682284055")
    s.inc_telegram_webhook_total("maria_username")
    assert _counter(s, "telegram_webhook_total", {"result": "unknown"}) == 2
    out = s.render_prometheus()
    assert "6682284055" not in out
    assert "maria_username" not in out


@pytest.mark.asyncio
async def test_gate_lgpd_render_nao_contem_pii_apos_fluxo_completo(
    store_isolado: MetricsStore,
) -> None:
    """Fluxo com payload cheio de PII: NADA vaza para as series Prometheus.

    FALHA se chat_id/username/CPF/telefone aparecer em QUALQUER linha do
    render das series G9 (label ou valor).
    """
    chat_id = 6682284055
    update = {
        "update_id": 7007,
        "message": {
            "message_id": 7007,
            "from": {
                "id": chat_id,
                "first_name": "Maria",
                "username": "maria_pii_username",
            },
            "chat": {"id": chat_id, "type": "private"},
            "text": "meu cpf 123.456.789-09 e fone 34999998888, quero agendar",
            "date": 1721308800,
        },
    }
    bus = _FakeBus()
    bt = BackgroundTasks()
    with (
        patch.object(tg, "get_bus", return_value=bus),
        patch.object(tg, "_send_typing_fast", new=AsyncMock()),
        patch.object(tg, "_react", new=AsyncMock()),
        patch.object(tg, "_client_profile_upsert", new=AsyncMock()),
        patch("app.api.v1.telegram._get_lgpd_consent", new_callable=AsyncMock, return_value=True),
        patch.object(tg, "_typing_loop", new=AsyncMock()),
        patch.object(tg, "DEBOUNCE_WINDOW", 0),
        patch.object(tg, "_call_cartorio_agent", new=AsyncMock(return_value=("Resposta", None))),
        patch.object(tg, "_get_tg_pool", return_value=_pool_ok()),
    ):
        await tg.telegram_webhook(_make_request(update), bt, None, MagicMock())
        for task in bt.tasks:
            await task()

    render = store_isolado.render_prometheus()
    # 1) Valores PII do payload NUNCA aparecem no render
    for pii_literal in ("6682284055", "maria_pii_username", "123.456.789-09", "34999998888"):
        assert pii_literal not in render, f"LGPD VIOLATION: {pii_literal!r} vazou no render"
    # 2) Linhas das series G9: labels restritas a {result} (ou nenhuma)
    for line in render.splitlines():
        if any(line.startswith(name) for name in TELEGRAM_G9_SERIES):
            m = re.search(r"\{([^}]*)\}", line)
            if m:
                keys = {kv.split("=")[0].strip() for kv in m.group(1).split(",")}
                assert keys <= {"result"}, f"LGPD VIOLATION: labels {keys} em {line!r}"
            assert not FORBIDDEN_LABEL_KEYS & {
                p.split("=")[0] for p in re.findall(r"(\w+)=", line)
            }, f"LGPD VIOLATION: label proibida em {line!r}"
    # 3) Nenhum pattern de PII nos VALORES de label do render inteiro
    for label_str in re.findall(r"\{([^}]*)\}", render):
        for pat in _PII_VALUE_PATTERNS:
            assert not pat.search(label_str), (
                f"LGPD VIOLATION: label {label_str!r} casa pattern {pat.pattern!r}"
            )


def test_gate_lgpd_source_nao_referencia_labels_proibidas_nas_series_g9() -> None:
    """Gate estatico: os helpers G9 em metrics.py so usam label `result`.

    FALHA se alguem adicionar chat_id/username/etc. como label das series
    telegram_* (revisao cartorio-lgpd obrigatoria — G9.S2.T5).
    """
    import inspect

    import app.services.metrics as metrics_mod

    src = inspect.getsource(metrics_mod.MetricsStore)
    for helper in (
        "inc_telegram_webhook_total",
        "inc_telegram_debounce_scheduled",
        "inc_telegram_response_sent",
        "observe_telegram_webhook_response_seconds",
    ):
        m = re.search(rf"def {helper}\(.*?\n(.*?)(?=\n    def |\Z)", src, re.S)
        assert m, f"helper {helper} nao encontrado em MetricsStore"
        body = m.group(1)
        for labels_match in re.findall(r"labels=\{([^}]*)\}", body):
            # chaves do dict de labels: so "chave": (split por virgula quebrava
            # quando o valor continha chamada com args, ex. _canonical_label)
            keys = set(re.findall(r'"(\w+)"\s*:', labels_match))
            assert keys <= {"result"}, (
                f"LGPD VIOLATION: helper {helper} usa labels {keys} (permitido: {{'result'}})"
            )
        for forbidden in FORBIDDEN_LABEL_KEYS - {"secret"}:  # 'secret' so em comentario
            assert f'"{forbidden}"' not in body and f"'{forbidden}'" not in body, (
                f"LGPD VIOLATION: {forbidden!r} referenciado em {helper}"
            )
