"""Schemas Pydantic para LGPD DSAR (G6.C.T11)."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LGPDRight(str, Enum):
    """7 direitos LGPD art. 18."""

    CONFIRMACAO = "confirmacao"  # I
    ACESSO = "acesso"  # II
    CORRECAO = "correcao"  # III
    ANONIMIZACAO = "anonimizacao"  # IV
    PORTABILIDADE = "portabilidade"  # V
    ELIMINACAO = "eliminacao"  # VI
    COMPARTILHAMENTO = "compartilhamento"  # VII


class DSARCreate(BaseModel):
    """Payload para criar DSAR (LGPD art. 18)."""

    cpf: str = Field(..., min_length=11, max_length=14, description="CPF do titular (com ou sem formatacao)")
    email: EmailStr | None = Field(None, description="Email de contato")
    phone: str | None = Field(None, min_length=10, max_length=15, description="Telefone (10-15 chars)")
    rights: list[LGPDRight] = Field(..., min_length=1, max_length=7, description="Direitos exercidos (1-7)")
    justification: str | None = Field(None, max_length=500, description="Justificativa opcional")


class DSARCreateResponse(BaseModel):
    """Resposta de criacao DSAR."""

    request_id: str = Field(..., description="ID unico (DSAR-xxxxxxxx)")
    received_at: str = Field(..., description="ISO timestamp de recebimento")
    deadline: str = Field(..., description="ISO timestamp prazo legal (15 dias)")
    cpf_hash: str = Field(..., description="SHA256[:16] do CPF (LGPD art. 46)")
    email_hash: str | None = Field(None, description="SHA256[:16] do email")
    phone_hash: str | None = Field(None, description="SHA256[:16] do telefone")
    rights_requested: list[LGPDRight]
    message: str


class DSARStatus(BaseModel):
    """Status de uma DSAR."""

    request_id: str
    status: Literal["pending", "in_review", "approved", "denied", "completed"]
    received_at: str
    deadline: str
    rights_requested: list[LGPDRight]
    message: str
    download_url: str | None = None