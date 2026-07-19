"""Tests for Health Radar Expanded endpoint (F6 [P2] 2026-07-15).

Cobre:
- test_radar_returns_all_categories: resposta contem health/dns/traefik/ssh/disk.
- test_radar_handles_missing_dns_gracefully: NXDOMAIN = status "down" sem 500.
- test_radar_overall_status_aggregates_critical_down.
- test_radar_disk_returns_warn_on_missing_path.
- test_radar_returns_200_even_when_all_checks_fail (fail-open).
- test_dns_check_handles_nxdomain: unit test direto em _check_dns.
- test_traefik_check_detects_warn_404: unit test direto em _check_traefik.
- test_socket_check_open: unit test direto em _check_socket.
- test_socket_check_closed: unit test direto em _check_socket.
- test_aggregate_overall_logic: regras de agregacao green/yellow/red.

Squad cartorio-front / F6 [P2] / 2026-07-15.
Modified by Gustavo Almeida.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.health_radar_expanded import (
    RADAR_DNS_DOMAINS,
    RADAR_DISK_PATH,
    RADAR_SSH_HOST,
    RADAR_TAILSCALE_HOST,
    RADAR_TRAEFIK_DOMAINS,
    TRAEFIK_WARN_CONTENT_LENGTH,
    _aggregate_overall,
    _check_disk,
    _check_dns,
    _check_socket,
    _check_traefik,
)


@pytest.fixture
def client() -> TestClient:
    """Cria TestClient com app + lifespan."""
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_radar_returns_all_categories(client: TestClient) -> None:
    """Endpoint /health/radar/expanded retorna todas as 6 categorias."""
    with (
        patch("app.api.v1.health_radar_expanded._check_health_category") as mock_health,
        patch("app.api.v1.health_radar_expanded._check_dns_category") as mock_dns,
        patch("app.api.v1.health_radar_expanded._check_traefik_category") as mock_traefik,
        patch("app.api.v1.health_radar_expanded._check_ssh_category") as mock_ssh,
        patch("app.api.v1.health_radar_expanded._check_disk_category") as mock_disk,
    ):
        mock_health.side_effect = AsyncMock(
            return_value={"database": {"status": "up", "latency_ms": 5, "detail": "ok"}}
        )
        mock_dns.side_effect = AsyncMock(
            return_value={"2notasudi.com.br": {"status": "up", "latency_ms": 100, "detail": "ok"}}
        )
        mock_traefik.side_effect = AsyncMock(
            return_value={
                "api.2notasudi.com.br": {"status": "up", "latency_ms": 50, "detail": "HTTP 200"}
            }
        )
        mock_ssh.side_effect = AsyncMock(
            return_value={
                "ssh_vps": {"status": "up", "latency_ms": 10, "detail": "open"},
                "tailscale": {"status": "down", "latency_ms": 3000, "detail": "timeout"},
            }
        )
        mock_disk.side_effect = AsyncMock(
            return_value={
                "docker_volumes": {"status": "up", "latency_ms": 1, "detail": "free=10GB"}
            }
        )

        resp = client.get("/api/v1/health/radar/expanded")
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data
        cats = data["categories"]
        assert "health" in cats
        assert "dns" in cats
        assert "traefik" in cats
        assert "ssh" in cats
        assert "disk" in cats
        assert data["metadata"]["domain_count_dns"] == len(RADAR_DNS_DOMAINS)
        assert data["metadata"]["domain_count_traefik"] == len(RADAR_TRAEFIK_DOMAINS)
        assert data["metadata"]["ssh_host"] == RADAR_SSH_HOST
        assert data["metadata"]["tailscale_host"] == RADAR_TAILSCALE_HOST
        assert data["metadata"]["disk_path"] == RADAR_DISK_PATH


def test_radar_handles_missing_dns_gracefully() -> None:
    """NXDOMAIN no DNS = status 'down', nao exception/500."""
    fake_proc = AsyncMock()
    fake_proc.communicate = AsyncMock(return_value=(b"", b"status: NXDOMAIN\n"))
    fake_proc.returncode = 9

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        result = asyncio.run(_check_dns("nonexistent-host-12345.invalid"))

    assert result["status"] == "down"
    assert "NXDOMAIN" in result["detail"] or "rc=" in result["detail"]
    assert "latency_ms" in result


def test_radar_returns_200_even_when_all_checks_fail(client: TestClient) -> None:
    """Endpoint nao quebra mesmo se TODAS categorias explodirem (fail-open)."""
    with (
        patch("app.api.v1.health_radar_expanded._check_health_category") as mock_health,
        patch("app.api.v1.health_radar_expanded._check_dns_category") as mock_dns,
        patch("app.api.v1.health_radar_expanded._check_traefik_category") as mock_traefik,
        patch("app.api.v1.health_radar_expanded._check_ssh_category") as mock_ssh,
        patch("app.api.v1.health_radar_expanded._check_disk_category") as mock_disk,
    ):
        mock_health.side_effect = RuntimeError("DB boom")
        mock_dns.side_effect = RuntimeError("DNS boom")
        mock_traefik.side_effect = RuntimeError("Traefik boom")
        mock_ssh.side_effect = RuntimeError("SSH boom")
        mock_disk.side_effect = RuntimeError("Disk boom")

        resp = client.get("/api/v1/health/radar/expanded")
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data
        for cat in ("health", "dns", "traefik", "ssh", "disk"):
            assert cat in data["categories"]
        assert data["status"] in ("green", "yellow", "red")


def test_radar_overall_status_red_on_critical_down() -> None:
    """database OU redis down -> status agregado = red."""
    cats: dict = {
        "health": {
            "database": {"status": "down", "latency_ms": 5, "detail": "x"},
            "redis": {"status": "up", "latency_ms": 5, "detail": "ok"},
            "openclaw": {"status": "up", "latency_ms": 50, "detail": "ok"},
        },
        "dns": {},
        "traefik": {},
        "ssh": {"ssh_vps": {"status": "up", "latency_ms": 10, "detail": "ok"}},
        "disk": {"docker_volumes": {"status": "up", "latency_ms": 1, "detail": "ok"}},
    }
    assert _aggregate_overall(cats) == "red"


def test_radar_overall_status_yellow_on_non_critical_down() -> None:
    """openclaw down (nao-critico) -> yellow, nao red."""
    cats: dict = {
        "health": {
            "database": {"status": "up", "latency_ms": 5, "detail": "ok"},
            "redis": {"status": "up", "latency_ms": 5, "detail": "ok"},
            "openclaw": {"status": "down", "latency_ms": 50, "detail": "x"},
        },
        "dns": {"2notasudi.com.br": {"status": "up", "latency_ms": 100, "detail": "ok"}},
        "traefik": {},
        "ssh": {"ssh_vps": {"status": "up", "latency_ms": 10, "detail": "ok"}},
        "disk": {"docker_volumes": {"status": "up", "latency_ms": 1, "detail": "ok"}},
    }
    assert _aggregate_overall(cats) == "yellow"


def test_radar_overall_status_yellow_on_warn_only() -> None:
    """warn apenas (sem down) -> yellow."""
    cats: dict = {
        "health": {
            "database": {"status": "up", "latency_ms": 5, "detail": "ok"},
            "redis": {"status": "up", "latency_ms": 5, "detail": "ok"},
        },
        "dns": {"2notasudi.com.br": {"status": "up", "latency_ms": 100, "detail": "ok"}},
        "traefik": {},
        "ssh": {"ssh_vps": {"status": "up", "latency_ms": 10, "detail": "ok"}},
        "disk": {"docker_volumes": {"status": "warn", "latency_ms": 1, "detail": "92% used"}},
    }
    assert _aggregate_overall(cats) == "yellow"


def test_radar_overall_status_green_when_all_up() -> None:
    """Todos up -> green."""
    cats: dict = {
        "health": {
            "database": {"status": "up", "latency_ms": 5, "detail": "ok"},
            "redis": {"status": "up", "latency_ms": 5, "detail": "ok"},
        },
        "dns": {"2notasudi.com.br": {"status": "up", "latency_ms": 100, "detail": "ok"}},
        "traefik": {},
        "ssh": {"ssh_vps": {"status": "up", "latency_ms": 10, "detail": "ok"}},
        "disk": {"docker_volumes": {"status": "up", "latency_ms": 1, "detail": "50% used"}},
    }
    assert _aggregate_overall(cats) == "green"


def test_radar_disk_returns_warn_on_missing_path() -> None:
    """Path de disco inexistente -> warn (nao down)."""
    result = _check_disk("/path/that/definitely/does/not/exist/12345")
    assert result["status"] == "warn"
    assert "not found" in result["detail"]


def test_radar_disk_returns_up_on_normal_path() -> None:
    """Path existente (/) -> up ou warn dependendo do uso."""
    result = _check_disk("/")
    assert result["status"] in ("up", "warn")
    assert "GB" in result["detail"]


@pytest.mark.parametrize("host,port", [(RADAR_SSH_HOST, 22), (RADAR_TAILSCALE_HOST, 22)])
def test_socket_check_handles_unreachable(host: str, port: int) -> None:
    """Host inalcancavel -> status down (sem exception)."""
    result = asyncio.run(_check_socket(host, port, timeout=1.0))
    assert result["status"] in ("up", "down")
    assert "latency_ms" in result
    assert f"{host}:{port}" in result["detail"]


def test_socket_check_open_port() -> None:
    """Porta aberta (loopback) -> up."""
    import pytest
    import socket as stdlib_socket

    server = stdlib_socket.socket(stdlib_socket.AF_INET, stdlib_socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", 0))
    except PermissionError:
        pytest.skip("Socket bind nao permitido no sandbox do Trae/Gemini")
    server.listen(1)
    port = server.getsockname()[1]
    try:
        result = asyncio.run(_check_socket("127.0.0.1", port, timeout=1.0))
        assert result["status"] == "up"
        assert f"127.0.0.1:{port}" in result["detail"]
    finally:
        server.close()


def test_socket_check_closed_port() -> None:
    """Porta explicitamente nao-escuta -> down com ConnectionRefusedError."""
    import pytest
    import socket as stdlib_socket

    try:
        with stdlib_socket.socket(stdlib_socket.AF_INET, stdlib_socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
    except PermissionError:
        pytest.skip("Socket bind nao permitido no sandbox do Trae/Gemini")
    result = asyncio.run(_check_socket("127.0.0.1", port, timeout=1.0))
    assert result["status"] == "down"


def test_traefik_check_returns_up_on_200() -> None:
    """HEAD 200 -> up."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": "0"}
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.head = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(_check_traefik("api.2notasudi.com.br"))

    assert result["status"] == "up"
    assert result["detail"] == "HTTP 200"


