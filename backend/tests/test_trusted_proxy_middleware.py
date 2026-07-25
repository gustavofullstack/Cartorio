"""Regressões de confiança de proxy para identidade de IP.

O teste isola o limite ASGI: uma conexão direta nunca pode escolher seu IP
efetivo com X-Forwarded-For; somente um proxy configurado pode encaminhá-lo.

Mapa dos 9 cenários E3.04 (✓ = coberto neste arquivo ou em test_trusted_proxy.py):
1. direct + fake XFF ............... test_direct_client_cannot_spoof_xff ✓
2. trusted proxy + valid XFF ....... test_trusted_proxy_uses_rightmost_untrusted_xff_hop ✓
3. untrusted + XFF ................. test_untrusted_proxy_cannot_forward_xff ✓
4. múltiplos hops .................. test_multiple_hops_pick_first_public_from_right ✓
5. IP malformado ................... test_malformed_xff_is_ignored ✓
6. IPv4 ............................ test_ipv4_single_hop_xff ✓
7. IPv6 ............................ test_ipv6_client_is_supported ✓ (+ multi-hop IPv6)
8. localhost/test client ........... test_localhost_and_testclient_peers_are_trusted ✓
9. rate-limit não bypassável ....... test_direct_request_fake_xff_keeps_rate_limit_bucket ✓
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "a" * 64)

import pytest  # noqa: E402

import app.services.rate_limit_by_key as rlbk  # noqa: E402
from app.middleware.trusted_proxy import TrustedProxyMiddleware  # noqa: E402


def _middleware() -> TrustedProxyMiddleware:
    async def app(scope: object, receive: object, send: object) -> None:
        return None

    return TrustedProxyMiddleware(app, trusted_proxies=("10.0.0.0/8", "2001:db8::/32"))


def test_direct_client_cannot_spoof_xff() -> None:
    middleware = _middleware()
    assert middleware.resolve_client_ip("198.51.100.17", "203.0.113.9") == "198.51.100.17"


def test_trusted_proxy_uses_rightmost_untrusted_xff_hop() -> None:
    middleware = _middleware()
    assert middleware.resolve_client_ip("10.1.2.3", "198.51.100.17, 10.2.3.4") == "198.51.100.17"


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


def test_multiple_hops_pick_first_public_from_right() -> None:
    """Cadeia longa: percorre da direita e ancora no primeiro hop NAO confiável."""
    middleware = _middleware()
    assert (
        middleware.resolve_client_ip(
            "10.0.0.2",
            "203.0.113.9, 10.0.0.9, 2001:db9::5, 10.0.0.8",
        )
        == "2001:db9::5"
    )


def test_ipv4_single_hop_xff() -> None:
    """IPv4 simples via proxy confiável resolve para o IP encaminhado."""
    middleware = _middleware()
    assert middleware.resolve_client_ip("10.0.0.1", "192.0.2.44") == "192.0.2.44"


def test_ipv6_multiple_hops_xff() -> None:
    """Cadeia IPv6 com hops confiáveis no fim ancora no primeiro público."""
    middleware = _middleware()
    assert middleware.resolve_client_ip("2001:db8::1", "2001:db9::7, 2001:db8::2") == "2001:db9::7"


def test_localhost_and_testclient_peers_are_trusted() -> None:
    """Loopback (v4/v6) e o peer 'testclient' do TestClient são confiáveis."""
    middleware = TrustedProxyMiddleware(app=None)  # type: ignore[arg-type]
    assert middleware.is_trusted("127.0.0.1")
    assert middleware.is_trusted("::1")
    assert middleware.is_trusted("testclient")
    assert not middleware.is_trusted("203.0.113.1")
    # Peer loopback com XFF resolve o IP encaminhado (integração TestClient).
    assert middleware.resolve_client_ip("127.0.0.1", "198.51.100.23") == "198.51.100.23"


@pytest.mark.asyncio
async def test_direct_request_fake_xff_keeps_rate_limit_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E3.04 (cenário 9): rate limit NÃO é bypassável via XFF forjado.

    Dois requests da MESMA conexão direta (peer não confiável) com XFFs
    forjados DIFERENTES devem cair no MESMO bucket de rate limit (derivado
    do IP real do peer). Se o XFF mudasse o bucket, o atacante rotacionaria
    o header e nunca atingiria o limite por IP.
    """
    resolved_peers: list[tuple[str, int] | None] = []

    async def recorder_app(scope, receive, send) -> None:  # noqa: ANN001, ANN202
        resolved_peers.append(scope.get("client"))
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b"{}"})

    # Chain real: TrustedProxy (borda) -> RateLimitByKey (consome scope["client"]).
    rate_limit = rlbk.RateLimitByKeyMiddleware(app=recorder_app, redis_url="redis://fake")
    chain = TrustedProxyMiddleware(rate_limit, trusted_proxies=("10.0.0.0/8",))

    incr_keys: list[str] = []
    pipe = MagicMock()
    pipe.incr.side_effect = lambda key: incr_keys.append(key)
    pipe.expire.return_value = None
    pipe.execute = AsyncMock(return_value=[1, True])
    redis_client = MagicMock()
    redis_client.pipeline = MagicMock(return_value=pipe)
    redis_client.ping = AsyncMock(return_value=True)

    monkeypatch.setattr(rlbk.redis_async, "from_url", lambda *a, **k: redis_client)
    # Tempo congelado: elimina flake de virada de minuto nas chaves de bucket.
    monkeypatch.setattr(rlbk.time, "time", lambda: 1_700_000_000.0)

    async def _sliding_allow(*args, **kwargs):  # noqa: ANN001, ANN202
        from app.services.sliding_window import SlidingWindowResult

        return SlidingWindowResult(allowed=True, current=0, limit=100, retry_after=0)

    monkeypatch.setattr(rlbk, "sliding_window_check", _sliding_allow)

    async def run_request(fake_xff: str) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [(b"x-forwarded-for", fake_xff.encode("latin1"))],
            "client": ("198.51.100.10", 5555),  # peer direto NAO confiável
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
        }

        async def receive():  # noqa: ANN202
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message) -> None:  # noqa: ANN001
            return None

        await chain(scope, receive, send)

    await run_request("1.2.3.4")
    await run_request("5.6.7.8")

    # 1) TrustedProxy: peer direto não confiável => XFF ignorado nos DOIS requests.
    assert resolved_peers == [("198.51.100.10", 5555), ("198.51.100.10", 5555)]

    # 2) Rate limit: buckets derivados do IP REAL (hash), nunca do XFF forjado.
    real_hash = rlbk._hash_api_key("ip:198.51.100.10")
    spoofed_hashes = {rlbk._hash_api_key("ip:1.2.3.4"), rlbk._hash_api_key("ip:5.6.7.8")}

    ddos_keys = [k for k in incr_keys if k.startswith("ratelimit:ip:")]
    tier_keys = [k for k in incr_keys if k.startswith("ratelimit:apikey:")]
    assert len(ddos_keys) == 2
    assert len(set(ddos_keys)) == 1, "XFF forjado mudou o bucket DDoS por IP"
    assert len(tier_keys) == 2
    assert len(set(tier_keys)) == 1, "XFF forjado mudou o bucket por tier"
    assert real_hash in ddos_keys[0]
    assert real_hash in tier_keys[0]
    assert not any(any(s in k for s in spoofed_hashes) for k in incr_keys)
