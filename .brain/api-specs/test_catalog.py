"""Testes do API Endpoints Catalog (BRAIN2)."""
from __future__ import annotations

import pytest  # noqa: E402

from brain.api_specs.catalog import (  # noqa: E402
    API_ENDPOINTS,
    API_V2_ENDPOINTS,
    ApiEndpoint,
    get_all_endpoints,
    get_endpoints_by_tag,
    get_endpoints_by_version,
    get_endpoints_with_lgpd_scope,
    get_stats,
)


def test_v1_tem_pelo_menos_50_endpoints() -> None:
    """v1 >= 50 endpoints (canonical baseline)."""
    assert len(API_ENDPOINTS) >= 50


def test_v2_tem_pelo_menos_3_endpoints() -> None:
    """v2 >= 3 endpoints (alpha inicial)."""
    assert len(API_V2_ENDPOINTS) >= 3


def test_cada_endpoint_tem_method_e_path() -> None:
    """Cada endpoint tem method e path nao-vazios."""
    for e in get_all_endpoints():
        assert e.method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert e.path.startswith("/")


def test_paths_sao_unicos_por_method() -> None:
    """Mesma combinacao method+path nao se repete."""
    seen = set()
    for e in get_all_endpoints():
        key = (e.method, e.path)
        assert key not in seen, f"Duplicado: {key}"
        seen.add(key)


def test_get_endpoints_by_tag_filtra() -> None:
    """Filtro por tag retorna apenas endpoints com aquela tag."""
    clientes = get_endpoints_by_tag("clientes")
    assert len(clientes) >= 8
    for e in clientes:
        assert e.tag == "clientes"


def test_get_endpoints_by_version_filtra() -> None:
    """Filtro por versao retorna apenas daquela versao."""
    v1 = get_endpoints_by_version("v1")
    v2 = get_endpoints_by_version("v2")
    assert all(e.version == "v1" for e in v1)
    assert all(e.version == "v2" for e in v2)


def test_get_endpoints_with_lgpd_scope() -> None:
    """Endpoints LGPD sao apenas os que acessam PII."""
    lgpd = get_endpoints_with_lgpd_scope()
    assert len(lgpd) >= 15  # cliente/protocolo/agendamento/lgpd direitos
    for e in lgpd:
        assert e.lgpd_scope is True


def test_stats_agregadas_corretas() -> None:
    """Stats tem totais coerentes."""
    stats = get_stats()
    assert stats["total"] == stats["v1"] + stats["v2"]
    assert stats["v1"] >= 50
    assert stats["v2"] >= 3
    assert stats["stable"] + stats["alpha"] == stats["total"]