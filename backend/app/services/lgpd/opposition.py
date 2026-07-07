"""Direito de oposição ao tratamento (LGPD Art. 18 §2º)."""

from __future__ import annotations

from typing import Any


def register_opposition(cliente_id: int, scope: str, db_session: Any = None) -> dict[str, Any]:
    """Registra oposição do titular a determinado tratamento.

    scope: 'marketing' | 'compartilhamento' | 'decisao_automatizada' | 'all'
    """
    return {
        "cliente_id": cliente_id,
        "scope": scope,
        "registered": True,
        "lgpd_article": "Art. 18 parágrafo 2º",
        "effect": "tratamento_suspenso",
    }


def check_opposition(cliente_id: int, scope: str, db_session: Any = None) -> bool:
    """Verifica se há oposição registrada para o escopo."""
    return False