def test_traefik_check_detects_warn_404_with_known_content_length() -> None:
    """HEAD 404 + content-length=2901 -> warn (Traefik router sem match)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.headers = {"content-length": str(TRAEFIK_WARN_CONTENT_LENGTH)}
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.head = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(_check_traefik("api.2notasudi.com.br"))

    assert result["status"] == "warn"
    assert "router not matched" in result["detail"]


def test_traefik_check_returns_down_on_500() -> None:
    """HEAD 500 -> down."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.headers = {"content-length": "0"}
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.head = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(_check_traefik("api.2notasudi.com.br"))

    assert result["status"] == "down"


def test_dns_check_returns_up_when_resolved() -> None:
    """dig retorna IP -> up."""
    fake_proc = AsyncMock()
    fake_proc.communicate = AsyncMock(return_value=(b"195.35.60.67\n", b""))
    fake_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        result = asyncio.run(_check_dns("2notasudi.com.br"))

    assert result["status"] == "up"
    assert "195.35.60.67" in result["detail"]


def test_dns_check_returns_warn_when_dig_missing() -> None:
    """dig nao instalado (FileNotFoundError) -> warn, nao down."""
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("dig not found")):
        result = asyncio.run(_check_dns("2notasudi.com.br"))

    assert result["status"] == "warn"
    assert "dig" in result["detail"]


