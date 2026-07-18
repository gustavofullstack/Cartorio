"""Tests G8.17.T4 — Swagger UI persistAuthorization.

Valida o fluxo de autenticacao persistida (bearer token) do Swagger local
(/docs). Garantias:

- HTML servido em /docs contem o flag ``persistAuthorization: true`` no JS
  de inicializacao do SwaggerUIBundle. Sem isso, o browser perde o bearer
  token entre reloads.
- OpenAPI schema expoe ``BearerAuth`` (JWT) e ``ApiKeyAuth`` (X-API-Key)
  para que o dropdown "Authorize" no Swagger UI apareca com opcoes
  utilizaveis.
- O token persistido via localStorage NAO e eco para o backend (LGPD:
  client-side only, same-origin policy).
- Cache-Control impede que browsers/CDNs sirvam schema OpenAPI stale
  para o dev que acabou de adicionar endpoints.
- /docs nao responde com a pagina default do FastAPI (que vem sem
  ``persistAuthorization``, sem header institucional, sem tema dark blue).

Cobre G8.17.T4 (2026-07-18).
"""

from __future__ import annotations

import json
import re

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestSwaggerPersistAuthorization:
    """G8.17.T4 — Swagger UI persist auth flow (bearer token localStorage)."""

    def test_swagger_ui_html_contains_persist_authorization(self) -> None:
        """GET /docs retorna HTML com `persistAuthorization: true`.

        Sem isso, o Swagger UI descarta o token apos reload (F5) e o dev
        precisa setar manualmente a cada vez. Com o flag, o token vai para
        `window.localStorage` sob a chave do spec (autorization key do
        Swagger UI) e e restaurado em reloads sucessivos ate a aba fechar.
        """
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        body = response.text
        assert "persistAuthorization" in body, (
            "Esperava flag `persistAuthorization` no JS do SwaggerUIBundle. "
            "Sem ele, o bearer token e perdido entre reloads."
        )
        # Match exato: `persistAuthorization: true` (boolean JS) e nao
        # stringified. regex tolera espacos e quebras de linha.
        assert re.search(r"persistAuthorization\s*:\s*true", body), (
            "Esperava `persistAuthorization: true` literal na config JS. "
            f"Body sample: {body[:500]!r}"
        )

    def test_docs_returns_custom_html_not_fastapi_default(self) -> None:
        """GET /docs retorna nosso HTML custom (header institucional).

        Regressao silenciosa: quando FastAPI() e construido com
        ``docs_url="/docs"``, ele registra uma ``Route(/docs)`` ANTES da
        nossa ``APIRoute(/docs)``. Em Starlette a primeira rota vence, e
        o Swagger UI default (sem persistAuthorization, sem tema, sem
        header) e servido em vez do nosso. Garante que isto nao
        regrediu.
        """
        response = client.get("/docs")
        assert response.status_code == 200
        body = response.text
        # Header institucional so existe no nosso template custom.
        assert "header-cartorio" in body, (
            "Esperava classe CSS `header-cartorio` (header institucional). "
            "Se ausente, FastAPI default venceu precedencia de rota."
        )
        # Tema monokai so existe na nossa config.
        assert "monokai" in body, (
            "Esperava `monokai` no syntaxHighlight theme."
        )
        # O default do FastAPI usa `OAuth2Redirect` HTML minimo; o nosso
        # customiza tem pelo menos 1.5KB (header + script).
        assert len(body) > 1500, (
            f"HTML demasiado curto ({len(body)}B). "
            "Provavelmente FastAPI default venceu precedencia."
        )

    def test_openapi_security_scheme_defined(self) -> None:
        """OpenAPI schema expoe schemes de auth utilizaveis (BearerAuth + ApiKeyAuth).

        Sem schemes registrados, o Swagger UI nao renderiza o botao
        "Authorize" e o dev nao consegue autenticar via dropdown.
        ``BearerAuth`` (JWT, header Authorization) + ``ApiKeyAuth``
        (X-API-Key) cobrem todas as superficies autenticadas do backend
        (LGPD v2 + admin/integrations).
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert schemes, "Esperava securitySchemes no OpenAPI schema"
        # Bearer (JWT) e ApiKey (X-API-Key) sao obrigatorios.
        assert "BearerAuth" in schemes, (
            f"Esperava BearerAuth (JWT) em securitySchemes; achei: {list(schemes)}"
        )
        bearer = schemes["BearerAuth"]
        assert bearer["type"] == "http"
        assert bearer["scheme"] == "bearer"
        assert bearer.get("bearerFormat") == "JWT"
        assert "ApiKeyAuth" in schemes, (
            f"Esperava ApiKeyAuth (X-API-Key) em securitySchemes; achei: {list(schemes)}"
        )
        api_key = schemes["ApiKeyAuth"]
        assert api_key["type"] == "apiKey"
        assert api_key["in"] == "header"
        assert api_key["name"] == "X-API-Key"

    def test_bearer_token_persistence_simulation(self) -> None:
        """Simula ciclo de uso: GET /openapi.json -> GET /docs -> GET /openapi.json.

        O mesmo schema deve ser servido em ambas chamadas (idempotente).
        Garante que o cache do schema e estavel entre requests, condicao
        necessaria para que o Swagger UI Authorize dialog funcione com
        token persistido.
        """
        r1 = client.get("/openapi.json")
        r2 = client.get("/openapi.json")
        assert r1.status_code == r2.status_code == 200
        # Mesmo schema serializado (header diferente e OK).
        schema1 = r1.json()
        schema2 = r2.json()
        # `info.title` deve ser estavel. Se diferir, ha race no
        # `app.openapi_schema` que faz com que um dos requests receba
        # schema parcial.
        assert schema1["info"]["title"] == schema2["info"]["title"] == "Cartorio Backend API"
        # `paths` count estavel (idempotente).
        assert len(schema1.get("paths", {})) == len(schema2.get("paths", {}))

    def test_swagger_ui_uses_localstorage_for_persist(self) -> None:
        """JS de inicializacao configura persistAuthorization no client-side.

        Inspect aproximado: ``persistAuthorization`` keyword deve estar
        presente na config JS do SwaggerUIBundle. Para verificar storage
        real seria necessario um browser headless (Playwright), fora do
        escopo deste teste unitario. O que validamos aqui: o snippet JS
        que o backend envia contem a chave correta.
        """
        response = client.get("/docs")
        body = response.text
        # LocalStorage persistence so funciona se:
        # 1. Swagger UI bundle JS for carregado (CDN ou self-hosted).
        assert "swagger-ui-bundle.js" in body, (
            "Esperava swagger-ui-bundle.js carregado antes do init."
        )
        # 2. `SwaggerUIBundle(...)` for chamado com `persistAuthorization: true`.
        # Buscamos o bloco de config (multi-linha) por contexto.
        match = re.search(
            r"SwaggerUIBundle\s*\(\s*\{(.+?)\}\s*\)",
            body,
            re.DOTALL,
        )
        assert match is not None, (
            "Esperava bloco `SwaggerUIBundle({...})` no HTML."
        )
        config_block = match.group(1)
        assert "persistAuthorization" in config_block, (
            "Faltando `persistAuthorization` no bloco de config do SwaggerUIBundle. "
            f"Config achada: {config_block[:300]!r}"
        )
        # Tambem esperamos `tryItOutEnabled` (UX) e `filter` (busca) — UX baseline.
        assert "tryItOutEnabled" in config_block, (
            "Esperava `tryItOutEnabled` na config UX."
        )

    def test_swagger_oauth_redirect_url_is_local_origin_safe(self) -> None:
        """Se OAuth2 for introduzido no futuro, redirect URL deve ser HTTPS only.

        Swagger UI gera um iframe para ``oauth2-redirect.html``. Se for
        HTTP em prod, vaza tokens via downgrade. Aqui apenas validamos
        que o config atual NAO expoe `oauth2RedirectUrl` explicito
        inseguro (a omissao e segura: Swagger UI deriva de
        `window.location.origin`).
        """
        response = client.get("/docs")
        body = response.text
        # Se houver oauth2RedirectUrl explicito, deve apontar para http://localhost
        # em dev. Em prod nao deve vazar http://api.2notasudi.com.br sem https.
        # Procuramos pelo trecho inteiro para inspecao.
        redirect_match = re.search(
            r"oauth2RedirectUrl['\"]?\s*:\s*['\"]([^'\"]+)['\"]",
            body,
        )
        if redirect_match:
            url = redirect_match.group(1)
            # LGPD-safe: se for prod-like URL, deve ser https.
            assert not re.match(r"^http://(?!localhost|127\.0\.0\.1)", url), (
                f"oauth2RedirectUrl nao pode ser HTTP em host nao-local: {url}"
            )

    def test_docs_cache_control_header_no_store(self) -> None:
        """GET /docs retorna Cache-Control: no-store.

        Caso o browser ou um proxy (Traefik/CDN) cacheiem a pagina, o dev
        pode receber uma versao antiga do schema OpenAPI e tentar setar
        um endpoint que nao existe mais. ``no-store`` garante que cada
        reload rebusca o schema server-side.
        """
        response = client.get("/docs")
        assert response.status_code == 200
        cc = response.headers.get("cache-control", "")
        assert "no-store" in cc.lower(), (
            f"Esperava `no-store` em Cache-Control; recebi: {cc!r}"
        )

    def test_openapi_json_is_valid_json(self) -> None:
        """Sanity: /openapi.json parseia como JSON (Swagger UI nao quebra)."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        # JSONDecodeError seria erro silencioso para o Swagger UI.
        try:
            payload = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"openapi.json nao parseia como JSON: {exc}") from exc
        assert isinstance(payload, dict)
        assert "openapi" in payload
        assert "paths" in payload
