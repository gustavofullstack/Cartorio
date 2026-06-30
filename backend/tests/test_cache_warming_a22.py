"""Testes A22 — Cache warming cron 06:00 BRT."""

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock, patch

from app.services.cache_warming import FOLHAS_TIPICAS, TIPOS_PRINCIPAIS, warm_emolumento_cache


def test_tipos_principais_contem_escritura_e_certidao() -> None:
    """Lista de tipos principais inclui os 3 mais usados."""
    assert "escritura_compra_venda" in TIPOS_PRINCIPAIS
    assert "certidao_negativa" in TIPOS_PRINCIPAIS
    assert "procuracao" in TIPOS_PRINCIPAIS


def test_folhas_tipicas_cobrem_faixa_real() -> None:
    """Folhas tipicas cobrem 1 a 10 (90% dos casos reais)."""
    assert min(FOLHAS_TIPICAS) == 1
    assert max(FOLHAS_TIPICAS) == 10
    assert len(FOLHAS_TIPICAS) >= 3


def test_warm_emolumento_cache_com_mock() -> None:
    """warm roda todos tipos*folhas com funcao mockada que retorna dataclass-like."""

    @dataclasses.dataclass
    class FakeCalculo:
        tipo: str = "x"
        folhas: int = 1
        urgencia: bool = False
        base: float = 0.0
        adicional_folhas: float = 0.0
        adicional_urgencia: float = 0.0
        total: float = 0.0
        tabela_referencia: str = "TABELA_2026_MG"
        valido_ate: str = "2026-12-31"

    mock_func = MagicMock(return_value=FakeCalculo())
    with patch("app.services.emolumento_cache.set_cached") as mock_set:
        result = warm_emolumento_cache(emolumento_func=mock_func)
    # 8 tipos * 4 folhas = 32
    assert result["cached"] == len(TIPOS_PRINCIPAIS) * len(FOLHAS_TIPICAS)
    assert result["errors"] == 0
    assert mock_func.call_count == len(TIPOS_PRINCIPAIS) * len(FOLHAS_TIPICAS)
    assert mock_set.call_count == len(TIPOS_PRINCIPAIS) * len(FOLHAS_TIPICAS)


def test_warm_emolumento_cache_com_erros() -> None:
    """warm continua mesmo se algumas chamadas falham."""

    def fake_calc(tipo, *, folhas=1, urgencia=False):
        if folhas == 2:
            raise RuntimeError("simulado")
        return {"valor_total": 108.0}

    with patch("app.services.emolumento_cache.set_cached"):
        result = warm_emolumento_cache(emolumento_func=fake_calc)
    # 8 tipos * 1 erro cada (folhas=2) = 8 errors
    assert result["errors"] == 8
    # 8*4 - 8 = 24 sucessos
    assert result["cached"] == (len(TIPOS_PRINCIPAIS) * len(FOLHAS_TIPICAS)) - 8


def test_warm_retorna_duracao_ms() -> None:
    """Result inclui duracao_ms (sempre presente)."""
    result = warm_emolumento_cache(emolumento_func=MagicMock(return_value={}))
    assert "duration_ms" in result
    assert result["duration_ms"] >= 0
