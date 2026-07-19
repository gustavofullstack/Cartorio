"""G8.10.T2 — DNS CI checks (mocked where needed).

Modified by Gustavo Almeida — Wave 41.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services.dns_ci_check import (
    EXPECTED_HOSTS,
    cloudflare_configured,
    resolve_host,
    run_dns_ci_checks,
)


def test_expected_hosts_nonempty() -> None:
    assert len(EXPECTED_HOSTS) >= 3
    assert any(h.startswith("api.") for h in EXPECTED_HOSTS)


def test_resolve_success_mock() -> None:
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("1.2.3.4", 0))]):
        r = resolve_host("api.2notasudi.com.br")
    assert r.ok is True
    assert "1.2.3.4" in r.detail


def test_resolve_fail_mock() -> None:
    with patch("socket.getaddrinfo", side_effect=socket_error()):
        r = resolve_host("nope.invalid")
    assert r.ok is False


def socket_error() -> OSError:
    return OSError("nxdomain")


def test_run_soft_ok_if_api_resolves() -> None:
    def fake(host: str, timeout: float = 3.0):
        from app.services.dns_ci_check import DnsCheckResult

        ok = host.startswith("api.")
        return DnsCheckResult(host, ok, 1, "ok" if ok else "fail")

    with patch("app.services.dns_ci_check.resolve_host", side_effect=fake):
        report = run_dns_ci_checks(require_all=False)
    assert report.ok is True
    d = report.to_dict()
    assert "checks" in d


def test_require_all_fails() -> None:
    def fake(host: str, timeout: float = 3.0):
        from app.services.dns_ci_check import DnsCheckResult

        return DnsCheckResult(host, False, 1, "fail")

    with patch("app.services.dns_ci_check.resolve_host", side_effect=fake):
        report = run_dns_ci_checks(require_all=True)
    assert report.ok is False


def test_cloudflare_flag() -> None:
    # just callable; env may or may not be set
    assert isinstance(cloudflare_configured(), bool)