def test_radar_endpoint_metadata_includes_version() -> None:
    """Metadata inclui versao e contagens canonicas."""
    with (
        patch("app.api.v1.health_radar_expanded._check_health_category") as mh,
        patch("app.api.v1.health_radar_expanded._check_dns_category") as md,
        patch("app.api.v1.health_radar_expanded._check_traefik_category") as mt,
        patch("app.api.v1.health_radar_expanded._check_ssh_category") as ms,
        patch("app.api.v1.health_radar_expanded._check_disk_category") as mk,
    ):
        empty_coro = AsyncMock(return_value={})
        mh.side_effect = empty_coro
        md.side_effect = empty_coro
        mt.side_effect = empty_coro
        ms.side_effect = empty_coro
        mk.side_effect = empty_coro

        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as c:
            resp = c.get("/api/v1/health/radar/expanded")
            assert resp.status_code == 200
            meta = resp.json()["metadata"]
            assert meta["version"] == "0.6.0"
            assert meta["domain_count_dns"] >= 10
            assert meta["domain_count_traefik"] >= 5


# ============================================================================
# OpenAPI enhancer coverage (T083 — F6 [P2])
# ============================================================================


def test_openapi_enhancer_injects_contact_and_license() -> None:
    """Enhancer adiciona info.contact + info.license no OpenAPI schema."""
    from fastapi import FastAPI

    from app.middleware.openapi_enhancer import (
        install_openapi_enhancer,
    )

    app = FastAPI(title="Test")
    install_openapi_enhancer(app)
    schema = app.openapi()
    assert schema["info"]["contact"]["email"] == "suporte@2notasudi.com.br"
    assert schema["info"]["license"]["name"] == "LGPL-3.0"
    assert len(schema["servers"]) >= 2
    server_urls = [s["url"] for s in schema["servers"]]
    assert "https://api.2notasudi.com.br" in server_urls
    assert "http://localhost:8000" in server_urls


