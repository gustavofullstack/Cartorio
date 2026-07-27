"""Testes da Fase 3 — Telemetria de uso da IA (ia_usage + counter MCP).

Cobre:
- URL nao configurada -> indisponivel (sem exception)
- Agregacoes corretas sobre SQLite em memoria com tabela LiteLLM_SpendLogs fake
- Tabela ausente -> indisponivel (sem exception vazando)
- Decorator contabilizar_tool incrementa cartorio_mcp_tool_calls_total
"""

import asyncio
import datetime
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.services import ia_usage
from app.services.metrics import store


@pytest.fixture(autouse=True)
def _reset_engine() -> Iterator[None]:
    """Garante engine do ia_usage limpa antes/depois de cada teste."""
    ia_usage.fechar_engine()
    yield
    ia_usage.fechar_engine()


@pytest.fixture()
def engine_sqlite() -> Iterator[Engine]:
    """SQLite em memoria com uma tabela LiteLLM_SpendLogs fake populada."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    agora = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    ontem = agora - datetime.timedelta(days=1)
    antigo = agora - datetime.timedelta(days=60)
    with engine.begin() as conn:
        conn.execute(
            text(
                'CREATE TABLE "LiteLLM_SpendLogs" ('
                "request_id TEXT, model TEXT, spend REAL, "
                "prompt_tokens INTEGER, completion_tokens INTEGER, "
                '"startTime" TIMESTAMP, api_key TEXT)'
            )
        )
        rows = [
            ("r1", "gpt-a", 0.50, 100, 50, agora, "sk-fake-1"),
            ("r2", "gpt-a", 0.25, 200, 100, agora, "sk-fake-2"),
            ("r3", "gpt-b", 1.00, 10, 5, ontem, "sk-fake-3"),
            # Fora da janela de 30 dias — nao pode entrar nas agregacoes.
            ("r4", "gpt-old", 9.99, 999, 999, antigo, "sk-fake-4"),
        ]
        conn.execute(
            text(
                'INSERT INTO "LiteLLM_SpendLogs" '
                "(request_id, model, spend, prompt_tokens, completion_tokens, "
                '"startTime", api_key) '
                "VALUES (:rid, :model, :spend, :pt, :ct, :st, :ak)"
            ),
            [
                {"rid": r, "model": m, "spend": s, "pt": p, "ct": c, "st": t, "ak": a}
                for r, m, s, p, c, t, a in rows
            ],
        )
    yield engine
    engine.dispose()


def test_sem_url_configurada_retorna_indisponivel(monkeypatch: pytest.MonkeyPatch) -> None:
    """LITELLM_SPEND_DATABASE_URL=None -> indisponivel com motivo canonico."""
    monkeypatch.setattr(settings, "litellm_spend_database_url", None)
    result = ia_usage.uso_agregado()
    assert result["disponivel"] is False
    assert result["motivo"] == ia_usage.MOTIVO_NAO_CONFIGURADA


def test_uso_agregado_somas_corretas(
    monkeypatch: pytest.MonkeyPatch, engine_sqlite: Engine
) -> None:
    """Agregacoes por modelo/dia corretas na janela de 30 dias."""
    monkeypatch.setattr(ia_usage, "_get_engine", lambda: engine_sqlite)
    result = ia_usage.uso_agregado(dias=30)

    assert result["disponivel"] is True
    assert result["dias"] == 30

    resumo = result["resumo"]
    assert resumo["gasto_total_usd"] == pytest.approx(1.75)
    assert resumo["chamadas_total"] == 3
    assert resumo["tokens_prompt"] == 310
    assert resumo["tokens_completion"] == 155

    por_modelo = {row["modelo"]: row for row in result["por_modelo"]}
    assert set(por_modelo) == {"gpt-a", "gpt-b"}  # gpt-old fora da janela
    assert por_modelo["gpt-a"]["gasto_usd"] == pytest.approx(0.75)
    assert por_modelo["gpt-a"]["chamadas"] == 2
    assert por_modelo["gpt-a"]["tokens_prompt"] == 300
    assert por_modelo["gpt-b"]["gasto_usd"] == pytest.approx(1.00)

    por_dia = result["por_dia"]
    assert len(por_dia) == 2
    assert sum(row["chamadas"] for row in por_dia) == 3
    assert sum(row["gasto_usd"] for row in por_dia) == pytest.approx(1.75)


def test_uso_agregado_nunca_seleciona_colunas_sensiveis(
    monkeypatch: pytest.MonkeyPatch, engine_sqlite: Engine
) -> None:
    """LGPD: o resultado nunca carrega api_key/request_id (so agregados)."""
    monkeypatch.setattr(ia_usage, "_get_engine", lambda: engine_sqlite)
    result = ia_usage.uso_agregado(dias=30)
    payload = str(result)
    assert "sk-fake" not in payload
    assert "api_key" not in payload
    assert "request_id" not in payload


def test_tabela_ausente_retorna_indisponivel_sem_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tabela LiteLLM_SpendLogs inexistente -> indisponivel, sem vazar erro."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(ia_usage, "_get_engine", lambda: engine)
    result = ia_usage.uso_agregado(dias=30)
    assert result["disponivel"] is False
    assert "erro ao consultar" in result["motivo"]
    engine.dispose()


def test_fechar_engine_reseta_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """fechar_engine descarta a engine cached (rotacao de credencial/testes)."""
    monkeypatch.setattr(settings, "litellm_spend_database_url", "sqlite://")
    engine = ia_usage._get_engine()
    assert engine is not None
    ia_usage.fechar_engine()
    assert ia_usage._engine is None


def test_contabilizar_tool_incrementa_counter() -> None:
    """Decorator MCP incrementa cartorio_mcp_tool_calls_total{tool} e aparece no export."""
    import mcp_server

    tool = "tool_teste_fase3"
    antes = store.counters.get("cartorio_mcp_tool_calls_total", {}).get(f"tool={tool}", 0)

    @mcp_server.contabilizar_tool(tool)
    async def _fake_tool() -> dict:
        return {"ok": True}

    result = asyncio.run(_fake_tool())
    assert result == {"ok": True}

    depois = store.counters["cartorio_mcp_tool_calls_total"][f"tool={tool}"]
    assert depois == antes + 1
    assert f'cartorio_mcp_tool_calls_total{{tool="{tool}"}}' in store.render_prometheus()


def test_tool_real_decorada_contabiliza() -> None:
    """cartorio_saudacao (tool real) roda via FastMCP+wraps e contabiliza."""
    import mcp_server

    tool = "cartorio_saudacao"
    antes = store.counters.get("cartorio_mcp_tool_calls_total", {}).get(f"tool={tool}", 0)
    result = asyncio.run(mcp_server.cartorio_saudacao())
    assert result["api_status"] == 200
    depois = store.counters["cartorio_mcp_tool_calls_total"][f"tool={tool}"]
    assert depois == antes + 1
