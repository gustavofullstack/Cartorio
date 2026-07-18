from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.api.v1.router as router_module
from app.main import app
from app.models.agendamento import TipoAtendimento
from app.schemas.agendamento import AgendamentoCreateRequest
from app.schemas.metrics import N8nMetricsIngest
from app.services.agendamento import (
    AgendamentoConflictError,
    ClienteNotFoundError,
    ProtocoloNotFoundError,
)

client = TestClient(app)


def _request() -> MagicMock:
    request = MagicMock()
    request.headers = {}
    request.state = SimpleNamespace(request_id=None, client_ip=None, user_agent=None, canal=None)
    return request


@contextmanager
def _session(db: MagicMock):
    yield db


def test_get_postman_returns_collection() -> None:
    response = client.get("/api/v1/postman")
    assert response.status_code == 200
    assert response.json()["info"]["name"] == "Cartorio API"


@pytest.mark.parametrize(
    ("path", "query"),
    [
        ("/api/v1/emolumento/calcular", {"tipo": "escritura_compra_venda"}),
        ("/api/v1/health/live", {}),
        ("/api/v1/health/db", {}),
        ("/api/v1/health/redis", {}),
        ("/api/v1/health/backup", {}),
        ("/api/v1/health/backup-v2", {}),
        ("/api/v1/metrics/prometheus", {}),
        ("/api/v1/metrics", {}),
        ("/api/v1/agendamento/disponibilidade", {"dia": "segunda"}),
    ],
)
def test_get_public_endpoints_happy_path(path: str, query: dict[str, str]) -> None:
    response = client.get(path, params=query)
    assert response.status_code in (200, 503)


def test_documento_segunda_via_happy_path() -> None:
    response = client.post(
        "/api/v1/documento/segunda-via",
        params={"protocolo": "2026-00001"},
    )
    assert response.status_code == 200


def test_get_emolumento_invalid_type_returns_error_payload() -> None:
    response = client.get("/api/v1/emolumento/calcular", params={"tipo": "inexistente"})
    assert response.status_code == 200
    assert "erro" in response.json()


def test_get_query_validation_returns_422() -> None:
    cases = [
        ("/api/v1/emolumento/calcular", {"tipo": "escritura_compra_venda", "folhas": "0"}),
        ("/api/v1/agendamento/disponibilidade", {"dia": "segunda", "hora": "24"}),
        ("/api/v1/cliente/abc", {}),
    ]
    for path, query in cases:
        response = client.get(path, params=query, headers={"X-API-Key": "a" * 64})
        assert response.status_code in (401, 422)


def test_protocolo_not_found_is_audited() -> None:
    with (
        patch("app.api.v1.router.buscar_protocolo_por_numero", return_value=None),
        patch("app.api.v1.router.AuditService.log") as audit,
    ):
        response = client.get("/api/v1/protocolo/2026-99999")
    assert response.status_code == 404
    assert response.json()["detail"]["erro"] == "PROTOCOLO_NOT_FOUND"
    audit.assert_called_once()


def test_protocolo_unknown_status_falls_back_to_generic_history() -> None:
    cliente = SimpleNamespace(nome="Cliente", cpf_hash="a" * 64)
    protocolo = SimpleNamespace(
        id=1,
        numero="2026-00001",
        status="status_desconhecido",
        tipo="certidao_negativa",
        canal_origem="web",
        cliente=cliente,
        valor_base=Decimal("10.00"),
        valor_total=Decimal("10.00"),
        tabela_referencia="TABELA_2026_MG",
        prazo_dias=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        concluido_em=None,
    )

    class FakeStatus:
        DRAFT = object()
        ABERTO = object()
        EM_ANDAMENTO = object()
        AGUARDANDO_DOC = object()
        CONCLUIDO = object()
        CANCELADO = object()
        EXPIRADO = object()

        def __new__(cls, value: object) -> "FakeStatus":
            return object.__new__(cls)

    with (
        patch("app.api.v1.router.buscar_protocolo_por_numero", return_value=protocolo),
        patch("app.api.v1.router.AuditService.log"),
        patch.object(router_module, "StatusProtocolo", FakeStatus),
        patch.object(
            router_module, "ProtocoloResponse", return_value=MagicMock()
        ) as response_model,
    ):
        router_module.get_protocolo(_request(), "2026-00001", MagicMock())
    assert response_model.called


def test_verify_api_key_configuration_missing_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router_module.settings, "cartorio_api_key", "")
    with pytest.raises(HTTPException) as exc_info:
        router_module._verify_api_key("anything")
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_agendamento_disponibilidade_error_paths() -> None:
    assert (await router_module.agendamento_disponibilidade("domingo"))["vagas"] == 0
    assert (await router_module.agendamento_disponibilidade("segunda", 8))["vagas"] == 0
    result = await router_module.agendamento_disponibilidade("segunda", 16)
    assert len(result["slots"]) == 1


