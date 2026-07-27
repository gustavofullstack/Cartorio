"""Fase 3 — Telemetria de uso da IA: agregacao read-only de custo do LiteLLM.

Le o Postgres do proxy LiteLLM (tabela `"LiteLLM_SpendLogs"`) e agrega custo,
chamadas e tokens por modelo e por dia. Nenhum endpoint HTTP nesta fase —
o painel da Fase 4 consome este service diretamente.

LGPD / seguranca:
- SELECT SOMENTE de colunas agregadas (model, spend, tokens, data).
  NUNCA api_key, user, metadata, prompt/response (dados sensiveis).
- Erros de conexao/tabela inexistente NUNCA vazam exception: retornam
  `{"disponivel": False, "motivo": ...}` com motivo sanitizado (apenas o
  tipo do erro, sem DSN/credencial na mensagem).
- Engine criada lazy a partir de `settings.litellm_spend_database_url`;
  None = telemetria desabilitada.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine, create_engine

MOTIVO_NAO_CONFIGURADA = "LITELLM_SPEND_DATABASE_URL não configurada"

# Engine singleton lazy (1 por processo; pool minimo — leitura esporadica).
_engine: Engine | None = None


def _indisponivel(motivo: str) -> dict[str, Any]:
    """Payload canonico de indisponibilidade (sem exception, sem stack)."""
    return {"disponivel": False, "motivo": motivo}


def _get_engine() -> Engine | None:
    """Retorna a engine lazy do DB de spend, ou None se nao configurada."""
    global _engine
    if _engine is not None:
        return _engine
    from app.config import settings

    url = settings.litellm_spend_database_url
    if not url:
        return None
    _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def fechar_engine() -> None:
    """Descarta a engine cached (testes, rotacao de credencial, shutdown)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def _float(value: Any) -> float:
    """Coerce Decimal/None para float (JSON-serializavel)."""
    return float(value) if value is not None else 0.0


def _int(value: Any) -> int:
    """Coerce None para int (SUM/COUNT podem vir None em tabela vazia)."""
    return int(value) if value is not None else 0


def uso_agregado(dias: int = 30) -> dict[str, Any]:
    """Agrega custo/uso do LiteLLM na janela dos ultimos `dias` dias.

    Args:
        dias: janela de agregacao (default 30). Valores <= 0 caem no default.

    Returns:
        - Indisponivel: `{"disponivel": False, "motivo": str}` quando a URL
          nao esta configurada, a tabela nao existe ou a conexao falha.
        - Disponivel: `{"disponivel": True, "dias": int, "resumo": {...},
          "por_modelo": [...], "por_dia": [...]}` — somente colunas
          agregadas (modelo, gasto, chamadas, tokens, data).
    """
    if dias <= 0:
        dias = 30

    engine = _get_engine()
    if engine is None:
        return _indisponivel(MOTIVO_NAO_CONFIGURADA)

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=dias)

    # LGPD: SELECT apenas de colunas agregadas. NUNCA api_key/user/metadata.
    sql_resumo = text(
        "SELECT COALESCE(SUM(spend), 0) AS gasto_total, COUNT(*) AS chamadas, "
        "COALESCE(SUM(prompt_tokens), 0) AS tokens_prompt, "
        "COALESCE(SUM(completion_tokens), 0) AS tokens_completion "
        'FROM "LiteLLM_SpendLogs" WHERE "startTime" >= :cutoff'
    )
    sql_por_modelo = text(
        "SELECT model AS modelo, COALESCE(SUM(spend), 0) AS gasto, COUNT(*) AS chamadas, "
        "COALESCE(SUM(prompt_tokens), 0) AS tokens_prompt, "
        "COALESCE(SUM(completion_tokens), 0) AS tokens_completion "
        'FROM "LiteLLM_SpendLogs" WHERE "startTime" >= :cutoff '
        "GROUP BY model ORDER BY gasto DESC"
    )
    sql_por_dia = text(
        'SELECT date("startTime") AS dia, COALESCE(SUM(spend), 0) AS gasto, '
        "COUNT(*) AS chamadas, "
        "COALESCE(SUM(prompt_tokens), 0) AS tokens_prompt, "
        "COALESCE(SUM(completion_tokens), 0) AS tokens_completion "
        'FROM "LiteLLM_SpendLogs" WHERE "startTime" >= :cutoff '
        'GROUP BY date("startTime") ORDER BY dia'
    )

    try:
        with engine.connect() as conn:
            resumo_row = conn.execute(sql_resumo, {"cutoff": cutoff}).one()
            por_modelo_rows = conn.execute(sql_por_modelo, {"cutoff": cutoff}).all()
            por_dia_rows = conn.execute(sql_por_dia, {"cutoff": cutoff}).all()
    except Exception as exc:
        # Sanitiza: apenas o TIPO do erro (nunca str(exc), que pode embutir
        # DSN/credencial). Tabela inexistente cai aqui tambem.
        return _indisponivel(f"erro ao consultar LiteLLM_SpendLogs: {type(exc).__name__}")

    return {
        "disponivel": True,
        "dias": dias,
        "resumo": {
            "gasto_total_usd": _float(resumo_row.gasto_total),
            "chamadas_total": _int(resumo_row.chamadas),
            "tokens_prompt": _int(resumo_row.tokens_prompt),
            "tokens_completion": _int(resumo_row.tokens_completion),
        },
        "por_modelo": [
            {
                "modelo": str(row.modelo) if row.modelo is not None else "desconhecido",
                "gasto_usd": _float(row.gasto),
                "chamadas": _int(row.chamadas),
                "tokens_prompt": _int(row.tokens_prompt),
                "tokens_completion": _int(row.tokens_completion),
            }
            for row in por_modelo_rows
        ],
        "por_dia": [
            {
                "data": str(row.dia),
                "gasto_usd": _float(row.gasto),
                "chamadas": _int(row.chamadas),
                "tokens_prompt": _int(row.tokens_prompt),
                "tokens_completion": _int(row.tokens_completion),
            }
            for row in por_dia_rows
        ],
    }
