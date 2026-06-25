"""API v2 (alpha) - sunset 2027.

SQUAD A A24 - versionamento /api/v1 + /api/v2.

API v2 eh um ESQUELETO alpha criado em 2026-06-25.
- Path prefix: /api/v2/
- Sunset date: 2027-12-31 (apos isso, v1 sera removido)
- Migration path: clientes devem migrar de v1 para v2 ate 2027-Q3
- Breaking changes vs v1 (planejado):
  * Autenticacao: X-API-Key v1 + JWT v2 (OAuth2 ready)
  * Paginacao: offset/limit v1 -> cursor v2 (estilo Relay)
  * Webhook payload: v1 simples -> v2 envelope com metadata
  * Rate limit headers: X-RateLimit-* v1 -> RFC 9239 v2
  * Erro: RFC 7807 v1 -> RFC 9457 v2 (Problem Details for HTTP APIs bis)

Por enquanto v2 expoe apenas 1 endpoint (/api/v2/info) que retorna
metadata do versionamento. Demais endpoints serao adicionados em sprints
seguintes (gradual migration).

Endpoint:
  GET /api/v2/info
  Resposta: {version, sunset_date, migration_guide_url, deprecations: [...]}
"""
from __future__ import annotations

from fastapi import APIRouter

api_v2_router = APIRouter()


@api_v2_router.get(
    "/info",
    tags=["v2", "versioning"],
    summary="API v2 metadata (alpha)",
    description=(
        "Retorna informacoes sobre a versao 2 da API (alpha, sunset 2027-12-31). "
        "Use este endpoint para verificar se sua integracao com v1 ainda eh "
        "suportada e quando migrar para v2."
    ),
    response_description="Metadata do versionamento v2.",
)
async def v2_info() -> dict:
    """Info sobre API v2 (alpha)."""
    return {
        "version": "2.0.0-alpha.1",
        "status": "alpha",
        "released_at": "2026-06-25",
        "sunset_date": "2027-12-31",
        "sunset_target": "v1",
        "migration_guide_url": "https://github.com/gustavofullstack/Cartorio/blob/master/docs/api-v1-to-v2-migration.md",
        "current_v1": "1.x (production stable, recommend for new integrations too)",
        "breaking_changes_vs_v1": [
            "Auth: X-API-Key v1 + JWT/OAuth2 v2",
            "Paginacao: offset/limit v1 -> cursor (Relay) v2",
            "Webhook payload: v1 flat -> v2 envelope (event, data, metadata)",
            "Rate limit: X-RateLimit-* v1 -> RFC 9239 v2",
            "Erro: RFC 7807 v1 -> RFC 9457 v2 (bis)",
        ],
        "deprecations": [
            {
                "v1_endpoint": "GET /api/v1/clientes?offset=0&limit=100",
                "v2_replacement": "GET /api/v2/clientes?first=100&after=cursor",
                "deprecated_at": "2026-06-25",
                "removed_at": "2027-12-31",
            },
        ],
        "available_endpoints": [
            "GET /api/v2/info (este endpoint)",
        ],
        "endpoints_coming": [
            "GET /api/v2/clientes",
            "GET /api/v2/clientes/{id}",
            "POST /api/v2/clientes",
            "GET /api/v2/protocolos",
            "GET /api/v2/emolumento/tabela",
        ],
    }
