# Modified by Gustavo Almeida
"""Testes de segurança do TrustedProxyMiddleware (E3.04)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware.trusted_proxy import TrustedProxyMiddleware

app = FastAPI()
app.add_middleware(TrustedProxyMiddleware)


@app.get("/test-ip")
def get_ip(request: Request) -> dict[str, str]:
    return {"client_ip": request.client.host if request.client else "unknown"}


client = TestClient(app)


def test_trusted_proxy_direct_untrusted_peer_ignores_fake_xff() -> None:
    """Cliente direto não confiável enviando XFF falso tem o XFF ignorado."""
    # TestClient por padrão usa client ('127.0.0.1', 50000). Para simular peer não confiável,
    # instanciamos a classe diretamente.
    mw = TrustedProxyMiddleware(app=None)
    resolved = mw.resolve_client_ip(direct_ip="198.51.100.42", xff_header="1.1.1.1, 2.2.2.2")
    assert resolved == "198.51.100.42"


def test_trusted_proxy_trusted_peer_parses_valid_xff() -> None:
    """Proxy confiável (127.0.0.1 ou 172.16.x.x) repassando XFF extrai o IP real do cliente."""
    mw = TrustedProxyMiddleware(app=None)
    resolved = mw.resolve_client_ip(direct_ip="127.0.0.1", xff_header="203.0.113.195, 172.16.0.10")
    assert resolved == "203.0.113.195"


def test_trusted_proxy_multiple_hops_extracts_first_untrusted() -> None:
    """Vários hops no XFF extrai o primeiro IP público/não-confiável a partir da direita."""
    mw = TrustedProxyMiddleware(app=None)
    resolved = mw.resolve_client_ip(
        direct_ip="172.16.0.1",
        xff_header="198.51.100.50, 10.0.0.4, 172.16.0.2",
    )
    assert resolved == "198.51.100.50"


def test_trusted_proxy_malformed_ip_fallback() -> None:
    """IP malformado no XFF não gera exceção e faz fallback seguro."""
    mw = TrustedProxyMiddleware(app=None)
    resolved = mw.resolve_client_ip(direct_ip="127.0.0.1", xff_header="not_an_ip, 203.0.113.10")
    assert resolved == "203.0.113.10"

    # Se todos forem inválidos, fallback para o direct_ip
    resolved_invalid = mw.resolve_client_ip(direct_ip="127.0.0.1", xff_header="garbage_only")
    assert resolved_invalid == "127.0.0.1"


def test_trusted_proxy_ipv6_support() -> None:
    """Suporte a endereços IPv4 e IPv6."""
    mw = TrustedProxyMiddleware(app=None)
    resolved = mw.resolve_client_ip(direct_ip="::1", xff_header="2001:db8::1, 10.0.0.1")
    assert resolved == "2001:db8::1"


def test_trusted_proxy_http_client_integration() -> None:
    """Integração via TestClient (que conecta via 127.0.0.1 localmente)."""
    response = client.get("/test-ip", headers={"X-Forwarded-For": "203.0.113.99"})
    assert response.status_code == 200
    assert response.json()["client_ip"] == "203.0.113.99"
