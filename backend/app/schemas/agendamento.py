"""Schemas Pydantic para agendamentos (API I/O).

Validação de entrada/saída para endpoints de agendamento.
Usa enums compartilhados com models.agendamento para consistência.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.agendamento import StatusAgendamento, TipoAtendimento


class AgendamentoBase(BaseModel):
    """Base para schemas de agendamento."""

    model_config = ConfigDict(from_attributes=True)

    titulo: str = Field(..., min_length=5, max_length=255, examples=["Reconhecimento de firma"])
    descricao: str | None = Field(
        None, max_length=1000, examples=["Documentos: RG, CPF, contrato"]
    )
    tipo: TipoAtendimento = Field(
        default=TipoAtendimento.NORMAL,
        description="Tipo de atendimento (normal, prioritário, urgente)",
    )
    local: str = Field(
        default="balcao_1",
        min_length=3,
        max_length=100,
        examples=["balcao_1", "sala_reuniao", "guiche_2"],
    )


class AgendamentoCreateRequest(AgendamentoBase):
    """Request para criação de agendamento."""

    cliente_id: int = Field(..., gt=0, description="ID do cliente (FK)")
    cliente_cpf: str = Field(
        ...,
        min_length=11,
        max_length=14,
        description="CPF do cliente (será hasheado - LGPD)",
        examples=["12345678909"],
    )
    data_hora: datetime.datetime = Field(
        ...,
        description="Data/hora do agendamento (ISO 8601)",
        examples=["2026-07-01T14:30:00-03:00"],
    )
    protocolo_id: int | None = Field(
        None,
        gt=0,
        description="ID do protocolo associado (opcional)",
        examples=[123],
    )
    duration_minutes: int = Field(
        default=30,
        ge=15,
        le=180,
        description="Duração em minutos (para validação de conflito)",
        examples=[30],
    )


class AgendamentoResponse(AgendamentoBase):
    """Response com dados do agendamento."""

    id: int = Field(..., gt=0, description="ID do agendamento")
    cliente_id: int = Field(..., gt=0, description="ID do cliente (FK)")
    protocolo_id: int | None = Field(
        None, gt=0, description="ID do protocolo associado"
    )
    status: StatusAgendamento = Field(..., description="Status atual")
    data_hora: datetime.datetime = Field(..., description="Data/hora do agendamento")
    data_hora_fim: datetime.datetime | None = Field(
        None, description="Data/hora de término (se concluído)"
    )
    criado_em: datetime.datetime = Field(..., description="Timestamp de criação")
    atualizado_em: datetime.datetime = Field(..., description="Timestamp de atualização")
    cpf_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="CPF hasheado (SHA256 - LGPD)",
        examples=["a" * 64],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "cliente_id": 42,
                    "protocolo_id": 123,
                    "titulo": "Reconhecimento de firma",
                    "descricao": "Documentos: RG, CPF, contrato",
                    "status": "agendado",
                    "tipo": "normal",
                    "local": "balcao_1",
                    "data_hora": "2026-07-01T14:30:00-03:00",
                    "data_hora_fim": None,
                    "criado_em": "2026-06-25T10:00:00-03:00",
                    "atualizado_em": "2026-06-25T10:00:00-03:00",
                    "cpf_hash": "a" * 64,
                }
            ]
        }
    )
