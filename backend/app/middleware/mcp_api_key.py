"""HTTP authentication boundary for the Cartorio MCP transport.

FastMCP tools are available over a separate ASGI sub-application, so the
FastAPI dependency system does not run for requests to ``/mcp``.  This
middleware protects that boundary before a JSON-RPC request can create an MCP
session or invoke a tool.
"""

from __future__ import annotations

import hmac

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

MCP_AUTH_SCHEME = "Bearer"


class MCPApiKeyMiddleware:
    """Require a configured bearer API key for every MCP HTTP request.

    An absent server-side key is an operational error, not permission to
    expose tools.  Returning 503 fails closed while distinguishing it from an
    invalid client credential (401), without logging or returning the key.
    """

    def __init__(self, app: ASGIApp, api_key: str | None) -> None:
        self.app = app
        self.api_key = api_key.strip() if api_key else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.api_key:
            await self._send_error(
                scope,
                receive,
                send,
                status_code=503,
                detail="MCP authentication is not configured.",
            )
            return

        provided = self._bearer_token(Request(scope=scope))
        if not provided or not hmac.compare_digest(provided, self.api_key):
            await self._send_error(
                scope,
                receive,
                send,
                status_code=401,
                detail="MCP authentication required.",
            )
            return

        await self.app(scope, receive, send)

    @staticmethod
    def _bearer_token(request: Request) -> str | None:
        authorization = request.headers.get("authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.casefold() != MCP_AUTH_SCHEME.casefold():
            return None
        return token.strip() or None

    @staticmethod
    async def _send_error(
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        detail: str,
    ) -> None:
        response: Response = JSONResponse(
            status_code=status_code,
            content={"detail": detail},
            headers={"WWW-Authenticate": MCP_AUTH_SCHEME},
        )
        await response(scope, receive, send)


__all__ = ["MCP_AUTH_SCHEME", "MCPApiKeyMiddleware"]
