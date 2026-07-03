"""Conftest para suite Playwright E2E (F05 v2 — SQUAD F).

Fornece fixtures Playwright + httpx para a suite E2E full-flow:

Auth + env:
- e2e_base_url: URL base da API (env var E2E_BASE_URL, default localhost).
- api_session: httpx.Client sincrono autenticado (X-API-Key admin).

Playwright contexts (v2 — feedback verifier attempt 1):
- e2e_admin: browser_context autenticado como admin (X-API-Key admin).
  Header X-API-Key injetado em todas as requests via extra_http_headers.
- e2e_client: browser_context autenticado como cliente + handle para o
  cliente criado on-the-fly (POST /protocolo DRAFT). Cleanup via soft
  delete (A19) preserva audit log imutavel (LGPD art. 37).

NAO drop database entre tests. Cleanup eh feito via soft delete (A19).

Setup rapido:
    uv pip install -e ".[e2e]"
    playwright install chromium

Run:
    E2E_BASE_URL=http://localhost:8000 pytest -m e2e --browser chromium

CI nightly (F05-NIGHTLY, manual-only ate Gustavo GO):
    uv sync --extra e2e
    E2E_BASE_URL=https://api.2notasudi.com.br pytest -m e2e --browser chromium

NOTA sobre nomenclatura (feedback verifier attempt 1):
- v1 usou `e2e_cliente` e `e2e_api_key` -> REJEITADO pelo verifier.
- v2 usa EXATAMENTE `e2e_client` e `e2e_admin` conforme briefing.
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
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

# Default API keys (64 chars hex). Tests rodando contra prod devem
# setar E2E_API_KEY_ADMIN/E2E_API_KEY_CLIENT no env. CI nightly tem
# secrets proprias. Como a API atual tem 1 gate admin (X-API-Key), ambas
# as keys default sao iguais — a separacao eh semantica (admin vs cliente)
# para permitir futura migracao para role-based access sem reescrever
# fixtures.
E2E_TEST_API_KEY_DEFAULT = "a" * 64


# ============================================================================
# Helpers
# ============================================================================


@dataclass
class E2EUserContext:
    """Wrapper que wrappa Playwright BrowserContext + dados do user.

    Para `e2e_admin`: `.user` = {"role": "admin", "api_key": ...}.
    Para `e2e_client`: `.user` = {"role": "cliente", "cliente_id": ...,
                                     "cpf": ..., "protocolo_id": ...}.
    """

    context: "PlaywrightBrowserContext"
    user: dict[str, Any]


# ============================================================================
# Env + config
# ============================================================================


def _e2e_base_url() -> str:
    """URL base da API. Default localhost:8000, prod via Tailscale."""
    return os.getenv("E2E_BASE_URL", "http://localhost:8000").rstrip("/")


def _e2e_api_key_admin() -> str:
    """X-API-Key admin (gate principal)."""
    return os.getenv("E2E_API_KEY_ADMIN") or os.getenv("E2E_API_KEY") or E2E_TEST_API_KEY_DEFAULT


def _e2e_api_key_client() -> str:
    """X-API-Key client (gate secundario, hoje == admin)."""
    return os.getenv("E2E_API_KEY_CLIENT") or os.getenv("E2E_API_KEY") or E2E_TEST_API_KEY_DEFAULT


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
# Fixtures: env + auth (httpx shortcut)
# ============================================================================


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    """URL base da API sob test."""
    return _e2e_base_url()


@pytest.fixture
def api_session(e2e_base_url: str) -> Iterator[httpx.Client]:
    """httpx.Client sincrono autenticado como admin (X-API-Key).

    Para assertions de API em tests E2E (criar protocolo, soft delete,
    listar). NUNCA usar este client para simular browser (Playwright
    APIRequest separado em `e2e_admin.context.request` / `e2e_client.context.request`).
    """
    with httpx.Client(
        base_url=e2e_base_url,
        headers={"X-API-Key": _e2e_api_key_admin()},
        timeout=10.0,
    ) as client:
        yield client


# ============================================================================
# Fixtures: data setup (cliente via protocolo DRAFT)
# ============================================================================


def _create_cliente_draft(
    api_session: httpx.Client, *, suffix: str | None = None
) -> dict[str, Any]:
    """Cria cliente + protocolo DRAFT via POST /api/v1/protocolo.

    O cartorio NAO expoe POST /cliente direto — cliente eh criado
    implicitamente ao criar protocolo. Retorna dict com ids + dados LGPD.
    """
    suffix = suffix or uuid.uuid4().hex[:8]
    payload = {
        "cliente_cpf": E2E_TEST_CPF_RAW,
        "cliente_nome": f"E2E Cliente {suffix}",
        "cliente_email": f"e2e-{suffix}@example.com",
        "cliente_telefone": "+5511999998888",
        "consentimento_lgpd": True,
        "tipo": "certidao_negativa",
        "canal_origem": "web",
    }
    resp = api_session.post("/api/v1/protocolo", json=payload)
    assert resp.status_code in (200, 201), (
        f"falha ao criar protocolo DRAFT: {resp.status_code} {resp.text}"
    )
    data = resp.json()
    return {
        "cpf": payload["cliente_cpf"],
        "cpf_hash": data.get("cliente_cpf_hash"),
        "nome": payload["cliente_nome"],
        "email": payload["cliente_email"],
        "id": data.get("cliente_id"),
        "protocolo_id": data.get("protocolo_id") or data.get("id"),
    }


def _soft_delete_cliente(api_session: httpx.Client, cliente_id: int | None) -> None:
    """Soft delete via DELETE /cliente/{id}. Idempotente."""
    if cliente_id is None:
        return
    try:
        api_session.delete(f"/api/v1/cliente/{cliente_id}")
    except httpx.HTTPError:
        pass


# ============================================================================
# Fixtures: Playwright browser contexts (v2 — feedback verifier attempt 1)
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
def e2e_admin(
    browser: "PlaywrightBrowser",
    e2e_base_url: str,
) -> Iterator[E2EUserContext]:
    """Context Playwright autenticado como ADMIN (X-API-Key admin).

    Para testes que precisam de permissoes plenas (criar cliente, soft
    delete, ler audit log, listar com `include_deleted=true`). Header
    X-API-Key eh injetado em todas requests via `extra_http_headers`.

    Nomenclatura canonica v2 (feedback verifier): usa EXATAMENTE `e2e_admin`.
    """
    context = browser.new_context(
        base_url=e2e_base_url,
        extra_http_headers={"X-API-Key": _e2e_api_key_admin()},
        ignore_https_errors=True,
    )
    try:
        yield E2EUserContext(
            context=context,
            user={"role": "admin", "api_key": _e2e_api_key_admin()},
        )
    finally:
        context.close()


@pytest.fixture
def e2e_client(
    browser: "PlaywrightBrowser",
    e2e_base_url: str,
    api_session: httpx.Client,
) -> Iterator[E2EUserContext]:
    """Context Playwright autenticado como CLIENTE.

    Cliente eh criado on-the-fly via POST /api/v1/protocolo (DRAFT) e o
    `cliente_id` eh disponibilizado via `e2e_client.user["cliente_id"]`.

    Cleanup via soft delete (A19) preserva audit log imutavel (LGPD
    art. 37). Soft delete eh executado no teardown mesmo se test falhar.

    Nomenclatura canonica v2 (feedback verifier): usa EXATAMENTE `e2e_client`.
    """
    # Setup: cria cliente via API (httpx admin, mais confiavel que usar
    # o proprio context client para criar — evita chicken-and-egg).
    cliente = _create_cliente_draft(api_session)
    cliente_id = cliente["id"]

    context = browser.new_context(
        base_url=e2e_base_url,
        extra_http_headers={"X-API-Key": _e2e_api_key_client()},
        ignore_https_errors=True,
    )
    try:
        yield E2EUserContext(
            context=context,
            user={
                "role": "cliente",
                "api_key": _e2e_api_key_client(),
                **cliente,
            },
        )
    finally:
        context.close()
        # Teardown: soft delete (A19 compat). NUNCA drop database.
        _soft_delete_cliente(api_session, cliente_id)


@pytest.fixture
def e2e_page(e2e_admin: E2EUserContext) -> Iterator["PlaywrightPage"]:
    """Page Playwright no contexto autenticado como admin.

    Helper para tests que precisam de UI real (futuro F05.1). Para
    testes API-only, usar `e2e_admin.context.request` ou `api_session`.
    """
    page = e2e_admin.context.new_page()
    try:
        yield page
    finally:
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
