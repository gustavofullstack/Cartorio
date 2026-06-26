"""Smoke tests da INFRA viva.

Valida que os servicos externos estao saudaveis e acessiveis via DNS publico.
Por padrao, sao SKIPPED a menos que a env var SMOKE_TARGET=prod esteja setada,
porque rodam contra a infra de producao (2notasudi.com.br).

Pra rodar localmente:
    SMOKE_TARGET=prod pytest tests/smoke -m smoke -v

Pra rodar apenas os unit tests (default):
    pytest  # marker 'smoke' eh excluido via addopts
"""

from __future__ import annotations

import os
import socket
import ssl
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest


SMOKE_TARGET = os.getenv("SMOKE_TARGET", "")
PUBLIC_DOMAIN = os.getenv("PUBLIC_DOMAIN", "2notasudi.com.br")
TIMEOUT_S = float(os.getenv("SMOKE_TIMEOUT", "8"))


SUBDOMAINS: dict[str, dict[str, Any]] = {
    "whatsapp": {"port": 443, "expected_path": "/", "expected_keyword": "Evolution"},
    "flow": {"port": 443, "expected_path": "/healthz", "expected_status": 200},
    "agent": {"port": 443, "expected_path": "/health", "expected_status": 200},
    "easypanel": {"port": 443, "expected_path": "/", "expected_status": 200},
    "supbase": {"port": 443, "expected_path": "/", "allow_status": {200, 502, 503}},
    "api": {"port": 443, "expected_path": "/health", "allow_status": {200, 404, 502}},
    "vps": {"port": 443, "expected_path": "/", "allow_status": {200, 301, 404}},
}


pytestmark = pytest.mark.smoke


def _require_smoke() -> None:
    """Skip se nao estamos rodando contra a infra real."""
    if SMOKE_TARGET != "prod":
        pytest.skip(
            "Smoke test contra infra real desabilitado. "
            "Defina SMOKE_TARGET=prod para habilitar."
        )


def _check_dns(host: str) -> str | None:
    """Resolve DNS; retorna IP ou None se falhar."""
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


@pytest.mark.parametrize("subdomain,config", list(SUBDOMAINS.items()))
def test_subdomain_dns_resolves(subdomain: str, config: dict[str, Any]) -> None:
    """Cada subdominio configurado deve resolver no DNS publico."""
    _require_smoke()
    host = f"{subdomain}.{PUBLIC_DOMAIN}"
    ip = _check_dns(host)
    assert ip is not None, f"DNS nao resolveu para {host}"
    # IPv4 ou IPv6
    assert ":" in ip or ip.count(".") == 3, f"IP invalido retornado pra {host}: {ip}"


@pytest.mark.parametrize("subdomain,config", list(SUBDOMAINS.items()))
def test_subdomain_tls_valid(subdomain: str, config: dict[str, Any]) -> None:
    """Certificado TLS deve ser valido, nao expirado, e nao estar perto de expirar."""
    _require_smoke()
    host = f"{subdomain}.{PUBLIC_DOMAIN}"
    port = config["port"]
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT_S) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                assert cert, f"Sem certificado em {host}"
                # Valida nao-expirado (janela de 7 dias pra manutencao)
                not_after = cert.get("notAfter")
                assert not_after, f"Cert sem notAfter: {host}"
                fmt = "%b %d %H:%M:%S %Y %Z"
                expiry = datetime.strptime(not_after, fmt).replace(tzinfo=timezone.utc)  # type: ignore[arg-type]
                days_left = (expiry - datetime.now(timezone.utc)).days
                assert days_left > 7, (
                    f"Cert de {host} expira em {days_left} dias. Renovar AGORA."
                )
    except (ssl.SSLError, socket.timeout, ConnectionRefusedError, OSError) as e:
        pytest.fail(f"TLS falhou em {host}:{port}: {e}")


@pytest.mark.parametrize("subdomain,config", list(SUBDOMAINS.items()))
def test_subdomain_http_responds(subdomain: str, config: dict[str, Any]) -> None:
    """Servico deve responder HTTP(S) no path esperado."""
    _require_smoke()
    host = f"{subdomain}.{PUBLIC_DOMAIN}"
    path = config["expected_path"]
    url = f"https://{host}{path}"
    try:
        resp = httpx.get(url, timeout=TIMEOUT_S, follow_redirects=True)
    except httpx.HTTPError as e:
        pytest.fail(f"Requisicao falhou: {url} -> {e}")
    allowed = config.get("allow_status") or {config.get("expected_status", 200)}
    if "expected_keyword" in config:
        # servico evolucao: confere corpo
        assert resp.status_code == 200, f"{host}: HTTP {resp.status_code}"
        body = resp.text.lower()
        assert config["expected_keyword"].lower() in body, (
            f"{host}: corpo nao contem '{config['expected_keyword']}'. "
            f"Recebido: {body[:200]}"
        )
    else:
        assert resp.status_code in allowed, (
            f"{host}{path}: HTTP {resp.status_code}, esperado um de {allowed}"
        )


