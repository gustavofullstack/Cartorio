"""Schemas Pydantic para emolumentos (API I/O).

Validação de saída para a API estendida de cálculo de emolumentos.
"""

from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field


class EmolumentoCalculoResponse(BaseModel):
    """Resposta com dados detalhados do cálculo de emolumentos."""

    tipo: str = Field(..., description="Tipo do ato notarial.")
    folhas: int = Field(..., description="Quantidade de folhas processadas.")
    urgencia: bool = Field(..., description="Se foi aplicado acréscimo de urgência.")
    base: Decimal = Field(..., description="Valor emolumento base de tabela.")
    adicional_folhas: Decimal = Field(..., description="Adicional calculado pelas folhas excedentes.")
    adicional_urgencia: Decimal = Field(..., description="Adicional de 50% para atos urgentes.")
    total: Decimal = Field(..., description="Valor total a ser cobrado.")
    isento: bool = Field(..., description="Flag indicando se foi aplicada isenção total.")
    isencao_motivo: str | None = Field(None, description="Motivo legal de isenção, se aplicável.")
    tabela_referencia: str = Field(..., description="Identificação da tabela de custas vigente.")
    valido_ate: str = Field(..., description="Data limite de vigência da tabela.")
