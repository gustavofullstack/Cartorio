"""G8.04.T1 — OpenClaw status no radar expandido.

Cobre:
- probe HTTP (respx) up / auth-gated
- offline path → warn (fail-open)
- inventário de config local (basename only, sem secrets)
- _check_openclaw_category fail-open

Modified by Gustavo Almeida — G8.04.T1 Wave 32.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from app.services.openclaw_radar import (
    DEFAULT_OPENCLAW_PUBLIC_BASE,
    build_openclaw_radar,
    inventory_openclaw_config,
)


@respx.mock
def test_build_openclaw_radar_up() -> None:
    base = "https://agent.2notasudi.com.br"
    respx.head(f"{base}/health").mock(return_value=httpx.Response(200))
    report = build_openclaw_radar(base_url=base)
    assert report.status == "up"
    assert report.http_status == 200
    d = report.to_dict()
    assert d["status"] == "up"
    assert "latency_ms" in d
    assert "detail" in d
    assert d["url"] == f"{base}/health"


@respx.mock
def test_build_openclaw_radar_auth_gated_is_up() -> None:
    """401/403 = gateway alive (auth required)."""
    base = "http://openclaw.test:18789"
    respx.head(f"{base}/health").mock(return_value=httpx.Response(401))
    report = build_openclaw_radar(base_url=base)
    assert report.status == "up"
    assert report.http_status == 401


@respx.mock
def test_build_openclaw_radar_head_405_falls_back_to_get() -> None:
    base = "https://agent.example.test"
    respx.head(f"{base}/health").mock(return_value=httpx.Response(405))
    respx.get(f"{base}/health").mock(return_value=httpx.Response(200))
    report = build_openclaw_radar(base_url=base)
    assert report.status == "up"
    assert report.http_status == 200


@respx.mock
def test_build_openclaw_radar_offline_is_warn() -> None:
    """Fail-open: connection error → warn, not down, no exception."""
    base = "http://127.0.0.1:1"
    respx.head(f"{base}/health").mock(side_effect=httpx.ConnectError("refused"))
    respx.get(f"{base}/health").mock(side_effect=httpx.ConnectError("refused"))
    report = build_openclaw_radar(base_url=base)
    assert report.status == "warn"
    assert "offline" in report.detail or "ConnectError" in report.detail
    assert report.http_status is None


@respx.mock
def test_build_openclaw_radar_timeout_is_warn() -> None:
    base = "http://slow.openclaw.test"
    respx.head(f"{base}/health").mock(side_effect=httpx.TimeoutException("timeout"))
    respx.get(f"{base}/health").mock(side_effect=httpx.TimeoutException("timeout"))
    # Timeout on HEAD path returns warn without GET retry when TimeoutException
    # is raised from the outer try of HEAD/GET block — exercise via connect path.
    report = build_openclaw_radar(base_url=base, timeout_s=0.1)
    assert report.status == "warn"
    assert "timeout" in report.detail.lower() or "Timeout" in report.detail


def test_build_openclaw_radar_skip_probe_offline_path() -> None:
    """Pure offline path: no network."""
    report = build_openclaw_radar(
        base_url=DEFAULT_OPENCLAW_PUBLIC_BASE,
        skip_probe=True,
        config_path=Path("/nonexistent/openclaw.json"),
    )
    assert report.status == "warn"
    assert report.config.get("present") is False
    d = report.to_dict()
    assert set(d) >= {"status", "latency_ms", "detail", "url"}


def test_inventory_config_present(tmp_path: Path) -> None:
    cfg = tmp_path / "openclaw.json"
    cfg.write_text('{"models":[]}\n', encoding="utf-8")
    inv = inventory_openclaw_config(cfg)
    assert inv["present"] is True
    assert inv["path"] == "openclaw.json"
    assert inv["bytes"] > 0
    # Must not expose parent path or file body.
    assert str(tmp_path) not in inv["path"]
    assert "models" not in str(inv)


def test_inventory_config_absent(tmp_path: Path) -> None:
    inv = inventory_openclaw_config(tmp_path / "missing.json")
    assert inv == {"present": False}


@pytest.mark.asyncio
async def test_check_openclaw_category_fail_open() -> None:
    from app.api.v1 import health_radar_expanded as mod

    with patch(
        "app.services.openclaw_radar.build_openclaw_radar",
        side_effect=RuntimeError("boom"),
    ):
        # Patch import target used inside _run via module path after import —
        # force category to raise by patching asyncio.to_thread.
        with patch.object(mod.asyncio, "to_thread", side_effect=RuntimeError("boom")):
            out = await mod._check_openclaw_category()
    assert "gateway" in out
    assert out["gateway"]["status"] == "warn"
    assert "openclaw radar error" in out["gateway"]["detail"]


@pytest.mark.asyncio
async def test_check_openclaw_category_ok() -> None:
    from app.api.v1 import health_radar_expanded as mod

    fake = {
        "status": "up",
        "latency_ms": 12,
        "detail": "HTTP 200; config=absent",
        "url": "https://agent.2notasudi.com.br/health",
        "http_status": 200,
    }
    with patch(
        "app.services.openclaw_radar.build_openclaw_radar",
    ) as mock_build:
        mock_build.return_value.to_dict.return_value = fake
        # _run imports and calls build_openclaw_radar in a thread; patch at source
        # and also allow real to_thread to call _run which uses patched import.
        out = await mod._check_openclaw_category()
    assert out["gateway"]["status"] == "up"
    assert out["gateway"]["latency_ms"] == 12


@pytest.mark.asyncio
async def test_health_radar_expanded_includes_openclaw_category() -> None:
    """Endpoint categories includes openclaw when all category fns mocked."""
    from app.api.v1 import health_radar_expanded as mod

    empty = AsyncMock(return_value={})
    oc = AsyncMock(
        return_value={
            "gateway": {
                "status": "up",
                "latency_ms": 5,
                "detail": "HTTP 200",
                "url": "https://agent.2notasudi.com.br/health",
            }
        }
    )
    with (
        patch.object(mod, "_check_health_category", empty),
        patch.object(mod, "_check_dns_category", empty),
        patch.object(mod, "_check_traefik_category", empty),
        patch.object(mod, "_check_ssh_category", empty),
        patch.object(mod, "_check_disk_category", empty),
        patch.object(mod, "_check_mcp_category", empty),
        patch.object(mod, "_check_openclaw_category", oc),
    ):
        data = await mod.health_radar_expanded()
    assert "openclaw" in data["categories"]
    assert data["categories"]["openclaw"]["gateway"]["status"] == "up"