def test_humanize_size_all_units() -> None:
    assert router_module._humanize_size(0) == "0"
    assert router_module._humanize_size(1) == "1B"
    assert router_module._humanize_size(1024) == "1.0K"
    assert router_module._humanize_size(1024**2) == "1.0M"
    assert router_module._humanize_size(1024**3) == "1.0G"


def test_metrics_helpers_cover_filters_and_parse_errors() -> None:
    assert router_module._parse_labels_key_safe("") == {}
    assert router_module._parse_labels_key_safe("a=1|invalid|long=" + "x" * 65) == {"a": "1"}
    assert router_module._looks_like_prometheus("") is False
    assert router_module._looks_like_prometheus("# HELP x") is False
    assert router_module._looks_like_prometheus("metric 1") is True
    store = MagicMock()
    counts = router_module._ingest_prometheus_text(
        "# TYPE x counter\nrequests_total{method=GET} 2\nload 1.5\nbroken nope\ninvalid",
        store,
    )
    assert counts == (1, 1)


@pytest.mark.asyncio
async def test_health_llm_provider_paths() -> None:
    with patch.object(router_module.settings, "opencode_go_base_url", ""):
        offline = await router_module.health_llm()
    assert offline.status_code == 503

    response = SimpleNamespace(status_code=503)
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(return_value=response)
    with (
        patch.object(router_module.settings, "opencode_go_base_url", "http://llm"),
        patch("app.api.v1.router.httpx.AsyncClient", return_value=mock_client),
    ):
        degraded = await router_module.health_llm()
    assert degraded.status_code == 503


@pytest.mark.asyncio
async def test_update_backup_status_success_and_failure() -> None:
    redis_client = MagicMock()
    with patch("app.api.v1.router.redis.from_url", return_value=redis_client):
        result = await router_module.update_backup_status(
            router_module.BackupStatusUpdate(
                ok=True, last_backup_size_bytes=1024, backup_count_7d=2
            )
        )
    assert result == {"ok": True, "stored": "redis", "ttl_hours": 28}
    redis_client.setex.assert_called_once()

    with patch("app.api.v1.router.redis.from_url", side_effect=RuntimeError("redis down")):
        failed = await router_module.update_backup_status(router_module.BackupStatusUpdate())
    assert failed["stored"] == "none"


@pytest.mark.asyncio
async def test_health_backup_redis_and_json_fallbacks() -> None:
    redis_client = MagicMock()
    redis_client.get.return_value = '{"ok": true, "last_backup_size_bytes": 1024}'
    with patch("app.api.v1.router.redis.from_url", return_value=redis_client):
        result = await router_module.health_backup()
    assert result["source"] == "redis"

    with (
        patch("app.api.v1.router.redis.from_url", side_effect=RuntimeError("down")),
        patch("app.api.v1.router.os.path.exists", return_value=True),
        patch("builtins.open", side_effect=OSError("bad status file")),
        patch("app.api.v1.router.os.path.isdir", return_value=True),
        patch("app.api.v1.router.os.listdir", return_value=[]),
    ):
        fallback = await router_module.health_backup()
    assert fallback["source"] == "local_path"
    assert "warning" in fallback


@pytest.mark.asyncio
async def test_health_radar_handles_all_http_failures() -> None:
    with (
        patch("app.api.v1.router.redis.from_url", side_effect=RuntimeError("redis")),
        patch("app.api.v1.router.httpx.AsyncClient") as client_cls,
    ):
        http_client = MagicMock()
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=None)
        http_client.get = AsyncMock(side_effect=RuntimeError("http"))
        client_cls.return_value = http_client
        result = await router_module.health_radar()
    assert result["status"] == "red"
    assert result["services"]["redis"] == "offline"


@pytest.mark.asyncio
async def test_atendimento_not_found_paths() -> None:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    with patch("app.api.v1.router.session_scope", side_effect=lambda: _session(db)):
        pesquisa = await router_module.marcar_pesquisa_enviada(_request(), 99)
        conclusao = await router_module.concluir_atendimento(_request(), 99)
    assert pesquisa["error"] == "not_found"
    assert conclusao["error"] == "not_found"


@pytest.mark.asyncio
async def test_chatwoot_invalid_json_is_rejected() -> None:
    request = _request()
    request.body = AsyncMock(return_value=b"not-json")
    with patch("app.api.v1.router.AuditService.log"):
        result = await router_module.webhook_chatwoot(request)
    assert result == {"status": "rejected", "reason": "invalid_json"}


@pytest.mark.asyncio
async def test_webhook_evolution_empty_payload_uses_handoff() -> None:
    result = await router_module.webhook_evolution(_request(), {"message": {"text": ""}})
    assert result["needs_human_handoff"] is True
    assert result["handoff_reason"] == "payload_empty_message"


