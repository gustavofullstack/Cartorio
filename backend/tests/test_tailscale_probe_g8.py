"""G8.09.T1 — Testes do probe de latência Tailscale.

Cobre:
  - TailscaleProbeResult dataclass fields
  - probe_tcp success (socket mock)
  - probe_tcp fail (OSError)
  - probe_tcp timeout (TimeoutError)
  - probe_tailscale_defaults host default 100.99.172.84:22
  - format_report non-empty markdown
  - CLI smoke (import path)

Modified by Gustavo Almeida — G8 Wave 37 Squad 09.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.tailscale_probe import (
    DEFAULT_TAILSCALE_HOST,
    DEFAULT_TAILSCALE_PORT,
    TailscaleProbeResult,
    format_report,
    probe_tailscale_defaults,
    probe_tcp,
    _cli,
)


class TestTailscaleProbeResult:
    def test_dataclass_fields(self) -> None:
        r = TailscaleProbeResult(
            host="100.99.172.84",
            port=22,
            ok=True,
            latency_ms=12.5,
            detail="ok",
        )
        assert r.host == "100.99.172.84"
        assert r.port == 22
        assert r.ok is True
        assert r.latency_ms == 12.5
        assert r.detail == "ok"
        d = r.to_dict()
        assert d["host"] == "100.99.172.84"
        assert d["ok"] is True


class TestProbeTcp:
    def test_success(self) -> None:
        mock_sock = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_sock
        mock_cm.__exit__.return_value = False

        with patch(
            "app.services.tailscale_probe.socket.create_connection",
            return_value=mock_cm,
        ) as m_conn:
            result = probe_tcp("100.99.172.84", 22, timeout=1.0)

        m_conn.assert_called_once_with(("100.99.172.84", 22), timeout=1.0)
        assert result.ok is True
        assert result.host == "100.99.172.84"
        assert result.port == 22
        assert result.latency_ms >= 0.0
        assert "OK" in result.detail

    def test_connection_refused(self) -> None:
        with patch(
            "app.services.tailscale_probe.socket.create_connection",
            side_effect=ConnectionRefusedError("Connection refused"),
        ):
            result = probe_tcp("100.99.172.84", 22, timeout=1.0)

        assert result.ok is False
        assert result.host == "100.99.172.84"
        assert result.port == 22
        assert result.latency_ms >= 0.0
        assert "ConnectionRefusedError" in result.detail

    def test_timeout_path(self) -> None:
        with patch(
            "app.services.tailscale_probe.socket.create_connection",
            side_effect=TimeoutError("timed out"),
        ):
            result = probe_tcp("100.99.172.84", 22, timeout=0.5)

        assert result.ok is False
        assert "TimeoutError" in result.detail
        assert result.latency_ms >= 0.0

    def test_generic_oserror(self) -> None:
        with patch(
            "app.services.tailscale_probe.socket.create_connection",
            side_effect=OSError("Network is unreachable"),
        ):
            result = probe_tcp("10.0.0.1", 9999, timeout=1.0)

        assert result.ok is False
        assert "OSError" in result.detail


class TestProbeTailscaleDefaults:
    def test_default_host_port(self) -> None:
        with patch(
            "app.services.tailscale_probe.probe_tcp",
            return_value=TailscaleProbeResult(
                host=DEFAULT_TAILSCALE_HOST,
                port=DEFAULT_TAILSCALE_PORT,
                ok=True,
                latency_ms=5.0,
                detail="ok",
            ),
        ) as m_probe:
            with patch.dict("os.environ", {}, clear=False):
                # Ensure no TAILSCALE_API_HOST unless present
                env = {
                    k: v
                    for k, v in __import__("os").environ.items()
                    if k
                    not in (
                        "RADAR_TAILSCALE_HOST",
                        "RADAR_TAILSCALE_PORT",
                        "TAILSCALE_API_HOST",
                        "TAILSCALE_API_PORT",
                    )
                }
                with patch.dict("os.environ", env, clear=True):
                    results = probe_tailscale_defaults(timeout=1.0)

        assert len(results) == 1
        m_probe.assert_called_once_with(
            DEFAULT_TAILSCALE_HOST, DEFAULT_TAILSCALE_PORT, timeout=1.0
        )
        assert results[0].ok is True

    def test_custom_targets(self) -> None:
        with patch(
            "app.services.tailscale_probe.probe_tcp",
            side_effect=lambda h, p, timeout=2.0: TailscaleProbeResult(
                host=h, port=p, ok=True, latency_ms=1.0, detail="ok"
            ),
        ):
            results = probe_tailscale_defaults(
                targets=[("100.64.0.1", 22), ("100.64.0.2", 443)],
                timeout=0.5,
            )
        assert len(results) == 2
        assert results[0].host == "100.64.0.1"
        assert results[1].port == 443

    def test_optional_api_host_env(self) -> None:
        with patch(
            "app.services.tailscale_probe.probe_tcp",
            side_effect=lambda h, p, timeout=2.0: TailscaleProbeResult(
                host=h, port=p, ok=True, latency_ms=1.0, detail="ok"
            ),
        ) as m_probe:
            with patch.dict(
                "os.environ",
                {
                    "RADAR_TAILSCALE_HOST": "100.99.172.84",
                    "RADAR_TAILSCALE_PORT": "22",
                    "TAILSCALE_API_HOST": "100.99.172.50",
                    "TAILSCALE_API_PORT": "8000",
                },
                clear=False,
            ):
                results = probe_tailscale_defaults(timeout=1.0)

        assert len(results) == 2
        assert m_probe.call_count == 2
        hosts = {r.host for r in results}
        assert "100.99.172.84" in hosts
        assert "100.99.172.50" in hosts


class TestFormatReport:
    def test_format_report_non_empty(self) -> None:
        results = [
            TailscaleProbeResult(
                host="100.99.172.84",
                port=22,
                ok=True,
                latency_ms=8.25,
                detail="TCP connect OK",
            ),
            TailscaleProbeResult(
                host="100.99.172.50",
                port=8000,
                ok=False,
                latency_ms=2000.0,
                detail="TimeoutError: timed out",
            ),
        ]
        md = format_report(results)
        assert md
        assert len(md) > 50
        assert "# Tailscale" in md
        assert "100.99.172.84" in md
        assert "Latency" in md
        assert "YELLOW" in md or "Summary" in md
        assert "8.250" in md or "8.25" in md

    def test_format_report_all_ok_green(self) -> None:
        results = [
            TailscaleProbeResult(
                host="100.99.172.84",
                port=22,
                ok=True,
                latency_ms=3.0,
                detail="ok",
            )
        ]
        md = format_report(results)
        assert "GREEN" in md

    def test_format_report_all_fail_red(self) -> None:
        results = [
            TailscaleProbeResult(
                host="x",
                port=1,
                ok=False,
                latency_ms=1.0,
                detail="fail",
            )
        ]
        md = format_report(results)
        assert "RED" in md


class TestCli:
    def test_cli_json_exit_0_on_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(
            "app.services.tailscale_probe.probe_tcp",
            return_value=TailscaleProbeResult(
                host="h",
                port=22,
                ok=True,
                latency_ms=1.0,
                detail="ok",
            ),
        ):
            code = _cli(["--host", "h", "--port", "22", "--json"])
        assert code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert data[0]["ok"] is True

    def test_cli_markdown_exit_1_on_fail(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch(
            "app.services.tailscale_probe.probe_tcp",
            return_value=TailscaleProbeResult(
                host="h",
                port=22,
                ok=False,
                latency_ms=5.0,
                detail="down",
            ),
        ):
            code = _cli(["--host", "h", "--port", "22"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Tailscale" in out
