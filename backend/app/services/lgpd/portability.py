"""Export de dados do titular em formato estruturado (LGPD Art. 18 V)."""

from __future__ import annotations

import json
from typing import Any


def export_cliente_data(cliente_id: int, db_session: Any = None) -> dict[str, Any]:
    """Exporta todos os dados de um cliente em JSON estruturado.

    Direito à portabilidade (Art. 18 V): titular pode receber seus dados
    em formato estruturado e de uso comum.
    """
    # Stub — implementação real usa SQLAlchemy session
    return {
        "cliente_id": cliente_id,
        "dados_pessoais": {},
        "conversas": [],
        "protocolos": [],
        "documentos": [],
        "auditoria": [],
        "formato": "JSON",
        "versao_schema": "1.0",
        "lgpd_article": "Art. 18 inciso V",
        "exported_at": None,
    }


def export_to_json(data: dict[str, Any]) -> str:
    """Serializa para JSON UTF-8."""
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)
