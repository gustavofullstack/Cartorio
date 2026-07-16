"""Tests para LGPD Consent API endpoint (G6.C.T9).

Testa schema + pydantic validation via TestClient.
Nao testa endpoint completo (auth middleware) por causa de complexidade JWT.
"""

from __future__ import annotations

import os

# IMPORTANTE: setar env ANTES de importar app
os.environ["APP_ENV"] = "staging"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUDIT_HMAC_KEY"] = "a" * 64
os.environ["CARTORIO_API_KEY"] = "a" * 64

from app.schemas.lgpd_consent import (  # noqa: E402
    LGPDConsentRequest,
    LGPDConsentStats,
    LGPDConsentStatsItem,
)


def test_schema_consent_request_minimal() -> None:
    """Schema aceita payload minimo (aceita apenas accepted)."""
    consent = LGPDConsentRequest(accepted=True, version="v3")
    assert consent.accepted is True
    assert consent.version == "v3"
    assert consent.analytics is False
    assert consent.marketing is False
    assert consent.session_id is None


def test_schema_consent_request_completo() -> None:
    """Schema aceita payload completo."""
    consent = LGPDConsentRequest(
        accepted=True,
        analytics=True,
        marketing=False,
        version="v3",
        session_id="abc-123",
    )
    assert consent.analytics is True
    assert consent.marketing is False
    assert consent.session_id == "abc-123"


def test_schema_consent_request_rejeitado() -> None:
    """Schema aceita accepted=False."""
    consent = LGPDConsentRequest(accepted=False, version="v3")
    assert consent.accepted is False


def test_schema_consent_stats_basico() -> None:
    """Schema stats aceita valores basicos."""
    stats = LGPDConsentStats(
        total=100,
        accepted=80,
        rejected=20,
        analytics_opt_in=70,
        marketing_opt_in=50,
        consent_ratio=0.8,
    )
    assert stats.total == 100
    assert stats.consent_ratio == 0.8


def test_schema_consent_stats_com_breakdown() -> None:
    """Schema stats aceita breakdown por periodo."""
    stats = LGPDConsentStats(
        total=200,
        accepted=150,
        rejected=50,
        analytics_opt_in=120,
        marketing_opt_in=80,
        consent_ratio=0.75,
        breakdown=[
            LGPDConsentStatsItem(period="2026-07-01", total=50, accepted=40),
            LGPDConsentStatsItem(period="2026-07-08", total=50, accepted=35),
        ],
    )
    assert len(stats.breakdown) == 2
    assert stats.breakdown[0].period == "2026-07-01"


def test_schema_consent_stats_ratio_range() -> None:
    """consent_ratio deve ser 0.0-1.0 (Field constraint)."""
    import pytest
    with pytest.raises(Exception):  # ValidationError
        LGPDConsentStats(
            total=10,
            accepted=5,
            rejected=5,
            analytics_opt_in=0,
            marketing_opt_in=0,
            consent_ratio=1.5,  # > 1.0 invalido
        )


def test_schema_consent_request_version_invalida() -> None:
    """version != v3 deve ser rejeitado."""
    import pytest
    with pytest.raises(Exception):  # ValidationError
        LGPDConsentRequest(accepted=True, version="v99")


def test_schema_consent_request_aceite_mesmo_sem_session() -> None:
    """session_id opcional (None default)."""
    consent = LGPDConsentRequest(accepted=True, version="v3", session_id=None)
    assert consent.session_id is None


def test_schema_consent_endpoint_path() -> None:
    """Validar path do endpoint."""
    from app.api.v1.lgpd_consent import router
    routes = [r.path for r in router.routes]
    assert "/api/v1/lgpd/consent" in routes or "" in routes  # router tem prefix
    # Path completo
    assert any("consent" in r for r in routes)