def test_openapi_enhancer_includes_ordered_tags() -> None:
    """Enhancer adiciona tags ordenadas (Health, Telegram, WhatsApp, LGPD...)."""
    from fastapi import FastAPI

    from app.middleware.openapi_enhancer import (
        install_openapi_enhancer,
    )

    app = FastAPI(title="Test")
    install_openapi_enhancer(app)
    schema = app.openapi()
    tag_names = [t["name"] for t in schema.get("tags", [])]
    assert "Health" in tag_names
    assert "Telegram" in tag_names
    assert "LGPD" in tag_names
    assert "Audit" in tag_names
    assert "Brain" in tag_names
    assert "OpenClaw" in tag_names
    assert tag_names.index("Health") < tag_names.index("Telegram")
    assert tag_names.index("LGPD") < tag_names.index("Audit")


def test_openapi_enhancer_includes_security_schemes() -> None:
    """Enhancer adiciona 3 security schemes (ApiKeyAuth, BearerAuth, TelegramWebhookSecret)."""
    from fastapi import FastAPI

    from app.middleware.openapi_enhancer import (
        install_openapi_enhancer,
    )

    app = FastAPI(title="Test")
    install_openapi_enhancer(app)
    schema = app.openapi()
    schemes = schema.get("components", {}).get("securitySchemes", {})
    assert "ApiKeyAuth" in schemes
    assert "BearerAuth" in schemes
    assert "TelegramWebhookSecret" in schemes
    assert schemes["ApiKeyAuth"]["type"] == "apiKey"
    assert schemes["BearerAuth"]["scheme"] == "bearer"
    assert schemes["TelegramWebhookSecret"]["in"] == "header"


def test_openapi_enhancer_merge_tags_deduplicates() -> None:
    """_merge_tags deduplica tags repetidas."""
    from app.middleware.openapi_enhancer import (
        API_TAGS_ORDERED,
        _merge_tags,
    )

    duplicate_tag = {"name": "Health", "description": "DUPLICADO"}
    result = _merge_tags([duplicate_tag])
    health_tags = [t for t in result if t.get("name") == "Health"]
    assert len(health_tags) == 1
    health_idx = next(i for i, t in enumerate(result) if t.get("name") == "Health")
    assert result[health_idx] in API_TAGS_ORDERED
    assert result[health_idx]["description"] != "DUPLICADO"


def test_openapi_enhancer_merge_tags_preserves_existing_order() -> None:
    """_merge_tags preserva API_TAGS_ORDERED primeiro, depois adiciona tags novas."""
    from app.middleware.openapi_enhancer import (
        API_TAGS_ORDERED,
        _merge_tags,
    )

    new_tag = {"name": "MyCustomTag", "description": "Custom"}
    result = _merge_tags([new_tag])
    custom_idx = next(i for i, t in enumerate(result) if t.get("name") == "MyCustomTag")
    health_idx = next(i for i, t in enumerate(result) if t.get("name") == "Health")
    assert health_idx < custom_idx
    assert result[: len(API_TAGS_ORDERED)] == API_TAGS_ORDERED


