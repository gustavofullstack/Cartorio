"""Test fixtures para smoke tests.

Le credenciais de env vars - nunca commita secrets.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def smoke_enabled() -> bool:
    """Sinaliza se smoke contra infra real esta habilitado."""
    return os.getenv("SMOKE_TARGET", "").lower() == "prod"


@pytest.fixture(scope="session")
def vps_ip() -> str:
    """IP publico da VPS pra testes de port scan."""
    return os.getenv("VPS_IP", "187.77.236.77")


@pytest.fixture(scope="session")
def public_domain() -> str:
    return os.getenv("PUBLIC_DOMAIN", "2notasudi.com.br")


@pytest.fixture
def evolution_headers() -> dict[str, str]:
    """Header de auth do Evolution API. Vazio se nao configurado."""
    api_key = os.getenv("EVOLUTION_API_KEY", "")
    if not api_key:
        return {}
    return {"apikey": api_key}


@pytest.fixture
def evolution_base_url() -> str:
    """Base URL da Evolution API. Aponta pra prod se rodando contra prod."""
    return os.getenv(
        "EVOLUTION_BASE_URL", "https://whatsapp.2notasudi.com.br"
    )