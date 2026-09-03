"""CORS: métodos e headers explícitos em vez de curinga.

Origem do achado: Jules, 2026-09-02 — "Overly Permissive CORS Configuration".
A origem já era restrita a uma allowlist (produção rejeita origem desconhecida),
então isso é endurecimento, não fechamento de buraco aberto. Estes testes travam
as duas pontas: o curinga não volta, e a allowlist de origem continua valendo.
"""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

ORIGEM_PERMITIDA = "https://app.2notasudi.com.br"
ORIGEM_DESCONHECIDA = "https://evil.example.com"


class TestConfiguracao:
    def test_metodos_nao_usam_curinga(self):
        assert "*" not in settings.cors_allow_methods

    def test_headers_nao_usam_curinga(self):
        assert "*" not in settings.cors_allow_headers

    def test_metodos_cobrem_os_verbos_que_a_api_expoe(self):
        for verbo in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            assert verbo in settings.cors_allow_methods, verbo

    def test_headers_cobrem_os_que_o_codigo_le(self):
        # Derivados de middleware/, api/deps.py e main.py. Perder um destes
        # quebra cliente de navegador em produção.
        lower = {h.lower() for h in settings.cors_allow_headers}
        for header in (
            "authorization",
            "content-type",
            "idempotency-key",
            "x-idempotency-key",
            "x-api-key",
            "x-canal",
            "x-correlation-id",
            "x-request-id",
        ):
            assert header in lower, header


class TestPreflight:
    def test_origem_permitida_recebe_allow_origin(self):
        r = client.options(
            "/health",
            headers={
                "Origin": ORIGEM_PERMITIDA,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert r.headers.get("access-control-allow-origin") == ORIGEM_PERMITIDA

    def test_origem_desconhecida_nao_recebe_allow_origin(self):
        r = client.options(
            "/health",
            headers={
                "Origin": ORIGEM_DESCONHECIDA,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in r.headers

    def test_preflight_nao_ecoa_header_arbitrario(self):
        # Com allow_headers="*" o Starlette refletia qualquer header pedido.
        r = client.options(
            "/health",
            headers={
                "Origin": ORIGEM_PERMITIDA,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-header-inventado",
            },
        )
        permitidos = r.headers.get("access-control-allow-headers", "").lower()
        assert "x-header-inventado" not in permitidos