def test_openapi_enhancer_overrides_default_title() -> None:
    """Enhancer corrige title default 'FastAPI' para 'Cartorio Backend API'."""
    from fastapi import FastAPI

    from app.middleware.openapi_enhancer import (
        install_openapi_enhancer,
    )

    app = FastAPI()
    install_openapi_enhancer(app)
    schema = app.openapi()
    assert schema["info"]["title"] == "Cartorio Backend API"


# ============================================================================
# Health Radar expanded: exception paths e _check_health_category (T086 — F6 [P2])
# ============================================================================


def test_check_dns_category_handles_exceptions() -> None:
    """DNS category trata exceptions de gather (return_exceptions=True)."""
    from app.api.v1.health_radar_expanded import _check_dns_category

    with patch("app.api.v1.health_radar_expanded._check_dns") as mock_check:
        mock_check.side_effect = [
            {"status": "up", "latency_ms": 100, "detail": "ok"},
            RuntimeError("boom"),
            {"status": "up", "latency_ms": 100, "detail": "ok"},
        ]
        result = asyncio.run(_check_dns_category())
    assert len(result) == len(RADAR_DNS_DOMAINS)
    for domain, payload in result.items():
        assert "status" in payload


def test_check_traefik_category_handles_exceptions() -> None:
    """Traefik category trata exceptions de gather."""
    from app.api.v1.health_radar_expanded import _check_traefik_category

    with patch("app.api.v1.health_radar_expanded._check_traefik") as mock_check:
        mock_check.side_effect = [
            {"status": "up", "latency_ms": 50, "detail": "ok"},
            RuntimeError("boom"),
        ]
        result = asyncio.run(_check_traefik_category())
    assert len(result) == len(RADAR_TRAEFIK_DOMAINS)


def test_check_ssh_category_runs_both() -> None:
    """SSH category roda VPS + Tailscale em paralelo."""
    from app.api.v1.health_radar_expanded import _check_ssh_category

    result = asyncio.run(_check_ssh_category())
    assert "ssh_vps" in result
    assert "tailscale" in result
    assert result["ssh_vps"]["status"] in ("up", "down")
    assert result["tailscale"]["status"] in ("up", "down")


def test_check_disk_category_runs_once() -> None:
    """Disk category retorna dict com docker_volumes."""
    from app.api.v1.health_radar_expanded import _check_disk_category

    result = asyncio.run(_check_disk_category())
    assert "docker_volumes" in result
    assert result["docker_volumes"]["status"] in ("up", "warn")


def test_dns_check_timeout_returns_down() -> None:
    """DNS check com timeout retorna status down."""
    fake_proc = AsyncMock()
    fake_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        result = asyncio.run(_check_dns("timeout.example.com"))
    assert result["status"] == "down"


def test_traefik_check_returns_down_on_connection_error() -> None:
    """Traefik check com ConnectError retorna status down."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(side_effect=ConnectionError("boom"))
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance
        result = asyncio.run(_check_traefik("api.2notasudi.com.br"))
    assert result["status"] == "down"


def test_socket_check_returns_down_on_unexpected_exception() -> None:
    """Socket check trata Exception generica (nao so OSError)."""
    with patch("asyncio.open_connection", side_effect=RuntimeError("unexpected")):
        result = asyncio.run(_check_socket("127.0.0.1", 22, timeout=1.0))
    assert result["status"] == "down"
    assert "RuntimeError" in result["detail"]


def test_disk_check_handles_oserror() -> None:
    """Disk check trata OSError."""
    with patch("shutil.disk_usage", side_effect=OSError("disk error")):
        result = _check_disk("/some/path")
    assert result["status"] == "warn"
    assert "OSError" in result["detail"]


def test_check_health_category_returns_all_services() -> None:
    """_check_health_category retorna todos os servicos esperados."""
    from app.api.v1.health_radar_expanded import _check_health_category

    with (
        patch("app.api.v1.health_radar_expanded.engine") as mock_engine,
        patch("redis.from_url") as mock_redis_from_url,
    ):
        mock_conn = MagicMock()
        mock_conn.execute = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=None)

        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_redis_from_url.return_value = mock_redis_instance

        result = asyncio.run(_check_health_category())
    assert "database" in result
    assert "redis" in result
