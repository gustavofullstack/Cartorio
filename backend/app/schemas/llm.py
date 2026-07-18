"""Schemas Pydantic para os endpoints de monitoramento e teste de LLM (Wave 5 S5.T1).

Modified by Gustavo Almeida.

G8.13.T1: LLMTestRequest recebe strict=True (recusa coerção implicita
int->float, str->int, etc).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings


class LLMModelInfo(BaseModel):
    """Informações de conformidade e rota de um modelo de linguagem."""

    name: str = Field(..., description="Nome de exibição ou ID do modelo.")
    provider: str = Field(..., description="Provedor de infraestrutura (ex: opencode_go, litellm).")
    dpa_status: Literal["SIGNED", "PENDING", "NOT_APPLICABLE"] = Field(
        ...,
        description="Status de DPA (Data Processing Agreement) assinado com o DPO do cartório.",
        # G8.13.T1: Literal aceita str wire nativamente (sem override).
    )


class LLMTestRequest(BaseModel):
    """Payload de requisição para execução do teste ativo (smoke check) de um provedor."""

    # G8.13.T1 — strict=True recusa coerção: temperature="0.2" string eh rejeitado.
    model_config = ConfigDict(
        strict=settings.pydantic_strict_mode,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    message: str = Field(
        default="ping",
        description="Mensagem de teste a ser enviada ao LLM.",
        max_length=2000,
    )
    model: Optional[str] = Field(
        default=None,
        description="Override opcional do modelo do provedor.",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Temperatura para amostragem das respostas.",
    )
    consent_granted: bool = Field(
        default=False,
        description="Confirmação de consentimento LGPD para envio do payload ao provedor.",
    )
    actor_id: str = Field(
        default="smoke_test_admin",
        description="ID do operador/administrador executando o teste.",
        max_length=200,
    )


class LLMTestResponse(BaseModel):
    """Resultado da execução do teste de fumaça e latência do provedor."""

    status: str = Field(
        ..., description="'ok' se resposta obtida com sucesso, 'erro' caso contrário."
    )
    provider: str = Field(..., description="Provedor acionado no teste.")
    model: str = Field(..., description="Modelo utilizado na chamada.")
    response: Optional[str] = Field(default=None, description="Conteúdo retornado pelo LLM.")
    latency_ms: int = Field(
        ..., ge=0, description="Tempo decorrido para processamento da chamada em milissegundos."
    )
    dpa_status: str = Field(..., description="Status de DPA do provedor testado.")
    erro: Optional[dict[str, Any]] = Field(
        default=None, description="Metadata da falha caso status='erro'."
    )
