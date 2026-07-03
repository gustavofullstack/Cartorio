"""Conftest para suite Playwright E2E (F05 SQUAD F).

Fornece fixtures:
- e2e_base_url: URL base da API (env var E2E_BASE_URL, default localhost).
- e2e_api_key: header X-API-Key admin (env var E2E_API_KEY, default
  64-char placeholder). Em CI nightly, secret do GH.
- e2e_cliente_payload / e2e_cliente: cliente criado via POST /protocolo
  (DRAFT) — o cartorio NAO expoe POST /cliente direto. Cliente eh
  criado implicitamente via protocolo. Cleanup via soft delete.
- browser: contexto Playwright chromium (headed=False default).
- e2e_context / e2e_page: contexto + pagina autenticados (X-API-Key).
- api_session: httpx.Client sincrono autenticado.

NAO drop database entre tests. Cleanup eh feito via soft delete (A19)
preservando audit log imutavel (LGPD art. 37).

Setup rapido:
    uv pip install -e ".[e2e]"
    playwright install chromium

Run:
    E2E_BASE_URL=http://localhost:8000 pytest -m e2e --browser chromium

CI nightly (F05-NIGHTLY):
    uv sync --extra e2e
    E2E_BASE_URL=https://api.2notasudi.com.br pytest -m e2e --browser chromium
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    # Apenas para type hints — playwright vive em [project.optional-dependencies.e2e].
    from playwright.sync_api import Browser as PlaywrightBrowser  # type: ignore[import-not-found]
    from playwright.sync_api import BrowserContext as PlaywrightBrowserContext  # type: ignore[import-not-found]
    from playwright.sync_api import Page as PlaywrightPage  # type: ignore[import-not-found]


# ============================================================================
# Constantes
# ============================================================================

# CPF valido (mas deterministico) para tests E2E. NUNCA usar CPF real.
# O CPF abaixo eh valido pelo algoritmo de validacao mas nao corresponde
# a nenhuma pessoa real. Pode ser compartilhado entre tests (cleanup via
# soft delete + suite roda em serie por default).
E2E_TEST_CPF = "529.982.247-25"
E2E_TEST_CPF_RAW = "52998224725"

# Default API key (64 chars hex). Tests rodando contra prod devem
# setar E2E_API_KEY no env. CI nightly tem secret proprio.
E2E_TEST_API_KEY_DEFAULT = "a" * 64


# ============================================================================
# Env + config
# ============================================================================


def _e2e_base_url() -> str:
    """URL base da API. Default localhost:8000, prod via Tailscale."""
    return os.getenv("E2E_BASE_URL", "http://localhost:8000").rstrip("/")


def _e2e_api_key() -> str:
    """X-API-Key admin. Default 64-a placeholder (aceito em dev/test)."""
    return os.getenv("E2E_API_KEY", E2E_TEST_API_KEY_DEFAULT)


# ============================================================================
# Pytest config (markers, collection)
# ============================================================================


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip E2E tests se Playwright NAO estiver instalado.

    Permite `pytest` rodar sem quebrar em CI unit onde Playwright nao foi
    instalado. Tests vao ser SKIPPED (nao FAILED) com reason explicito.
    """
    try:
        import playwright  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        skip_marker = pytest.mark.skip(
            reason="playwright nao instalado (rode `uv sync --extra e2e && playwright install chromium`)",
        )
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_marker)


# ============================================================================
# Fixtures: env + auth
# ============================================================================


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    """URL base da API sob test."""
    return _e2e_base_url()


@pytest.fixture(scope="session")
def e2e_api_key() -> str:
    """X-API-Key admin (64 hex chars)."""
    return _e2e_api_key()


@pytest.fixture
def api_session(e2e_base_url: str, e2e_api_key: str) -> Iterator[httpx.Client]:
    """httpx.Client sincrono autenticado para setup + assertions.

    Para assertions de API em tests E2E (criar protocolo, soft delete,
    listar). NUNCA usar este client para login de browser (Playwright
    APIRequest separado em browser.request fixture).
    """
    with httpx.Client(
        base_url=e2e_base_url,
        headers={"X-API-Key": e2e_api_key},
        timeout=10.0,
    ) as client:
        yield client


