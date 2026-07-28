"""Regression: valores oficiais Portaria CGJ/TJMG 8.664/2025 (campanha 2026-07-28).

P0 encontrado em prod: `cartorio_calcular_emolumento` servia tabela PLACEHOLDER
com valores inflados (autenticacao 28.90 vs oficial 11.21; procuracao 156.40
vs oficial 68.94) com selo "TABELA_2026_MG" — resposta financeira errada para
clientes reais. Estes testes FALHAM se os valores oficiais regredirem.

Fonte: backend/data/fontes/cpo86642025.pdf (SHA-256 84781a02...3417).
Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.emolumento import EMOLUMENTOS_2026, calcular


class TestTabelaOficial2026:
    """Valores 'Valor Final ao Usuario' transcritos da Tabela 1 (Notas)."""

    @pytest.mark.parametrize(
        "tipo,oficial",
        [
            ("autenticacao", "11.21"),  # item 3 (por folha)
            ("reconhecimento_firma", "11.21"),  # item 5.a
            ("procuracao", "68.94"),  # item 4.f.1 (generica)
        ],
    )
    def test_base_oficial(self, tipo: str, oficial: str) -> None:
        assert EMOLUMENTOS_2026[tipo] == Decimal(oficial)
        r = calcular(tipo)
        assert r.base == Decimal(oficial)
        assert r.total == Decimal(oficial)

    def test_placeholder_errado_nunca_mais(self) -> None:
        """Os valores placeholder inflados NAO podem voltar."""
        assert EMOLUMENTOS_2026["autenticacao"] != Decimal("28.90")
        assert EMOLUMENTOS_2026["procuracao"] != Decimal("156.40")
        assert EMOLUMENTOS_2026["reconhecimento_firma"] != Decimal("32.10")


class TestMcpToolFonteAutoritativa:
    """cartorio_calcular_emolumento delega para emolumento_real_djalma."""

    @pytest.mark.asyncio
    async def test_procuracao_published_valor_oficial(self) -> None:
        from mcp_server import cartorio_calcular_emolumento

        r = await cartorio_calcular_emolumento("procuracao")
        assert r["status"] == "PUBLISHED"
        assert r["total"] == "68.94"
        assert r["item_portaria"] == "Tabela 1, item 4.f.1"
        assert r["tabela_referencia"] == "PORTARIA_CGJ_TJMG_8664_2025_TABELA_1"

    @pytest.mark.asyncio
    async def test_autenticacao_published_valor_oficial(self) -> None:
        from mcp_server import cartorio_calcular_emolumento

        r = await cartorio_calcular_emolumento("autenticacao")
        assert r["status"] == "PUBLISHED"
        assert r["total"] == "11.21"

    @pytest.mark.asyncio
    async def test_slug_oficial_direto(self) -> None:
        from mcp_server import cartorio_calcular_emolumento

        r = await cartorio_calcular_emolumento("testamento")
        assert r["status"] == "PUBLISHED"
        assert r["total"] == "437.24"

    @pytest.mark.asyncio
    async def test_urgencia_hitl_nunca_infere_preco(self) -> None:
        """Urgencia nao tem acrescimo publicado -> HITL, nunca 50% inventado."""
        from mcp_server import cartorio_calcular_emolumento

        r = await cartorio_calcular_emolumento("procuracao", urgencia=True)
        assert r["status"] == "HITL_REQUIRED"
        assert r["total"] is None
        assert r["motivo_hitl"]

    @pytest.mark.asyncio
    async def test_folhas_adicionais_hitl(self) -> None:
        from mcp_server import cartorio_calcular_emolumento

        r = await cartorio_calcular_emolumento("autenticacao", folhas=3)
        assert r["status"] == "HITL_REQUIRED"
        assert r["total"] is None

    @pytest.mark.asyncio
    async def test_ato_desconhecido_hitl(self) -> None:
        """Ato fora da Tabela 1 (ex.: certidao de registro civil) -> HITL."""
        from mcp_server import cartorio_calcular_emolumento

        r = await cartorio_calcular_emolumento("certidao_casamento")
        assert r["status"] == "HITL_REQUIRED"
        assert r["total"] is None
