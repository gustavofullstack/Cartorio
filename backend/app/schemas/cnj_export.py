"""Contratos estritos da exportacao agregada CNJ."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CNJExportRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reference_period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class CNJExportApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=10, max_length=500)


class CNJExportStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: str
    reference_period: str
    requested_at: str
    approved_at: str | None = None
    generated_at: str | None = None
    report_sha256: str | None = None
    manifest_sha256: str | None = None


class CNJExportArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: dict[str, Any]
    manifest: dict[str, Any]


__all__ = [
    "CNJExportApprovalCreate",
    "CNJExportArtifactResponse",
    "CNJExportRequestCreate",
    "CNJExportStatusResponse",
]