# ============================================================================
# Fixtures: data setup (cliente via protocolo DRAFT)
# ============================================================================


@pytest.fixture
def e2e_cliente_payload() -> dict[str, Any]:
    """Payload LGPD-safe para criar cliente + protocolo DRAFT no test."""
    suffix = uuid.uuid4().hex[:8]
    return {
        "cliente_cpf": E2E_TEST_CPF_RAW,
        "cliente_nome": f"E2E Cliente {suffix}",
        "cliente_email": f"e2e-{suffix}@example.com",
        "cliente_telefone": "+5511999998888",
        "consentimento_lgpd": True,
        "tipo": "certidao_negativa",
        "canal_origem": "web",
    }


@pytest.fixture
def e2e_cliente(
    api_session: httpx.Client, e2e_cliente_payload: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    """Cria cliente via POST /api/v1/protocolo (DRAFT).

    O cartorio NAO expoe POST /cliente direto — cliente eh criado
    implicitamente ao criar protocolo. Cleanup via DELETE /cliente/{id}
    (LGPD direito ao esquecimento, soft delete se ha protocolos ativos).
    """
    resp = api_session.post("/api/v1/protocolo", json=e2e_cliente_payload)
    assert resp.status_code in (200, 201), (
        f"falha ao criar protocolo DRAFT: {resp.status_code} {resp.text}"
    )
    data = resp.json()
    cliente_id = data.get("cliente_id")
    protocolo_id = data.get("protocolo_id") or data.get("id")

    yield {
        "cpf": e2e_cliente_payload["cliente_cpf"],
        "cpf_hash": data.get("cliente_cpf_hash"),
        "nome": e2e_cliente_payload["cliente_nome"],
        "email": e2e_cliente_payload["cliente_email"],
        "id": cliente_id,
        "protocolo_id": protocolo_id,
    }

    # Teardown: soft delete via DELETE /cliente/{id}.
    if cliente_id is not None:
        try:
            api_session.delete(f"/api/v1/cliente/{cliente_id}")
        except httpx.HTTPError:
            pass  # idempotente


# ============================================================================
# Fixtures: Playwright browser
# ============================================================================


@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict[str, Any]:
    """Args de launch do chromium (headed=False default)."""
    return {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    }


@pytest.fixture
def e2e_context(
    browser: "PlaywrightBrowser", e2e_base_url: str, e2e_api_key: str
) -> Iterator["PlaywrightBrowserContext"]:
    """Context Playwright autenticado (X-API-Key no header).

    Para testes que exigem UI real. Para testes API-only, usar
    `api_session` (httpx) — bem mais rapido.
    """
    context = browser.new_context(
        base_url=e2e_base_url,
        extra_http_headers={
            "X-API-Key": e2e_api_key,
        },
        ignore_https_errors=True,
    )
    yield context
    context.close()


@pytest.fixture
def e2e_page(e2e_context: "PlaywrightBrowserContext") -> Iterator["PlaywrightPage"]:
    """Page Playwright no contexto autenticado."""
    page = e2e_context.new_page()
    yield page
    page.close()


# ============================================================================
# Fixtures: cleanup state
# ============================================================================


@pytest.fixture(autouse=True)
def _e2e_isolation_marker(request: pytest.FixtureRequest) -> Iterator[None]:
    """Marca inicio/fim de test E2E para diagnostic + log timing.

    Tests E2E sao lentos por natureza (Playwright launch + browser ops).
    Capturar tempo permite debug de regressao de performance.
    """
    if "e2e" not in request.keywords:
        # NAO interfere em tests unit — sem yield = no-op marker.
        return  # type: ignore[return-value]
    start = time.monotonic()
    yield
    elapsed = time.monotonic() - start
    print(f"[E2E] {request.node.name} took {elapsed:.2f}s")  # noqa: T201