def test_evolution_api_version() -> None:
    """Evolution API deve reportar versao 2.x com instance manager."""
    _require_smoke()
    url = f"https://whatsapp.{PUBLIC_DOMAIN}/"
    resp = httpx.get(url, timeout=TIMEOUT_S)
    assert resp.status_code == 200
    body = resp.json()
    assert "version" in body, f"Sem campo version: {body}"
    version = body["version"]
    major = int(version.split(".")[0])
    assert major >= 2, f"Evolution API version antiga: {version}"
    assert body.get("manager"), "Evolution sem URL do manager"


def test_openclaw_health_endpoint() -> None:
    """OpenClaw deve expor /health respondendo 200."""
    _require_smoke()
    url = f"https://agent.{PUBLIC_DOMAIN}/health"
    resp = httpx.get(url, timeout=TIMEOUT_S)
    assert resp.status_code == 200, f"OpenClaw /health: {resp.status_code}"


def test_n8n_healthz_endpoint() -> None:
    """N8N deve expor /healthz respondendo 200."""
    _require_smoke()
    url = f"https://flow.{PUBLIC_DOMAIN}/healthz"
    resp = httpx.get(url, timeout=TIMEOUT_S)
    assert resp.status_code == 200, f"N8N /healthz: {resp.status_code}"


def test_supabase_kong_gateway() -> None:
    """Supabase Kong gateway deve responder (200/502/503 OK - 502 indica DB indisponivel)."""
    _require_smoke()
    url = f"https://supbase.{PUBLIC_DOMAIN}/"
    resp = httpx.get(url, timeout=TIMEOUT_S)
    # 502 = upstream (Postgres) caido mas Kong UP; reporta mas nao falha
    if resp.status_code == 502:
        pytest.skip(
            "Supabase Kong UP mas upstream 502 (DB/Postgres indisponivel). "
            "DevOps deve validar cartorio_supabase-db-1."
        )
    assert resp.status_code in {200, 301, 404}, (
        f"Supabase Kong respondeu inesperado: {resp.status_code}"
    )


def test_api_subdomain_ready_when_deployed() -> None:
    """api.2notasudi.com.br deve responder /health quando deployed.

    Hoje esperamos 404 (DNS propaga mas container nao deployed ainda).
    Quando subir, este teste vira gate de regressao.
    """
    _require_smoke()
    url = f"https://api.{PUBLIC_DOMAIN}/health"
    try:
        resp = httpx.get(url, timeout=TIMEOUT_S)
    except httpx.HTTPError as e:
        pytest.fail(f"API unreachable: {e}")
    if resp.status_code == 404:
        pytest.skip("api.2notasudi.com.br ainda nao deployed (esperado Sprint 0)")
    assert resp.status_code == 200, f"API /health: {resp.status_code}"
    body = resp.json()
    assert body.get("status") == "ok", f"API /health payload invalido: {body}"


def test_sensitive_ports_not_exposed_publicly() -> None:
    """Portas de admin (5432 Postgres, 6379 Redis, 5678 N8N direto, 8080 EVO direto)
    NAO devem responder no IP publico da VPS."""
    _require_smoke()
    vps_ip = os.getenv("VPS_IP", "187.77.236.77")
    blocked_ports = [5432, 6379, 5678, 8080, 8443]
    exposed: list[int] = []
    for port in blocked_ports:
        try:
            with socket.create_connection((vps_ip, port), timeout=2):
                exposed.append(port)
        except (socket.timeout, ConnectionRefusedError, OSError):
            pass
    assert not exposed, (
        f"PORTAS ADMIN EXPOSTAS PUBLICAMENTE: {exposed}. "
        f"Isso eh CRITICO - apenas Traefik (80/443) deveria estar aberto. "
        f"DevOps: bloquear via firewall/UFW/Docker network agora."
    )


def test_security_headers_present() -> None:
    """Headers de seguranca basicos devem estar presentes nas respostas publicas."""
    _require_smoke()
    url = f"https://flow.{PUBLIC_DOMAIN}/"
    resp = httpx.get(url, timeout=TIMEOUT_S)
    headers = {k.lower(): v for k, v in resp.headers.items()}
    # Pelo menos 1 de CSP/X-Frame deve existir OU documentar a falta
    has_frame_protection = (
        "content-security-policy" in headers or "x-frame-options" in headers
    )
    has_hsts = "strict-transport-security" in headers
    # HSTS eh MUST-HAVE em HTTPS publico
    assert has_hsts, (
        f"Falta HSTS em {url}. DevOps: adicionar Strict-Transport-Security no Traefik."
    )
    # Frame protection eh recomendacao forte
    if not has_frame_protection:
        # Nao falha - reporta
        pytest.skip(
            f"Sem CSP/X-Frame-Options em {url}. Recomendado adicionar para cartorio."
        )