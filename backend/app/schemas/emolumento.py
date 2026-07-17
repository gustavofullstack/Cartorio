from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from decimal import Decimal


class EmolumentoCalculoResponse(BaseModel):
    valor_total: Decimal = Field(..., description="Valor total calculado")
    parcelas: Optional[Dict[str, Any]] = Field(
        default=None, description="Detalhamento das parcelas"
    )

    # Extra fields based on router
    tipo: Optional[str] = None
    folhas: Optional[int] = None
    tabela: Optional[str] = None
