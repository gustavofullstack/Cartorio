"""HTTP authentication boundary for the Cartorio MCP transport.

FastMCP tools are available over a separate ASGI sub-application, so the
FastAPI dependency system does not run for requests to ``/mcp``.  This
middleware protects that boundary before a JSON-RPC request can create an MCP
session or invoke a tool.
"""

from __future__ import annotations

import hmac
import json
from typing import Any, Literal

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

MCP_AUTH_SCHEME = "Bearer"
MCP_PUBLIC_ALLOWED_TOOL = "cartorio_calcular_emolumento"
MCP_PUBLIC_ALLOWED_METHODS = frozenset(
    {"initialize", "notifications/initialized", "ping", "tools/list", "tools/call"}
)
DEFAULT_MCP_PUBLIC_MAX_BODY_BYTES = 16_384
MCPProfile = Literal["internal", "public"]


class MCPBodyTooLargeError(ValueError):
    """Raised before parsing a public MCP body that exceeds the configured limit."""


class MCPApiKeyMiddleware:
    """Authenticate MCP credentials and apply the public least-privilege profile.

    An absent server-side key is an operational error, not permission to
    expose tools.  Returning 503 fails closed while distinguishing it from an
    invalid client credential (401), without logging or returning the key.
    """

    def __init__(
        self,
        app: ASGIApp,
        api_key: str | None,
        public_api_key: str | None = None,
        public_app: ASGIApp | None = None,
        public_max_body_bytes: int = DEFAULT_MCP_PUBLIC_MAX_BODY_BYTES,
    ) -> None:
        self.app = app
        self.api_key = api_key.strip() if api_key else None
        self.public_api_key = public_api_key.strip() if public_api_key else None
        self.public_app = public_app
        self.public_max_body_bytes = public_max_body_bytes

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
        profile = self._credential_profile(provided)
        if profile is None:
            await self._send_error(
                scope,
                receive,
                send,
                status_code=401,
                detail="MCP authentication required.",
            )
            return

        if profile == "internal":
            await self.app(scope, receive, send)
            return

        framing_error = self._public_framing_error(scope)
        if framing_error is not None:
            status_code, detail = framing_error
            await self._send_error(
                scope,
                receive,
                send,
                status_code=status_code,
                detail=detail,
            )
            return

        try:
            body = await self._read_body(receive, self.public_max_body_bytes)
        except MCPBodyTooLargeError:
            await self._send_error(
                scope,
                receive,
                send,
                status_code=413,
                detail="MCP public request body is too large.",
            )
            return
        request_data = self._json_rpc_request(body)
        if request_data is None or not self._public_request_is_allowed(request_data):
            await self._send_error(
                scope,
                receive,
                send,
                status_code=403,
                detail="MCP public profile is limited to emolumento consultation.",
            )
            return

        if self.public_app is None:
            await self._send_error(
                scope,
                receive,
                send,
                status_code=503,
                detail="MCP public profile is not configured.",
            )
            return
        await self._call_public_app(scope, receive, body, self.public_app, send)

    def _credential_profile(self, provided: str | None) -> MCPProfile | None:
        internal_api_key = self.api_key
        if not provided or internal_api_key is None:
            return None
        if self.public_api_key and hmac.compare_digest(provided, self.public_api_key):
            if hmac.compare_digest(self.public_api_key, internal_api_key):
                return None
            return "public"
        if hmac.compare_digest(provided, internal_api_key):
            return "internal"
        return None

    @staticmethod
    def _bearer_token(request: Request) -> str | None:
        authorization = request.headers.get("authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if (
            not separator
            or scheme.casefold() != MCP_AUTH_SCHEME.casefold()
            or not token
            or token != token.strip()
            or any(character.isspace() for character in token)
        ):
            return None
        return token

    def _public_framing_error(self, scope: Scope) -> tuple[int, str] | None:
        """Validate public-request framing without collapsing duplicate headers.

        ``Request.headers`` exposes a convenient mapping, but it loses repeated
        ``Content-Length`` values.  Inspecting ASGI's raw header list keeps the
        request boundary fail-closed against ambiguous HTTP message framing.
        """

        raw_headers = scope.get("headers", ())
        content_lengths = [
            value for name, value in raw_headers if name.lower() == b"content-length"
        ]
        transfer_encodings = [
            value for name, value in raw_headers if name.lower() == b"transfer-encoding"
        ]

        if len(content_lengths) > 1:
            return 400, "Invalid MCP public HTTP framing."
        if content_lengths and transfer_encodings:
            return 400, "Invalid MCP public HTTP framing."

        if content_lengths:
            content_length = content_lengths[0]
            if not content_length or not all(48 <= byte <= 57 for byte in content_length):
                return 400, "Invalid MCP public HTTP framing."
            if int(content_length) > self.public_max_body_bytes:
                return 413, "MCP public request body is too large."

        if transfer_encodings:
            if len(transfer_encodings) != 1 or transfer_encodings[0].strip().lower() != b"chunked":
                return 400, "Invalid MCP public HTTP framing."

        return None

    @staticmethod
    async def _read_body(receive: Receive, maximum_bytes: int) -> bytes:
        chunks: list[bytes] = []
        received_bytes = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return b""
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            received_bytes += len(chunk)
            if received_bytes > maximum_bytes:
                raise MCPBodyTooLargeError
            chunks.append(chunk)
            if not message.get("more_body", False):
                return b"".join(chunks)

    @staticmethod
    def _json_rpc_request(body: bytes) -> dict[str, Any] | None:
        try:
            data = json.loads(body)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _public_request_is_allowed(request_data: dict[str, Any]) -> bool:
        method = request_data.get("method")
        if method not in MCP_PUBLIC_ALLOWED_METHODS:
            return False
        if method != "tools/call":
            return True
        params = request_data.get("params")
        return isinstance(params, dict) and params.get("name") == MCP_PUBLIC_ALLOWED_TOOL

    async def _call_public_app(
        self,
        scope: Scope,
        receive: Receive,
        body: bytes,
        public_app: ASGIApp,
        send: Send,
    ) -> None:
        request_replayed = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal request_replayed
            if request_replayed:
                return dict(await receive())
            request_replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await public_app(scope, replay_receive, send)

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


__all__ = [
    "MCP_AUTH_SCHEME",
    "DEFAULT_MCP_PUBLIC_MAX_BODY_BYTES",
    "MCP_PUBLIC_ALLOWED_TOOL",
    "MCPApiKeyMiddleware",
]
