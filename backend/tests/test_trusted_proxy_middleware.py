"""Regressões de confiança de proxy para identidade de IP.

O teste isola o limite ASGI: uma conexão direta nunca pode escolher seu IP
efetivo com X-Forwarded-For; somente um proxy configurado pode encaminhá-lo.
"""

from __future__ import annotations

from app.middleware.trusted_proxy import TrustedProxyMiddleware


def _middleware() -> TrustedProxyMiddleware:
    async def app(scope: object, receive: object, send: object) -> None:
        return None

    return TrustedProxyMiddleware(app, trusted_proxies=("10.0.0.0/8", "2001:db8::/32"))


def test_direct_client_cannot_spoof_xff() -> None:
    middleware = _middleware()
    assert middleware.resolve_client_ip("198.51.100.17", "203.0.113.9") == "198.51.100.17"


def test_trusted_proxy_uses_rightmost_untrusted_xff_hop() -> None:
    middleware = _middleware()
    assert (
        middleware.resolve_client_ip("10.1.2.3", "198.51.100.17, 10.2.3.4")
        == "198.51.100.17"
    )


def test_untrusted_proxy_cannot_forward_xff() -> None:
    middleware = _middleware()
    assert middleware.resolve_client_ip("172.20.1.4", "198.51.100.17") == "172.20.1.4"


def test_malformed_xff_is_ignored() -> None:
    middleware = _middleware()
    assert middleware.resolve_client_ip("10.1.2.3", "not-an-ip, also-bad") == "10.1.2.3"


def test_all_trusted_xff_hops_fail_closed_to_peer() -> None:
    middleware = _middleware()
    assert middleware.resolve_client_ip("10.1.2.3", "10.4.5.6, 10.2.3.4") == "10.1.2.3"


def test_ipv6_client_is_supported() -> None:
    middleware = _middleware()
    assert middleware.resolve_client_ip("2001:db8::1", "2001:db9::7") == "2001:db9::7"
