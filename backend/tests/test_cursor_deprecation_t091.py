"""T091 — Coverage boost: cursor.py + deprecation.py (v22 plan).

Era 47.4% + 42.9% respectivamente; alvo: >=80% cada.
"""

from __future__ import annotations

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.deprecation import (
    DeprecationHeadersMiddleware,
    V1_SUNSET_DT,
    V1_SUNSET_RFC7231,
    _build_v2_link,
)
from app.services.cursor import decode_cursor, decode_cursor_safe, encode_cursor


# ============================================================================
# Cursor — pure functions
# ============================================================================


class TestCursorEncodeDecode:
    def test_encode_then_decode_roundtrip(self):
        original = {"id_after": 42, "filtro": "x"}
        cursor = encode_cursor(original)
        assert isinstance(cursor, str)
        assert decode_cursor(cursor) == original

    def test_encode_is_opaque_base64_url_safe(self):
        """Encode deve produzir base64 url-safe SEM padding."""
        cursor = encode_cursor({"id_after": 1})
        assert "=" not in cursor
        # urlsafe: - e _ em vez de + e /
        assert "+" not in cursor
        assert "/" not in cursor

    def test_decode_valid_cursor_returns_dict(self):
        payload = {"id_after": 7}
        cursor = encode_cursor(payload)
        assert decode_cursor(cursor) == payload

    def test_decode_invalid_base64_raises_value_error(self):
        with pytest.raises(ValueError):
            decode_cursor("!!!not-base64!!!")

    def test_decode_invalid_json_raises_value_error(self):
        # base64 valido mas nao-JSON
        bad = base64.urlsafe_b64encode(b"not json at all").decode().rstrip("=")
        with pytest.raises(ValueError):
            decode_cursor(bad)


class TestCursorSafe:
    def test_safe_returns_key_value_when_valid(self):
        cursor = encode_cursor({"id_after": 99})
        assert decode_cursor_safe(cursor, "id_after") == 99

    def test_safe_returns_none_when_malformed(self):
        assert decode_cursor_safe("!!!invalid!!!", "id_after") is None

    def test_safe_returns_none_when_key_missing(self):
        cursor = encode_cursor({"other_key": "x"})
        assert decode_cursor_safe(cursor, "id_after") is None

    def test_safe_returns_none_on_empty_string(self):
        assert decode_cursor_safe("", "id_after") is None


# ============================================================================
# Deprecation middleware
# ============================================================================


class TestBuildV2Link:
    def test_converts_v1_to_v2_preserving_path(self):
        assert _build_v2_link("/api/v1/clientes") == "/api/v2/clientes"

    def test_handles_nested_path(self):
        assert _build_v2_link("/api/v1/protocolo/42") == "/api/v2/protocolo/42"

    def test_non_v1_path_defaults_to_v2_root(self):
        assert _build_v2_link("/health") == "/api/v2/"

    def test_empty_string_defaults_to_v2_root(self):
        assert _build_v2_link("") == "/api/v2/"


@pytest.fixture
def deprecation_app():
    app = FastAPI()
    app.add_middleware(DeprecationHeadersMiddleware)

    @app.get("/api/v1/clientes")
    def list_clientes():
        return {"clientes": []}

    @app.get("/api/v2/clientes")
    def list_clientes_v2():
        return {"clientes": [], "version": "v2"}

    @app.get("/health/live")
    def health():
        return {"status": "ok"}

    return app


def test_v1_path_gets_deprecation_headers(deprecation_app):
    client = TestClient(deprecation_app)
    r = client.get("/api/v1/clientes")
    assert r.status_code == 200
    assert r.headers.get("Deprecation") == "true"
    assert r.headers.get("Sunset") == V1_SUNSET_RFC7231
    assert r.headers.get("Link") == '</api/v2/clientes>; rel="successor-version"'


def test_v2_path_does_not_get_deprecation_headers(deprecation_app):
    client = TestClient(deprecation_app)
    r = client.get("/api/v2/clientes")
    assert r.status_code == 200
    assert "Deprecation" not in r.headers
    assert "Sunset" not in r.headers
    assert "Link" not in r.headers


def test_health_path_does_not_get_deprecation_headers(deprecation_app):
    client = TestClient(deprecation_app)
    r = client.get("/health/live")
    assert r.status_code == 200
    assert "Deprecation" not in r.headers


def test_v1_sunset_constant_is_2027_12_31():
    """Sunset canonico: 2027-12-31 00:00:00 UTC."""
    assert V1_SUNSET_DT.year == 2027
    assert V1_SUNSET_DT.month == 12
    assert V1_SUNSET_DT.day == 31
    assert V1_SUNSET_DT.tzinfo is not None
