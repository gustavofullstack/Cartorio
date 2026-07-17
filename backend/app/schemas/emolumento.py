from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class EmolumentoCalculoResponse(BaseModel):
    # From router
    tipo: str
    folhas: int
    urgencia: bool
    base: Decimal
    adicional_folhas: Decimal
    adicional_urgencia: Decimal
    total: Decimal
    isento: bool
    isencao_motivo: Optional[str] = None
    tabela_referencia: str
    valido_ate: datetime
