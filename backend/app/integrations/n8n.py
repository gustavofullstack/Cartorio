"""N8N HTTP client integration (G8.23.T4).

Wrapper sobre o ``N8NTokenRouter`` para chamadas HTTP ao N8N.
Fornece headers padrao com ``X-N8N-API-KEY`` (token ativo) e
``X-N8N-KEY-ID`` (kid para correlacao em audit log e debug).

Uso:

    from app.integrations.n8n import get_n8n_headers, get_n8n_base_url

    headers = get_n8n_headers()
    url = f"{get_n8n_base_url()}/api/v1/workflows"

    resp = httpx.get(url, headers=headers)

O token e selecionado pelo ``N8NTokenRouter`` (singleton). A primeira
chamada popula o registry a partir de ``settings.n8n_api_key`` com kid
``legacy``; operacoes de rotacao chamam ``router.rotate(new_kid,
new_token)`` e ``router.revoke_old(grace_period_days=7)``.

Failure modes:
- ``settings.n8n_api_key`` vazio e nenhum kid registrado ->
  ``RuntimeError`` na primeira chamada HTTP
- Token active revogado por ``revoke_old`` -> ``RuntimeError``
  (consistente com o router)

Decisao de design (G8.23.T4):
- Modulo dedicado em vez de usar ``settings.n8n_api_key`` direto nos
  callers (SRP, testavel, suporte a rotacao).
- Headers sao gerados on-demand (cada request). Custo: 1 lock acquire.
- ``get_n8n_base_url()`` -> settings.n8n_base_url (com lazy import
  para evitar ciclos no bootstrap).

LGPD-by-design:
- Art. 46: rotacao periodica reduz blast radius. Token nao eh logado
  nem exposto em snapshot (apenas hash sha256[:8] para audit).
- Art. 50: grace period documentado (7 dias default).

Backward-compat:
- Codigo legado em ``app/api/v1/n8n_metrics.py`` continua usando
  ``settings.n8n_api_key`` direto. Migracao gradual recomendada
  (proxima wave). NAO quebrar callers existentes.

Modified by Gustavo Almeida + cartorio-n8n -- G8.23.T4 (Wave 53).
"""

from __future__ import annotations

from app.services.n8n_token_router import get_router

__all__ = ["get_n8n_headers", "get_n8n_base_url", "bootstrap_from_settings"]


def _ensure_bootstrapped() -> None:
    """Bootstrap lazy do router a partir de settings, idempotente.

    Se o router ja tem um ACTIVE (ex.: registrado por testes ou por
    ``bootstrap_from_settings()`` explicito), noop. Senao, le
    ``settings.n8n_api_key`` e chama ``router.bootstrap_legacy``.

    Raises:
        RuntimeError: settings.n8n_api_key ausente e router vazio.
    """
    from app.config import settings

    router = get_router()
    if router._bootstrapped:  # noqa: SLF001 -- pattern inherited from audit_keys
        return
    if router._active_kid:  # noqa: SLF001 -- ja tem kid ativo (testes/explicit)
        return
    token = settings.n8n_api_key
    if not token:
        raise RuntimeError(
            "n8n_token_router: settings.n8n_api_key is empty and router has no active kid"
        )
    router.bootstrap_legacy(token=token)


def bootstrap_from_settings() -> None:
    """Forca bootstrap a partir de ``settings.n8n_api_key``.

    Idempotente. Util para chamar explicitamente no startup da app.
    """
    _ensure_bootstrapped()


def get_n8n_headers() -> dict[str, str]:
    """Retorna headers para chamada autenticada ao N8N.

    Headers retornados:
      - ``X-N8N-API-KEY``: token ativo
      - ``X-N8N-KEY-ID``: kid do token (para audit + debug)

    Raises:
        RuntimeError: nenhum token configurado.
    """
    _ensure_bootstrapped()
    kid, token = get_router().get_token()
    return {
        "X-N8N-API-KEY": token,
        "X-N8N-KEY-ID": kid,
    }


def get_n8n_base_url() -> str:
    """Retorna a base URL do N8N configurada em settings."""
    from app.config import settings

    return settings.n8n_base_url
