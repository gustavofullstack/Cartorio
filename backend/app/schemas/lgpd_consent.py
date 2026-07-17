"""Schemas Pydantic para LGPD Consent (G6.C.T9)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LGPDConsentRequest(BaseModel):
    """Payload do banner LGPD enviado via sendBeacon."""

    accepted: bool = Field(..., description="Aceita todos os cookies?")
    analytics: bool = Field(default=False, description="Aceita analytics?")
    marketing: bool = Field(default=False, description="Aceita marketing?")
    version: Literal["v3"] = Field(default="v3", description="Versao LGPD")
    session_id: str | None = Field(default=None, max_length=128, description="Session ID (anonimo)")


class LGPDConsentStatsItem(BaseModel):
    """Item de breakdown (por dia/semana)."""

    period: str
    total: int
    accepted: int


class LGPDConsentStats(BaseModel):
    """Estatisticas agregadas de consentimento."""

    total: int
    accepted: int
    rejected: int
    analytics_opt_in: int
    marketing_opt_in: int
    consent_ratio: float = Field(..., ge=0.0, le=1.0)
    breakdown: list[LGPDConsentStatsItem] = Field(default_factory=list)
    last_updated: datetime | None = None
