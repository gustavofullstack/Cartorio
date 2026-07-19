"""Contratos estritos da exportacao agregada CNJ."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CNJExportRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reference_period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class CNJExportApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=10, max_length=500)


__all__ = ["CNJExportApprovalCreate", "CNJExportRequestCreate"]
