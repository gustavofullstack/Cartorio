"""Schemas Pydantic para Dead Man's Switch (G6.A.T11)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeadMansSwitchStatus(BaseModel):
    """Status atual do dead man's switch."""

    enabled: bool = Field(..., description="Esta habilitado?")
    threshold_minutes: int = Field(..., ge=0, description="Threshold em minutos")
    last_heartbeat: str | None = Field(None, description="ISO timestamp do ultimo heartbeat")
    age_seconds: int | None = Field(None, description="Idade em segundos desde o ultimo")
    is_alive: bool = Field(..., description="Esta vivo?")
    message: str = Field(..., description="Mensagem legivel")


class DeadMansSwitchHistoryItem(BaseModel):
    """Item do historico de heartbeats."""

    timestamp: str
    actor: str = Field(..., description="cron (automatica) ou manual (admin)")
    action: str
    hash: str = Field(..., description="SHA256 chain hash do audit log entry")


class DeadMansSwitchHistory(BaseModel):
    """Historico de heartbeats do dead man's switch."""

    total: int
    items: list[DeadMansSwitchHistoryItem] = Field(default_factory=list)