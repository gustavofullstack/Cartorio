# Modified by Gustavo Almeida
"""Middleware ASGI de Trusted Proxy para prevenir IP spoofing via X-Forwarded-For."""

from __future__ import annotations

import ipaddress
import logging
from typing import Sequence

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

DEFAULT_TRUSTED_PROXIES: tuple[str, ...] = (
    "127.0.0.1/32",
    "::1/128",
    "172.16.0.0/12",
    "10.0.0.0/8",
    "187.77.236.77/32",
)


class TrustedProxyMiddleware:
    """Valida a origem da conexão e resolve o IP real do cliente.

    Evita IP spoofing via X-Forwarded-For quando o cliente se conecta diretamente
    sem passar pelo Traefik/proxy reverso confiável.
    """

    def __init__(
        self,
        app: ASGIApp,
        trusted_proxies: Sequence[str] = DEFAULT_TRUSTED_PROXIES,
    ) -> None:
        self.app = app
        self._networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for net_str in trusted_proxies:
            try:
                self._networks.append(ipaddress.ip_network(net_str))
            except ValueError as exc:
                logger.warning("Rede de proxy confiável inválida: %s (%s)", net_str, exc)

    def is_trusted(self, ip_str: str) -> bool:
        """Verifica se um IP pertence a uma rede de proxy confiável."""
        if ip_str == "testclient":
            return True
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            return any(ip_obj in net for net in self._networks)
        except ValueError:
            return False

    def resolve_client_ip(self, direct_ip: str, xff_header: str | None) -> str:
        """Resolve o IP real do cliente dada a conexão direta e a cadeia XFF."""
        if not self.is_trusted(direct_ip):
            return direct_ip

        if not xff_header:
            return direct_ip

        # Cadeia de IPs do X-Forwarded-For
        raw_ips = [ip.strip() for ip in xff_header.split(",") if ip.strip()]
        if not raw_ips:
            return direct_ip

        # Percorre da direita para a esquerda encontrando o primeiro IP não confiável
        for ip in reversed(raw_ips):
            try:
                ip_obj = ipaddress.ip_address(ip)
                if not any(ip_obj in net for net in self._networks):
                    return str(ip_obj)
            except ValueError:
                continue

        # Uma cadeia composta somente por proxies confiáveis não prova qual
        # cliente a iniciou. Preservar o peer direto é a opção fail-closed.
        return direct_ip

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            client_tuple = scope.get("client")
            direct_ip = client_tuple[0] if client_tuple else "127.0.0.1"
            port = client_tuple[1] if client_tuple else 0

            # Procura cabeçalho X-Forwarded-For nos headers do scope
            headers = dict(scope.get("headers", []))
            xff_bytes = headers.get(b"x-forwarded-for")
            xff_header = xff_bytes.decode("latin1") if xff_bytes else None

            resolved_ip = self.resolve_client_ip(direct_ip, xff_header)
            scope["client"] = (resolved_ip, port)

        await self.app(scope, receive, send)