@pytest.mark.parametrize(
    ("exception", "status_code"),
    [
        (
            AgendamentoConflictError(SimpleNamespace(id=1, data_hora=datetime.now(), titulo="X")),
            409,
        ),  # type: ignore[arg-type]
        (ClienteNotFoundError(1), 404),
        (ProtocoloNotFoundError(1), 404),
        (ValueError("invalid"), 400),
    ],
)
def test_criar_agendamento_maps_domain_errors(exception: Exception, status_code: int) -> None:
    payload = AgendamentoCreateRequest(
        cliente_id=1,
        cliente_cpf="12345678909",
        data_hora=datetime.now(timezone.utc) + timedelta(days=1),
        titulo="Atendimento",
        descricao=None,
        tipo=TipoAtendimento.NORMAL,
        local="balcao_1",
        protocolo_id=None,
        duration_minutes=30,
    )
    with patch(
        "app.services.agendamento.AgendamentoService.criar_agendamento", side_effect=exception
    ):
        with pytest.raises(HTTPException) as exc_info:
            router_module.criar_agendamento(_request(), payload, MagicMock())
    assert exc_info.value.status_code == status_code


@pytest.mark.asyncio
async def test_n8n_metric_canonical_payload_is_ingested() -> None:
    db = MagicMock()
    payload = N8nMetricsIngest(
        counters={"requests_total": {"method=GET": 2}},
        gauges={"load": {"host=a": 1}, "scalar": 3},
        uptime_seconds=10,
        workflows_active=2,
        memory_rss_mb=5,
    )
    with (
        patch("app.services.metrics.store") as store,
        patch("app.api.v1.router.AuditService.log"),
    ):
        result = await router_module.post_metrics_n8n(_request(), payload, "key", db)
    assert result.payload_kind == "canonical"
    assert result.counters_ingested == 1
    assert result.gauges_ingested == 5
    store.inc_counter.assert_called_once()


@pytest.mark.asyncio
async def test_n8n_metric_prometheus_and_unknown_payloads() -> None:
    db = MagicMock()
    with (
        patch("app.services.metrics.store") as store,
        patch("app.api.v1.router.AuditService.log"),
    ):
        prometheus = await router_module.post_metrics_n8n(
            _request(),
            N8nMetricsIngest(raw="requests_total 2\nload 1.5"),
            "key",
            db,
        )
        unknown = await router_module.post_metrics_n8n(
            _request(), N8nMetricsIngest(raw={"other": True}), "key", db
        )
    assert prometheus.payload_kind == "prometheus_raw"
    assert unknown.payload_kind == "unknown"
    assert store.inc_counter.call_count == 1


@pytest.mark.asyncio
async def test_admin_n8n_validator_auth_and_success() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await router_module.admin_validate_n8n_wfs(_request())
    assert exc_info.value.status_code == 401

    request = _request()
    request.headers = {"x-api-key": "a" * 64}
    result_data = {
        "directory": "/tmp/wfs",
        "total": 2,
        "valid": 1,
        "invalid": 1,
        "warning": 1,
        "wfs": [
            {"valid": False, "warnings": [], "name": "bad"},
            {"valid": True, "warnings": ["warn"], "name": "good"},
        ],
    }
    with patch("app.services.n8n_workflow_validator.validate_all", return_value=result_data):
        result = await router_module.admin_validate_n8n_wfs(request)
    assert result["top_invalid"][0]["name"] == "bad"
    assert result["top_warning"][0]["name"] == "good"


@pytest.mark.asyncio
async def test_admin_relatorio_json_and_markdown() -> None:
    request = _request()
    request.headers = {"x-api-key": "a" * 64}
    report = {"hash_anchor": "hash", "titulares": 1}
    with patch("app.services.lgpd_relatorio.gerar_relatorio_anual", return_value=report):
        json_response = await router_module.admin_lgpd_relatorio_anual(
            request, 2026, "json", MagicMock()
        )
    assert json_response.status_code == 200

    with (
        patch("app.services.lgpd_relatorio.gerar_relatorio_anual", return_value=report),
        patch("app.services.lgpd_relatorio.render_markdown", return_value="# report"),
    ):
        markdown_response = await router_module.admin_lgpd_relatorio_anual(
            request, 2026, "markdown", MagicMock()
        )
    assert markdown_response.body is not None


def test_dlq_and_admin_pool_auth_failures() -> None:
    request = _request()
    with pytest.raises(HTTPException) as exc_info:
        router_module.post_dlq_refresh_gauges(request, None, MagicMock())
    assert exc_info.value.status_code in (401, 503)

    with pytest.raises(HTTPException) as exc_info:
        router_module.get_admin_pool(_request(), None)
    assert exc_info.value.status_code in (401, 503)
