from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class EmolumentoCalculoResponse(BaseModel):
    valor_total: float
    impostos: float
    taxa_cartorio: float
    detalhes: Dict[str, Any]
